from src.websocket.exceptions import WebsocketTooManyRequests


async def websocket_callback(ws, pexpire):
    raise WebsocketTooManyRequests("Too many requests")
