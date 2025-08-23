"""
WebSocket Message Types

Message type definitions for WebSocket communication.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class MessageType(Enum):
    """WebSocket message types."""
    THREAD_UPDATE = "thread_update"
    THREAD_CREATE = "thread_create"
    THREAD_DELETE = "thread_delete"
    AGENT_RESPONSE = "agent_response"
    USER_MESSAGE = "user_message"
    STATUS_UPDATE = "status_update"

@dataclass
class ThreadUpdateMessage:
    """Thread update message structure."""
    thread_id: str
    title: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class ThreadCreatedMessage:
    """Thread creation message structure."""
    thread_id: str
    title: str
    user_id: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ThreadUpdatedMessage:
    """Thread update message structure."""
    thread_id: str
    user_id: str
    timestamp: str
    updates: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AgentResponseMessage:
    """Agent response message structure."""
    agent_id: str
    thread_id: str
    content: str
    response_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class UserMessage:
    """User message structure."""
    user_id: str
    thread_id: str
    content: str
    timestamp: str
    message_id: Optional[str] = None
