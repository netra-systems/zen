"""
WebSocket test helpers - Fixtures module compatibility layer
Created to resolve Issue #1332 Phase 3 - fixture import compatibility
"""

# Import all WebSocket test utilities from the main websocket_helpers module
from test_framework.websocket_helpers import (
    WebSocketTestClient,
    assert_websocket_events,
    assert_websocket_events_sent,
    wait_for_agent_completion,
    create_test_websocket_connection,
    WebSocketTestHelpers,
    MockWebSocket,
    MockWebSocketConnection
)

# Additional fixtures-specific aliases for compatibility
WebSocketTestSession = WebSocketTestClient

# Export all the imported functions and classes
__all__ = [
    'WebSocketTestClient',
    'WebSocketTestSession',
    'assert_websocket_events',
    'assert_websocket_events_sent',
    'wait_for_agent_completion',
    'create_test_websocket_connection',
    'WebSocketTestHelpers',
    'MockWebSocket',
    'MockWebSocketConnection'
]