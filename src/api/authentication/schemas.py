from pydantic import UUID4, BaseModel, EmailStr, Field, field_validator

from src.config import settings


class GoogleLoginSchema(BaseModel):
    access_token: str


class UserLoginResponseSchema(BaseModel):
    guid: UUID4 = Field(..., serialization_alias="user_guid")
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    user_image: str | None
    settings: dict

    class Config:
        from_attributes = True

    @field_validator("user_image")
    @classmethod
    def add_image_host(cls, image_url: str | None) -> str:
        if image_url:
            if "/static/" in image_url and settings.ENVIRONMENT == "development":
                return settings.STATIC_HOST + image_url
        return image_url
