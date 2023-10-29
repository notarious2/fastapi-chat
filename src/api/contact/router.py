from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.contact.schemas import GetUsersResponseSchema
from src.api.contact.services import get_all_users
from src.database import get_async_session
from src.dependencies import get_current_user
from src.models import User

contact_router = APIRouter(tags=["Contact Management"])


@contact_router.get("/users/", summary="Get all users", response_model=list[GetUsersResponseSchema])
async def get_contacts_view(
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    users: User = await get_all_users(db_session, current_user=current_user)

    return users
