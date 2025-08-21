"""
WebSocket Server Messages: Server-to-Client Message Types

This module contains all server-to-client WebSocket message types used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All server WebSocket message definitions MUST be imported from this module
- NO duplicate server WebSocket message definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.websocket_server_messages import AgentStartedMessage, AgentCompletedMessage
"""

from typing import Any, Dict, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Import WebSocket base types from registry to avoid circular imports
from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.core_enums import WebSocketMessageType, AgentStatus


# Base class for server messages
class ServerMessage(WebSocketMessage):
    """Base class for server-to-client messages."""
    pass


# Server-to-client message types
class AgentStartedMessage(ServerMessage):
    """Message indicating agent has started."""
    type: Literal[WebSocketMessageType.AGENT_STARTED] = WebSocketMessageType.AGENT_STARTED
    payload: Dict[str, Any] = Field(description="Agent start confirmation data")


class AgentCompletedMessage(ServerMessage):
    """Message indicating agent has completed."""
    type: Literal[WebSocketMessageType.AGENT_COMPLETED] = WebSocketMessageType.AGENT_COMPLETED
    payload: Dict[str, Any] = Field(description="Agent completion data and results")


class AgentStoppedMessage(ServerMessage):
    """Message indicating agent was stopped."""
    type: Literal[WebSocketMessageType.AGENT_STOPPED] = WebSocketMessageType.AGENT_STOPPED
    payload: Dict[str, Any] = Field(description="Agent stop confirmation")


class AgentErrorMessage(ServerMessage):
    """Message indicating agent error."""
    type: Literal[WebSocketMessageType.AGENT_ERROR] = WebSocketMessageType.AGENT_ERROR
    payload: Dict[str, Any] = Field(description="Error details")


class AgentUpdateMessage(ServerMessage):
    """Real-time agent status update."""
    type: Literal[WebSocketMessageType.AGENT_UPDATE] = WebSocketMessageType.AGENT_UPDATE
    payload: Dict[str, Any] = Field(description="Agent status and progress data")


class AgentLogMessage(ServerMessage):
    """Agent log message for monitoring."""
    type: Literal[WebSocketMessageType.AGENT_LOG] = WebSocketMessageType.AGENT_LOG
    payload: Dict[str, Any] = Field(description="Log data with level, message, sub_agent_name")


class ToolStartedMessage(ServerMessage):
    """Message indicating tool execution started."""
    type: Literal[WebSocketMessageType.TOOL_STARTED] = WebSocketMessageType.TOOL_STARTED
    payload: Dict[str, Any] = Field(description="Tool execution start data")


class ToolCompletedMessage(ServerMessage):
    """Message indicating tool execution completed."""
    type: Literal[WebSocketMessageType.TOOL_COMPLETED] = WebSocketMessageType.TOOL_COMPLETED
    payload: Dict[str, Any] = Field(description="Tool execution completion data")


class ToolCallMessage(ServerMessage):
    """Message indicating tool is being called."""
    type: Literal[WebSocketMessageType.TOOL_CALL] = WebSocketMessageType.TOOL_CALL
    payload: Dict[str, Any] = Field(description="Tool call data with name, args, sub_agent_name")


class ToolResultMessage(ServerMessage):
    """Message with tool execution result."""
    type: Literal[WebSocketMessageType.TOOL_RESULT] = WebSocketMessageType.TOOL_RESULT
    payload: Dict[str, Any] = Field(description="Tool result data with name, result, sub_agent_name")


class SubAgentStartedMessage(ServerMessage):
    """Message indicating sub-agent started."""
    type: Literal[WebSocketMessageType.SUBAGENT_STARTED] = WebSocketMessageType.SUBAGENT_STARTED
    payload: Dict[str, Any] = Field(description="Sub-agent start data")


class SubAgentCompletedMessage(ServerMessage):
    """Message indicating sub-agent completed."""
    type: Literal[WebSocketMessageType.SUBAGENT_COMPLETED] = WebSocketMessageType.SUBAGENT_COMPLETED
    payload: Dict[str, Any] = Field(description="Sub-agent completion data")


class ThreadHistoryMessage(ServerMessage):
    """Message containing thread history."""
    type: Literal[WebSocketMessageType.THREAD_HISTORY] = WebSocketMessageType.THREAD_HISTORY
    payload: Dict[str, Any] = Field(description="Thread history data")


class ErrorMessage(ServerMessage):
    """Error message."""
    type: Literal[WebSocketMessageType.ERROR] = WebSocketMessageType.ERROR
    payload: Dict[str, Any] = Field(description="Error details with error, code, sub_agent_name")


class ConnectionEstablishedMessage(ServerMessage):
    """Message confirming connection establishment."""
    type: Literal[WebSocketMessageType.CONNECTION_ESTABLISHED] = WebSocketMessageType.CONNECTION_ESTABLISHED
    payload: Dict[str, Any] = Field(description="Connection details")


class StreamChunkMessage(ServerMessage):
    """Streaming response chunk."""
    type: Literal[WebSocketMessageType.STREAM_CHUNK] = WebSocketMessageType.STREAM_CHUNK
    payload: Dict[str, Any] = Field(description="Stream chunk data")


class StreamCompleteMessage(ServerMessage):
    """Stream completion message."""
    type: Literal[WebSocketMessageType.STREAM_COMPLETE] = WebSocketMessageType.STREAM_COMPLETE
    payload: Dict[str, Any] = Field(description="Stream completion data")


class ThreadCreatedMessage(ServerMessage):
    """Message indicating thread has been created."""
    type: Literal[WebSocketMessageType.THREAD_CREATED] = WebSocketMessageType.THREAD_CREATED
    payload: Dict[str, Any] = Field(description="Thread creation data")


class ThreadUpdatedMessage(ServerMessage):
    """Message indicating thread has been updated."""
    type: Literal[WebSocketMessageType.THREAD_UPDATED] = WebSocketMessageType.THREAD_UPDATED
    payload: Dict[str, Any] = Field(description="Thread update data")


class ThreadDeletedMessage(ServerMessage):
    """Message indicating thread has been deleted."""
    type: Literal[WebSocketMessageType.THREAD_DELETED] = WebSocketMessageType.THREAD_DELETED
    payload: Dict[str, Any] = Field(description="Thread deletion data")


class ThreadLoadedMessage(ServerMessage):
    """Message indicating thread has been loaded."""
    type: Literal[WebSocketMessageType.THREAD_LOADED] = WebSocketMessageType.THREAD_LOADED
    payload: Dict[str, Any] = Field(description="Thread loading data")


class ThreadRenamedMessage(ServerMessage):
    """Message indicating thread has been renamed."""
    type: Literal[WebSocketMessageType.THREAD_RENAMED] = WebSocketMessageType.THREAD_RENAMED
    payload: Dict[str, Any] = Field(description="Thread rename data")


class ThreadSwitchedMessage(ServerMessage):
    """Message indicating thread has been switched."""
    type: Literal[WebSocketMessageType.THREAD_SWITCHED] = WebSocketMessageType.THREAD_SWITCHED
    payload: Dict[str, Any] = Field(description="Thread switch data")


class StepCreatedMessage(ServerMessage):
    """Message indicating step has been created."""
    type: Literal[WebSocketMessageType.STEP_CREATED] = WebSocketMessageType.STEP_CREATED
    payload: Dict[str, Any] = Field(description="Step creation data")


class ToolExecutingMessage(ServerMessage):
    """Message indicating tool is executing."""
    type: Literal[WebSocketMessageType.TOOL_EXECUTING] = WebSocketMessageType.TOOL_EXECUTING
    payload: Dict[str, Any] = Field(description="Tool execution data")


class AgentThinkingMessage(ServerMessage):
    """Message indicating agent is thinking."""
    type: Literal[WebSocketMessageType.AGENT_THINKING] = WebSocketMessageType.AGENT_THINKING
    payload: Dict[str, Any] = Field(description="Agent thinking data")


class PartialResultMessage(ServerMessage):
    """Message with partial result data."""
    type: Literal[WebSocketMessageType.PARTIAL_RESULT] = WebSocketMessageType.PARTIAL_RESULT
    payload: Dict[str, Any] = Field(description="Partial result data")


class FinalReportMessage(ServerMessage):
    """Message with final report data."""
    type: Literal[WebSocketMessageType.FINAL_REPORT] = WebSocketMessageType.FINAL_REPORT
    payload: Dict[str, Any] = Field(description="Final report data")


class MessageReceivedMessage(ServerMessage):
    """Message indicating a message has been received."""
    type: Literal[WebSocketMessageType.MESSAGE_RECEIVED] = WebSocketMessageType.MESSAGE_RECEIVED
    payload: Dict[str, Any] = Field(description="Message received confirmation data")


class MCPToolDiscoveryMessage(ServerMessage):
    """Message with MCP tool discovery results."""
    type: Literal[WebSocketMessageType.MCP_TOOL_DISCOVERY] = WebSocketMessageType.MCP_TOOL_DISCOVERY
    payload: Dict[str, Any] = Field(description="MCP tool discovery data with server_name, tools")


class MCPToolExecutionMessage(ServerMessage):
    """Message indicating MCP tool execution."""
    type: Literal[WebSocketMessageType.MCP_TOOL_EXECUTION] = WebSocketMessageType.MCP_TOOL_EXECUTION
    payload: Dict[str, Any] = Field(description="MCP tool execution data with server_name, tool_name, arguments")


class MCPToolResultMessage(ServerMessage):
    """Message with MCP tool execution result."""
    type: Literal[WebSocketMessageType.MCP_TOOL_RESULT] = WebSocketMessageType.MCP_TOOL_RESULT
    payload: Dict[str, Any] = Field(description="MCP tool result data with server_name, tool_name, result")


class MCPServerConnectedMessage(ServerMessage):
    """Message indicating MCP server connected."""
    type: Literal[WebSocketMessageType.MCP_SERVER_CONNECTED] = WebSocketMessageType.MCP_SERVER_CONNECTED
    payload: Dict[str, Any] = Field(description="MCP server connection data")


class MCPServerDisconnectedMessage(ServerMessage):
    """Message indicating MCP server disconnected."""
    type: Literal[WebSocketMessageType.MCP_SERVER_DISCONNECTED] = WebSocketMessageType.MCP_SERVER_DISCONNECTED
    payload: Dict[str, Any] = Field(description="MCP server disconnection data")


# Union type for all server-to-client messages
ServerMessageUnion = Union[
    AgentStartedMessage,
    AgentCompletedMessage,
    AgentStoppedMessage,
    AgentErrorMessage,
    AgentUpdateMessage,
    AgentLogMessage,
    AgentThinkingMessage,
    ToolStartedMessage,
    ToolCompletedMessage,
    ToolCallMessage,
    ToolResultMessage,
    ToolExecutingMessage,
    SubAgentStartedMessage,
    SubAgentCompletedMessage,
    ThreadHistoryMessage,
    ThreadCreatedMessage,
    ThreadUpdatedMessage,
    ThreadDeletedMessage,
    ThreadLoadedMessage,
    ThreadRenamedMessage,
    ThreadSwitchedMessage,
    StepCreatedMessage,
    PartialResultMessage,
    FinalReportMessage,
    MessageReceivedMessage,
    MCPToolDiscoveryMessage,
    MCPToolExecutionMessage,
    MCPToolResultMessage,
    MCPServerConnectedMessage,
    MCPServerDisconnectedMessage,
    ErrorMessage,
    ConnectionEstablishedMessage,
    StreamChunkMessage,
    StreamCompleteMessage
]


# Export all server message types
__all__ = [
    "AgentStartedMessage",
    "AgentCompletedMessage", 
    "AgentStoppedMessage",
    "AgentErrorMessage",
    "AgentUpdateMessage",
    "AgentLogMessage",
    "AgentThinkingMessage",
    "ToolStartedMessage",
    "ToolCompletedMessage",
    "ToolCallMessage", 
    "ToolResultMessage",
    "ToolExecutingMessage",
    "SubAgentStartedMessage",
    "SubAgentCompletedMessage",
    "ThreadHistoryMessage",
    "ThreadCreatedMessage",
    "ThreadUpdatedMessage",
    "ThreadDeletedMessage", 
    "ThreadLoadedMessage",
    "ThreadRenamedMessage",
    "ThreadSwitchedMessage",
    "StepCreatedMessage",
    "PartialResultMessage",
    "FinalReportMessage",
    "MessageReceivedMessage",
    "MCPToolDiscoveryMessage",
    "MCPToolExecutionMessage", 
    "MCPToolResultMessage",
    "MCPServerConnectedMessage",
    "MCPServerDisconnectedMessage",
    "ErrorMessage",
    "ConnectionEstablishedMessage",
    "StreamChunkMessage",
    "StreamCompleteMessage",
    "ServerMessageUnion"
]