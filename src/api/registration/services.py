import aiofiles
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.registration.schemas import UserRegisterSchema
from src.models import User
from src.utils import get_hashed_password

DEFAULT_CHUNK_SIZE = 1024 * 1024 * 1  # 1 megabyte


async def get_user_by_email_or_username(db_session: AsyncSession, *, email: str, username: str):
    query = select(User).where(or_(User.email == email, User.username == username))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()
    return user


async def create_user(db_session: AsyncSession, user_schema: UserRegisterSchema):
    hashed_password = get_hashed_password(user_schema.password)
    new_user = User(
        username=user_schema.username,
        email=user_schema.email,
        first_name=user_schema.first_name,
        last_name=user_schema.last_name,
        password=hashed_password,
    )
    if uploaded_image := user_schema.uploaded_image:
        file_extension = uploaded_image.filename.split(".")[-1]
        file_path = f"/static/images/profile/{user_schema.username}.{file_extension}"

        async with aiofiles.open("src" + file_path, "wb") as f:
            while chunk := await uploaded_image.read(DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

        new_user.user_image = file_path

    db_session.add(new_user)

    await db_session.commit()
