from unittest import mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from src.models import Chat, Message


async def test_get_older_messages_succeeds_given_older_messages_exist(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Message]
):
    message_guid = bob_emily_chat_messages_history[-1].guid
    url = f"/chat/{bob_emily_chat.guid}/messages/old/{message_guid}/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"messages": mock.ANY, "has_more_messages": True}
    assert len(response.json()["messages"]) == 10


async def test_get_older_messages_succeeds_given_no_older_messages(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Message]
):
    message_guid = bob_emily_chat_messages_history[0].guid
    url = f"/chat/{bob_emily_chat.guid}/messages/old/{message_guid}/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"messages": [], "has_more_messages": False}


async def test_get_older_messages_fails_given_chat_does_not_exist(
    authenticated_bob_client: AsyncClient, bob_emily_chat_messages_history: list[Message]
):
    unexisting_chat_guid = uuid4()
    message_guid = bob_emily_chat_messages_history[0].guid
    url = f"/chat/{unexisting_chat_guid}/messages/old/{message_guid}/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Chat with provided guid is not found"}


async def test_get_older_messages_fails_given_user_is_not_in_chat(
    authenticated_doug_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Message]
):
    message_guid = bob_emily_chat_messages_history[0].guid
    url = f"/chat/{bob_emily_chat.guid}/messages/old/{message_guid}/"

    response = await authenticated_doug_client.get(url)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "You don't have access to this chat"}


async def test_get_older_messages_fails_given_no_message_with_provided_guid(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_emily_chat_messages_history: list[Message]
):
    unexisting_message_guid = uuid4()
    url = f"/chat/{bob_emily_chat.guid}/messages/old/{unexisting_message_guid}/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Message with provided guid is not found"}
