from unittest import mock

from fastapi import status
from httpx import AsyncClient

from src.models import User


async def test_user_login_succeeds_given_valid_credentials(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.username, "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "first_name": bob_user.first_name,
        "last_name": bob_user.last_name,
        "email": bob_user.email,
        "username": bob_user.username,
        "user_guid": str(bob_user.guid),
        "user_image": None,
        "settings": {},
    }

    assert response.cookies["access_token"] == mock.ANY
    assert response.cookies["refresh_token"] == mock.ANY


async def test_user_login_succeeds_given_capitalized_username(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.username.capitalize(), "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "first_name": bob_user.first_name,
        "last_name": bob_user.last_name,
        "email": bob_user.email,
        "username": bob_user.username,
        "user_guid": str(bob_user.guid),
        "user_image": None,
        "settings": {},
    }

    assert response.cookies["access_token"] == mock.ANY
    assert response.cookies["refresh_token"] == mock.ANY


async def test_user_login_succeeds_given_capitalized_email(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.email.capitalize(), "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "first_name": bob_user.first_name,
        "last_name": bob_user.last_name,
        "email": bob_user.email,
        "username": bob_user.username,
        "user_guid": str(bob_user.guid),
        "user_image": None,
        "settings": {},
    }

    assert response.cookies["access_token"] == mock.ANY
    assert response.cookies["refresh_token"] == mock.ANY


async def test_user_login_fails_given_invalid_username(async_client: AsyncClient):
    url = "/login/"
    payload = {"username": "some username", "password": "password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Incorrect email/username or password"}


async def test_user_login_fails_given_invalid_password(async_client: AsyncClient, bob_user: User):
    url = "/login/"
    payload = {"username": bob_user.username, "password": "wrong_password"}

    response = await async_client.post(url, data=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Incorrect email/username or password"}
