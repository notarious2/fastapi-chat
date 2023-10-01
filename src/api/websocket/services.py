import asyncio
import logging
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Message, ReadStatus, User
from src.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


async def check_user_statuses(cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chats: dict):
    while True:
        is_online = await cache.exists(f"user:{current_user.id}:status")
        # make sure to translate to all chats that the user is in

        user_chat_guids = set(chats.keys()) & {str(chat.guid) for chat in current_user.chats}

        if is_online:
            for chat_guid in user_chat_guids:
                # Update the user's status as "offline" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid, {"type": "status", "username": current_user.username, "online": True}
                )
                pass
        else:
            for chat_guid in user_chat_guids:
                # Update the user's status as "offline" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid, {"type": "status", "username": current_user.username, "online": False}
                )
        await asyncio.sleep(10)  # Sleep for 5 seconds before the next check


async def mark_user_as_offline(cache: aioredis.Redis, current_user: User):
    # Remove the user's status key from Redis
    await cache.delete(f"user:{current_user.id}:status")


async def mark_user_as_online(cache: aioredis.Redis, current_user: User):
    await cache.set(f"user:{current_user.id}:status", "online", ex=60 * 60 * 2)


async def get_message_by_guid(db_session: AsyncSession, *, message_guid: UUID) -> Message | None:
    query = select(Message).where(and_(Message.guid == message_guid, Message.is_active.is_(True)))
    result = await db_session.execute(query)
    message: Message | None = result.scalar_one_or_none()

    return message


async def mark_last_read_message(
    db_session: AsyncSession, *, user_id: int, chat_id: int, last_read_message_id: int
) -> ReadStatus:
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
        else:
            print("MY NEW LAST READ MESSAGE", last_read_message_id)
            read_status.last_read_message_id = last_read_message_id

    db_session.add(read_status)
    await db_session.commit()

    return read_status


async def get_read_status(db_session: AsyncSession, *, user_id: int, chat_id: int) -> ReadStatus | None:
    query = select(ReadStatus).where(and_(ReadStatus.user_id == user_id, ReadStatus.chat_id == chat_id))
    result = await db_session.execute(query)
    read_status: ReadStatus | None = result.scalar_one_or_none()

    return read_status
