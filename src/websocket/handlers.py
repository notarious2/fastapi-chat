import asyncio
import logging
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from src.managers.websocket_manager import WebSocketManager
from src.models import Chat, Message, ReadStatus, User
from src.utils import clear_cache_for_get_direct_chats, clear_cache_for_get_messages
from src.websocket.schemas import (
    AddUserToChatSchema,
    MessageReadSchema,
    NotifyChatRemovedSchema,
    ReceiveMessageSchema,
    SendMessageSchema,
    UserTypingSchema,
)
from src.websocket.services import (
    get_chat_id_by_guid,
    get_message_by_guid,
    mark_last_read_message,
    mark_user_as_online,
    send_new_chat_created_ws_message,
)

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
    cache_enabled: bool,
    **kwargs,
):
    """
    message is received as "new_message" type but broadcasted to all users
    as "new" type
    """
    message_schema = ReceiveMessageSchema(**incoming_message)
    chat_guid: str = str(message_schema.chat_guid)

    notify_friend_about_new_chat: bool = False
    # newly created chat
    if not chats or chat_guid not in chats:
        chat_id: int | None = await get_chat_id_by_guid(db_session, chat_guid=chat_guid)
        if chat_id:
            # this action modifies chats variable in websocket view
            chats[chat_guid] = chat_id
            await socket_manager.add_user_to_chat(chat_guid, websocket)
            # must notify friend that new chat has been created
            notify_friend_about_new_chat = True

        else:
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
        chat: Chat = await db_session.get(Chat, chat_id)
        chat.updated_at = datetime.now()
        db_session.add(chat)

        await db_session.commit()
        await db_session.refresh(message, attribute_names=["user", "chat"])  # ?
        await db_session.refresh(chat, attribute_names=["users"])  # ?

    except Exception as exc_info:
        await db_session.rollback()
        logger.exception(f"[new_message] Exception, rolling back session, detail: {exc_info}")
        raise exc_info

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )
    # clear cache for all users
    if cache_enabled:
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

    if notify_friend_about_new_chat:
        logger.info("Notifying friend about newly created chat")
        await send_new_chat_created_ws_message(socket_manager=socket_manager, current_user=current_user, chat=chat)


@socket_manager.handler("message_read")
async def message_read_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    cache_enabled: bool,
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
            f"[read_status] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return
    chat_id = chats.get(chat_guid)

    # Mark message read for own user, if none is returned, message is already read
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
        if cache_enabled:
            # clear cache for getting messages
            await clear_cache_for_get_messages(cache=cache, chat_guid=chat_guid)

        await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("user_typing")
async def user_typing_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    **kwargs,
):
    # TODO: Rate limit
    # TODO: Validate chat_guid and user_guid

    user_typing_schema = UserTypingSchema(**incoming_message)
    chat_guid: str = str(user_typing_schema.chat_guid)
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[user_typing] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )

    outgoing_message: dict = user_typing_schema.model_dump_json()
    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("add_user_to_chat")
async def add_user_to_chat_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    **kwargs,
):
    """
    `add_user_to_chat` type is only received by non-initiator user active websockets
    it subscribes the user to the newly created chat and marks non-initiator user
    as active since he/she has an active websocket connection that received this message
    """
    add_user_to_chat_schema = AddUserToChatSchema(**incoming_message)

    chat_guid = add_user_to_chat_schema.chat_guid
    chat_id = add_user_to_chat_schema.chat_id

    await socket_manager.add_user_to_chat(chat_guid=chat_guid, websocket=websocket)
    # modify chats variable in websocket view
    chats[chat_guid] = chat_id

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )


@socket_manager.handler("chat_deleted")
async def chat_deleted_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    """
    `chat_deleted` - sends ws notification to all active websocket connections to display
    a message that the chat has been deleted/actual deletion happens via HTTP request
    """

    notify_chat_removed_schema = NotifyChatRemovedSchema(**incoming_message)
    chat_guid = notify_chat_removed_schema.chat_guid
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[chat_deleted] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return

    # get all websocket connections that belong to this chat (except for ws that sent this messsage)
    # and send notification that chat has been removed

    target_websockets: set[WebSocket] = socket_manager.chats.get(chat_guid)

    outgoing_message = {
        "type": "chat_deleted",
        "user_guid": str(current_user.guid),
        "user_name": current_user.first_name,
        "chat_guid": chat_guid,
    }

    if target_websockets:
        # Send the notification message to the target user concurrently
        # used to notify frontend
        await asyncio.gather(
            *[
                socket.send_json(jsonable_encoder(outgoing_message))
                for socket in target_websockets
                if socket != websocket
            ]
        )
