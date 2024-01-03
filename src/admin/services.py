import asyncio
from contextlib import contextmanager

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.admin.models import AdminUser
from src.config import settings
from src.database import get_async_session
from src.utils import verify_password


# Authenticate admin based on username/email and password
async def authenticate_admin_user(db_session: AsyncSession, login_identifier: str, password: str) -> AdminUser | None:
    # Introduce a small delay to mitigate user enumeration attacks
    await asyncio.sleep(0.1)

    query = select(AdminUser).where(or_(AdminUser.email == login_identifier, AdminUser.username == login_identifier))
    result = await db_session.execute(query)
    admin: AdminUser | None = result.scalar_one_or_none()

    if not admin or admin.is_deleted:
        return None

    # if admin is found check password
    if not verify_password(plain_password=password, hashed_password=admin.password):
        return None

    return admin


@contextmanager
def clear_session_on_exception(request):
    try:
        yield
    except (jwt.PyJWTError, HTTPException) as e:
        request.session.clear()
        raise e


async def verify_admin_user_by_token(
    token: str,
    request: Request,
    db_session: AsyncSession = Depends(get_async_session),
) -> None:
    with clear_session_on_exception(request):
        try:
            payload = jwt.decode(token, settings.JWT_ACCESS_SECRET_KEY, algorithms=[settings.ENCRYPTION_ALGORITHM])
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

        statement = select(AdminUser).where(
            or_(AdminUser.email == login_identifier, AdminUser.username == login_identifier)
        )
        result = await db_session.execute(statement)
        admin: AdminUser | None = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if admin.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin is not active",
                headers={"WWW-Authenticate": "Bearer"},
            )
