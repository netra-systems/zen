#!/usr/bin/env python3
"""
Startup import test for factory pattern cleanup verification
"""

print('=== Backend Startup Import Test ===')

# Test 1: Core app state contracts
try:
    from netra_backend.app.core.app_state_contracts import validate_app_state_contracts
    print('✅ app_state_contracts import: SUCCESS')
except Exception as e:
    print(f'❌ app_state_contracts import: FAILED - {e}')

# Test 2: WebSocket Manager
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print('✅ WebSocketManager import: SUCCESS')
except Exception as e:
    print(f'❌ WebSocketManager import: FAILED - {e}')

# Test 3: Agent Service Factory
try:
    from netra_backend.app.agents.factories.agent_service_factory import AgentServiceFactory
    print('✅ AgentServiceFactory import: SUCCESS')
except Exception as e:
    print(f'❌ AgentServiceFactory import: FAILED - {e}')

# Test 4: Test framework real service setup
try:
    from test_framework.real_service_setup import setup_real_services
    print('✅ test_framework.real_service_setup import: SUCCESS')
except Exception as e:
    print(f'❌ test_framework.real_service_setup import: FAILED - {e}')

# Test 5: Simple WebSocket creation module
try:
    from test_framework.simple_websocket_creation import create_websocket_connection
    print('✅ simple_websocket_creation import: SUCCESS')
except Exception as e:
    print(f'❌ simple_websocket_creation import: FAILED - {e}')

print('\n=== Import Test Complete ===')