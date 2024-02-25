from datetime import datetime

from pydantic import UUID4, BaseModel, field_validator

from src.config import settings
from src.models import ChatType


class ChatSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType


class CreateDirectChatSchema(BaseModel):
    recipient_user_guid: UUID4


class UserSchema(BaseModel):
    guid: UUID4
    first_name: str
    last_name: str
    username: str
    user_image: str | None

    class Config:
        from_attributes = True

    @field_validator("user_image")
    @classmethod
    def add_image_host(cls, image_url: str | None) -> str:
        if image_url:
            if "/static/" in image_url and settings.ENVIRONMENT == "development":
                return settings.STATIC_HOST + image_url
        return image_url


class MessageSchema(BaseModel):
    guid: UUID4
    content: str
    created_at: datetime
    user: UserSchema
    chat: ChatSchema
    is_read: bool | None = False
    is_new: bool | None = True


class DisplayDirectChatSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType
    created_at: datetime
    updated_at: datetime
    users: list[UserSchema]


class GetDirectChatSchema(BaseModel):
    chat_guid: UUID4
    chat_type: ChatType
    created_at: datetime
    updated_at: datetime
    users: list[UserSchema]
    new_messages_count: int

    class Config:
        from_attributes = True


class GetDirectChatsSchema(BaseModel):
    chats: list[GetDirectChatSchema]
    total_unread_messages_count: int


class LastReadMessageSchema(BaseModel):
    guid: UUID4
    content: str
    created_at: datetime


class GetMessageSchema(BaseModel):
    message_guid: UUID4
    user_guid: UUID4
    chat_guid: UUID4
    content: str
    created_at: datetime
    is_read: bool | None = False


class GetMessagesSchema(BaseModel):
    messages: list[GetMessageSchema]
    has_more_messages: bool
    last_read_message: LastReadMessageSchema = None


class GetOldMessagesSchema(BaseModel):
    messages: list[GetMessageSchema]
    has_more_messages: bool
