from datetime import datetime

from pydantic import UUID4, BaseModel, RootModel, field_validator

from src.config import settings


class GetUserSchema(BaseModel):
    guid: UUID4
    username: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    user_image: str | None

    @field_validator("user_image")
    @classmethod
    def add_image_host(cls, image_url: str | None) -> str:
        if image_url:
            if "/static/" in image_url and settings.ENVIRONMENT == "development":
                return settings.STATIC_HOST + image_url
        return image_url


class GetUsersResponseSchema(RootModel[GetUserSchema]):
    root: list[GetUserSchema]
