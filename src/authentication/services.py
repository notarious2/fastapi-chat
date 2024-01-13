import asyncio
import secrets
import string

from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.utils import get_hashed_password, verify_password


# Authenticate user based on username/email and password
async def authenticate_user(db_session: AsyncSession, login_identifier: str, password: str) -> User | None:
    # Introduce a small delay to mitigate user enumeration attacks
    await asyncio.sleep(0.1)

    user: User | None = await get_user_by_login_identifier(db_session, login_identifier=login_identifier)

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


async def get_user_by_email(db_session: AsyncSession, *, email: str) -> User | None:
    query = select(User).where(and_(User.email == email, User.is_deleted.is_(False)))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user


async def create_user_from_google_credentials(db_session: AsyncSession, **kwargs) -> User:
    # generate random password for google user and hash it
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(20))
    hashed_password = get_hashed_password(password)

    user = User(
        username=kwargs.get("email"),  # Using Google email as username
        email=kwargs.get("email"),
        first_name=kwargs.get("given_name"),
        last_name=kwargs.get("family_name"),
        user_image=kwargs.get("picture"),
        password=hashed_password,
    )
    db_session.add(user)
    await db_session.commit()

    return user


# https://stackoverflow.com/questions/16501895/how-do-i-get-user-profile-using-google-access-token
# Verify the auth token received by client after google signin
async def verify_google_token(google_access_token: str) -> dict[str, str] | None:
    google_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={google_access_token}"

    async with AsyncClient() as client:
        response: Response = await client.get(google_url)
        if response.status_code == status.HTTP_200_OK:
            user_info: dict = response.json()
        else:
            return None

    # check that user_info contains email, given and family name
    if {"email", "given_name", "family_name"}.issubset(set(user_info)):
        return user_info

    return None


async def update_user_last_login(db_session: AsyncSession, *, user: User) -> None:
    user.last_login = func.now()
    await db_session.commit()
