from fastapi import WebSocket
import json
from typing import Dict, Any

class DevBypassService:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def handle_message(self, data: Dict[str, Any]):
        # Echo the message back to the client
        await self.websocket.send_json({"echo": data})