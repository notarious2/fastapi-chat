from pydantic import UUID4, BaseModel

from src.api.chat.schemas import MessageSchema

# TODO: Add data validation


class ReceiveMessageSchema(BaseModel):
    chat_guid: UUID4
    content: str


class SendMessageSchema(MessageSchema):
    type: str = "new"

    class Config:
        from_attributes = True
