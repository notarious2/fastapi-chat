from fastapi import status
from httpx import AsyncClient

from src.models import Chat


async def test_get_user_chats_succeeds_given_chat_exists(authenticated_bob_client: AsyncClient, bob_emily_chat: Chat):
    url = "/chats/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK

    chats = response.json()
    assert len(chats) == 1
    assert set(chats[0].keys()) == {
        "chat_guid",
        "chat_type",
        "created_at",
        "updated_at",
        "users",
        "has_new_messages",
        "new_messages_count",
    }


async def test_get_user_chats_succeeds_given_user_has_multiple_chats(
    authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, bob_doug_chat: Chat
):
    url = "/chats/"

    response = await authenticated_bob_client.get(url)

    assert response.status_code == status.HTTP_200_OK

    chats = response.json()
    assert len(chats) == 2
    for chat in chats:
        assert set(chat.keys()) == {
            "chat_guid",
            "chat_type",
            "created_at",
            "updated_at",
            "users",
            "has_new_messages",
            "new_messages_count",
        }
