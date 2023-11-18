from uuid import UUID

import redis.asyncio as aioredis

from src.config import settings


class RedisPubSubManager:
    def __init__(self):
        self.pubsub = None

    async def _get_redis_connection(self) -> aioredis.Redis:
        pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=1
        )
        return aioredis.Redis(connection_pool=pool)

    async def connect(self):
        self.redis_connection = await self._get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def subscribe(self, chat_guid: UUID) -> aioredis.Redis:
        await self.pubsub.subscribe(chat_guid)
        return self.pubsub

    async def unsubscribe(self, chat_guid: UUID):
        await self.pubsub.unsubscribe(chat_guid)

    async def publish(self, chat_guid: UUID, message: str):
        await self.redis_connection.publish(chat_guid, message)

    async def disconnect(self):
        await self.redis_connection.close()
