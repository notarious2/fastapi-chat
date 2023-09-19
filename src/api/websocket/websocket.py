import logging
from json.decoder import JSONDecodeError

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.services.websocket_manager import WebSocketManager
from src.dependencies import get_current_user
from src.models import User, Message, Chat
from src.api.websocket.schemas import ReceiveMessageSchema, SendMessageSchema
from src.api.chat.services import get_chat_by_guid

from typing import Annotated
from uuid import UUID

logger = logging.getLogger(__name__)


websocket_router = APIRouter()

socket_manager = WebSocketManager()


@websocket_router.websocket("/ws/")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_guid: Annotated[UUID | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    await socket_manager.connect_socket(websocket=websocket)
    await websocket.send_json({"message": "You are connected", "user": "Bekzod"})

    # keep track of open redis pub/sub channels holds guid/id key-value pairs
    chats = dict()

    try:
        while True:
            try:
                is_new_message = False
                incoming_message = await websocket.receive_json()
                # Get chat guid as a first message
                if "chatGUID" in incoming_message:
                    chat_guid = incoming_message["chatGUID"]
                    # create channel and subscribe
                    await socket_manager.add_user_to_chat(chat_guid, websocket)

                else:
                    message_schema = ReceiveMessageSchema(**incoming_message)
                    chat_guid = str(message_schema.chat_guid)
                    is_new_message = True

                if chat_guid not in chats:
                    chat: Chat = await get_chat_by_guid(db_session, chat_guid=chat_guid)
                    # Validate that chat exists
                    if not chat:
                        logger.exception(f"Could not find chat with provided guid: {chat_guid}")
                        await socket_manager.send_error(f"Chat with guid {chat_guid} does not exist", websocket)

                    # await socket_manager.add_user_to_chat(chat_guid, websocket)
                    chats[chat_guid] = chat.id

                if is_new_message:
                    # get chat id for message to broadcast
                    chat_id = chats.get(chat_guid)
                    # Save message and broadcast it back
                    message = Message(
                        content=message_schema.content,
                        chat_id=chat_id,
                        user_id=current_user.id,
                    )
                    db_session.add(message)
                    await db_session.commit()

                    send_message_schema = SendMessageSchema.model_validate(message, from_attributes=True)
                    outgoing_message: dict = send_message_schema.model_dump_json()
                    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)

            except (JSONDecodeError, AttributeError) as excinfo:
                logger.exception(f"Websocket error, detail: {excinfo}")
                await socket_manager.send_error("Wrong message format", websocket)
                continue
            except ValueError as excinfo:
                logger.exception(f"Websocket error, detail: {excinfo}")
                await socket_manager.send_error("Could not validate incoming message", websocket)

    except WebSocketDisconnect:
        for chat_guid in chats.keys():
            await socket_manager.remove_user_from_chat(chat_guid, websocket)
            await socket_manager.broadcast_to_chat(chat_guid, {"message": "user disconnected"})
