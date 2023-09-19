from pydantic import BaseModel, UUID4
from src.api.chat.schemas import MessageSchema


# TODO: Add data validation


class ReceiveMessageSchema(BaseModel):
    chat_guid: UUID4
    content: str


class SendMessageSchema(MessageSchema):
    class Config:
        from_attributes = True
