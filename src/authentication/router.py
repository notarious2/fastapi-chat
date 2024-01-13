import logging
from datetime import datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.schemas import GoogleLoginSchema, UserLoginResponseSchema
from src.authentication.services import (
    authenticate_user,
    create_user_from_google_credentials,
    get_user_by_email,
    get_user_by_login_identifier,
    update_user_last_login,
    verify_google_token,
)
from src.authentication.utils import create_access_token, create_refresh_token
from src.config import settings
from src.database import get_async_session
from src.dependencies import get_current_user
from src.models import User

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post(
    "/google-login/",
    dependencies=[
        Depends(RateLimiter(times=50, hours=24)),  # keep lower of result on top
        Depends(RateLimiter(times=10, minutes=1)),
    ],
    summary="Login with Google oauth2",
)
async def login_with_google(
    response: Response,
    google_login_schema: GoogleLoginSchema,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
):
    google_access_token: str = google_login_schema.access_token
    user_info: dict[str, str] | None = await verify_google_token(google_access_token)

    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not verify Google credentials")

    # email field is case insensitive, db holds only lower case representation
    email: str = user_info.get("email", "").lower()
    if not email:
        HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email was not provided")

    if not (user := await get_user_by_email(db_session, email=email)):
        user: User = await create_user_from_google_credentials(db_session, **user_info)

    else:
        # update last login for existing user
        background_tasks.add_task(update_user_last_login, db_session, user=user)

    access_token: str = create_access_token(email)
    refresh_token: str = create_refresh_token(email)

    # Send access and refresh tokens in HTTP only cookies
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="none", secure=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="none", secure=True)

    login_response = UserLoginResponseSchema.model_validate(user)
    return login_response


@auth_router.post(
    "/login/",
    dependencies=[
        Depends(RateLimiter(times=50, hours=24)),  # keep lower of result on top
        Depends(RateLimiter(times=10, minutes=1)),
    ],
    summary="Create access and refresh tokens for a user",
)
async def login(
    response: Response,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    login_identifier, password = form_data.username.lower(), form_data.password
    user: User | None = await authenticate_user(
        db_session=db_session, login_identifier=login_identifier, password=password
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email/username or password")

    # create token based on login identifier instead of static username/email
    access_token: str = create_access_token(login_identifier)
    refresh_token: str = create_refresh_token(login_identifier)

    logger.debug(f"Access token: {access_token}")

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="none", secure=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="none", secure=True)

    # update last login date
    background_tasks.add_task(update_user_last_login, db_session, user=user)

    login_response = UserLoginResponseSchema.model_validate(user)
    return login_response


@auth_router.post("/refresh/", summary="Create new access token for user")
async def get_new_access_token_from_refresh_token(
    refresh_token: Annotated[str, Cookie()],
    response: Response,
    db_session: AsyncSession = Depends(get_async_session),
):
    try:
        payload = jwt.decode(refresh_token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.ENCRYPTION_ALGORITHM])
        login_identifier: str = payload.get("sub")
        if not login_identifier:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Access Token")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = await get_user_by_login_identifier(db_session, login_identifier=login_identifier)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token(
        login_identifier, expires_delta=timedelta(minutes=settings.NEW_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response.set_cookie(key="access_token", value=new_access_token, httponly=True, samesite="none", secure=True)

    return "Access token has been successfully refreshed"


@auth_router.get("/logout/", summary="Logout by removing http-only cookies")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    expires = datetime.utcnow() + timedelta(seconds=1)
    response.set_cookie(
        key="access_token",
        value="",
        secure=True,
        httponly=True,
        samesite="none",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        secure=True,
        httponly=True,
        samesite="none",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    # this doesn't work, must expire
    # response.delete_cookie("access_token")
    # response.delete_cookie("refresh_token")
    return "Cookies removed"
