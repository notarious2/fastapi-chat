from src.authentication.router import auth_router
from src.chat.router import chat_router
from src.contact.router import contact_router
from src.registration.router import account_router
from src.settings.router import settings_router
from src.websocket.router import websocket_router

routers = [
    websocket_router,
    account_router,
    auth_router,
    chat_router,
    contact_router,
    settings_router,
]
