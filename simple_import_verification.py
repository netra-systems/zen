#!/usr/bin/env python3
"""Simple import test for factory cleanup verification"""

print("Testing critical imports...")

# Test 1: Core imports
try:
    import sys
    import os
    print("✅ Basic Python imports: SUCCESS")
except Exception as e:
    print(f"❌ Basic Python imports: FAILED - {e}")

# Test 2: Backend imports
try:
    sys.path.insert(0, '/c/netra-apex')
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("✅ WebSocketManager import: SUCCESS")
except Exception as e:
    print(f"❌ WebSocketManager import: FAILED - {e}")

# Test 3: Test framework imports
try:
    from test_framework.real_service_setup import setup_real_services
    print("✅ real_service_setup import: SUCCESS")
except Exception as e:
    print(f"❌ real_service_setup import: FAILED - {e}")

# Test 4: Simple WebSocket creation
try:
    from test_framework.simple_websocket_creation import create_websocket_connection
    print("✅ simple_websocket_creation import: SUCCESS")
except Exception as e:
    print(f"❌ simple_websocket_creation import: FAILED - {e}")

print("Import test complete.")