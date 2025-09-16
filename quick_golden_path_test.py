#!/usr/bin/env python3
"""Quick Golden Path validation for Phase 2 import fixes"""

print('=== GOLDEN PATH VALIDATION ===')

# Test 1: Core imports work
try:
    from netra_backend.app.dependencies import get_agent_websocket_bridge
    print('PASS: get_agent_websocket_bridge imported successfully')
except Exception as e:
    print(f'FAIL: get_agent_websocket_bridge import: {e}')

# Test 2: WebSocket manager imports work
try:
    from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
    print('PASS: WebSocketManager imported successfully')
except Exception as e:
    print(f'FAIL: WebSocketManager import: {e}')

# Test 3: Agent bridge works
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    bridge = AgentWebSocketBridge()
    print('PASS: AgentWebSocketBridge instantiated successfully')
except Exception as e:
    print(f'FAIL: AgentWebSocketBridge instantiation: {e}')

# Test 4: Handler imports work
try:
    from netra_backend.app.handlers.example_message_handler import ExampleMessageHandler
    handler = ExampleMessageHandler()
    print('PASS: ExampleMessageHandler instantiated successfully')
except Exception as e:
    print(f'FAIL: ExampleMessageHandler instantiation: {e}')

print('=== VALIDATION COMPLETE ===')