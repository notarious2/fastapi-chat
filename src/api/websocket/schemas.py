from datetime import datetime

from pydantic import UUID4, BaseModel

# TODO: Add data validation


class ReceiveMessageSchema(BaseModel):
    user_guid: UUID4
    chat_guid: UUID4
    content: str


class SendMessageSchema(BaseModel):
    type: str = "new"
    message_guid: UUID4
    user_guid: UUID4
    chat_guid: UUID4
    content: str
    created_at: datetime
    is_read: bool | None = False
    is_new: bool | None = True


class MessageReadSchema(BaseModel):
    type: str
    chat_guid: UUID4
    message_guid: UUID4


class UserTypingSchema(BaseModel):
    type: str
    chat_guid: UUID4
    user_guid: UUID4
