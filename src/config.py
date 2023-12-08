import os

import boto3
from pydantic_settings import BaseSettings


class GlobalSettings(BaseSettings):
    ENVIRONMENT: str = "production"
    # app settings
    ALLOWED_ORIGINS: str = "http://127.0.0.1:3000"

    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "chat-postgres"
    DB_PORT: str = "5432"
    DB_NAME: str = "postgres"
    DB_SCHEMA: str = "chat"
    # specify single database url
    DATABASE_URL: str | None = None

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
    REDIS_CACHE_ENABLED: bool = False
    REDIS_HOST: str = "chat-redis"
    REDIS_PORT: str | int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_CACHE_EXPIRATION_SECONDS: int = 60 * 30
    REDIS_DB: int = 0

    # websocket
    # user status
    SECONDS_TO_SEND_USER_STATUS: int = 60

    # admin
    ADMIN_SECRET_KEY: str = "Hs9LGqARc909ceBUYDw2Fs0QaXOA3Ky4"

    # static files
    STATIC_HOST: str = "http://localhost:8001"


class TestSettings(GlobalSettings):
    DB_SCHEMA: str = "test"


class DevelopmentSettings(GlobalSettings):
    pass


class ProductionSettings(GlobalSettings):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION_NAME: str
    AWS_IMAGES_BUCKET: str

    @staticmethod
    def get_aws_client_for_image_upload():
        if all(
            (
                aws_access_key_id := os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key := os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name := os.environ.get("AWS_REGION_NAME", ""),
            )
        ):
            aws_session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
            )
            s3_resource = aws_session.resource("s3")

            return s3_resource.meta.client
        else:
            return None


def get_settings():
    env = os.environ.get("ENVIRONMENT", "")
    if env == "test":
        return TestSettings()
    elif env == "development":
        return DevelopmentSettings()
    elif env == "production":
        return ProductionSettings()

    return GlobalSettings()


settings = get_settings()
