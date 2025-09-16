"""
WebSocket Bridge Factory - WebSocket Core Compatibility Module

This module provides backward compatibility for tests and components that expect
to import WebSocket bridge factory classes from the websocket_core directory.

The actual implementation is in netra_backend.app.factories.websocket_bridge_factory.
This module re-exports those classes for compatibility.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Backward compatibility for existing test infrastructure
- Value Impact: Prevents test breakage during factory migration - fixes "0 tests executed but claiming success"
- Revenue Impact: Maintains test coverage for $500K+ ARR chat functionality

This module specifically addresses Issue #1176 by ensuring all import paths work correctly,
preventing the recursive manifestation pattern where tests silently fail due to import errors.
"""

# Re-export all classes from the actual factory module for backward compatibility
from netra_backend.app.factories.websocket_bridge_factory import (
    StandardWebSocketBridge,
    WebSocketBridgeAdapter,
    WebSocketBridgeFactory,
    create_standard_websocket_bridge,
    create_agent_bridge_adapter,
    create_websocket_bridge_for_testing,
    create_websocket_bridge_with_context,
    AgentWebSocketBridge,
    create_agent_websocket_bridge,
)

# Export all for backward compatibility
__all__ = [
    "StandardWebSocketBridge",
    "WebSocketBridgeAdapter",
    "WebSocketBridgeFactory",
    "create_standard_websocket_bridge",
    "create_agent_bridge_adapter",
    "create_websocket_bridge_for_testing",
    "create_websocket_bridge_with_context",
    "AgentWebSocketBridge",
    "create_agent_websocket_bridge",
]