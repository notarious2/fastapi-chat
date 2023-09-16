from unittest import mock

from fastapi import status
from httpx import AsyncClient

from src.models import User


async def bob_user_login_succeeds_given_valid_credentials(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.username, "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"access_token": mock.ANY, "refresh_token": mock.ANY}


async def bob_user_login_fails_given_invalid_username(async_client: AsyncClient):
    url = "/login/"
    payload = {"username": "some username", "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Incorrect email/username or password"}


async def bob_user_login_fails_given_invalid_password(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.username, "password": "wrong_password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Incorrect email/username or password"}
