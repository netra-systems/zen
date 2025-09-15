#!/usr/bin/env python3
"""
Quick test to verify direct instantiation prevention is working.
"""

# Set up the path
import sys
sys.path.insert(0, '.')

from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketManagerMode

# Mock user context
class MockUserContext:
    def __init__(self):
        self.user_id = "test-user-123"
        self.thread_id = "test-thread-123"
        self.request_id = "test-request-123"

print("Testing direct instantiation prevention...")

try:
    # This should fail - no authorization token provided
    manager = UnifiedWebSocketManager(
        mode=WebSocketManagerMode.UNIFIED,
        user_context=MockUserContext()
    )
    print("❌ FAILED: Direct instantiation was allowed!")
except Exception as e:
    print(f"✅ SUCCESS: Direct instantiation prevented with: {e}")

print("Testing factory pattern...")

try:
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    import asyncio

    async def test_factory():
        manager = get_websocket_manager(user_context=MockUserContext())
        print("✅ SUCCESS: Factory pattern works!")

    asyncio.run(test_factory())
except Exception as e:
    print(f"❌ FAILED: Factory pattern failed with: {e}")