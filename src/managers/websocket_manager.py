import asyncio
import json
import logging

from fastapi import WebSocket

from src.managers.pubsub_manager import RedisPubSubManager

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.handlers: dict = {}
        self.chats: dict = {}  # stores user WebSocket connections by chat {"chat_guid": {ws1, ws2}, ...}
        self.pubsub_client = RedisPubSubManager()
        self.user_guid_to_websocket: dict = {}  # stores user_guid: {ws1, ws2} combinations

    def handler(self, message_type):
        def decorator(func):
            self.handlers[message_type] = func
            return func

        return decorator

    async def connect_socket(self, websocket: WebSocket):
        await websocket.accept()

    async def add_user_socket_connection(self, user_guid: str, websocket: WebSocket):
        self.user_guid_to_websocket.setdefault(user_guid, set()).add(websocket)

    async def add_user_to_chat(self, chat_guid: str, websocket: WebSocket):
        if chat_guid in self.chats:
            self.chats[chat_guid].add(websocket)
        else:
            self.chats[chat_guid] = {websocket}
            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(chat_guid)
            asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))

    async def broadcast_to_chat(self, chat_guid: str, message: str | dict) -> None:
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.pubsub_client.publish(chat_guid, message)

    async def remove_user_from_chat(self, chat_guid: str, websocket: WebSocket) -> None:
        self.chats[chat_guid].remove(websocket)
        if len(self.chats[chat_guid]) == 0:
            del self.chats[chat_guid]
            logger.info("Removing user from PubSub channel {chat_guid}")
            await self.pubsub_client.unsubscribe(chat_guid)

    async def remove_user_guid_to_websocket(self, user_guid: str, websocket: WebSocket):
        if user_guid in self.user_guid_to_websocket:
            self.user_guid_to_websocket.get(user_guid).remove(websocket)

    # https://github.com/redis/redis-py/issues/2523
    async def _pubsub_data_reader(self, pubsub_subscriber):
        try:
            while True:
                message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    chat_guid = message["channel"].decode("utf-8")
                    sockets = self.chats.get(chat_guid)
                    if sockets:
                        for socket in sockets:
                            data = message["data"].decode("utf-8")
                            await socket.send_text(data)
        except Exception as exc:
            logger.exception(f"Exception occurred: {exc}")

    async def send_error(self, message: str, websocket: WebSocket):
        await websocket.send_json({"status": "error", "message": message})
