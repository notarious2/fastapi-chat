import os

from pydantic_settings import BaseSettings


class GlobalSettings(BaseSettings):
    db_user: str = os.environ.get("DB_USER", "postgres")
    db_password: str = os.environ.get("DB_PASSWORD", "postgres")
    db_host: str = os.environ.get("DB_HOST", "chat-postgres")
    db_port: str = os.environ.get("DB_PORT", "5432")
    db_name: str = os.environ.get("DB_NAME", "postgres")
    db_schema: str = os.environ.get("DB_SCHEMA", "chat")

    # authentication related
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "9d9bc4d77ac3a6fce1869ec8222729d2")
    JWT_REFRESH_SECRET_KEY: str = os.environ.get("JWT_REFRESH_SECRET_KEY", "fdc5635260b464a0b8e12835800c9016")

    # admin
    ADMIN_SECRET_KEY: str = os.environ.get("ADMIN_SECRET_KEY", "Hv9LGqARc473ceBUYDw1FR0QaXOA3Ky4")


class TestSettings(GlobalSettings):
    db_schema: str = "test"


def get_settings():
    env = os.environ.get("ENVIRONMENT", "development")
    if env == "test":
        return TestSettings()
    return GlobalSettings()


settings = get_settings()
