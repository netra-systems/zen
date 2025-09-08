"""
Comprehensive WebSocket Agent Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time user feedback during agent execution  
- Value Impact: WebSocket events prevent user abandonment and provide transparency
- Strategic Impact: Chat UX is our primary value delivery mechanism

Integration Points Tested:
1. WebSocket message delivery across components
2. Agent execution event propagation 
3. Multi-user WebSocket isolation
4. Event ordering and timing guarantees
5. Connection management during agent execution
6. Error handling and recovery via WebSocket
7. Trace context propagation in WebSocket events
8. Performance monitoring of WebSocket delivery
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.handlers import WebSocketHandler
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class MockWebSocket:
    """Mock WebSocket connection for integration testing."""
    
    def __init__(self, user_id: str = "test_user", thread_id: str = "test_thread"):
        self.user_id = user_id
        self.thread_id = thread_id
        self.messages_sent = []
        self.is_closed = False
        self.close_code = None
        self.headers = {"user-id": user_id}
        
    async def send_text(self, message: str):
        """Mock send text message."""
        if self.is_closed:
            raise ConnectionError("WebSocket closed")
        self.messages_sent.append({
            "type": "text",
            "data": message,
            "timestamp": time.time()
        })
        
    async def send_json(self, data: Dict):
        """Mock send JSON message."""  
        if self.is_closed:
            raise ConnectionError("WebSocket closed")
        self.messages_sent.append({
            "type": "json", 
            "data": data,
            "timestamp": time.time()
        })
        
    async def close(self, code: int = 1000):
        """Mock close connection."""
        self.is_closed = True
        self.close_code = code


class MockConnectionManager:
    """Mock connection manager for WebSocket integration testing."""
    
    def __init__(self):
        self.connections = {}  # user_id -> MockWebSocket
        self.thread_connections = {}  # thread_id -> List[MockWebSocket]
        self.broadcasts = []
        
    async def add_connection(self, websocket: MockWebSocket, user_id: str, thread_id: str):
        """Add mock connection."""
        self.connections[user_id] = websocket
        if thread_id not in self.thread_connections:
            self.thread_connections[thread_id] = []
        self.thread_connections[thread_id].append(websocket)
        
    async def remove_connection(self, user_id: str, thread_id: str):
        """Remove mock connection."""
        if user_id in self.connections:
            del self.connections[user_id]
        if thread_id in self.thread_connections:
            self.thread_connections[thread_id] = [
                ws for ws in self.thread_connections[thread_id] 
                if ws.user_id != user_id
            ]
            
    async def send_to_user(self, user_id: str, message: Dict) -> bool:
        """Send message to specific user."""
        if user_id in self.connections:
            await self.connections[user_id].send_json(message)
            return True
        return False
        
    async def send_to_thread(self, thread_id: str, message: Dict) -> bool:
        """Send message to all users in thread."""
        if thread_id in self.thread_connections:
            for websocket in self.thread_connections[thread_id]:
                try:
                    await websocket.send_json(message)
                except ConnectionError:
                    continue
            return True
        return False
        
    async def broadcast(self, message: Dict) -> int:
        """Broadcast message to all connections."""
        sent_count = 0
        self.broadcasts.append({
            "message": message,
            "timestamp": time.time()
        })
        for websocket in self.connections.values():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except ConnectionError:
                continue
        return sent_count
        
    def get_connections_for_thread(self, thread_id: str) -> List[MockWebSocket]:
        """Get all connections for a thread."""
        return self.thread_connections.get(thread_id, [])


@pytest.mark.integration
@pytest.mark.real_services
class TestWebSocketAgentIntegrationComprehensive:
    """Comprehensive WebSocket agent integration tests."""
    
    @pytest.fixture
    def mock_connection_manager(self):
        """Provide mock connection manager."""
        return MockConnectionManager()
        
    @pytest.fixture 
    def websocket_manager(self, mock_connection_manager):
        """Provide WebSocket manager with mock connections."""
        manager = UnifiedWebSocketManager()
        manager.connection_manager = mock_connection_manager
        return manager
        
    @pytest.fixture
    def websocket_bridge(self, websocket_manager):
        """Provide agent WebSocket bridge."""
        return AgentWebSocketBridge(websocket_manager)
        
    @pytest.fixture
    def test_websocket_user1(self):
        """Provide test WebSocket for user 1."""
        return MockWebSocket(user_id="user_1", thread_id="thread_1")
        
    @pytest.fixture
    def test_websocket_user2(self):
        """Provide test WebSocket for user 2.""" 
        return MockWebSocket(user_id="user_2", thread_id="thread_2")
        
    @pytest.fixture
    def agent_context(self):
        """Provide agent execution context."""
        return AgentExecutionContext(
            agent_name="integration_test_agent",
            run_id=uuid4(),
            correlation_id="integration_test_correlation"
        )
        
    @pytest.fixture
    def trace_context(self):
        """Provide trace context."""
        return UnifiedTraceContext(
            user_id="test_user",
            thread_id="test_thread", 
            correlation_id="test_correlation"
        )
    
    async def test_single_user_websocket_agent_integration(
        self, websocket_bridge, mock_connection_manager, test_websocket_user1, 
        agent_context, trace_context
    ):
        """Test complete WebSocket integration for single user agent execution."""
        # BUSINESS VALUE: Ensure single user receives all agent execution events
        
        # Setup: Connect user WebSocket
        await mock_connection_manager.add_connection(
            test_websocket_user1, "user_1", "thread_1"
        )
        
        # Execute: Complete agent execution event sequence  
        run_id = str(agent_context.run_id)
        
        # Agent started
        await websocket_bridge.notify_agent_started(
            run_id=run_id,
            agent_name="integration_test_agent",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Agent thinking
        await websocket_bridge.notify_agent_thinking(
            run_id=run_id,
            agent_name="integration_test_agent", 
            reasoning="Analyzing integration patterns...",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Tool executing
        await websocket_bridge.notify_tool_executing(
            run_id=run_id,
            agent_name="integration_test_agent",
            tool_name="integration_analyzer",
            tool_purpose="Validate cross-component interactions",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Tool completed
        await websocket_bridge.notify_tool_completed(
            run_id=run_id,
            agent_name="integration_test_agent", 
            tool_name="integration_analyzer",
            result={"status": "validated", "issues_found": 0},
            trace_context=trace_context.to_websocket_context()
        )
        
        # Agent completed
        await websocket_bridge.notify_agent_completed(
            run_id=run_id,
            agent_name="integration_test_agent",
            result={"success": True, "integration_score": 95},
            execution_time_ms=1500,
            trace_context=trace_context.to_websocket_context()
        )
        
        # Verify: All events received by WebSocket
        messages = test_websocket_user1.messages_sent
        assert len(messages) == 5
        
        # Verify: Event types and ordering
        message_types = [json.loads(msg["data"])["type"] for msg in messages]
        expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert message_types == expected_types
        
        # Verify: Agent started event
        started_event = json.loads(messages[0]["data"])
        assert started_event["type"] == "agent_started"
        assert started_event["payload"]["run_id"] == run_id
        assert started_event["payload"]["agent_name"] == "integration_test_agent" 
        assert started_event["payload"]["trace_context"]["user_id"] == "test_user"
        
        # Verify: Tool events include proper details
        tool_executing_event = json.loads(messages[2]["data"])
        assert tool_executing_event["payload"]["tool_name"] == "integration_analyzer"
        assert tool_executing_event["payload"]["tool_purpose"] == "Validate cross-component interactions"
        
        tool_completed_event = json.loads(messages[3]["data"]) 
        assert tool_completed_event["payload"]["result"]["status"] == "validated"
        assert tool_completed_event["payload"]["result"]["issues_found"] == 0
        
        # Verify: Agent completed includes results and timing
        completed_event = json.loads(messages[4]["data"])
        assert completed_event["payload"]["result"]["success"] is True
        assert completed_event["payload"]["result"]["integration_score"] == 95
        assert completed_event["payload"]["execution_time_ms"] == 1500
        
    async def test_multi_user_websocket_isolation_integration(
        self, websocket_bridge, mock_connection_manager, 
        test_websocket_user1, test_websocket_user2
    ):
        """Test WebSocket event isolation between multiple users."""
        # BUSINESS VALUE: Ensure user privacy and data isolation in multi-tenant system
        
        # Setup: Connect both users to different threads
        await mock_connection_manager.add_connection(test_websocket_user1, "user_1", "thread_1")
        await mock_connection_manager.add_connection(test_websocket_user2, "user_2", "thread_2")
        
        # Execute: Send agent events to user 1 only
        user1_context = AgentExecutionContext(
            agent_name="user1_agent", 
            run_id=uuid4(),
            correlation_id="user1_correlation"
        )
        user1_trace = UnifiedTraceContext(
            user_id="user_1",
            thread_id="thread_1", 
            correlation_id="user1_correlation"
        )
        
        await websocket_bridge.notify_agent_started(
            run_id=str(user1_context.run_id),
            agent_name="user1_agent",
            trace_context=user1_trace.to_websocket_context()
        )
        
        await websocket_bridge.notify_agent_thinking(
            run_id=str(user1_context.run_id),
            agent_name="user1_agent",
            reasoning="Processing user 1 sensitive data...", 
            trace_context=user1_trace.to_websocket_context()
        )
        
        # Execute: Send agent events to user 2 only
        user2_context = AgentExecutionContext(
            agent_name="user2_agent",
            run_id=uuid4(),
            correlation_id="user2_correlation"  
        )
        user2_trace = UnifiedTraceContext(
            user_id="user_2",
            thread_id="thread_2",
            correlation_id="user2_correlation"
        )
        
        await websocket_bridge.notify_agent_started(
            run_id=str(user2_context.run_id),
            agent_name="user2_agent",
            trace_context=user2_trace.to_websocket_context()
        )
        
        await websocket_bridge.notify_agent_completed(
            run_id=str(user2_context.run_id), 
            agent_name="user2_agent",
            result={"user2_secret_data": "confidential"},
            execution_time_ms=800,
            trace_context=user2_trace.to_websocket_context()
        )
        
        # Verify: User 1 isolation
        user1_messages = test_websocket_user1.messages_sent
        assert len(user1_messages) == 2  # Only user1 events
        
        user1_run_ids = [json.loads(msg["data"])["payload"]["run_id"] for msg in user1_messages]
        assert all(run_id == str(user1_context.run_id) for run_id in user1_run_ids)
        
        user1_thinking = json.loads(user1_messages[1]["data"])
        assert "user 1 sensitive data" in user1_thinking["payload"]["reasoning"]
        
        # Verify: User 2 isolation  
        user2_messages = test_websocket_user2.messages_sent
        assert len(user2_messages) == 2  # Only user2 events
        
        user2_run_ids = [json.loads(msg["data"])["payload"]["run_id"] for msg in user2_messages]
        assert all(run_id == str(user2_context.run_id) for run_id in user2_run_ids)
        
        user2_completed = json.loads(user2_messages[1]["data"])
        assert user2_completed["payload"]["result"]["user2_secret_data"] == "confidential"
        
        # Verify: No cross-contamination
        user1_content = " ".join([json.loads(msg["data"])["payload"].get("reasoning", "") 
                                 for msg in user1_messages])
        assert "user2_secret_data" not in user1_content
        assert "confidential" not in user1_content
        
        user2_content = " ".join([json.loads(msg["data"])["payload"].get("reasoning", "")
                                 for msg in user2_messages])
        assert "user 1 sensitive data" not in user2_content
        
    async def test_websocket_connection_failure_recovery_integration(
        self, websocket_bridge, mock_connection_manager, agent_context, trace_context
    ):
        """Test WebSocket integration handles connection failures gracefully."""
        # BUSINESS VALUE: Graceful degradation maintains user experience during network issues
        
        # Setup: WebSocket that will fail during execution
        failing_websocket = MockWebSocket("failing_user", "failing_thread")
        await mock_connection_manager.add_connection(failing_websocket, "failing_user", "failing_thread")
        
        run_id = str(agent_context.run_id)
        
        # Execute: Send initial event successfully
        await websocket_bridge.notify_agent_started(
            run_id=run_id,
            agent_name="resilient_agent",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Verify: Initial event sent
        assert len(failing_websocket.messages_sent) == 1
        
        # Simulate: Connection failure
        failing_websocket.is_closed = True
        
        # Execute: Try to send events after connection failure
        await websocket_bridge.notify_agent_thinking(
            run_id=run_id,
            agent_name="resilient_agent", 
            reasoning="This should handle failure gracefully...",
            trace_context=trace_context.to_websocket_context()
        )
        
        await websocket_bridge.notify_agent_completed(
            run_id=run_id,
            agent_name="resilient_agent",
            result={"status": "completed_despite_connection_failure"},
            execution_time_ms=1000,
            trace_context=trace_context.to_websocket_context()
        )
        
        # Verify: No additional messages sent after failure (connection closed)
        assert len(failing_websocket.messages_sent) == 1  # Only the initial success
        
        # Verify: WebSocket bridge handled failures without crashing
        # (If we reach this point, the bridge handled errors gracefully)
        assert True
        
    async def test_websocket_event_performance_integration(
        self, websocket_bridge, mock_connection_manager, trace_context
    ):
        """Test WebSocket event delivery performance under load."""
        # BUSINESS VALUE: Fast event delivery prevents user abandonment
        
        # Setup: Multiple WebSocket connections
        websockets = []
        for i in range(10):
            ws = MockWebSocket(f"user_{i}", f"thread_{i}")
            websockets.append(ws)
            await mock_connection_manager.add_connection(ws, f"user_{i}", f"thread_{i}")
        
        # Execute: Concurrent agent executions with WebSocket events
        async def simulate_agent_execution(agent_id: int):
            """Simulate complete agent execution with timing."""
            context = AgentExecutionContext(
                agent_name=f"perf_agent_{agent_id}",
                run_id=uuid4(),
                correlation_id=f"perf_correlation_{agent_id}"
            )
            
            start_time = time.time()
            
            # Send agent execution sequence
            run_id = str(context.run_id)
            await websocket_bridge.notify_agent_started(
                run_id=run_id,
                agent_name=context.agent_name,
                trace_context=trace_context.to_websocket_context()
            )
            
            await websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=context.agent_name,
                reasoning=f"Processing performance test {agent_id}...",
                trace_context=trace_context.to_websocket_context()
            )
            
            await websocket_bridge.notify_tool_executing(
                run_id=run_id,
                agent_name=context.agent_name,
                tool_name="performance_tester",
                tool_purpose=f"Test concurrent execution {agent_id}",
                trace_context=trace_context.to_websocket_context()
            )
            
            await websocket_bridge.notify_tool_completed(
                run_id=run_id,
                agent_name=context.agent_name, 
                tool_name="performance_tester",
                result={"test_id": agent_id, "status": "success"},
                trace_context=trace_context.to_websocket_context()
            )
            
            await websocket_bridge.notify_agent_completed(
                run_id=run_id,
                agent_name=context.agent_name,
                result={"agent_id": agent_id, "performance_test": "passed"},
                execution_time_ms=int((time.time() - start_time) * 1000),
                trace_context=trace_context.to_websocket_context()
            )
            
            return time.time() - start_time
        
        # Execute: All agent executions concurrently
        start_time = time.time()
        execution_times = await asyncio.gather(*[
            simulate_agent_execution(i) for i in range(10)
        ])
        total_time = time.time() - start_time
        
        # Verify: Performance characteristics
        assert total_time < 5.0  # Should complete all executions quickly
        assert max(execution_times) < 1.0  # Individual executions should be fast
        
        # Verify: All WebSockets received complete event sequences
        for i, ws in enumerate(websockets):
            assert len(ws.messages_sent) == 5  # All 5 events received
            
            # Verify: Events are for correct agent
            messages = [json.loads(msg["data"]) for msg in ws.messages_sent]
            agent_names = [msg["payload"]["agent_name"] for msg in messages]
            assert all(name == f"perf_agent_{i}" for name in agent_names)
            
            # Verify: Event timing is reasonable 
            timestamps = [msg["timestamp"] for msg in ws.messages_sent]
            event_duration = timestamps[-1] - timestamps[0]
            assert event_duration < 2.0  # Events delivered within reasonable time
            
    async def test_websocket_trace_context_integration(
        self, websocket_bridge, mock_connection_manager, agent_context
    ):
        """Test trace context integration in WebSocket events.""" 
        # BUSINESS VALUE: Distributed tracing enables debugging and monitoring
        
        # Setup: WebSocket connection
        test_websocket = MockWebSocket("trace_user", "trace_thread")
        await mock_connection_manager.add_connection(test_websocket, "trace_user", "trace_thread")
        
        # Setup: Trace context with full details
        trace_context = UnifiedTraceContext(
            user_id="trace_user",
            thread_id="trace_thread",
            correlation_id="trace_correlation_123",
            session_id="trace_session_456", 
            request_id="trace_request_789"
        )
        
        # Execute: Send events with rich trace context
        run_id = str(agent_context.run_id)
        await websocket_bridge.notify_agent_started(
            run_id=run_id,
            agent_name="trace_agent",
            trace_context=trace_context.to_websocket_context()
        )
        
        await websocket_bridge.notify_tool_executing(
            run_id=run_id,
            agent_name="trace_agent",
            tool_name="trace_tool",
            tool_purpose="Test trace propagation", 
            trace_context=trace_context.to_websocket_context()
        )
        
        # Verify: Trace context included in events
        messages = [json.loads(msg["data"]) for msg in test_websocket.messages_sent]
        assert len(messages) == 2
        
        # Verify: Trace context details
        for message in messages:
            trace_ctx = message["payload"]["trace_context"]
            assert trace_ctx["user_id"] == "trace_user"
            assert trace_ctx["thread_id"] == "trace_thread" 
            assert trace_ctx["correlation_id"] == "trace_correlation_123"
            assert "session_id" in trace_ctx
            assert "request_id" in trace_ctx
            assert "timestamp" in trace_ctx  # Added by bridge
            
    async def test_websocket_error_event_integration(
        self, websocket_bridge, mock_connection_manager, agent_context, trace_context
    ):
        """Test WebSocket integration for agent error scenarios."""
        # BUSINESS VALUE: Clear error communication prevents user confusion
        
        # Setup: WebSocket connection
        error_websocket = MockWebSocket("error_user", "error_thread")
        await mock_connection_manager.add_connection(error_websocket, "error_user", "error_thread")
        
        run_id = str(agent_context.run_id)
        
        # Execute: Agent execution with various error scenarios
        
        # Normal start
        await websocket_bridge.notify_agent_started(
            run_id=run_id,
            agent_name="error_test_agent",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Tool error
        await websocket_bridge.notify_tool_error(
            run_id=run_id,
            agent_name="error_test_agent", 
            tool_name="failing_tool",
            error="Connection timeout to external API",
            trace_context=trace_context.to_websocket_context()
        )
        
        # Agent error with recovery attempt
        await websocket_bridge.notify_agent_error(
            run_id=run_id,
            agent_name="error_test_agent",
            error="Temporary service unavailable - retrying...",
            error_type="service_unavailable",
            is_recoverable=True,
            trace_context=trace_context.to_websocket_context()
        )
        
        # Final failure
        await websocket_bridge.notify_agent_error(
            run_id=run_id,
            agent_name="error_test_agent", 
            error="Max retries exceeded - operation failed",
            error_type="max_retries_exceeded",
            is_recoverable=False,
            trace_context=trace_context.to_websocket_context()
        )
        
        # Verify: Error event sequence
        messages = [json.loads(msg["data"]) for msg in error_websocket.messages_sent]
        assert len(messages) == 4
        
        event_types = [msg["type"] for msg in messages]
        assert event_types == ["agent_started", "tool_error", "agent_error", "agent_error"]
        
        # Verify: Tool error details
        tool_error = messages[1]
        assert tool_error["payload"]["tool_name"] == "failing_tool"
        assert "Connection timeout" in tool_error["payload"]["error"]
        
        # Verify: Recoverable error
        recoverable_error = messages[2]
        assert recoverable_error["payload"]["is_recoverable"] is True
        assert "retrying" in recoverable_error["payload"]["error"]
        
        # Verify: Final error
        final_error = messages[3]
        assert final_error["payload"]["is_recoverable"] is False
        assert "Max retries exceeded" in final_error["payload"]["error"]
        
    async def test_websocket_broadcast_integration(
        self, websocket_bridge, mock_connection_manager
    ):
        """Test WebSocket broadcast functionality for system-wide events."""
        # BUSINESS VALUE: System-wide notifications inform all users of important events
        
        # Setup: Multiple user connections
        users = ["user_a", "user_b", "user_c"]
        websockets = []
        for user in users:
            ws = MockWebSocket(user, f"{user}_thread")
            websockets.append(ws)
            await mock_connection_manager.add_connection(ws, user, f"{user}_thread")
        
        # Execute: System-wide broadcast
        await websocket_bridge.broadcast_system_notification(
            notification_type="maintenance_window",
            message="System maintenance scheduled for 2 AM UTC",
            severity="info",
            metadata={
                "maintenance_start": "2024-01-15T02:00:00Z",
                "estimated_duration_minutes": 30,
                "affected_services": ["optimization_engine", "cost_analyzer"]
            }
        )
        
        # Verify: All users received broadcast
        for i, ws in enumerate(websockets):
            messages = ws.messages_sent
            assert len(messages) == 1
            
            broadcast_msg = json.loads(messages[0]["data"])
            assert broadcast_msg["type"] == "system_notification"
            assert broadcast_msg["payload"]["notification_type"] == "maintenance_window"
            assert "maintenance scheduled" in broadcast_msg["payload"]["message"]
            assert broadcast_msg["payload"]["severity"] == "info"
            assert broadcast_msg["payload"]["metadata"]["estimated_duration_minutes"] == 30
        
        # Verify: Broadcast recorded in connection manager
        assert len(mock_connection_manager.broadcasts) == 1
        broadcast_record = mock_connection_manager.broadcasts[0]
        assert broadcast_record["message"]["type"] == "system_notification"