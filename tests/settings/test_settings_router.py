from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


async def test_set_user_theme_succeeds_given_theme_exists(
    authenticated_bob_client: AsyncClient, bob_user: User, db_session: AsyncSession
):
    response: Response = await authenticated_bob_client.post("/user/settings/theme/", json={"theme": "teal"})
    await db_session.refresh(bob_user)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "New theme has been set"}
    assert bob_user.settings == {"theme": "teal"}


async def test_set_user_theme_fails_given_theme_does_not_exist(
    authenticated_bob_client: AsyncClient,
):
    response: Response = await authenticated_bob_client.post("/user/settings/theme/", json={"theme": "Unknown"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["msg"] == "Input should be 'teal' or 'midnight'"
