from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.authentication.services import authenticate_user
from src.api.authentication.utils import create_access_token, create_refresh_token
from src.database import get_async_session
from src.models import User

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post("/login/", summary="Create access and refresh tokens for a user")
async def login(
    response: Response,
    db_session: AsyncSession = Depends(get_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    login_identifier, password = form_data.username, form_data.password
    user: User | None = await authenticate_user(
        db_session=db_session, login_identifier=login_identifier, password=password
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email/username or password")

    # create token based on login identifier instead of static username/email
    access_token: str = create_access_token(login_identifier)
    refresh_token: str = create_refresh_token(login_identifier)

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="none", secure=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="none", secure=True)

    return {
        "access_token": create_access_token(login_identifier),
        "refresh_token": create_refresh_token(login_identifier),
    }
