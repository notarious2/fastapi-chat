import asyncio
import logging
from json.decoder import JSONDecodeError

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi_limiter.depends import WebSocketRateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.websocket.exceptions import WebsocketTooManyRequests
from src.api.websocket.handlers import socket_manager
from src.api.websocket.rate_limiter import websocket_callback
from src.api.websocket.services import (
    check_user_statuses,
    get_user_active_direct_chats,
    mark_user_as_offline,
    mark_user_as_online,
)
from src.database import get_async_session
from src.dependencies import get_cache, get_current_user
from src.models import User

logger = logging.getLogger(__name__)


websocket_router = APIRouter()


@websocket_router.websocket("/ws/")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
    cache: aioredis.Redis = Depends(get_cache),
):
    await socket_manager.connect_socket(websocket=websocket)
    ratelimit = WebSocketRateLimiter(times=50, seconds=10, callback=websocket_callback)

    # Update the user's status in Redis with a new TTL
    await mark_user_as_online(cache=cache, current_user=current_user)

    # keep track of open redis pub/sub channels holds guid/id key-value pairs
    chats = dict()
    # get all users direct chats and subscribe # TODO: Generalize for group chats?
    if direct_chats := await get_user_active_direct_chats(db_session, current_user=current_user):
        chats = direct_chats
        for chat_guid in chats.keys():
            # subscribe this websocket instance to many Redis PubSub channels
            await socket_manager.add_user_to_chat(chat_guid, websocket)

    asyncio.create_task(check_user_statuses(cache, socket_manager, current_user, chats))
    try:
        while True:
            try:
                incoming_message = await websocket.receive_json()
                await ratelimit(websocket)

                message_type = incoming_message.get("type")
                if not message_type:
                    await socket_manager.send_error("You should provide message type", websocket)

                handler = socket_manager.handlers.get(message_type)

                if not handler:
                    logger.exception(f"No handler [{message_type}] exists")
                    await socket_manager.send_error(f"Type: {message_type} was not found", websocket)
                    continue

                await handler(
                    websocket=websocket,
                    db_session=db_session,
                    cache=cache,
                    incoming_message=incoming_message,
                    chats=chats,
                    current_user=current_user,
                )
            except (JSONDecodeError, AttributeError) as excinfo:
                logger.exception(f"Websocket error, detail: {excinfo}")
                await socket_manager.send_error("Wrong message format", websocket)
                continue
            except ValueError as excinfo:
                logger.exception(f"Websocket error, detail: {excinfo}")
                await socket_manager.send_error("Could not validate incoming message", websocket)

            except WebsocketTooManyRequests:
                logger.info(f"User: {current_user} sent too many ws requests")
                await socket_manager.send_error("You have sent too many requests", websocket)

    except WebSocketDisconnect:
        for chat_guid in chats.keys():
            await mark_user_as_offline(
                cache=cache, socket_manager=socket_manager, current_user=current_user, chat_guid=chat_guid
            )
            await socket_manager.remove_user_from_chat(chat_guid, websocket)
