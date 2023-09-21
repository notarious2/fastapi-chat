import asyncio

import redis.asyncio as aioredis

from src.models import User
from src.services.websocket_manager import WebSocketManager


async def check_user_statuses(cache: aioredis.Redis, socket_manager: WebSocketManager, current_user: User, chats: dict):
    while True:
        is_online = await cache.exists(f"user:{current_user.id}:status")
        if is_online:
            for chat in chats:
                # Update the user's status as "offline" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat, {"type": "status", "username": current_user.username, "online": True}
                )
        else:
            for chat in chats:
                # Update the user's status as "offline" in the frontend
                await socket_manager.broadcast_to_chat(
                    chat, {"type": "status", "username": current_user.username, "online": False}
                )
        await asyncio.sleep(5)  # Sleep for 5 seconds before the next check
