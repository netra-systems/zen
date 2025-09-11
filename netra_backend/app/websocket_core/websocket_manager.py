"""WebSocket Manager - SSOT for WebSocket Management

This module provides the unified WebSocket manager interface for the Golden Path.
It serves as the primary interface for WebSocket operations while maintaining
compatibility with legacy imports.

CRITICAL: This module supports the Golden Path user flow requirements:
- User isolation via ExecutionEngineFactory pattern
- WebSocket event emission (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Connection state management for race condition prevention

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Enable reliable WebSocket communication for Golden Path
- Value Impact: Critical infrastructure for AI chat interactions
- Revenue Impact: Foundation for all AI-powered user interactions
"""

from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    _serialize_message_safely
)
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.logging_config import central_logger
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, 
    ensure_user_id, ensure_thread_id
)
from typing import Dict, Set, Optional, Any, Union
from datetime import datetime

logger = central_logger.get_logger(__name__)

# Export the SSOT unified manager as WebSocketManager for compatibility
# This creates a direct reference to the singleton WebSocketManager class
WebSocketManager = UnifiedWebSocketManager

# Export the protocol for type checking
__all__ = [
    'WebSocketManager',
    'WebSocketConnection', 
    'WebSocketManagerProtocol',
    '_serialize_message_safely'
]

logger.info("WebSocket Manager module loaded - Golden Path compatible")