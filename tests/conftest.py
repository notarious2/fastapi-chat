import asyncio
from datetime import datetime
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.api.authentication.utils import create_access_token
from src.config import settings
from src.database import get_async_session, metadata
from src.main import app
from src.models import Chat, ChatType, Message, User
from src.utils import get_hashed_password

DATABASE_URL_TEST = (
    f"postgresql+asyncpg://"
    f"{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)
engine_test = create_async_engine(DATABASE_URL_TEST, connect_args={"server_settings": {"jit": "off"}})
async_session_maker = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)
metadata.bind = engine_test


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(scope="session")
async def db_session():
    async with engine_test.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        await conn.run_sync(metadata.create_all)
    async with async_session_maker() as session:
        yield session
        await session.flush()
        await session.rollback()
    async with engine_test.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA {settings.db_schema} CASCADE"))


# https://stackoverflow.com/questions/4763472/sqlalchemy-clear-database-content-but-dont-drop-the-schema
@pytest.fixture(autouse=True)
async def clear_tables(db_session: AsyncSession):
    for table in reversed(metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()


client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def bob_user(db_session: AsyncSession) -> User:
    user = User(
        password=get_hashed_password("password"),
        username="bob_username",
        first_name="Bob",
        last_name="Stewart",
        email="user@example.com",
    )
    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
def authenticated_bob_client(async_client: AsyncClient, bob_user: User):
    access_token = create_access_token(subject=bob_user.email)
    async_client.cookies.update({"access_token": access_token})

    yield async_client


@pytest.fixture
async def emily_user(db_session: AsyncSession) -> User:
    user = User(
        password=get_hashed_password("password"),
        username="emily",
        first_name="Emily",
        last_name="Hazel",
        email="emily@example.com",
    )
    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
async def doug_user(db_session: AsyncSession) -> User:
    user = User(
        password=get_hashed_password("password"),
        username="douglas",
        first_name="Douglas",
        last_name="Walrus",
        email="douglas@example.com",
    )
    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
def authenticated_doug_client(async_client: AsyncClient, doug_user: User):
    access_token = create_access_token(subject=doug_user.email)
    async_client.cookies.update({"access_token": access_token})

    yield async_client


@pytest.fixture
async def bob_emily_chat(db_session: AsyncSession, bob_user: User, emily_user: User) -> Chat:
    chat = Chat(chat_type=ChatType.DIRECT)
    chat.users.append(bob_user)
    chat.users.append(emily_user)
    db_session.add(chat)
    await db_session.commit()

    return chat


@pytest.fixture
async def bob_doug_chat(db_session: AsyncSession, doug_user: User, bob_user: User) -> Chat:
    chat = Chat(chat_type=ChatType.DIRECT)
    chat.users.append(doug_user)
    chat.users.append(bob_user)
    db_session.add(chat)
    await db_session.commit()

    return chat


@pytest.fixture
async def bob_emily_chat_messages_history(
    db_session: AsyncSession, bob_user: User, emily_user: User, bob_emily_chat: Chat
) -> list[Message]:
    await db_session.refresh(bob_emily_chat, attribute_names=["messages"])
    Bob = True
    sender_id = bob_user.id if Bob else emily_user.id
    sender_name = "Bob" if Bob else "Emily"

    for i in range(1, 21):
        message = Message(
            content=f"#{i} message sent by {sender_name}",
            user_id=sender_id,
            chat_id=bob_emily_chat.id,
            created_at=datetime.now(),
        )
        Bob = not Bob
        bob_emily_chat.messages.append(message)

    db_session.add(bob_emily_chat)
    await db_session.commit()

    return bob_emily_chat.messages
