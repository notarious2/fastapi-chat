import logging

from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models import User
from src.settings.schemas import UserThemeSchema
from src.settings.services import set_user_theme

settings_router = APIRouter(tags=["Settings Management"])

logger = logging.getLogger(__name__)


@settings_router.post(
    "/user/settings/theme/", dependencies=[Depends(RateLimiter(times=10, minutes=1))], summary="Set user theme"
)
async def set_user_theme_view(
    user_theme_schema: UserThemeSchema,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    await set_user_theme(db_session, user=current_user, theme=user_theme_schema.theme)

    return {"message": "New theme has been set"}
