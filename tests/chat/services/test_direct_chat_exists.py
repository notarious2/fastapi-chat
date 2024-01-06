from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.services import direct_chat_exists
from src.models import Chat, User


async def test_direct_chat_exists_returns_true_given_chat_exists(
    db_session: AsyncSession,
    bob_doug_chat: Chat,
    bob_emily_chat: Chat,
    bob_user: User,
    emily_user: User,
):
    assert await direct_chat_exists(db_session, current_user=bob_user, recipient_user=emily_user)


async def test_direct_chat_exists_returns_false_given_chat_does_not_exist(
    db_session: AsyncSession,
    bob_doug_chat: Chat,
    bob_user: User,
    emily_user: User,
):
    assert not await direct_chat_exists(db_session, current_user=bob_user, recipient_user=emily_user)
