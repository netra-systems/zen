"""Strong type definitions for WebSocket messages and payloads.

This module provides TypedDict and Pydantic models for all WebSocket
message types to ensure type safety across the application.

NOTE: This module avoids duplicating types already defined in other schemas.
It imports and reuses existing types where possible.
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Import existing types to avoid duplication
from app.schemas.Request import StartAgentPayload as StartAgentPayloadPydantic


# TypedDict definitions for WebSocket messages
class BaseMessagePayload(TypedDict):
    """Base payload structure"""
    pass


class UserMessagePayload(TypedDict):
    """Payload for user_message"""
    text: str
    references: Optional[List[str]]
    thread_id: Optional[str]


class CreateThreadPayload(TypedDict):
    """Payload for create_thread"""
    name: Optional[str]
    metadata: Optional[Dict[str, Any]]


class SwitchThreadPayload(TypedDict):
    """Payload for switch_thread"""
    thread_id: str


class DeleteThreadPayload(TypedDict):
    """Payload for delete_thread"""
    thread_id: str


class ThreadHistoryResponse(TypedDict):
    """Response structure for thread history"""
    thread_id: str
    messages: List[Dict[str, Any]]


class AgentCompletedPayload(TypedDict):
    """Payload for agent_completed message"""
    response: Any
    thread_id: Optional[str]
    run_id: Optional[str]


class AgentStoppedPayload(TypedDict):
    """Payload for agent_stopped message"""
    status: Literal["stopped"]


class ErrorPayload(TypedDict):
    """Payload for error messages"""
    error: str
    code: Optional[str]
    details: Optional[Dict[str, Any]]


# Message type literals
MessageTypeLiteral = Literal[
    "start_agent",
    "user_message",
    "get_thread_history",
    "stop_agent",
    "create_thread",
    "switch_thread",
    "delete_thread",
    "list_threads",
    "agent_completed",
    "agent_stopped",
    "thread_history",
    "error",
    "agent_update",
    "tool_started",
    "tool_completed",
    "subagent_started",
    "subagent_completed"
]


class WebSocketMessageIn(TypedDict):
    """Incoming WebSocket message structure"""
    type: MessageTypeLiteral
    payload: Optional[Dict[str, Any]]


class WebSocketMessageOut(TypedDict):
    """Outgoing WebSocket message structure"""
    type: MessageTypeLiteral
    payload: Dict[str, Any]
    timestamp: Optional[str]


# Pydantic models for validation
class WebSocketRequest(BaseModel):
    """Base model for WebSocket requests"""
    type: MessageTypeLiteral
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_message",
                "payload": {
                    "text": "Analyze my workload",
                    "thread_id": "thread-123"
                }
            }
        }


class WebSocketResponse(BaseModel):
    """Base model for WebSocket responses"""
    type: MessageTypeLiteral
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "agent_completed",
                "payload": {"response": "Analysis complete"},
                "timestamp": "2025-01-12T10:00:00Z"
            }
        }


class ThreadMessage(BaseModel):
    """Model for a message in a thread"""
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    references: Optional[List[str]] = None


class ThreadInfo(BaseModel):
    """Model for thread information"""
    id: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0


class AgentUpdatePayload(BaseModel):
    """Payload for agent update messages"""
    status: Literal["thinking", "planning", "executing", "completed", "error"]
    message: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    current_task: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolInvocationPayload(BaseModel):
    """Payload for tool invocation messages"""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_id: str
    status: Literal["started", "completed", "error"]
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class SubAgentPayload(BaseModel):
    """Payload for sub-agent messages"""
    agent_name: str
    agent_id: str
    status: Literal["started", "running", "completed", "error"]
    task: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Type aliases for better readability
ParsedMessage = Union[WebSocketMessageIn, Dict[str, Any]]
MessageHandler = Dict[MessageTypeLiteral, Any]  # Maps message types to handler functions