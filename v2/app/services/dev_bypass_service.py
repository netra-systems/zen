
from fastapi import WebSocket
import json

class DevBypassService:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def handle_message(self, data: str):
        # Echo the message back to the client
        await self.websocket.send_text(f"Echo: {data}")
