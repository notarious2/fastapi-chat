import asyncio
import json

from fastapi import WebSocket

from src.services.pubsub_manager import RedisPubSubManager


class WebSocketManager:
    def __init__(self):
        self.handlers: dict = {}
        self.chats: dict = {}  # stores WebSocket connections in different chats
        self.pubsub_client = RedisPubSubManager()

    def handler(self, message_type):
        def decorator(func):
            self.handlers[message_type] = func
            return func

        return decorator

    async def connect_socket(self, websocket: WebSocket):
        await websocket.accept()

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
            await self.pubsub_client.unsubscribe(chat_guid)

    async def _pubsub_data_reader(self, pubsub_subscriber):
        while True:
            message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
            if message is not None:
                chat_guid = message["channel"].decode("utf-8")
                all_sockets = self.chats[chat_guid]
                for socket in all_sockets:
                    data = message["data"].decode("utf-8")
                    await socket.send_text(data)

    async def send_error(self, message: str, websocket: WebSocket):
        await websocket.send_json({"status": "error", "message": message})
