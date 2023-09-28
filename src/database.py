from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Boolean, DateTime, MetaData, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)


metadata = MetaData(schema=settings.db_schema)


class RemoveBaseFieldsMixin:
    created_at = None
    updated_at = None
    is_active = None


class BaseModel(DeclarativeBase):
    __abstract__ = True
    # to not declare schema each time table is created
    metadata = metadata

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}


engine = create_async_engine(
    DATABASE_URL, pool_size=40, max_overflow=20, pool_recycle=3600, isolation_level="AUTOCOMMIT"
)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
