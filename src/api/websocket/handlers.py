import logging
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.websocket.schemas import MessageReadSchema, ReceiveMessageSchema, SendMessageSchema, UserTypingSchema
from src.api.websocket.services import get_message_by_guid, mark_last_read_message, mark_user_as_online
from src.managers.websocket_manager import WebSocketManager
from src.models import Chat, Message, ReadStatus, User
from src.utils import clear_cache_for_get_direct_chats, clear_cache_for_get_messages

logger = logging.getLogger(__name__)


socket_manager = WebSocketManager()


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
    chat_guid: str = str(message_schema.chat_guid)

    if chat_guid not in chats:
        await socket_manager.send_error("Chat has not been added", websocket)
        return

    chat_id = chats.get(chat_guid)
    try:
        # Save message and broadcast it back
        message = Message(
            content=message_schema.content,
            chat_id=chat_id,
            user_id=current_user.id,
        )
        db_session.add(message)
        await db_session.flush()  # to generate id

        # Update the updated_at field of the chat
        chat = await db_session.get(Chat, chat_id)
        chat.updated_at = datetime.now()
        db_session.add(chat)

        await db_session.commit()
        await db_session.refresh(message, attribute_names=["user", "chat"])
    except Exception as exc_info:
        await db_session.rollback()
        logger.exception(f"[new_message] Exception, rolling back session, detail: {exc_info}")
        raise exc_info

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )
    # clear cache for all users (display last read message)
    for user in chat.users:
        await clear_cache_for_get_direct_chats(cache=cache, user=user)
    # clear cache for getting messages
    await clear_cache_for_get_messages(cache=cache, chat_guid=chat_guid)

    send_message_schema = SendMessageSchema(
        message_guid=message.guid,
        chat_guid=chat.guid,
        user_guid=current_user.guid,
        content=message.content,
        created_at=message.created_at,
        is_read=False,
        is_new=True,
    )
    outgoing_message: dict = send_message_schema.model_dump_json()
    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("message_read")
async def message_read_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    **kwargs,
):
    print("MARKING MESSAGE AS READ", current_user, incoming_message)
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
            f"[read_status] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return
    chat_id = chats.get(chat_guid)

    # Mark message read for own user
    print(f"Marking message {message.content} read for user {current_user.username}")
    read_status: ReadStatus | None = await mark_last_read_message(
        db_session, user_id=current_user.id, chat_id=chat_id, last_read_message_id=message.id
    )
    if read_status:
        outgoing_message = {
            "type": "message_read",
            "user_guid": str(current_user.guid),
            "chat_guid": str(chat_guid),
            "last_read_message_guid": str(message.guid),
            "last_read_message_created_at": str(message.created_at),
        }
        # change redis/send ws message showing status is online
        await mark_user_as_online(
            cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
        )
        # clear cache for getting messages
        await clear_cache_for_get_messages(cache=cache, chat_guid=chat_guid)

        await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("user_typing")
async def user_typing_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    # TODO: Rate limit
    # TODO: Validate chat_guid and user_guid
    # TODO: mark user that is typing as online

    user_typing_schema = UserTypingSchema(**incoming_message)
    chat_guid: str = str(user_typing_schema.chat_guid)
    outgoing_message: dict = user_typing_schema.model_dump_json()
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[user_typing] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return

    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)
