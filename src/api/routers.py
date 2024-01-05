from src.api.authentication.router import auth_router
from src.api.chat.router import chat_router
from src.api.contact.router import contact_router
from src.api.registration.router import account_router
from src.api.settings.router import settings_router
from src.api.websocket.router import websocket_router

routers = [
    websocket_router,
    account_router,
    auth_router,
    chat_router,
    contact_router,
    settings_router,
]
