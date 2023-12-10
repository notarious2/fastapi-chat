from unittest import mock
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient, Response
from pytest_mock.plugin import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Chat, ChatType, User

url = "/chat/direct/"


async def test_post_succeeds_given_no_chat_exists(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient, bob_user: User, emily_user: User
):
    payload: dict = {"recipient_user_guid": str(emily_user.guid)}

    response: Response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "guid": mock.ANY,
        "chat_type": "direct",
        "created_at": mock.ANY,
        "updated_at": mock.ANY,
        "users": [
            {
                "guid": mock.ANY,
                "first_name": bob_user.first_name,
                "last_name": bob_user.last_name,
                "username": bob_user.username,
                "user_image": None,
            },
            {
                "guid": mock.ANY,
                "first_name": emily_user.first_name,
                "last_name": emily_user.last_name,
                "username": emily_user.username,
                "user_image": None,
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


async def test_post_fails_given_chat_already_exists(
    mocker: AsyncMock, authenticated_bob_client: AsyncClient, bob_emily_chat: Chat, emily_user: User
):
    recipient_user_guid: str = str(uuid4())
    payload: dict = {"recipient_user_guid": recipient_user_guid}
    mock_get_user_by_guid: AsyncMock = mocker.patch("src.api.chat.router.get_user_by_guid")
    mock_direct_chat_exists: AsyncMock = mocker.patch("src.api.chat.router.direct_chat_exists", return_value=True)

    response: Response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": f"Chat with recipient user exists [{recipient_user_guid}]"}
    mock_get_user_by_guid.assert_called_once()
    mock_direct_chat_exists.assert_called_once()


async def test_post_fails_given_recipient_does_not_exist(
    mocker: MockerFixture,
    authenticated_bob_client: AsyncClient,
):
    mock_get_user_by_guid: AsyncMock = mocker.patch("src.api.chat.router.get_user_by_guid", return_value=None)
    recipient_user_guid: str = str(uuid4())
    payload: dict = {"recipient_user_guid": recipient_user_guid}

    response: Response = await authenticated_bob_client.post(url, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": f"There is no recipient user with provided guid [{recipient_user_guid}]"}
    mock_get_user_by_guid.assert_called_once()
