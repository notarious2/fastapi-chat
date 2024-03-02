import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_cache
from src.models import User
from src.registration.schemas import UserRegisterSchema
from src.registration.services import ImageSaver, create_user, get_user_by_email_or_username
from src.utils import clear_cache_for_all_users

account_router = APIRouter(tags=["Account Management"])

# user data and image in one endpoint
# https://github.com/tiangolo/fastapi/issues/2257
# https://stackoverflow.com/questions/60127234/how-to-use-a-pydantic-model-with-form-data-in-fastapi


@account_router.post("/register/", summary="Register user")
async def register_user(
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
    cache: aioredis.Redis = Depends(get_cache),
    user_schema: UserRegisterSchema = Depends(UserRegisterSchema),
):
    # check if user with username or email already exists
    if await get_user_by_email_or_username(db_session, email=user_schema.email, username=user_schema.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User with provided credentials already exists"
        )

    try:
        user: User = await create_user(db_session, user_schema=user_schema)
        # background_task is executed after the response is sent to the client.
        # this allows to save an image without affecting the user experience.
        if uploaded_image := user_schema.uploaded_image:
            image_saver = ImageSaver(db_session, user=user)
            background_tasks.add_task(image_saver.save_user_image, user, uploaded_image)

    except Exception as excinfo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{excinfo}")
    else:
        # clear cache for all users
        await clear_cache_for_all_users(cache)
        return "User has been successfully created"
