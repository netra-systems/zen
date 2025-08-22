import json
from typing import Any, Dict

from fastapi import WebSocket


class DevBypassService:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def handle_message(self, data: Dict[str, Any]):
        # Echo the message back to the client
        await self.websocket.send_json({"echo": data})