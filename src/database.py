from datetime import datetime
from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy import Boolean, DateTime, MetaData, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.config import settings

DATABASE_URL = settings.DATABASE_URL or (
    f"postgresql+asyncpg://"
    f"{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)


metadata = MetaData(schema=settings.DB_SCHEMA)


class RemoveBaseFieldsMixin:
    created_at = None
    updated_at = None
    is_deleted = None


class BaseModel(DeclarativeBase):
    __abstract__ = True
    # to not declare schema each time table is created
    metadata = metadata

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}


engine = create_async_engine(
    DATABASE_URL, pool_size=40, max_overflow=20, pool_recycle=3600, isolation_level="AUTOCOMMIT"
)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def create_redis_pool():
    return aioredis.ConnectionPool(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=settings.REDIS_DB
    )


redis_pool = create_redis_pool()
