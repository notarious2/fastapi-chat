from datetime import datetime

from pydantic import UUID4, BaseModel

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


class MessageSchema(BaseModel):
    guid: UUID4
    content: str
    created_at: datetime
    user: UserSchema
    chat: ChatSchema


class DisplayDirectChatSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType
    created_at: datetime
    users: list[UserSchema]


class GetChatsSchema(BaseModel):
    guid: UUID4
    chat_type: ChatType
    created_at: datetime
    updated_at: datetime
    is_active: bool
    users: list[UserSchema]


class GetOldMessagesSchema(BaseModel):
    messages: list[MessageSchema]
    has_more_messages: bool
