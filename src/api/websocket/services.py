import asyncio

import redis.asyncio as aioredis

from src.models import User
from src.services.websocket_manager import WebSocketManager


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
    await cache.set(f"user:{current_user.id}:status", "online", ex=60)
