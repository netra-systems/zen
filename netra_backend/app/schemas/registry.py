"""
Type Registry: Single Source of Truth for All Python Types

This module serves as the central registry for all type definitions in the Netra platform,
eliminating duplication and ensuring consistency across the entire codebase.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All type definitions MUST be imported from this registry
- NO duplicate type definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (ACHIEVED by modular design)

The registry now imports from focused modules to maintain the 450-line limit:
- core_enums.py: All enumeration types
- core_models.py: User, Message, Thread models  
- agent_models.py: Agent-related models and states
- websocket_models.py: WebSocket message types and payloads
- audit_models.py: Corpus audit models

Usage:
    from netra_backend.app.schemas.registry import User, Message, AgentState, WebSocketMessage
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

# Import all agent models from the dedicated module
from netra_backend.app.schemas.agent_models import (
    AgentMetadata,
    AgentResult,
    AgentState,
    DeepAgentState,
    ToolResultData,
)

# Import all audit models from the dedicated module
from netra_backend.app.schemas.audit_models import (
    CorpusAuditMetadata,
    CorpusAuditRecord,
    CorpusAuditReport,
    CorpusAuditSearchFilter,
)

# ============================================================================
# IMPORTS FROM FOCUSED MODULES (450-line COMPLIANCE)
# ============================================================================
# Import all enums from the dedicated module
from netra_backend.app.schemas.core_enums import (
    AgentStatus,
    CorpusAuditAction,
    CorpusAuditStatus,
    MessageType,
    MessageTypeLiteral,
    TaskPriority,
    WebSocketConnectionState,
    WebSocketMessageType,
)

# Import all core models from the dedicated module
from netra_backend.app.schemas.core_models import (
    Message,
    MessageMetadata,
    Optimization,
    Thread,
    ThreadMetadata,
    User,
    UserBase,
    UserCreate,
    UserCreateOAuth,
)

# Import all WebSocket models from the dedicated module
from netra_backend.app.schemas.websocket_models import (
    AgentCompleted,
    AgentCompletedPayload,
    AgentLog,
    AgentMessage,
    AgentResponse,
    AgentResponseData,
    AgentStarted,
    AgentStoppedPayload,
    AgentUpdate,
    AgentUpdatePayload,
    AnalysisRequest,
    BaseWebSocketPayload,
    BroadcastResult,
    CreateThreadPayload,
    DeleteThreadPayload,
    MessageData,
    MessageToUser,
    RateLimitInfo,
    ServerMessage,
    StartAgentPayload,
    StopAgent,
    StopAgentPayload,
    StreamChunk,
    StreamComplete,
    StreamEvent,
    SubAgentUpdate,
    SwitchThreadPayload,
    ThreadHistoryResponse,
    ToolCall,
    ToolResult,
    UserMessage,
    UserMessagePayload,
    WebSocketError,
    WebSocketMessage,
    WebSocketMessageIn,
    WebSocketStats,
    WebSocketValidationError,
)

# Import additional WebSocket message types from websocket_payloads
from netra_backend.app.schemas.websocket_payloads import (
    BaseWebSocketMessage,
    ClientToServerMessage,
    ServerToClientMessage,
)

# ============================================================================
# BACKWARD COMPATIBILITY AND EXPORTS
# ============================================================================


# ============================================================================
# EXPORTS - EXPLICIT TYPE REGISTRY
# ============================================================================

# Core domain types - maintaining complete backward compatibility
__all__ = [
    # Enums
    "MessageType", "AgentStatus", "WebSocketMessageType", "WebSocketConnectionState",
    "CorpusAuditAction", "CorpusAuditStatus", "TaskPriority", "MessageTypeLiteral",
    
    # Core models  
    "UserBase", "UserCreate", "UserCreateOAuth", "User", "Message", "Thread", "Optimization",
    "MessageMetadata", "ThreadMetadata",
    
    # Agent models
    "DeepAgentState", "AgentState", "AgentResult", "AgentMetadata", "ToolResultData",
    
    # WebSocket models
    "WebSocketMessage", "WebSocketError", "BaseWebSocketPayload", 
    "UserMessagePayload", "AgentUpdatePayload", "MessageToUser", "AnalysisRequest",
    "UserMessage", "AgentMessage", "StopAgent", "StopAgentPayload", "StreamEvent",
    "AgentStarted", "SubAgentUpdate", "AgentCompleted", "StartAgentPayload",
    "WebSocketMessageIn", "CreateThreadPayload", "SwitchThreadPayload", 
    "DeleteThreadPayload", "MessageData", "ThreadHistoryResponse",
    "AgentResponseData", "AgentResponse", "AgentCompletedPayload", "AgentStoppedPayload",
    "AgentUpdate", "AgentLog", "ToolCall", "ToolResult", "StreamChunk", "StreamComplete",
    "BaseWebSocketMessage", "ClientToServerMessage", "ServerToClientMessage", "ServerMessage",
    
    # Audit models
    "CorpusAuditRecord", "CorpusAuditMetadata", "CorpusAuditSearchFilter", 
    "CorpusAuditReport",
]


# Type registry for programmatic access - maintains all existing types
TYPE_REGISTRY = {
    # Core models
    "UserBase": UserBase,
    "UserCreate": UserCreate,
    "UserCreateOAuth": UserCreateOAuth,
    "User": User,
    "Message": Message, 
    "Thread": Thread,
    "Optimization": Optimization,
    "MessageMetadata": MessageMetadata,
    "ThreadMetadata": ThreadMetadata,
    
    # Agent models
    "DeepAgentState": DeepAgentState,
    "AgentState": AgentState,  # Backward compatibility
    "AgentResult": AgentResult,
    "AgentMetadata": AgentMetadata,
    "ToolResultData": ToolResultData,
    
    # WebSocket models
    "WebSocketMessage": WebSocketMessage,
    "WebSocketError": WebSocketError,
    "BaseWebSocketPayload": BaseWebSocketPayload,
    "UserMessagePayload": UserMessagePayload,
    "AgentUpdatePayload": AgentUpdatePayload,
    "StartAgentPayload": StartAgentPayload,
    "CreateThreadPayload": CreateThreadPayload,
    "SwitchThreadPayload": SwitchThreadPayload,
    "DeleteThreadPayload": DeleteThreadPayload,
    "WebSocketMessageIn": WebSocketMessageIn,
    "MessageData": MessageData,
    "ThreadHistoryResponse": ThreadHistoryResponse,
    "AgentResponseData": AgentResponseData,
    "AgentResponse": AgentResponse,
    "AgentCompletedPayload": AgentCompletedPayload,
    "AgentStoppedPayload": AgentStoppedPayload,
    "MessageToUser": MessageToUser,
    "AnalysisRequest": AnalysisRequest,
    "UserMessage": UserMessage,
    "AgentMessage": AgentMessage,
    "StopAgent": StopAgent,
    "StopAgentPayload": StopAgentPayload,
    "AgentUpdate": AgentUpdate,
    "AgentLog": AgentLog,
    "ToolCall": ToolCall,
    "ToolResult": ToolResult,
    "StreamChunk": StreamChunk,
    "StreamComplete": StreamComplete,
    "StreamEvent": StreamEvent,
    "AgentStarted": AgentStarted,
    "SubAgentUpdate": SubAgentUpdate,
    "AgentCompleted": AgentCompleted,
    "BaseWebSocketMessage": BaseWebSocketMessage,
    "ClientToServerMessage": ClientToServerMessage,
    "ServerToClientMessage": ServerToClientMessage,
    "ServerMessage": ServerMessage,
    
    # Enums
    "MessageType": MessageType,
    "AgentStatus": AgentStatus,
    "WebSocketMessageType": WebSocketMessageType,
    "WebSocketConnectionState": WebSocketConnectionState,
    "MessageTypeLiteral": MessageTypeLiteral,
    "CorpusAuditAction": CorpusAuditAction,
    "CorpusAuditStatus": CorpusAuditStatus,
    "TaskPriority": TaskPriority,
    
    # Audit models
    "CorpusAuditRecord": CorpusAuditRecord,
    "CorpusAuditMetadata": CorpusAuditMetadata,
    "CorpusAuditSearchFilter": CorpusAuditSearchFilter,
    "CorpusAuditReport": CorpusAuditReport,
}


def get_type(type_name: str) -> Optional[type]:
    """Get a type from the registry by name."""
    return TYPE_REGISTRY.get(type_name)


def list_registered_types() -> List[str]:
    """List all registered type names."""
    return list(TYPE_REGISTRY.keys())