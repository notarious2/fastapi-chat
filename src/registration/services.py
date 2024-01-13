import logging
import os
from io import BytesIO

import aiofiles
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import User
from src.registration.schemas import UserRegisterSchema
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
        username=user_schema.username.lower(),
        email=user_schema.email.lower(),
        first_name=user_schema.first_name,
        last_name=user_schema.last_name,
        password=hashed_password,
    )

    db_session.add(new_user)
    await db_session.commit()

    return new_user


class ImageSaver:
    def __init__(self, db_session: AsyncSession, *, user: User):
        self.db_session: AsyncSession = db_session
        self.user: User = user

    async def save_user_image(self, user: User, uploaded_image: UploadFile) -> str | None:
        file_extension: str = uploaded_image.filename.split(".")[-1].lower()
        filename: str = f"{user.username}.{file_extension}"

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
        Handles the logic for saving user images to a static folder in a development environment.
        Saves user image to the static folder 'static/images/profile'.
        Returns the URL address where the image is saved.

        Parameters:
            - user (User): User object associated with the image.
            - uploaded_image (UploadFile): The image file uploaded.
            - filename (str): The desired filename for the saved image.

        Returns:
            - str: URL address where the image is saved.
        """
        # Ensure that the directory exists
        folder_path = "src/static/images/profile"
        os.makedirs(folder_path, exist_ok=True)

        # Create a temporary file path for saving the uploaded image
        file_path = f"{folder_path}/{filename}_temporary"

        # Load the image in chunks and save it to disk
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await uploaded_image.read(DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

        # Resize the saved image to 600x600
        resized_image: Image = self._resize_image(file_path)

        # Save the resized image with a modified file path
        resized_image_file_path = file_path.replace("_temporary", "")
        resized_image.save(resized_image_file_path, resized_image.format)

        # Remove the original uploaded image
        os.remove(file_path)

        # Form the URL address for the saved image
        image_url = resized_image_file_path.replace("src/", "/")

        # Update user information with the image URL and commit to the database
        user.user_image = image_url
        await self.db_session.commit()

        return image_url

    async def _save_image_to_aws_bucket(self, user: User, uploaded_image: UploadFile, filename: str) -> str | None:
        """
        Handles the logic for uploading user images to an AWS S3 bucket in a production environment.
        Returns URL address where image is saved.

        Parameters:
            - user (User): User object associated with the image.
            - uploaded_image (UploadFile): The image file uploaded
            - filename (str): The desired filename for the saved image.

        Returns:
            - str | None: URL address where the image is saved, or None if upload fails.
        """
        # Check if AWS client and bucket information are available
        if (
            (aws_client := settings.get_aws_client_for_image_upload(), aws_bucket := settings.AWS_IMAGES_BUCKET)
            and aws_client
            and aws_bucket
        ):
            # Read the content of the uploaded image
            image_file: bytes = await uploaded_image.read()

            # Resize the image using the _resize_image method
            resized_image: Image = self._resize_image(BytesIO(image_file))

            # Save the resized image to an in-memory file
            with BytesIO() as in_memory_image_file:
                resized_image.save(in_memory_image_file, format=resized_image.format)
                in_memory_image_file.seek(0)

                # Upload the resized image to AWS S3 bucket
                aws_client.upload_fileobj(
                    in_memory_image_file, aws_bucket, filename, ExtraArgs={"ContentType": "image/jpeg"}
                )

            # Form the URL address for the saved image
            image_url: str = f"https://{aws_bucket}.s3.amazonaws.com/{filename}"

            # Update user information with the image URL and commit to the database
            user.user_image = image_url
            await self.db_session.commit()

            return image_url

        else:
            logger.error(f"AWS client or bucket information is missing when registering: {user.username}")
            return None

    def _resize_image(self, file_path, width=600, height=600) -> Image:
        image = Image.open(file_path)
        image_format: str | None = image.format
        resized_image: Image = image.resize((width, height), Image.LANCZOS)
        resized_image.format = image_format

        return resized_image
