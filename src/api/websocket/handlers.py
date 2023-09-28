import logging
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat.services import get_chat_by_guid
from src.api.websocket.schemas import MessageReadSchema, ReceiveMessageSchema, SendMessageSchema
from src.api.websocket.services import get_message_by_guid, mark_last_read_message, mark_user_as_online
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
    cache: aioredis.Redis,
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

    # Update the updated_at field of the chat
    chat = await db_session.get(Chat, chat_id)
    chat.updated_at = datetime.now()
    db_session.add(chat)

    await db_session.commit()
    await db_session.refresh(message, attribute_names=["user", "chat"])

    await mark_user_as_online(cache, current_user)

    send_message_schema = SendMessageSchema.model_validate(message, from_attributes=True)
    outgoing_message: dict = send_message_schema.model_dump_json()
    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("message_read")
async def message_read_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    message_read_schema = MessageReadSchema(**incoming_message)

    message_guid = str(message_read_schema.message_guid)
    message: Message | None = await get_message_by_guid(db_session, message_guid=message_guid)
    if not message:
        await socket_manager.send_error(
            f"[read_status] Message with provided guid [{message_guid}] does not exist", websocket
        )

    chat_guid = str(message_read_schema.chat_guid)
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[read_status] Chat with provided guid [{message_guid}] does not exist", websocket
        )
        return
    chat_id = chats.get(chat_guid)

    await mark_last_read_message(db_session, user_id=current_user.id, chat_id=chat_id, last_read_message_id=message.id)

    outgoing_message = {
        "type": "message_read",
        "user_guid": str(current_user.guid),
        "chat_guid": str(chat_guid),
        "last_read_message_guid": str(message.guid),
        "last_read_message_created_at": str(message.created_at),
    }

    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)
