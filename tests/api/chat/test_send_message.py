from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Chat, Message, User


async def test_send_message_to_direct_chat_succeeds_given_valid_data(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_user: User
):
    url = f"/chat/{bob_emily_chat.guid}/message/"
    payload = {"content": "Hello World!"}

    response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "Message has been sent"

    # check message creation in db
    query = select(Message).where(and_(Message.user_id == bob_user.id, Message.chat_id == bob_emily_chat.id))
    result = await db_session.execute(query)
    message: Message | None = result.scalar_one_or_none()

    assert message is not None
    assert message.content == "Hello World!"
    assert message.user_id == bob_user.id
    assert message.chat_id == bob_emily_chat.id


async def test_send_message_to_direct_chat_fails_given_chat_does_not_exist(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient
):
    url = f"/chat/{uuid4()}/message/"
    payload = {"content": "Hello World!"}

    response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Chat with provided guid is not found"}
