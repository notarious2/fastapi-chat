import asyncio
import logging
from typing import Dict
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Chat, ChatType, Message, ReadStatus, User
from src.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


async def check_user_statuses(cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chats: dict):
    while True:
        is_online = await cache.exists(f"user:{current_user.id}:status")
        # make sure to translate to all chats that the user is in

        user_chat_guids = set(chats.keys()) & {str(chat.guid) for chat in current_user.chats}

        if is_online:
            for chat_guid in user_chat_guids:
                # Update the user's status as "online" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid, {"type": "status", "username": current_user.username, "status": "online"}
                )

        else:
            for chat_guid in user_chat_guids:
                # Update the user's status as "inactive" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat_guid, {"type": "status", "username": current_user.username, "status": "inactive"}
                )
        await asyncio.sleep(10)  # Sleep for 10 seconds before the next check


async def mark_user_as_offline(
    cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chat_guid: str
):
    await cache.delete(f"user:{current_user.id}:status")
    await socket_manager.broadcast_to_chat(
        chat_guid, {"type": "status", "username": current_user.username, "status": "offline"}
    )


async def mark_user_as_online(
    cache: aioredis.Redis, current_user: User, socket_manager: WebSocketManager = None, chat_guid: str = None
):
    await cache.set(f"user:{current_user.id}:status", "online", ex=60)  # 2 hours
    if socket_manager and chat_guid:
        await socket_manager.broadcast_to_chat(
            chat_guid, {"type": "status", "username": current_user.username, "status": "online"}
        )


async def get_message_by_guid(db_session: AsyncSession, *, message_guid: UUID) -> Message | None:
    query = select(Message).where(and_(Message.guid == message_guid, Message.is_active.is_(True)))
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


async def get_user_active_direct_chats(db_session: AsyncSession, *, current_user: User) -> Dict[UUID, int] | None:
    direct_chats_dict = dict()
    query = (
        select(Chat)
        .where(and_(Chat.chat_type == ChatType.DIRECT, Chat.is_active.is_(True), Chat.users.contains(current_user)))
        .options(selectinload(Chat.users))
    )
    result = await db_session.execute(query)
    direct_chats: list[Chat] = result.scalars().all()

    if direct_chats:
        for direct_chat in direct_chats:
            direct_chats_dict[str(direct_chat.guid)] = direct_chat.id
        return direct_chats_dict
    else:
        return None
