import logging
import os

import aiofiles
from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.registration.schemas import UserRegisterSchema
from src.config import settings
from src.models import User
from src.utils import get_hashed_password

logger = logging.getLogger(__name__)


DEFAULT_CHUNK_SIZE = 1024 * 1024 * 1  # 1 megabyte


async def get_user_by_email_or_username(db_session: AsyncSession, *, email: str, username: str) -> User | None:
    query = select(User).where(or_(User.email == email, User.username == username))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()
    return user


async def create_user(db_session: AsyncSession, *, user_schema: UserRegisterSchema) -> User:
    hashed_password = get_hashed_password(user_schema.password)
    new_user = User(
        username=user_schema.username,
        email=user_schema.email,
        first_name=user_schema.first_name,
        last_name=user_schema.last_name,
        password=hashed_password,
    )

    db_session.add(new_user)
    await db_session.commit()

    return new_user


class ImageSaver:
    def __init__(self, db_session: AsyncSession, *, user: User):
        self.db_session = db_session
        self.user = user

    async def save_user_image(self, user: User, uploaded_image: UploadFile) -> str | None:
        file_extension = uploaded_image.filename.split(".")[-1].lower()
        filename = f"{user.username}.{file_extension}"

        match settings.ENVIRONMENT:
            case "development":
                return await self._save_image_to_static(user, uploaded_image, filename)
            case "production":
                return await self._save_image_to_aws_bucket(user, uploaded_image, filename)
            case _:
                logger.error(f"Unsupported environment: {settings.ENVIRONMENT}")
                return None

    async def _save_image_to_static(self, user: User, uploaded_image: UploadFile, filename: str) -> str:
        """
        used in development environment
        saves user image to static folder 'static/images/profile'
        returns url address where image is saved
        """
        # Ensure that directory exists
        folder_path = "src/static/images/profile"
        os.makedirs(folder_path, exist_ok=True)

        file_path = f"{folder_path}/{filename}"
        # load image in chunks
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await uploaded_image.read(DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

        image_url = file_path.replace("src/", "/")

        user.user_image = image_url
        await self.db_session.commit()

    async def _save_image_to_aws_bucket(self, user: User, uploaded_image: UploadFile, filename: str) -> str | None:
        """
        used in production environment
        saves user image to AWS bucket
        returns url address where image is saved
        """

        if (
            (aws_client := settings.get_aws_client_for_image_upload(), aws_bucket := settings.AWS_IMAGES_BUCKET)
            and aws_client
            and aws_bucket
        ):
            aws_client.upload_fileobj(
                uploaded_image.file, aws_bucket, filename, ExtraArgs={"ContentType": "image/jpeg"}
            )

            image_url = f"https://{aws_bucket}.s3.amazonaws.com/{filename}"

            user.user_image = image_url
            await self.db_session.commit()

        else:
            logger.error(f"Could not upload image for username: {user.username}")
