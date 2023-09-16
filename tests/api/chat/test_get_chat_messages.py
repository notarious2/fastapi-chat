from unittest import mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from src.models import Chat


async def test_get_messages_succeeds_given_existing_chat_with_messages(
    authenticated_bob_client: AsyncClient, direct_chat: Chat, direct_chat_messages_history: list[Chat]
):
    url = f"/chat/{direct_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": mock.ANY, "total": 20, "page": 1, "size": 50, "pages": 1}
    assert len(response.json()["items"]) == 20


async def test_get_messages_succeeds_given_existing_chat_without_messages(
    authenticated_bob_client: AsyncClient, direct_chat: Chat
):
    url = f"/chat/{direct_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 50, "pages": 0}


async def test_get_messages_fails_given_chat_does_not_exist(authenticated_bob_client: AsyncClient):
    url = f"/chat/{uuid4()}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Chat with provided guid does not exist"}


async def test_get_messages_fails_given_user_is_not_chat_participant(
    authenticated_doug_client: AsyncClient, direct_chat: Chat
):
    url = f"/chat/{direct_chat.guid}/messages/"

    response = await authenticated_doug_client.get(url)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "You don't have access to this chat"}
