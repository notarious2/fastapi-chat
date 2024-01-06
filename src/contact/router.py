import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.contact.schemas import GetUsersResponseSchema
from src.contact.services import get_all_users
from src.database import get_async_session
from src.dependencies import get_cache, get_cache_setting, get_current_user
from src.models import User

logger = logging.getLogger(__name__)

contact_router = APIRouter(tags=["Contact Management"])


@contact_router.get("/users/", summary="Get all users")
async def get_contacts_view(
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
    cache_enabled: bool = Depends(get_cache_setting),
):
    cache_key = f"{current_user.guid}_all_users"

    if cache_enabled:
        # return cached users list if key exists
        if cached_all_users := await cache.get(cache_key):
            logging.info("Cache: Users")
            return json.loads(cached_all_users)

    users: list[User] = await get_all_users(db_session, current_user=current_user)

    response = GetUsersResponseSchema.model_validate(users, from_attributes=True)

    if cache_enabled:
        await cache.set(cache_key, response.model_dump_json(), ex=settings.REDIS_CACHE_EXPIRATION_SECONDS)

    return response
