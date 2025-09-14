"""
Message Router - Services Module Compatibility Layer

This module provides a compatibility layer for integration tests that expect
MessageRouter in the services module. The actual implementation is in
the websocket_core module.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Re-exports the canonical MessageRouter from websocket_core.handlers
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

# Import the canonical MessageRouter implementation
from netra_backend.app.websocket_core.handlers import MessageRouter

# Import related types and enums that tests might expect
from netra_backend.app.websocket_core.types import (
    MessageType,
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    BroadcastMessage
)

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Log compatibility usage for monitoring
logger.info("MessageRouter compatibility layer loaded from services module")

# Re-export for compatibility
__all__ = [
    'MessageRouter',
    'MessageType', 
    'WebSocketMessage',
    'ServerMessage',
    'ErrorMessage',
    'BroadcastMessage'
]