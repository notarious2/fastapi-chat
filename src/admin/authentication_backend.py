from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from src.admin.models import AdminUser
from src.admin.services import authenticate_admin_user, verify_admin_user_by_token
from src.authentication.utils import create_access_token
from src.config import settings
from src.database import async_session_maker

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        login_identifier, password = form["username"], form["password"]

        # Validate username/password credentials
        async with async_session_maker() as db_session:
            admin: AdminUser | None = await authenticate_admin_user(
                db_session=db_session, login_identifier=login_identifier, password=password
            )

        if not admin:
            raise HTTPException(status_code=401, detail="Invalid Credentials")

        access_token = create_access_token(
            subject=login_identifier, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        request.session.update({"token": f"{access_token}"})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")

        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        # Check the token
        async with async_session_maker() as db_session:
            await verify_admin_user_by_token(token=token, db_session=db_session, request=request)

        return True


authentication_backend = AdminAuth(secret_key=settings.ADMIN_SECRET_KEY)
