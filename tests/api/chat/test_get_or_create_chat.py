from unittest import mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Chat, ChatType, User


async def test_get_or_create_direct_chat_succeeds_given_no_chat_exists(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient, bob_user: User, emily_user: User
):
    url = "/chat/direct/"
    payload = {"recipient_user_guid": str(emily_user.guid)}

    response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "guid": mock.ANY,
        "chat_type": "direct",
        "created_at": mock.ANY,
        "users": [
            {
                "guid": mock.ANY,
                "first_name": bob_user.first_name,
                "last_name": bob_user.last_name,
                "username": bob_user.username,
            },
            {
                "guid": mock.ANY,
                "first_name": emily_user.first_name,
                "last_name": emily_user.last_name,
                "username": emily_user.username,
            },
        ],
    }

    # check chat creation in db
    query = select(Chat).where(Chat.chat_type == ChatType.DIRECT).options(selectinload(Chat.users))
    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    assert chat is not None
    assert chat.chat_type == ChatType.DIRECT
    assert {bob_user, emily_user} == set(chat.users)


async def test_get_or_create_direct_chat_succeeds_bob_emily_chat_exists(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, emily_user: User
):
    url = "/chat/direct/"
    payload = {"recipient_user_guid": str(emily_user.guid)}

    response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["guid"] == str(bob_emily_chat.guid)


async def test_get_or_create_direct_chat_fails_given_recipient_user_does_not_exist(
    db_session: AsyncSession,
    authenticated_bob_client: AsyncClient,
):
    url = "/chat/direct/"
    payload = {"recipient_user_guid": str(uuid4())}

    response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "There is no recipient user with provided guid"}
