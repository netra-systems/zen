import uuid
import enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class MessageType(str, enum.Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    ERROR = "error"
    TOOL = "tool"


class Message(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    content: str
    type: MessageType
    sub_agent_name: Optional[str] = None
    tool_info: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    displayed_to_user: bool = True
