from pydantic import BaseModel
from typing import Dict, Any

class WebSocketMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
    sender: str | None = None
