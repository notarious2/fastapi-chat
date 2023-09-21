import logging

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat.services import get_chat_by_guid
from src.api.websocket.schemas import ReceiveMessageSchema, SendMessageSchema
from src.models import Chat, Message, User
from src.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


socket_manager = WebSocketManager()


@socket_manager.handler("connect_chat")
async def get_chat_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    chat_guid = incoming_message["chat_guid"]

    if chat_guid not in chats:
        chat: Chat = await get_chat_by_guid(db_session, chat_guid=chat_guid)
        # Validate that chat exists
        if not chat:
            logger.exception(f"Could not find chat with provided guid: {chat_guid}")
            await socket_manager.send_error(f"Chat with guid {chat_guid} does not exist", websocket)
    chats[chat_guid] = chat.id

    # create channel and subscribe
    await socket_manager.add_user_to_chat(chat_guid, websocket)
    await socket_manager.broadcast_to_chat(
        chat_guid,
        {
            "type": "status",
            "username": current_user.username,
            "online": True,
        },
    )


@socket_manager.handler("new_message")
async def new_message_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    message_schema = ReceiveMessageSchema(**incoming_message)
    chat_guid = str(message_schema.chat_guid)

    if chat_guid not in chats:
        await socket_manager.send_error("Chat has not been added", websocket)
        return

    chat_id = chats.get(chat_guid)
    # Save message and broadcast it back
    message = Message(
        content=message_schema.content,
        chat_id=chat_id,
        user_id=current_user.id,
    )
    db_session.add(message)

    await db_session.commit()
    await db_session.refresh(message, attribute_names=["user", "chat"])

    send_message_schema = SendMessageSchema.model_validate(message, from_attributes=True)
    outgoing_message: dict = send_message_schema.model_dump_json()
    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)
