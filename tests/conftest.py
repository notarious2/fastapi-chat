import asyncio
from datetime import date, datetime, timedelta
from typing import AsyncGenerator, Tuple

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


from src.config import settings
from src.database import get_async_session, metadata
from src.main import app

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


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client
