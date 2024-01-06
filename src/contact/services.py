from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contact.schemas import GetUserSchema
from src.models import User


async def get_all_users(db_session: AsyncSession, *, current_user: User) -> list[GetUserSchema]:
    query = (
        select(User).where(
            and_(
                not_(User.id == current_user.id),
                User.is_deleted.is_(False),
            )
        )
    ).order_by(User.username)
    result = await db_session.execute(query)

    users: list[User] = result.scalars().all()

    return users
