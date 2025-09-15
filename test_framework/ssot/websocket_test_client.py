"""WebSocket Test Client - SSOT Compatibility Module

This module provides backward compatibility for the unified WebSocket test client import.

CRITICAL: This is an SSOT compatibility layer that re-exports the real WebSocket test client
to maintain existing import paths during infrastructure consolidation.

Business Justification:
- Maintains backward compatibility for existing e2e tests
- Prevents breaking changes during WebSocket test infrastructure consolidation  
- Supports mission-critical Golden Path test execution ($500K+ ARR dependency)
"""

# Import the actual implementation
from test_framework.ssot.real_websocket_test_client import (
    RealWebSocketTestClient,
    WebSocketConnectionState,
    WebSocketEvent,
    ConnectionMetrics,
    SecurityError
)

# Create compatibility alias
UnifiedWebSocketTestClient = RealWebSocketTestClient

# Re-export for compatibility
__all__ = [
    'UnifiedWebSocketTestClient',
    'RealWebSocketTestClient',
    'WebSocketConnectionState', 
    'WebSocketEvent',
    'ConnectionMetrics',
    'SecurityError'
]