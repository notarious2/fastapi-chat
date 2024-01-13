from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.utils import verify_password


async def test_register_succeeds_given_valid_data(db_session: AsyncSession, async_client: AsyncClient):
    url = "/register/"
    payload = {
        "email": "ExamPle@gmail.com",
        "username": "bOb_userName",
        "password": "test_password",
        "first_name": "John",
        "last_name": "Doe",
    }
    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "User has been successfully created"

    # confirm changes in db
    statement = select(User).where(User.email == "example@gmail.com")
    result = await db_session.execute(statement)

    user: User = result.scalar_one_or_none()

    assert user is not None
    assert user.username == "bob_username"
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.email == "example@gmail.com"
    assert verify_password("test_password", user.password) is True


async def test_register_fails_given_invalid_email(async_client: AsyncClient):
    url = "/register/"
    payload = {
        "email": "not_valid_email.com",
        "username": "bob_username",
        "password": "test_password",
        "first_name": "John",
        "last_name": "Doe",
    }

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "value is not a valid email address" in response.json()["detail"][0]["msg"]


async def test_register_fails_given_user_with_provided_email_already_exists(async_client: AsyncClient, bob_user: User):
    url = "/register/"
    payload = {
        "email": bob_user.email,
        "username": "bob_username",
        "password": "test_password",
        "first_name": "John",
        "last_name": "Doe",
    }

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "User with provided credentials already exists"}


async def test_register_fails_given_user_with_provided_username_already_exists(
    async_client: AsyncClient, bob_user: User
):
    url = "/register/"
    payload = {
        "email": "example2@email.com",
        "username": bob_user.username,
        "password": "test_password",
        "first_name": "John",
        "last_name": "Doe",
    }

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "User with provided credentials already exists"}
