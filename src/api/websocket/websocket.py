import logging
from json.decoder import JSONDecodeError

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


websocket_router = APIRouter()

socket_manager = WebSocketManager()


@websocket_router.websocket("/ws/")
async def websocket_endpoint(
    websocket: WebSocket,
    db_session: AsyncSession = Depends(get_async_session),
):
    chat_guid = "83b2dfa3-1317-4d03-b6b1-1d8188d0d3b7"
    await socket_manager.connect_socket(websocket=websocket)
    await socket_manager.add_user_to_chat(chat_guid, websocket)
    await websocket.send_json({"message": "You are connected", "user": "Bekzod"})

    chats = dict()
    chats[chat_guid] = 1

    try:
        while True:
            try:
                incoming_message = await websocket.receive_json()
                outgoing_message = {"user": "Bekzod", "message": incoming_message["message"]}
                await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)
            except (JSONDecodeError, AttributeError) as e:
                print("E", e)
                await socket_manager.send_error("Wrong message format", websocket)
                continue

    except WebSocketDisconnect:
        for chat_guid in chats.keys():
            await socket_manager.remove_user_from_chat(chat_guid, websocket)
            await socket_manager.broadcast_to_chat(chat_guid, {"message": "user disconnected"})
