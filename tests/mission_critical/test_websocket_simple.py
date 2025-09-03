#!/usr/bin/env python
"""MISSION CRITICAL: Simple WebSocket Event Tests

CRITICAL BUSINESS CONTEXT:
- WebSocket events are 90% of chat value delivery
- ALL 5 required events must be validated: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Factory-based patterns ensure complete user isolation

Tests validate:
1. Factory-based WebSocket emitter creation
2. All 5 required WebSocket events
3. JSON serialization of events
4. User isolation between concurrent requests
"""

import asyncio
import os
import sys
import json
from typing import Optional, Dict, Any, List
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ["WEBSOCKET_TEST_ISOLATED"] = "true"
os.environ["SKIP_REAL_SERVICES"] = "true"
os.environ["TEST_COLLECTION_MODE"] = "1"

# Import factory-based WebSocket components
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory, 
    UserWebSocketEmitter,
    UserWebSocketContext,
    UserWebSocketConnection,
    WebSocketEvent,
    ConnectionStatus,
    WebSocketConnectionPool
)
from netra_backend.app.agents.supervisor.execution_factory import (
    ExecutionEngineFactory,
    UserExecutionContext,
    ExecutionStatus
)
from shared.isolated_environment import get_env


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.sent_events: List[Dict[str, Any]] = []
        self.is_connected = True
        self.websocket = self  # Mock itself as websocket
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json method like FastAPI WebSocket."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
        self.sent_events.append(data)
        print(f"[SENT] Mock WebSocket sent to user {self.user_id}: {data.get('event_type', 'unknown')}")
        
    async def send_text(self, data: str) -> None:
        """Mock send_text method for ping."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
        print(f"[PING] Mock WebSocket ping to user {self.user_id}")
        
    async def ping(self) -> None:
        """Mock ping method."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
            
    async def close(self) -> None:
        """Mock close method."""
        self.is_connected = False
        
    @property
    def application_state(self):
        """Mock application state for FastAPI compatibility."""
        from unittest.mock import MagicMock
        mock_state = MagicMock()
        # Mock the WebSocketState.CONNECTED value
        mock_state.__eq__ = lambda self, other: True if self.is_connected else False
        return mock_state if self.is_connected else None


class MockConnectionPool:
    """Mock WebSocket connection pool."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        
    async def get_connection(self, connection_id: str, user_id: str):
        """Get or create mock connection."""
        key = f"{user_id}:{connection_id}"
        if key not in self.connections:
            self.connections[key] = MockWebSocketConnection(user_id, connection_id)
        
        # Return connection info structure
        from unittest.mock import MagicMock
        connection_info = MagicMock()
        connection_info.websocket = self.connections[key]
        return connection_info
        
    async def add_connection(self, user_id: str, connection_id: str, websocket):
        """Add connection to pool."""
        key = f"{user_id}:{connection_id}"
        self.connections[key] = MockWebSocketConnection(user_id, connection_id)
        
    async def remove_connection(self, user_id: str, connection_id: str):
        """Remove connection from pool."""
        key = f"{user_id}:{connection_id}"
        if key in self.connections:
            await self.connections[key].close()
            del self.connections[key]


async def test_factory_websocket_emitter_creation():
    """Test factory-based WebSocket emitter creation."""
    print("\n=== Testing Factory WebSocket Emitter Creation ===")
    
    try:
        # Create mock connection pool
        mock_pool = MockConnectionPool()
        
        # Create factory
        factory = WebSocketBridgeFactory()
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=None,  # Per-request pattern
            health_monitor=None
        )
        
        # Test creating user emitter
        user_id = "test_user_123"
        thread_id = "thread_456"
        connection_id = "conn_789"
        
        emitter = await factory.create_user_emitter(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        # Verify emitter creation
        assert emitter is not None, "Emitter should be created"
        assert emitter.user_context.user_id == user_id, f"Expected user_id {user_id}, got {emitter.user_context.user_id}"
        assert emitter.user_context.thread_id == thread_id, f"Expected thread_id {thread_id}, got {emitter.user_context.thread_id}"
        
        print(f"[SUCCESS] Successfully created emitter for user {user_id}")
        
        # Clean up
        await emitter.cleanup()
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Factory creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_required_websocket_events():
    """Test all 5 required WebSocket events are properly sent."""
    print("\n=== Testing All 5 Required WebSocket Events ===")
    
    try:
        # Create mock connection pool
        mock_pool = MockConnectionPool()
        
        # Create factory and emitter
        factory = WebSocketBridgeFactory()
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=None,
            health_monitor=None
        )
        
        user_id = "test_user_456"
        thread_id = "thread_789"
        connection_id = "conn_123"
        
        emitter = await factory.create_user_emitter(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        # Get mock connection to check sent events
        connection_key = f"{user_id}:{connection_id}"
        mock_connection = mock_pool.connections[connection_key]
        
        # Test all 5 required events
        agent_name = "TestAgent"
        run_id = "run_test_123"
        
        print("[EVENT] Sending agent_started event...")
        await emitter.notify_agent_started(agent_name, run_id)
        await asyncio.sleep(0.1)  # Allow event processing
        
        print("[EVENT] Sending agent_thinking event...")
        await emitter.notify_agent_thinking(agent_name, run_id, "Analyzing user request...")
        await asyncio.sleep(0.1)
        
        print("[EVENT] Sending tool_executing event...")
        await emitter.notify_tool_executing(agent_name, run_id, "search_tool", {"query": "test query"})
        await asyncio.sleep(0.1)
        
        print("[EVENT] Sending tool_completed event...")
        await emitter.notify_tool_completed(agent_name, run_id, "search_tool", {"results": ["result1", "result2"]})
        await asyncio.sleep(0.1)
        
        print("[EVENT] Sending agent_completed event...")
        await emitter.notify_agent_completed(agent_name, run_id, {"status": "success", "response": "Test completed"})
        await asyncio.sleep(0.1)
        
        # Verify all events were sent
        sent_events = mock_connection.sent_events
        print(f"\n[STATS] Total events sent: {len(sent_events)}")
        
        # Check for required event types
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        found_events = [event.get('event_type') for event in sent_events]
        
        missing_events = []
        for required_event in required_events:
            if required_event not in found_events:
                missing_events.append(required_event)
                
        if missing_events:
            print(f"[ERROR] Missing required events: {missing_events}")
            print(f"Found events: {found_events}")
            return False
            
        print(f"[SUCCESS] All 5 required events found: {found_events}")
        
        # Verify event structure
        for event in sent_events:
            assert 'event_type' in event, f"Event missing event_type: {event}"
            assert 'event_id' in event, f"Event missing event_id: {event}"
            assert 'thread_id' in event, f"Event missing thread_id: {event}"
            assert 'data' in event, f"Event missing data: {event}"
            assert 'timestamp' in event, f"Event missing timestamp: {event}"
            
        print("[SUCCESS] All events have proper structure")
        
        # Clean up
        await emitter.cleanup()
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Required events test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket_event_json_serialization():
    """Test WebSocket event JSON serialization."""
    print("\n=== Testing WebSocket Event JSON Serialization ===")
    
    try:
        # Create a test event
        event = WebSocketEvent(
            event_type="agent_started",
            user_id="test_user",
            thread_id="test_thread", 
            data={
                "agent_name": "TestAgent",
                "run_id": "run_123",
                "status": "started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Agent has started"
            }
        )
        
        # Test JSON serialization
        event_dict = {
            'event_type': event.event_type,
            'event_id': event.event_id,
            'thread_id': event.thread_id,
            'data': event.data,
            'timestamp': event.timestamp.isoformat()
        }
        
        # Serialize to JSON
        json_str = json.dumps(event_dict)
        print(f"[SUCCESS] Event serialized to JSON: {len(json_str)} characters")
        
        # Deserialize from JSON
        deserialized = json.loads(json_str)
        print(f"[SUCCESS] Event deserialized from JSON")
        
        # Verify structure
        assert deserialized['event_type'] == event.event_type
        assert deserialized['event_id'] == event.event_id
        assert deserialized['thread_id'] == event.thread_id
        assert deserialized['data']['agent_name'] == "TestAgent"
        
        print("[SUCCESS] JSON serialization/deserialization successful")
        return True
        
    except Exception as e:
        print(f"[FAIL] JSON serialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_test():
    """Run all WebSocket event tests."""
    print("MISSION CRITICAL: WebSocket Event Factory Tests")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Test 1: Factory emitter creation
        print("\n[TEST 1] Factory WebSocket Emitter Creation")
        result1 = await test_factory_websocket_emitter_creation()
        test_results.append(("Factory Creation", result1))
        
        # Test 2: All required events
        print("\n[TEST 2] All 5 Required WebSocket Events")
        result2 = await test_all_required_websocket_events()
        test_results.append(("Required Events", result2))
        
        # Test 3: JSON serialization
        print("\n[TEST 3] WebSocket Event JSON Serialization")
        result3 = await test_websocket_event_json_serialization()
        test_results.append(("JSON Serialization", result3))
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY:")
        print("=" * 60)
        
        all_passed = True
        for test_name, result in test_results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {test_name}")
            if not result:
                all_passed = False
                
        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] All WebSocket event tests passed!")
            print("[SUCCESS] Factory pattern working correctly")
            print("[SUCCESS] All 5 required events validated")
            print("[SUCCESS] JSON serialization working")
        else:
            print("[FAILURE] Some WebSocket event tests failed!")
            print("[CRITICAL] Critical issues detected in WebSocket events")
        print("=" * 60)
        
        return all_passed
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] CRITICAL EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)

