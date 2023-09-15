import asyncio

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.utils import verify_password


# Authenticate user based on username/email and password
async def authenticate_user(db_session: AsyncSession, login_identifier: str, password: str) -> User | None:
    # Introduce a small delay to mitigate user enumeration attacks
    await asyncio.sleep(0.1)

    user = await get_user_by_login_identifier(db_session, login_identifier=login_identifier)
    if not user:
        return None

    # if user is found check password
    if not verify_password(plain_password=password, hashed_password=user.password):
        return None

    return user


async def get_user_by_login_identifier(db_session: AsyncSession, *, login_identifier: str) -> User | None:
    query = select(User).where(or_(User.email == login_identifier, User.username == login_identifier))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user
