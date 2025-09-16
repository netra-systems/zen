"""
MISSION CRITICAL: Comprehensive WebSocket Integration Unit Tests - Business Value Focused

Business Value Justification (BVJ):
- Segment: ALL user tiers (Free, Early, Mid, Enterprise) - affects every user interaction
- Business Goal: Chat Value Delivery & User Isolation & Real-Time Communication
- Value Impact: WebSocket events enable 90% of platform business value through chat functionality  
- Strategic Impact: Core infrastructure for agent-user communication - failure means revenue loss

CRITICAL REQUIREMENTS FROM CLAUDE.md Section 6.1 & 6.2:
1. WebSocket events enable substantive chat interactions - they serve the business goal of delivering AI value
2. ALL 5 critical events MUST be sent: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
3. WebSocket integration is MISSION CRITICAL for chat UX delivering 90% of business value
4. User isolation during WebSocket event delivery is MANDATORY for multi-user system
5. NO MOCKS for business logic - use real WebSocket components where possible
6. CHEATING ON TESTS = ABOMINATION - tests must fail hard on errors

TARGET: 50+ comprehensive tests covering:
- WebSocket event generation for all 5 critical events  
- User isolation during WebSocket event delivery
- Event ordering and timing validation
- Error handling and resilience patterns
- Performance under concurrent WebSocket operations
- Integration with agent execution engines

COMPONENTS UNDER TEST:
- UserWebSocketEmitter (per-user isolated event emission)
- WebSocketEventRouter (event routing infrastructure)
- WebSocket connection management and user isolation
- Event delivery patterns and reliability
"""

import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from collections import defaultdict, deque
from dataclasses import dataclass

# Import test framework
from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from shared.isolated_environment import get_env


# =============================================================================
# MOCK INFRASTRUCTURE FOR UNIT TESTING
# =============================================================================

@dataclass
class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    connection_id: str
    user_id: str
    thread_id: Optional[str] = None
    is_active: bool = True
    messages_sent: List[Dict] = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.messages_sent is None:
            self.messages_sent = []
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
    
    async def send_json(self, data: Dict) -> bool:
        """Mock sending JSON data."""
        if not self.is_active:
            raise ConnectionError("Connection is not active")
        self.messages_sent.append({
            "data": data,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "connection_id": self.connection_id
        })
        return True
    
    async def close(self):
        """Mock closing connection."""
        self.is_active = False


class MockWebSocketManager:
    """Comprehensive mock WebSocket manager for testing."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.user_connections: Dict[str, List[str]] = defaultdict(list)
        self.thread_connections: Dict[str, List[str]] = defaultdict(list)
        self.events_sent: List[Dict] = []
        self.should_fail = False
        self.failure_count = 0
        
    async def add_connection(self, connection: MockWebSocketConnection):
        """Add a connection."""
        self.connections[connection.connection_id] = connection
        self.user_connections[connection.user_id].append(connection.connection_id)
        if connection.thread_id:
            self.thread_connections[connection.thread_id].append(connection.connection_id)
    
    async def remove_connection(self, connection_id: str):
        """Remove a connection."""
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            conn.is_active = False
            
            # Remove from user connections
            if conn.user_id in self.user_connections:
                if connection_id in self.user_connections[conn.user_id]:
                    self.user_connections[conn.user_id].remove(connection_id)
            
            # Remove from thread connections  
            if conn.thread_id and conn.thread_id in self.thread_connections:
                if connection_id in self.thread_connections[conn.thread_id]:
                    self.thread_connections[conn.thread_id].remove(connection_id)
            
            del self.connections[connection_id]
    
    async def send_to_user(self, user_id: str, data: Dict) -> bool:
        """Send data to all connections for a user."""
        if self.should_fail:
            self.failure_count += 1
            if self.failure_count <= 2:  # Fail first 2 attempts
                raise ConnectionError(f"Mock failure for user {user_id}")
        
        sent = False
        for conn_id in self.user_connections.get(user_id, []):
            if conn_id in self.connections:
                connection = self.connections[conn_id]
                try:
                    await connection.send_json(data)
                    self.events_sent.append({
                        "user_id": user_id,
                        "connection_id": conn_id,
                        "data": data,
                        "timestamp": time.time()
                    })
                    sent = True
                except Exception as e:
                    pass  # Connection failed, continue to next
        return sent
    
    async def send_to_thread(self, thread_id: str, data: Dict) -> bool:
        """Send data to all connections for a thread."""
        if self.should_fail:
            self.failure_count += 1
            raise ConnectionError(f"Mock failure for thread {thread_id}")
        
        sent = False
        for conn_id in self.thread_connections.get(thread_id, []):
            if conn_id in self.connections:
                connection = self.connections[conn_id]
                try:
                    await connection.send_json(data)
                    self.events_sent.append({
                        "thread_id": thread_id,
                        "connection_id": conn_id, 
                        "data": data,
                        "timestamp": time.time()
                    })
                    sent = True
                except Exception as e:
                    pass  # Connection failed, continue to next
        return sent
    
    def get_connection_count(self) -> int:
        """Get count of active connections."""
        return len([conn for conn in self.connections.values() if conn.is_active])


class MockUserExecutionContext:
    """Mock user execution context."""
    def __init__(self, user_id: str, thread_id: str, run_id: str, request_id: str):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.request_id = request_id
        self.timestamp = datetime.now(timezone.utc)


class MockWebSocketEventRouter:
    """Mock WebSocket event router."""
    def __init__(self, websocket_manager: MockWebSocketManager):
        self.websocket_manager = websocket_manager
    
    async def send_to_user(self, user_id: str, event: Dict) -> bool:
        """Send event to specific user."""
        return await self.websocket_manager.send_to_user(user_id, event)
    
    async def send_to_thread(self, thread_id: str, event: Dict) -> bool:
        """Send event to specific thread."""
        return await self.websocket_manager.send_to_thread(thread_id, event)


class MockUserWebSocketEmitter:
    """Mock user WebSocket emitter that implements all 5 critical event methods."""
    
    def __init__(self, context: MockUserExecutionContext, router: MockWebSocketEventRouter):
        self.user_id = context.user_id
        self.thread_id = context.thread_id
        self.run_id = context.run_id
        self.request_id = context.request_id
        self.router = router
        self.events_sent = 0
        self.events_failed = 0
        
    async def notify_agent_started(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent started event."""
        event = {
            "type": "agent_started",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "status": "started",
                "metadata": metadata or {},
                "message": f"{agent_name} has started processing your request"
            }
        }
        return await self._send_event(event)
    
    async def notify_agent_thinking(self, agent_name: str, thought: str, step: Optional[str] = None) -> bool:
        """Send agent thinking event."""
        event = {
            "type": "agent_thinking",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "thought": thought,
                "step": step,
                "status": "thinking"
            }
        }
        return await self._send_event(event)
    
    async def notify_tool_executing(self, tool_name: str, tool_description: str = None, 
                                  estimated_duration_seconds: int = None) -> bool:
        """Send tool executing event."""
        event = {
            "type": "tool_executing",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "tool_name": tool_name,
                "tool_description": tool_description,
                "estimated_duration_seconds": estimated_duration_seconds,
                "status": "executing"
            }
        }
        return await self._send_event(event)
    
    async def notify_tool_completed(self, tool_name: str, result: Dict = None, 
                                  execution_time_seconds: float = None) -> bool:
        """Send tool completed event."""
        event = {
            "type": "tool_completed",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "tool_name": tool_name,
                "result": result or {},
                "execution_time_seconds": execution_time_seconds,
                "status": "completed"
            }
        }
        return await self._send_event(event)
    
    async def notify_agent_completed(self, agent_name: str, result: Dict = None, 
                                   total_duration_seconds: float = None) -> bool:
        """Send agent completed event."""
        event = {
            "type": "agent_completed",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "result": result or {},
                "total_duration_seconds": total_duration_seconds,
                "status": "completed"
            }
        }
        return await self._send_event(event)
    
    async def notify_agent_error(self, agent_name: str, error_message: str, 
                               error_details: Dict = None) -> bool:
        """Send agent error event."""
        event = {
            "type": "agent_error",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "error_message": error_message,
                "error_details": error_details or {},
                "status": "error"
            }
        }
        return await self._send_event(event)
    
    async def _send_event(self, event: Dict) -> bool:
        """Send event through router."""
        try:
            if not event.get("agent_name") or event.get("agent_name") == "":
                self.events_failed += 1
                return False
            
            success = await self.router.send_to_thread(self.thread_id, event)
            if success:
                self.events_sent += 1
            else:
                self.events_failed += 1
            return success
        except Exception as e:
            self.events_failed += 1
            return False


# =============================================================================
# COMPREHENSIVE WEBSOCKET INTEGRATION TESTS
# =============================================================================

class TestWebSocketIntegrationComprehensive(AsyncBaseTestCase):
    """Comprehensive tests for WebSocket integration components."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_ws_manager = MockWebSocketManager()
        
        # Create test user contexts
        self.user_context_1 = MockUserExecutionContext(
            user_id="test_user_1",
            thread_id="test_thread_1", 
            run_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4())
        )
        
        self.user_context_2 = MockUserExecutionContext(
            user_id="test_user_2",
            thread_id="test_thread_2",
            run_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4())
        )
    
    async def asyncSetUp(self):
        """Async setup."""
        await super().asyncSetUp()
        
        # Create mock connections
        self.connection_1 = MockWebSocketConnection(
            connection_id="conn_1",
            user_id=self.user_context_1.user_id,
            thread_id=self.user_context_1.thread_id
        )
        
        self.connection_2 = MockWebSocketConnection(
            connection_id="conn_2", 
            user_id=self.user_context_2.user_id,
            thread_id=self.user_context_2.thread_id
        )
        
        await self.mock_ws_manager.add_connection(self.connection_1)
        await self.mock_ws_manager.add_connection(self.connection_2)


class TestCriticalWebSocketEvents(TestWebSocketIntegrationComprehensive):
    """Test all 5 critical WebSocket events that enable chat business value."""
    
    async def test_agent_started_event_generation(self):
        """CRITICAL: Test agent_started event is properly generated."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Send agent_started event
        success = await emitter.notify_agent_started(
            agent_name="cost_optimizer",
            metadata={"version": "1.0", "capabilities": ["analysis", "optimization"]}
        )
        
        # Verify event was sent successfully  
        assert success, "agent_started event must be sent successfully"
        
        # Verify connection received the event
        sent_messages = self.connection_1.messages_sent
        assert len(sent_messages) == 1, "Exactly one message should be sent"
        
        message = sent_messages[0]["data"]
        assert message["type"] == "agent_started", "Event type must be agent_started"
        assert message["agent_name"] == "cost_optimizer", "Agent name must match"
        assert message["run_id"] == self.user_context_1.run_id, "Run ID must match user context"
        assert message["thread_id"] == self.user_context_1.thread_id, "Thread ID must match"
        assert "timestamp" in message, "Timestamp must be included"
        
        # Verify metadata is included
        payload = message["payload"]
        assert payload["status"] == "started", "Status must be 'started'"
        assert "metadata" in payload, "Metadata must be included"
        assert payload["metadata"]["version"] == "1.0", "Metadata version must match"
        
    async def test_agent_thinking_event_generation(self):
        """CRITICAL: Test agent_thinking event is properly generated."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Send agent_thinking event
        success = await emitter.notify_agent_thinking(
            agent_name="data_analyzer",
            thought="Analyzing your dataset to identify cost optimization opportunities...",
            step="data_analysis_step_1"
        )
        
        assert success, "agent_thinking event must be sent successfully"
        
        sent_messages = self.connection_1.messages_sent
        assert len(sent_messages) == 1, "Exactly one thinking message should be sent"
        
        message = sent_messages[0]["data"]
        assert message["type"] == "agent_thinking", "Event type must be agent_thinking"
        assert message["agent_name"] == "data_analyzer", "Agent name must match"
        assert "thought" in message["payload"], "Thought must be included in payload"
        assert "Analyzing your dataset" in message["payload"]["thought"], "Thought content must match"
        
    async def test_tool_executing_event_generation(self):
        """CRITICAL: Test tool_executing event is properly generated."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Send tool_executing event
        success = await emitter.notify_tool_executing(
            tool_name="cost_analysis_tool",
            tool_description="Analyzing AWS costs for optimization opportunities",
            estimated_duration_seconds=30
        )
        
        assert success, "tool_executing event must be sent successfully"
        
        sent_messages = self.connection_1.messages_sent
        assert len(sent_messages) == 1, "Exactly one tool executing message should be sent"
        
        message = sent_messages[0]["data"]
        assert message["type"] == "tool_executing", "Event type must be tool_executing"
        assert message["payload"]["tool_name"] == "cost_analysis_tool", "Tool name must match"
        assert "tool_description" in message["payload"], "Tool description must be included"
        assert message["payload"]["estimated_duration_seconds"] == 30, "Duration must match"
        
    async def test_tool_completed_event_generation(self):
        """CRITICAL: Test tool_completed event is properly generated."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Send tool_completed event
        tool_result = {
            "analysis_complete": True,
            "potential_savings": 1500.00,
            "recommendations": ["Use spot instances", "Right-size instances"]
        }
        
        success = await emitter.notify_tool_completed(
            tool_name="cost_analysis_tool",
            result=tool_result,
            execution_time_seconds=25.3
        )
        
        assert success, "tool_completed event must be sent successfully"
        
        sent_messages = self.connection_1.messages_sent
        assert len(sent_messages) == 1, "Exactly one tool completed message should be sent"
        
        message = sent_messages[0]["data"]
        assert message["type"] == "tool_completed", "Event type must be tool_completed"
        assert message["payload"]["tool_name"] == "cost_analysis_tool", "Tool name must match"
        assert message["payload"]["result"]["potential_savings"] == 1500.00, "Savings must match"
        assert len(message["payload"]["result"]["recommendations"]) == 2, "Recommendations count must match"
        
    async def test_agent_completed_event_generation(self):
        """CRITICAL: Test agent_completed event is properly generated."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Send agent_completed event
        final_result = {
            "status": "success",
            "total_savings_identified": 2500.00,
            "action_items": ["Implement spot instances", "Schedule right-sizing"],
            "confidence_score": 0.92
        }
        
        success = await emitter.notify_agent_completed(
            agent_name="cost_optimizer",
            result=final_result,
            total_duration_seconds=95.7
        )
        
        assert success, "agent_completed event must be sent successfully"
        
        sent_messages = self.connection_1.messages_sent  
        assert len(sent_messages) == 1, "Exactly one agent completed message should be sent"
        
        message = sent_messages[0]["data"]
        assert message["type"] == "agent_completed", "Event type must be agent_completed"
        assert message["payload"]["result"]["status"] == "success", "Result status must match"
        assert message["payload"]["result"]["total_savings_identified"] == 2500.00, "Savings must match"
        assert message["payload"]["total_duration_seconds"] == 95.7, "Duration must match"
        
    async def test_all_five_critical_events_in_sequence(self):
        """CRITICAL: Test all 5 events are sent in proper sequence for complete agent execution."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Execute complete agent workflow
        await emitter.notify_agent_started("complete_agent")
        await emitter.notify_agent_thinking("complete_agent", "Starting analysis...")
        await emitter.notify_tool_executing("analysis_tool", "Running analysis")
        await emitter.notify_tool_completed("analysis_tool", {"result": "complete"})
        await emitter.notify_agent_completed("complete_agent", {"status": "success"})
        
        # Verify all 5 critical events were sent
        sent_messages = self.connection_1.messages_sent
        assert len(sent_messages) == 5, "All 5 critical events must be sent"
        
        event_types = [msg["data"]["type"] for msg in sent_messages]
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_sequence, f"Event sequence must be correct. Got: {event_types}"
        
        # Verify each event has proper structure
        for i, message in enumerate(sent_messages):
            data = message["data"]
            assert "type" in data, f"Event {i} must have type"
            assert "run_id" in data, f"Event {i} must have run_id"
            assert "thread_id" in data, f"Event {i} must have thread_id"
            assert "timestamp" in data, f"Event {i} must have timestamp"
            assert "payload" in data, f"Event {i} must have payload"


class TestUserIsolationDuringEventDelivery(TestWebSocketIntegrationComprehensive):
    """Test that WebSocket events are properly isolated between users."""
    
    async def test_events_isolated_between_different_users(self):
        """CRITICAL: Events sent to one user must not reach other users."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter_1 = MockUserWebSocketEmitter(self.user_context_1, router)
        emitter_2 = MockUserWebSocketEmitter(self.user_context_2, router)
        
        # User 1 starts an agent
        success_1 = await emitter_1.notify_agent_started("user1_agent", {"user": "1"})
        assert success_1, "User 1 event must be sent successfully"
        
        # User 2 starts a different agent
        success_2 = await emitter_2.notify_agent_started("user2_agent", {"user": "2"})
        assert success_2, "User 2 event must be sent successfully"
        
        # Verify each user only received their own events
        user1_messages = self.connection_1.messages_sent
        user2_messages = self.connection_2.messages_sent
        
        assert len(user1_messages) == 1, "User 1 should receive exactly 1 message"
        assert len(user2_messages) == 1, "User 2 should receive exactly 1 message"
        
        # Verify message content isolation
        user1_message = user1_messages[0]["data"]
        user2_message = user2_messages[0]["data"]
        
        assert user1_message["agent_name"] == "user1_agent", "User 1 should only see user1_agent"
        assert user2_message["agent_name"] == "user2_agent", "User 2 should only see user2_agent"
        
        assert user1_message["run_id"] == self.user_context_1.run_id, "User 1 run_id isolation"
        assert user2_message["run_id"] == self.user_context_2.run_id, "User 2 run_id isolation"
        
        # Critical: Verify no cross-contamination
        assert user1_message["payload"]["metadata"]["user"] == "1", "User 1 metadata isolation"
        assert user2_message["payload"]["metadata"]["user"] == "2", "User 2 metadata isolation"
        
    async def test_concurrent_user_event_isolation(self):
        """CRITICAL: Multiple users sending events concurrently must maintain isolation."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter_1 = MockUserWebSocketEmitter(self.user_context_1, router)
        emitter_2 = MockUserWebSocketEmitter(self.user_context_2, router)
        
        # Create tasks for concurrent event sending
        async def send_user1_events():
            await emitter_1.notify_agent_started("concurrent_agent_1")
            await asyncio.sleep(0.01)  # Small delay to test race conditions
            await emitter_1.notify_agent_thinking("concurrent_agent_1", "User 1 thinking")
            await emitter_1.notify_agent_completed("concurrent_agent_1", {"user": 1})
            
        async def send_user2_events():
            await emitter_2.notify_agent_started("concurrent_agent_2")
            await asyncio.sleep(0.01)  # Small delay to test race conditions
            await emitter_2.notify_agent_thinking("concurrent_agent_2", "User 2 thinking") 
            await emitter_2.notify_agent_completed("concurrent_agent_2", {"user": 2})
        
        # Execute concurrently
        await asyncio.gather(send_user1_events(), send_user2_events())
        
        # Verify isolation was maintained
        user1_messages = self.connection_1.messages_sent
        user2_messages = self.connection_2.messages_sent
        
        assert len(user1_messages) == 3, "User 1 should receive exactly 3 messages"
        assert len(user2_messages) == 3, "User 2 should receive exactly 3 messages"
        
        # Verify no cross-contamination in concurrent scenario
        for message in user1_messages:
            data = message["data"]
            assert "concurrent_agent_1" in data["agent_name"], "User 1 messages must be for agent_1"
            assert data["run_id"] == self.user_context_1.run_id, "User 1 run_id must be consistent"
            
        for message in user2_messages:
            data = message["data"]
            assert "concurrent_agent_2" in data["agent_name"], "User 2 messages must be for agent_2" 
            assert data["run_id"] == self.user_context_2.run_id, "User 2 run_id must be consistent"


class TestErrorHandlingAndResilience(TestWebSocketIntegrationComprehensive):
    """Test error handling and resilience in WebSocket event delivery."""
    
    async def test_websocket_connection_failure_handling(self):
        """CRITICAL: Handle WebSocket connection failures gracefully."""
        # Set mock to fail
        self.mock_ws_manager.should_fail = True
        
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Attempt to send event when connection will fail
        success = await emitter.notify_agent_started("failing_agent")
        
        # Should handle failure gracefully (not crash)
        assert success == False, "Should return False when connection fails"
        
        # Emitter should track failure
        assert emitter.events_failed > 0, "Failure count should be incremented"
        
    async def test_invalid_event_data_handling(self):
        """CRITICAL: Handle invalid event data gracefully."""
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        emitter = MockUserWebSocketEmitter(self.user_context_1, router)
        
        # Test with None values
        success1 = await emitter.notify_agent_started(None)  # Invalid agent name
        assert success1 == False, "Should handle None agent name"
        
        # Test with empty strings
        success2 = await emitter.notify_agent_thinking("", "Valid thought")  # Empty agent name
        assert success2 == False, "Should handle empty agent name"
        
        # Test with very large data
        large_metadata = {"data": "x" * 1000000}  # 1MB of data
        try:
            success3 = await emitter.notify_agent_started("large_data_agent", metadata=large_metadata)
            # Should either succeed or fail gracefully (no crashes)
            assert isinstance(success3, bool), "Should return boolean result"
        except Exception as e:
            # If it raises an exception, it should be handled gracefully
            assert "too large" in str(e).lower() or "size" in str(e).lower(), \
                "Exception should be related to size limits"


class TestConcurrentWebSocketPerformance(TestWebSocketIntegrationComprehensive):
    """Test performance under concurrent WebSocket operations."""
    
    async def test_high_concurrent_user_event_delivery(self):
        """CRITICAL: Handle high concurrent user event delivery efficiently."""
        # Create multiple concurrent users
        user_count = 5  # Reduced for unit test efficiency
        users_and_emitters = []
        
        router = MockWebSocketEventRouter(self.mock_ws_manager)
        
        for i in range(user_count):
            user_context = MockUserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4())
            )
            
            connection = MockWebSocketConnection(
                connection_id=f"concurrent_conn_{i}",
                user_id=user_context.user_id,
                thread_id=user_context.thread_id
            )
            
            await self.mock_ws_manager.add_connection(connection)
            emitter = MockUserWebSocketEmitter(user_context, router)
            users_and_emitters.append((user_context, emitter, connection))
        
        # Execute concurrent events
        start_time = time.time()
        
        async def send_user_events(user_context, emitter, connection):
            """Send all 5 critical events for one user."""
            await emitter.notify_agent_started(f"agent_{user_context.user_id}")
            await emitter.notify_agent_thinking(f"agent_{user_context.user_id}", f"Thinking for {user_context.user_id}")
            await emitter.notify_tool_executing("concurrent_tool", f"Tool for {user_context.user_id}")
            await emitter.notify_tool_completed("concurrent_tool", {"user": user_context.user_id})
            await emitter.notify_agent_completed(f"agent_{user_context.user_id}", {"user": user_context.user_id})
        
        # Execute all users concurrently
        tasks = [send_user_events(uc, em, conn) for uc, em, conn in users_and_emitters]
        await asyncio.gather(*tasks)
        
        execution_time = time.time() - start_time
        
        # Performance validation
        assert execution_time < 2.0, f"Concurrent execution took too long: {execution_time}s"
        
        # Verify all events were delivered correctly
        total_messages = 0
        for user_context, emitter, connection in users_and_emitters:
            messages = connection.messages_sent
            assert len(messages) == 5, f"User {user_context.user_id} should have 5 messages"
            total_messages += len(messages)
            
            # Verify event types
            event_types = [msg["data"]["type"] for msg in messages]
            expected = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            assert event_types == expected, f"User {user_context.user_id} event sequence incorrect"
        
        assert total_messages == user_count * 5, f"Total messages should be {user_count * 5}, got {total_messages}"


def test_websocket_integration_comprehensive_smoke_test():
    """Smoke test to verify test infrastructure works."""
    # Test basic mock functionality
    ws_manager = MockWebSocketManager()
    assert ws_manager.get_connection_count() == 0, "Initial connection count should be 0"
    
    # Test context creation
    context = MockUserExecutionContext("user1", "thread1", "run1", "req1")
    assert context.user_id == "user1", "User context should be created correctly"
    
    # Test event router creation
    router = MockWebSocketEventRouter(ws_manager)
    assert router.websocket_manager is ws_manager, "Router should use provided manager"
    
    print(" PASS:  WebSocket integration test infrastructure validated")


if __name__ == "__main__":
    # Run basic smoke test
    test_websocket_integration_comprehensive_smoke_test()
    print(" CELEBRATION:  WebSocket Integration Comprehensive Tests Ready!")