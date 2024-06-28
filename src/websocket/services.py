import asyncio
import logging
from typing import Dict
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.managers.websocket_manager import WebSocketManager
from src.models import Chat, ChatType, Message, ReadStatus, User
from src.websocket.schemas import NewChatCreated

logger = logging.getLogger(__name__)


async def check_user_statuses(cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chats: dict):
    while True:
        is_online = await cache.exists(f"user:{current_user.id}:status")
        # make sure to translate to all chats that the user is in
        if not chats:
            return
        user_chat_guids = set(chats.keys()) & {str(chat.guid) for chat in current_user.chats}

        if is_online:
            for chat_guid in user_chat_guids:
                # Update the user's status as "online" on the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid,
                    {
                        "type": "status",
                        "username": current_user.username,
                        "user_guid": str(current_user.guid),
                        "status": "online",
                    },
                )

        else:
            for chat_guid in user_chat_guids:
                # Update the user's status as "inactive" on the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid,
                    {
                        "type": "status",
                        "username": current_user.username,
                        "user_guid": str(current_user.guid),
                        "status": "inactive",
                    },
                )
        await asyncio.sleep(settings.SECONDS_TO_SEND_USER_STATUS)  # Sleep for 60 seconds before the next check


async def mark_user_as_offline(
    cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chat_guid: str
):
    await cache.delete(f"user:{current_user.id}:status")
    await socket_manager.broadcast_to_chat(
        chat_guid,
        {"type": "status", "username": current_user.username, "user_guid": str(current_user.guid), "status": "offline"},
    )


async def mark_user_as_online(
    cache: aioredis.Redis, current_user: User, socket_manager: WebSocketManager = None, chat_guid: str = None
):
    # set new redis key
    await cache.set(f"user:{current_user.id}:status", "online", ex=60)  # 1 hours
    if socket_manager and chat_guid:
        await socket_manager.broadcast_to_chat(
            chat_guid,
            {
                "type": "status",
                "username": current_user.username,
                "user_guid": str(current_user.guid),
                "status": "online",
            },
        )


async def get_message_by_guid(db_session: AsyncSession, *, message_guid: UUID) -> Message | None:
    query = select(Message).where(and_(Message.guid == message_guid, Message.is_deleted.is_(False)))
    result = await db_session.execute(query)
    message: Message | None = result.scalar_one_or_none()

    return message


async def mark_last_read_message(
    db_session: AsyncSession, *, user_id: int, chat_id: int, last_read_message_id: int
) -> ReadStatus | None:
    query = select(ReadStatus).where(and_(ReadStatus.user_id == user_id, ReadStatus.chat_id == chat_id))
    result = await db_session.execute(query)
    read_status: ReadStatus | None = result.scalar_one_or_none()

    if not read_status:
        read_status = ReadStatus(user_id=user_id, chat_id=chat_id)
        read_status.last_read_message_id = last_read_message_id
    else:
        if read_status.last_read_message_id >= last_read_message_id:
            logging.warn(
                f"This message has been already read, details: "
                f"user_id: {user_id}, chat_id: {chat_id}, last_read_message_id: {last_read_message_id}"
            )
            return
        else:
            read_status.last_read_message_id = last_read_message_id

    db_session.add(read_status)
    await db_session.commit()

    return read_status


async def get_read_status(db_session: AsyncSession, *, user_id: int, chat_id: int) -> ReadStatus | None:
    query = select(ReadStatus).where(and_(ReadStatus.user_id == user_id, ReadStatus.chat_id == chat_id))
    result = await db_session.execute(query)
    read_status: ReadStatus | None = result.scalar_one_or_none()

    return read_status


async def get_user_active_direct_chats(db_session: AsyncSession, *, current_user: User) -> Dict[str, int] | None:
    """
    Returns a dictionary chat_guid: chat_id key-value pair for a given user
    """
    direct_chats_dict = dict()
    query = (
        select(Chat)
        .where(and_(Chat.chat_type == ChatType.DIRECT, Chat.is_deleted.is_(False), Chat.users.contains(current_user)))
        .options(selectinload(Chat.users))
    )
    result = await db_session.execute(query)
    direct_chats: list[Chat] = result.scalars().all()

    if direct_chats:
        for direct_chat in direct_chats:
            direct_chats_dict[str(direct_chat.guid)] = direct_chat.id
        return direct_chats_dict


async def get_chat_id_by_guid(db_session: AsyncSession, *, chat_guid: UUID) -> int | None:
    query = select(Chat.id).where(Chat.guid == chat_guid)
    result = await db_session.execute(query)
    chat_id: int | None = result.scalar_one_or_none()

    return chat_id


async def send_new_chat_created_ws_message(socket_manager: WebSocketManager, current_user: User, chat: Chat):
    """
    Send a new chat created message to friend's websocket connections in the chat.
    This allows to update chats while user is still connected without refreshing the page
    via get_chats view
    """
    # current user becomes a friend for a user that receives this message
    friend: dict = {
        "guid": current_user.guid,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "username": current_user.username,
        "user_image": current_user.user_image,
    }

    # get friend guid
    friend_guid: UUID | None = next((user.guid for user in chat.users if not user == current_user), None)

    if friend_guid is None:
        logger.error("Friend guid not found", extra={"type": "new_chat_created", "friend_guid": friend_guid})
        return

    payload = NewChatCreated(
        chat_id=chat.id,
        chat_guid=chat.guid,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        friend=friend,
        has_new_messages=True,
        new_messages_count=1,
    )

    target_websockets: set[WebSocket] = socket_manager.user_guid_to_websocket.get(str(friend_guid))

    # send new chat data to each target websocket
    if target_websockets:
        # Send the notification message to the target user concurrently
        # used to notify frontend
        await asyncio.gather(*[socket.send_json(jsonable_encoder(payload)) for socket in target_websockets])
        return

    logger.debug(
        "User has no active websocket connections", extra={"type": "new_chat_created", "friend_guid": friend_guid}
    )
