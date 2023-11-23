import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_pagination import add_pagination
from sqladmin import Admin

from src.admin.admin import admin_models
from src.admin.authentication_backend import authentication_backend
from src.api.authentication.router import auth_router
from src.api.chat.router import chat_router
from src.api.contact.router import contact_router
from src.api.registration.router import account_router
from src.api.websocket.router import websocket_router
from src.config import settings
from src.database import engine

app = FastAPI()
admin = Admin(app, engine, authentication_backend=authentication_backend)

app.include_router(websocket_router)
app.include_router(account_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(contact_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_pagination(app)


redis_pool = aioredis.ConnectionPool(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=2
)


@app.on_event("startup")
async def startup():
    redis = aioredis.Redis(connection_pool=redis_pool)
    await FastAPILimiter.init(redis)


# Error displayed on shutdown (will be fixed in later versions): https://github.com/python/cpython/issues/109538
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutdown complete.")


# register admin models
for model in admin_models:
    admin.add_view(model)
