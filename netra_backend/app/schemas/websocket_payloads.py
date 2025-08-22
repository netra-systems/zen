"""WebSocket payload classes for type safety compliance.

This module contains additional WebSocket payload classes that extend the base
payload classes from registry.py, following the single source of truth principle.

ARCHITECTURAL COMPLIANCE:
- File limit: 300 lines maximum
- Function limit: 8 lines maximum
- Imports from registry.py as single source of truth
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.registry import BaseWebSocketPayload


class RenameThreadPayload(BaseWebSocketPayload):
    """Payload for renaming a thread."""
    thread_id: str
    new_title: str


class ListThreadsPayload(BaseWebSocketPayload):
    """Payload for listing threads."""
    pass  # No additional fields needed


class ThreadHistoryPayload(BaseWebSocketPayload):
    """Payload for getting thread history."""
    thread_id: str
    limit: Optional[int] = Field(default=50, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)


class AgentStartedPayload(BaseWebSocketPayload):
    """Payload for agent started message."""
    run_id: str
    agent_type: Optional[str] = None


class AgentErrorPayload(BaseWebSocketPayload):
    """Payload for agent error message."""
    run_id: str
    message: str
    code: str
    severity: Optional[ErrorSeverity] = ErrorSeverity.MEDIUM


class ToolStartedPayload(BaseWebSocketPayload):
    """Payload for tool started message."""
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    run_id: str


class ToolCompletedPayload(BaseWebSocketPayload):
    """Payload for tool completed message."""
    tool_name: str
    tool_output: Optional[Union[str, Dict[str, Any]]] = None
    run_id: str
    status: str


class ToolCallPayload(BaseWebSocketPayload):
    """Payload for tool call message."""
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    run_id: str


class ToolResultPayload(BaseWebSocketPayload):
    """Payload for tool result message."""
    tool_name: str
    result: Optional[Union[str, Dict[str, Any]]] = None
    run_id: str


class SubAgentStartedPayload(BaseWebSocketPayload):
    """Payload for sub-agent started message."""
    subagent_id: str
    subagent_type: str
    parent_run_id: str


class SubAgentCompletedPayload(BaseWebSocketPayload):
    """Payload for sub-agent completed message."""
    subagent_id: str
    result: Optional[Dict[str, Any]] = None
    parent_run_id: str


class ThreadCreatedPayload(BaseWebSocketPayload):
    """Payload for thread created message."""
    thread_id: str
    title: str


class ThreadSwitchedPayload(BaseWebSocketPayload):
    """Payload for thread switched message."""
    thread_id: str
    previous_thread_id: Optional[str] = None


class ThreadDeletedPayload(BaseWebSocketPayload):
    """Payload for thread deleted message."""
    thread_id: str


class ThreadRenamedPayload(BaseWebSocketPayload):
    """Payload for thread renamed message."""
    thread_id: str
    new_title: str


class ThreadListPayload(BaseWebSocketPayload):
    """Payload for thread list message."""
    threads: List[Dict[str, str]] = Field(default_factory=list)


class StreamChunkPayload(BaseWebSocketPayload):
    """Payload for stream chunk message."""
    content: str
    index: int
    finished: bool = False
    metadata: Optional[Dict[str, Any]] = None


class StreamCompletePayload(BaseWebSocketPayload):
    """Payload for stream complete message."""
    total_chunks: int
    total_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ErrorPayload(BaseWebSocketPayload):
    """Payload for error message."""
    message: str
    code: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    details: Optional[Dict[str, Any]] = None


class ConnectionEstablishedPayload(BaseWebSocketPayload):
    """Payload for connection established message."""
    connection_id: str
    session_id: Optional[str] = None
    server_version: Optional[str] = None


# Message wrapper classes for type safety
from netra_backend.app.schemas.registry import WebSocketMessage, WebSocketMessageType


class BaseWebSocketMessage(WebSocketMessage):
    """Base WebSocket message with correlation support."""
    correlation_id: Optional[str] = None


class ClientToServerMessage(BaseWebSocketMessage):
    """Client-to-server WebSocket message."""
    pass


class ServerToClientMessage(BaseWebSocketMessage):
    """Server-to-client WebSocket message."""
    pass


# Export all payload classes
__all__ = [
    "RenameThreadPayload", "ListThreadsPayload", "ThreadHistoryPayload",
    "AgentStartedPayload", "AgentErrorPayload", "ToolStartedPayload",
    "ToolCompletedPayload", "ToolCallPayload", "ToolResultPayload",
    "SubAgentStartedPayload", "SubAgentCompletedPayload", "ThreadCreatedPayload",
    "ThreadSwitchedPayload", "ThreadDeletedPayload", "ThreadRenamedPayload",
    "ThreadListPayload", "StreamChunkPayload", "StreamCompletePayload",
    "ErrorPayload", "ConnectionEstablishedPayload",
    "BaseWebSocketMessage", "ClientToServerMessage", "ServerToClientMessage"
]