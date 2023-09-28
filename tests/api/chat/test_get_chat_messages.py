from unittest import mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from src.models import Chat


async def test_get_messages_succeeds_given_existing_chat_with_messages(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Chat]
):
    url = f"/chat/{bob_emily_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"messages": mock.ANY, "has_more_messages": False}
    messages = response.json()["messages"]
    assert len(messages) == 20
    assert set(messages[0].keys()) == {"guid", "content", "created_at", "user", "chat", "is_read"}


async def test_get_messages_succeeds_given_existing_chat_with_messages_and_read_status_for_bob(
    authenticated_bob_client: AsyncClient,
    bob_emily_chat: Chat,
    bob_emily_chat_messages_history: list[Chat],
    bob_read_status,
):
    url = f"/chat/{bob_emily_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"has_more_messages": False, "messages": mock.ANY}
    messages = response.json()["messages"]
    assert len(messages) == 20
    assert sum([message["is_read"] for message in messages]) == 10  # half of messages are read


async def test_get_messages_succeeds_given_existing_chat_with_messages_and_size(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Chat]
):
    url = f"/chat/{bob_emily_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url, params={"size": 10})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"messages": mock.ANY, "has_more_messages": True}
    assert len(response.json()["messages"]) == 10


async def test_get_messages_succeeds_given_existing_chat_without_messages(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat
):
    url = f"/chat/{bob_emily_chat.guid}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"messages": [], "has_more_messages": False}


async def test_get_messages_fails_given_chat_does_not_exist(authenticated_bob_client: AsyncClient):
    url = f"/chat/{uuid4()}/messages/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Chat with provided guid does not exist"}


async def test_get_messages_fails_given_user_is_not_chat_participant(
    authenticated_doug_client: AsyncClient, bob_emily_chat: Chat
):
    url = f"/chat/{bob_emily_chat.guid}/messages/"

    response = await authenticated_doug_client.get(url)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "You don't have access to this chat"}
