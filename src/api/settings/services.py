from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.api.settings.schemas import ThemeEnum
from src.models import User


async def set_user_theme(db_session: AsyncSession, *, user: User, theme: ThemeEnum) -> None:
    user.settings["theme"] = theme.value
    flag_modified(user, "settings")

    await db_session.commit()
