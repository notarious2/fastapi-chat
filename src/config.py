import os

from pydantic_settings import BaseSettings


class GlobalSettings(BaseSettings):
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "chat-postgres"
    DB_PORT: str = "5432"
    DB_NAME: str = "postgres"
    DB_SCHEMA: str = "chat"

    # authentication related
    JWT_ACCESS_SECRET_KEY: str = "9d9bc4d77ac3a6fce1869ec8222729d2"
    JWT_REFRESH_SECRET_KEY: str = "fdc5635260b464a0b8e12835800c9016"
    ENCRYPTION_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    NEW_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # admin
    ADMIN_SECRET_KEY: str = "Hv9LGqARc473ceBUYDw1FR0QaXOA3Ky4"

    # redis for caching
    REDIS_CACHE_ENABLED: bool = True
    REDIS_HOST: str = "chat-redis"
    REDIS_PORT: str | int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_CACHE_EXPIRATION_SECONDS: int = 60 * 30

    # websocket
    # user status
    SECONDS_TO_SEND_USER_STATUS: int = 60


class TestSettings(GlobalSettings):
    DB_SCHEMA: str = "test"


def get_settings():
    env = os.environ.get("ENVIRONMENT", "development")
    if env == "test":
        return TestSettings()
    return GlobalSettings()


settings = get_settings()
