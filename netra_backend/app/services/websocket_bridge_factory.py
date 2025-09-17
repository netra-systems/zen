"""
WebSocket Bridge Factory - Compatibility Import Module

This module provides backward compatibility for tests and components that expect
to import WebSocket bridge factory classes from the services directory.

The actual implementation is in netra_backend.app.factories.websocket_bridge_factory.
This module re-exports those classes for compatibility.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Backward compatibility for existing test infrastructure
- Value Impact: Prevents test breakage during factory migration
- Revenue Impact: Maintains test coverage for $500K+ ARR chat functionality
"""

# Re-export all classes from the actual factory module for backward compatibility
from netra_backend.app.factories.websocket_bridge_factory import (
    StandardWebSocketBridge,
    WebSocketBridgeAdapter,
    WebSocketBridgeFactory,
    get_websocket_bridge_factory,  # Added missing function
    reset_websocket_bridge_factory,
    create_standard_websocket_bridge,
    create_agent_bridge_adapter,
    create_websocket_bridge_for_testing,
    create_websocket_bridge_with_context,
    AgentWebSocketBridge,
    create_agent_websocket_bridge,
)

# Additional classes that some tests may expect
try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UserWebSocketEmitter
except ImportError:
    # Fallback if import fails
    UserWebSocketEmitter = None

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext as UserWebSocketContext
except ImportError:
    # Fallback if import fails
    UserWebSocketContext = None

# Export all for backward compatibility
__all__ = [
    "StandardWebSocketBridge",
    "WebSocketBridgeAdapter",
    "WebSocketBridgeFactory",
    "get_websocket_bridge_factory",  # Added missing function
    "reset_websocket_bridge_factory",
    "create_standard_websocket_bridge",
    "create_agent_bridge_adapter",
    "create_websocket_bridge_for_testing",
    "create_websocket_bridge_with_context",
    "AgentWebSocketBridge",
    "create_agent_websocket_bridge",
    "UserWebSocketEmitter",
    "UserWebSocketContext",
]