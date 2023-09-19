from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.registration.schemas import UserRegisterSchema
from src.api.registration.services import create_user, get_user_by_email_or_username
from src.database import get_async_session

account_router = APIRouter(tags=["Account Management"])


@account_router.post("/register/", summary="Register user")
async def register_user(user_schema: UserRegisterSchema, db_session: AsyncSession = Depends(get_async_session)):
    # check if user with username or email already exists
    user = await get_user_by_email_or_username(db_session, email=user_schema.email, username=user_schema.username)

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User with provided credentials already exists"
        )

    try:
        await create_user(db_session, user_schema=user_schema)
    except Exception as excinfo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{excinfo}")
    else:
        return "User has been successfully created"