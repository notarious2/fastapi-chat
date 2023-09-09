from fastapi import FastAPI, WebSocket


app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/messages/")
async def get_messages():
    message_history = []

    for i in range(1, 21):
        if i%2 == 0:
            message_history.append({"number": i, "user": "Bekzod", "message": f"My message #{i}"})
        else:
            message_history.append({"number": i, "user": "Vasya", "message": f"Hey bro, this is my message #{i}"}) 

    # for i in range(20):
    #     message_history.append(i)
    # message_history.reverse()

    return message_history



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"message": f"{data}", "user": "Bekzod"})