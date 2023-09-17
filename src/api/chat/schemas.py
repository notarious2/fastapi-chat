from datetime import datetime

from pydantic import UUID4, BaseModel

from src.models import ChatType


class MessageSchema(BaseModel):
    guid: UUID4
    content: str
    created_at: datetime


class CreateDirectChatSchema(BaseModel):
    recipient_user_guid: UUID4


class UserSchema(BaseModel):
    guid: UUID4
    first_name: str
    last_name: str
    username: str


class DisplayDirectChatSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType
    created_at: datetime
    users: list[UserSchema]


class GetChatsSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType
    created_at: datetime
    is_active: bool
    users: list[UserSchema]
