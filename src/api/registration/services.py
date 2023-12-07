import os
from tempfile import NamedTemporaryFile

# import aiofiles
import boto3
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.registration.schemas import UserRegisterSchema

# from src.config import settings
from src.models import User
from src.utils import get_hashed_password

aws_session = boto3.Session(aws_access_key_id="", aws_secret_access_key="")
s3_resource = aws_session.resource("s3")


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
    # Ensure that directory exists
    # folder_path = "src/static/images/profile/"
    # os.makedirs(folder_path, exist_ok=True)
    print("HERE 1")
    if uploaded_image := user_schema.uploaded_image:
        temp = NamedTemporaryFile(delete=False)
        try:
            try:
                contents = uploaded_image.file.read()
                with temp as f:
                    f.write(contents)
            except Exception:
                print("EXCEPTION RAISED")
                raise HTTPException(status_code=500, detail="Error on uploading the file")
            finally:
                uploaded_image.file.close()
                print("HERE 2")

            # Upload the file to your S3 service using `temp.name`
            s3_resource.meta.client.upload_file(temp.name, "myfastapichatbucket", "myfile.jpg")

        except Exception as e:
            print("HERE 3", e)
            raise HTTPException(status_code=500, detail="Something went wrong")
        finally:
            # temp.close()  # the `with` statement above takes care of closing the file
            try:
                os.remove(temp.name)  # Delete temp file
                print("HERE 4")
            except Exception as e:
                print("ERROR", e)

        print("CONTENT", contents)

    # if uploaded_image := user_schema.uploaded_image:
    #     file_extension = uploaded_image.filename.split(".")[-1]
    #     file_path = f"{folder_path}{user_schema.username}.{file_extension}"
    #     # load image in chunks
    #     async with aiofiles.open(file_path, "wb") as f:
    #         while chunk := await uploaded_image.read(DEFAULT_CHUNK_SIZE):
    #             await f.write(chunk)

    #     new_user.user_image = file_path.replace("src/", "/")

    # if uploaded_image := user_schema.uploaded_image:
    #     folder_path = "src/static/images/profile/"
    #     file_extension = uploaded_image.filename.split(".")[-1]
    #     file_path = f"{folder_path}{user_schema.username}.{file_extension}"
    #     s3.meta.client.upload_file(Filename=file_path, Bucket='myfastapichatbucket', Key='s3_output_key')

    db_session.add(new_user)

    await db_session.commit()
