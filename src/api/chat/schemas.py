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

    class Config:
        from_attributes = True


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
    users: list[UserSchema]


class GetChatSchema(BaseModel):
    chat_guid: UUID4
    chat_type: ChatType
    created_at: datetime
    updated_at: datetime
    users: list[UserSchema]
    has_new_messages: bool
    new_messages_count: int

    class Config:
        from_attributes = True


class LastReadMessageSchema(BaseModel):
    guid: str
    content: str
    created_at: datetime


class GetMessageSchema(BaseModel):
    message_guid: UUID4
    user_guid: UUID4
    chat_guid: UUID4
    content: str
    created_at: datetime
    is_read: bool | None = False
    is_new: bool | None = True


class GetMessagesSchema(BaseModel):
    messages: list[GetMessageSchema]
    has_more_messages: bool
    last_read_message: LastReadMessageSchema = None


class GetOldMessagesSchema(BaseModel):
    messages: list[GetMessageSchema]
    has_more_messages: bool
