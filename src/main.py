import redis.asyncio as aioredis
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from fastapi_pagination import add_pagination

from src.api.authentication.router import auth_router
from src.api.chat.router import chat_router
from src.api.registration.router import account_router
from src.api.websocket.router import websocket_router
from src.config import settings

app = FastAPI()

app.include_router(websocket_router)
app.include_router(account_router)
app.include_router(auth_router)
app.include_router(chat_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_pagination(app)


redis_pool = aioredis.ConnectionPool(
    host=settings.redis_host, port=settings.redis_port, password=settings.redis_password, db=2
)


@app.on_event("startup")
async def startup():
    redis = aioredis.Redis(connection_pool=redis_pool)
    await FastAPILimiter.init(redis)


@app.get("/messages/", dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def get_messages():
    message_history = []

    for i in range(1, 21):
        if i % 2 == 0:
            message_history.append({"number": i, "user": "Bekzod", "message": f"My message #{i}"})
        else:
            message_history.append({"number": i, "user": "Vasya", "message": f"Hey bro, this is my message #{i}"})

    for i in range(20):
        message_history.append(i)
    message_history.reverse()

    return message_history
