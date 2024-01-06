from unittest import mock

from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


async def test_get_contacts_returns_empty_list_given_only_current_user(
    db_session: AsyncSession, authenticated_bob_client: AsyncClient, bob_user: User
):
    response: Response = await authenticated_bob_client.get("/users/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


async def test_get_contacts_returns_users_list_given_multiple_other_users(
    mocker,
    db_session: AsyncSession,
    authenticated_bob_client: AsyncClient,
    bob_user: User,
    emily_user: User,
    doug_user: User,
):
    response: Response = await authenticated_bob_client.get("/users/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "guid": mock.ANY,
            "username": "douglas",
            "email": "douglas@example.com",
            "first_name": "Douglas",
            "last_name": "Walrus",
            "created_at": mock.ANY,
            "user_image": None,
        },
        {
            "guid": mock.ANY,
            "username": "emily",
            "email": "emily@example.com",
            "first_name": "Emily",
            "last_name": "Hazel",
            "created_at": mock.ANY,
            "user_image": None,
        },
    ]
