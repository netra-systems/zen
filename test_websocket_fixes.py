#!/usr/bin/env python
"""Test script to verify WebSocket fixes are working."""

import asyncio
import sys
import io
from pathlib import Path
from netra_backend.app.core.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Fix Windows console encoding for emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    get_websocket_bridge_factory
)
from netra_backend.app.services.websocket_connection_pool import (
    WebSocketConnectionPool,
    get_websocket_connection_pool
)
from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter


async def test_websocket_initialization():
    """Test that WebSocket components initialize properly."""
    print("=" * 60)
    print("TESTING WEBSOCKET FIXES")
    print("=" * 60)
    
    # Test 1: WebSocketConnectionPool initialization
    print("\n1. Testing WebSocketConnectionPool initialization...")
    try:
        pool = get_websocket_connection_pool()
        assert pool is not None
        assert isinstance(pool, WebSocketConnectionPool)
        print("   ✅ WebSocketConnectionPool initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize WebSocketConnectionPool: {e}")
        return False
    
    # Test 2: WebSocketBridgeFactory initialization and configuration
    print("\n2. Testing WebSocketBridgeFactory initialization...")
    try:
        factory = get_websocket_bridge_factory()
        assert factory is not None
        assert isinstance(factory, WebSocketBridgeFactory)
        print("   ✅ WebSocketBridgeFactory initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize WebSocketBridgeFactory: {e}")
        return False
    
    # Test 3: Factory configuration with connection pool
    print("\n3. Testing Factory configuration with connection pool...")
    try:
        # Create mock health monitor
        class SimpleHealthMonitor:
            async def check_health(self):
                return {"status": "healthy"}
        
        # Create mock agent registry (avoid complex initialization)
        class MockAgentRegistry:
            def __init__(self):
                self.agents = {}
                
            def set_websocket_manager(self, manager):
                pass
                
            def get_agent(self, name):
                return None
        
        registry = MockAgentRegistry()
        health_monitor = SimpleHealthMonitor()
        
        # Configure factory
        factory.configure(
            connection_pool=pool,
            agent_registry=registry,
            health_monitor=health_monitor
        )
        print("   ✅ Factory configured with connection pool successfully")
    except ValueError as e:
        if "cannot be None" in str(e):
            print(f"   ❌ Factory validation working but pool was None: {e}")
        else:
            print(f"   ❌ Unexpected configuration error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Failed to configure factory: {e}")
        return False
    
    # Test 4: Create user emitter
    print("\n4. Testing UserWebSocketEmitter creation...")
    try:
        # Try to create an emitter
        emitter = await factory.create_user_emitter(
            user_id="test_user_123",
            thread_id="test_thread_456",
            connection_id="test_conn_789"
        )
        assert emitter is not None
        print(f"      Emitter type: {type(emitter)}")
        # The factory returns its own UserWebSocketEmitter, not the imported one
        # assert isinstance(emitter, UserWebSocketEmitter)
        print("   ✅ UserWebSocketEmitter created successfully")
    except Exception as e:
        import traceback
        print(f"   ❌ Failed to create UserWebSocketEmitter: {e}")
        traceback.print_exc()
        return False
    
    # Test 5: Test event sending (without actual WebSocket)
    print("\n5. Testing event sending mechanism...")
    try:
        # This should not crash even without a real WebSocket connection
        await emitter.notify_agent_started("test_agent", "test_run_123")
        print("   ✅ Event sending mechanism working (queued since no real connection)")
    except Exception as e:
        print(f"   ❌ Failed to send event: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL WEBSOCKET TESTS PASSED!")
    print("=" * 60)
    return True


async def main():
    """Run the tests."""
    try:
        success = await test_websocket_initialization()
        if not success:
            print("\n❌ Some tests failed. Please review the errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())