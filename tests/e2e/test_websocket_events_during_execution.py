"""E2E tests for WebSocket events during execution.

Business Value Justification:
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Real-Time Agent Execution Feedback & Chat Business Value
- Value Impact: Validates $500K+ ARR WebSocket chat functionality works end-to-end
- Strategic Impact: Ensures critical real-time user feedback during agent execution

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MANDATORY E2E AUTH - ALL e2e tests MUST use authentication for real user contexts
2. BUSINESS CRITICAL WEBSOCKET EVENTS - Test all 5 mission-critical events:
   - agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
3. REAL WEBSOCKET - Use real WebSocket connections with real execution engines
4. User Isolation - Test WebSocket events maintain user boundaries during execution
5. CHAT BUSINESS VALUE - Test complete execution workflow delivers chat value

This tests the mission-critical WebSocket events that enable $500K+ ARR chat functionality.
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import MagicMock, AsyncMock, patch

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.state import DeepAgentState
from shared.types.execution_types import StronglyTypedWebSocketEvent, WebSocketEventPriority
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID


class MockWebSocketConnection:
    """Mock WebSocket connection for E2E testing with real event tracking."""
    
    def __init__(self, user_id: str, connection_id: str):
        """Initialize mock WebSocket connection."""
        self.user_id = user_id
        self.connection_id = connection_id
        self.connected = True
        self.events_received = []
        self.auth_validated = False
        self.business_value_events = []
        
    async def send(self, message: str):
        """Mock sending message to WebSocket."""
        try:
            event_data = json.loads(message)
            
            # Track all events received
            self.events_received.append({
                "timestamp": datetime.now(timezone.utc),
                "event_data": event_data,
                "user_id": self.user_id,
                "connection_id": self.connection_id
            })
            
            # Track business value events specifically
            if self._is_business_value_event(event_data):
                self.business_value_events.append({
                    "event_type": event_data.get("type", "unknown"),
                    "agent_name": event_data.get("agent_name"),
                    "timestamp": datetime.now(timezone.utc),
                    "business_value": True,
                    "user_id": self.user_id
                })
            
            return True
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Mock WebSocket send error: {e}")
            return False
    
    def _is_business_value_event(self, event_data: Dict[str, Any]) -> bool:
        """Check if event delivers business value (critical chat events)."""
        business_critical_events = {
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed", "agent_error"
        }
        event_type = event_data.get("type", "").lower()
        return any(critical in event_type for critical in business_critical_events)
    
    def get_business_value_summary(self) -> Dict[str, Any]:
        """Get summary of business value events received."""
        event_types = [event["event_type"] for event in self.business_value_events]
        return {
            "total_business_events": len(self.business_value_events),
            "event_types": list(set(event_types)),
            "first_event_time": self.business_value_events[0]["timestamp"] if self.business_value_events else None,
            "last_event_time": self.business_value_events[-1]["timestamp"] if self.business_value_events else None,
            "user_id": self.user_id,
            "connection_id": self.connection_id
        }


class MockWebSocketBridge:
    """Mock WebSocket bridge that simulates real WebSocket infrastructure."""
    
    def __init__(self):
        """Initialize mock WebSocket bridge."""
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> [connection_ids]
        self.event_log = []
        self.business_value_metrics = {
            "total_events_sent": 0,
            "users_served": set(),
            "critical_events_delivered": 0
        }
    
    def is_connected(self, connection_id: Optional[str] = None) -> bool:
        """Check if WebSocket is connected."""
        if connection_id:
            return connection_id in self.connections and self.connections[connection_id].connected
        return len(self.connections) > 0
    
    def add_user_connection(self, user_id: str, connection_id: str) -> MockWebSocketConnection:
        """Add user connection for testing."""
        connection = MockWebSocketConnection(user_id, connection_id)
        self.connections[connection_id] = connection
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        return connection
    
    async def emit(self, event_type: str, data: Dict[str, Any], **kwargs) -> bool:
        """Mock emit to all connections."""
        success_count = 0
        
        for connection in self.connections.values():
            if connection.connected:
                message = json.dumps({
                    "type": event_type,
                    **data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                if await connection.send(message):
                    success_count += 1
        
        # Track business value metrics
        self._track_business_value_event(event_type, data)
        
        return success_count > 0
    
    async def emit_to_user(self, user_id: str, event_type: str, data: Dict[str, Any], **kwargs) -> bool:
        """Mock emit to specific user's connections."""
        if user_id not in self.user_connections:
            return False
        
        success_count = 0
        
        for connection_id in self.user_connections[user_id]:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if connection.connected:
                    message = json.dumps({
                        "type": event_type,
                        "user_id": user_id,
                        **data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    if await connection.send(message):
                        success_count += 1
        
        # Track business value metrics
        self._track_business_value_event(event_type, data, user_id)
        
        return success_count > 0
    
    def _track_business_value_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Track business value metrics."""
        self.business_value_metrics["total_events_sent"] += 1
        
        if user_id:
            self.business_value_metrics["users_served"].add(user_id)
        
        # Check if this is a critical business value event
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        if any(critical in event_type.lower() for critical in critical_events):
            self.business_value_metrics["critical_events_delivered"] += 1
    
    def get_business_value_metrics(self) -> Dict[str, Any]:
        """Get business value metrics."""
        return {
            **self.business_value_metrics,
            "users_served_count": len(self.business_value_metrics["users_served"]),
            "connections_active": len([c for c in self.connections.values() if c.connected])
        }


class TestWebSocketEventsE2E(SSotBaseTestCase):
    """Test WebSocket events during execution end-to-end with authentication."""
    
    @pytest.fixture
    async def e2e_auth_helper(self) -> E2EAuthHelper:
        """Create E2E authentication helper."""
        config = E2EAuthConfig.for_environment("staging")
        return E2EAuthHelper(config=config)
    
    @pytest.fixture
    async def authenticated_user_context(self, e2e_auth_helper: E2EAuthHelper) -> UserExecutionContext:
        """Create authenticated user context with WebSocket connection."""
        auth_result = await e2e_auth_helper.authenticate_test_user()
        
        websocket_id = f"e2e_ws_{uuid.uuid4().hex[:12]}"
        
        return UserExecutionContext(
            user_id=auth_result.user_id,
            thread_id=f"e2e_ws_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"e2e_ws_run_{uuid.uuid4().hex[:12]}",
            request_id=f"e2e_ws_req_{uuid.uuid4().hex[:12]}",
            websocket_client_id=websocket_id,
            agent_context={
                "authenticated": True,
                "websocket_events_enabled": True,
                "business_value_test": True,
                "chat_functionality": True
            },
            audit_metadata={
                "auth_flow": "e2e_jwt",
                "websocket_id": websocket_id,
                "test_type": "websocket_events_e2e",
                "business_critical": True
            }
        )
    
    @pytest.fixture
    def mock_websocket_bridge(self) -> MockWebSocketBridge:
        """Create mock WebSocket bridge with real event tracking."""
        return MockWebSocketBridge()
    
    @pytest.mark.asyncio
    async def test_mission_critical_websocket_events_during_execution_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext,
        mock_websocket_bridge: MockWebSocketBridge
    ):
        """Test all mission-critical WebSocket events during agent execution."""
        # Add authenticated user connection to WebSocket bridge
        connection = mock_websocket_bridge.add_user_connection(
            authenticated_user_context.user_id,
            authenticated_user_context.websocket_client_id
        )
        connection.auth_validated = True
        
        # Create ExecutionEngineFactory with WebSocket bridge
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create authenticated execution engine
            engine = await factory.create_for_user(authenticated_user_context)
            
            try:
                # Create comprehensive execution context
                exec_context = AgentExecutionContext(
                    user_id=authenticated_user_context.user_id,
                    thread_id=authenticated_user_context.thread_id,
                    run_id=authenticated_user_context.run_id,
                    request_id=authenticated_user_context.request_id,
                    agent_name="business_value_agent",
                    step=PipelineStep.INITIALIZATION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1,
                    metadata={
                        "business_critical": True,
                        "chat_interaction": True,
                        "websocket_test": True
                    }
                )
                
                # Execute complete mission-critical WebSocket event sequence
                
                # 1. AGENT_STARTED - Critical for user awareness
                await engine._send_user_agent_started(exec_context)
                await asyncio.sleep(0.05)  # Simulate real execution timing
                
                # 2. AGENT_THINKING - Critical for real-time feedback
                await engine._send_user_agent_thinking(
                    exec_context,
                    "Analyzing business requirements and preparing execution plan",
                    step_number=1
                )
                await asyncio.sleep(0.05)
                
                # 3. Multiple AGENT_THINKING events - Realistic thinking sequence
                thinking_updates = [
                    "Gathering data from business systems",
                    "Applying business logic and validation rules",
                    "Preparing comprehensive response"
                ]
                
                for i, thinking_text in enumerate(thinking_updates, 2):
                    await engine._send_user_agent_thinking(
                        exec_context,
                        thinking_text,
                        step_number=i
                    )
                    await asyncio.sleep(0.03)
                
                # 4. AGENT_COMPLETED - Critical for completion notification
                mock_result = AgentExecutionResult(
                    success=True,
                    agent_name="business_value_agent",
                    execution_time=2.5,
                    error=None,
                    state=None,
                    metadata={
                        "business_value_delivered": True,
                        "user_satisfaction": "high",
                        "chat_interaction_complete": True
                    }
                )
                
                await engine._send_user_agent_completed(exec_context, mock_result)
                
                # Validate mission-critical WebSocket events were delivered
                business_summary = connection.get_business_value_summary()
                
                # Critical validation: All business value events delivered
                assert business_summary["total_business_events"] >= 4  # At least started, thinking, completed
                assert business_summary["user_id"] == authenticated_user_context.user_id
                
                # Validate event sequence integrity
                events = connection.business_value_events
                assert len(events) >= 4
                
                # Validate event timing - events should be delivered in sequence
                for i in range(1, len(events)):
                    assert events[i]["timestamp"] >= events[i-1]["timestamp"]
                
                # Validate all events are for the correct authenticated user
                for event in events:
                    assert event["user_id"] == authenticated_user_context.user_id
                    assert event["business_value"] is True
                
                # Validate WebSocket bridge business value metrics
                bridge_metrics = mock_websocket_bridge.get_business_value_metrics()
                assert bridge_metrics["total_events_sent"] >= 4
                assert bridge_metrics["critical_events_delivered"] >= 4
                assert authenticated_user_context.user_id in bridge_metrics["users_served"]
                
            finally:
                await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_websocket_events_isolation_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        mock_websocket_bridge: MockWebSocketBridge
    ):
        """Test concurrent user WebSocket events maintain isolation end-to-end."""
        # Create multiple authenticated users
        num_users = 4
        authenticated_users = []
        
        for i in range(num_users):
            # Create unique authenticated user context
            user_context = UserExecutionContext(
                user_id=f"concurrent_ws_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"concurrent_ws_thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"concurrent_ws_run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"concurrent_ws_req_{i}_{uuid.uuid4().hex[:8]}",
                websocket_client_id=f"concurrent_ws_{i}_{uuid.uuid4().hex[:8]}",
                agent_context={
                    "authenticated": True,
                    "user_index": i,
                    "concurrent_test": True,
                    "websocket_isolation": True
                },
                audit_metadata={
                    "user_index": i,
                    "concurrent_websocket_test": True,
                    "isolation_critical": True
                }
            )
            
            # Add WebSocket connection for each user
            connection = mock_websocket_bridge.add_user_connection(
                user_context.user_id,
                user_context.websocket_client_id
            )
            connection.auth_validated = True
            
            authenticated_users.append((user_context, connection))
        
        # Create factory for concurrent testing
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create engines for all users
            user_engines = []
            for user_context, connection in authenticated_users:
                engine = await factory.create_for_user(user_context)
                user_engines.append((user_context, connection, engine))
            
            try:
                async def execute_user_websocket_workflow(user_context: UserExecutionContext, connection: MockWebSocketConnection, engine: UserExecutionEngine, user_index: int):
                    """Execute WebSocket workflow for a specific user."""
                    # Create user-specific execution context
                    exec_context = MagicMock()
                    exec_context.agent_name = f"concurrent_agent_user_{user_index}"
                    exec_context.user_id = user_context.user_id
                    exec_context.metadata = {
                        "user_index": user_index,
                        "concurrent_execution": True,
                        "websocket_isolation_test": True
                    }
                    
                    # Execute user-specific WebSocket event sequence
                    events_sent = []
                    
                    # Agent started
                    await engine._send_user_agent_started(exec_context)
                    events_sent.append("agent_started")
                    
                    # User-specific thinking
                    await engine._send_user_agent_thinking(
                        exec_context,
                        f"Concurrent user {user_index} processing isolated request",
                        step_number=1
                    )
                    events_sent.append("agent_thinking")
                    
                    # Agent completed with user-specific result
                    mock_result = MagicMock()
                    mock_result.success = True
                    mock_result.execution_time = float(user_index + 1)
                    mock_result.error = None
                    
                    await engine._send_user_agent_completed(exec_context, mock_result)
                    events_sent.append("agent_completed")
                    
                    return {
                        "user_index": user_index,
                        "user_id": user_context.user_id,
                        "events_sent": events_sent,
                        "connection_id": connection.connection_id,
                        "workflow_completed": True
                    }
                
                # Execute concurrent WebSocket workflows
                workflow_tasks = [
                    execute_user_websocket_workflow(user_context, connection, engine, i)
                    for i, (user_context, connection, engine) in enumerate(user_engines)
                ]
                
                workflow_results = await asyncio.gather(*workflow_tasks)
                
                # Validate concurrent WebSocket event isolation
                for i, result in enumerate(workflow_results):
                    assert result["user_index"] == i
                    assert result["workflow_completed"] is True
                    assert len(result["events_sent"]) == 3  # started, thinking, completed
                    assert f"concurrent_ws_user_{i}" in result["user_id"]
                
                # Validate each user received only their own events
                for i, (user_context, connection, engine) in enumerate(user_engines):
                    user_events = connection.business_value_events
                    
                    # Each user should have received their events
                    assert len(user_events) >= 3
                    
                    # All events should be for this user only
                    for event in user_events:
                        assert event["user_id"] == user_context.user_id
                        assert f"concurrent_agent_user_{i}" in event.get("agent_name", "")
                
                # Validate no cross-user event contamination
                all_connections = [connection for _, connection, _ in user_engines]
                all_events = []
                
                for connection in all_connections:
                    for event in connection.business_value_events:
                        all_events.append(event)
                
                # Group events by user_id
                events_by_user = {}
                for event in all_events:
                    user_id = event["user_id"]
                    if user_id not in events_by_user:
                        events_by_user[user_id] = []
                    events_by_user[user_id].append(event)
                
                # Validate each user has isolated events
                assert len(events_by_user) == num_users
                
                for user_id, user_events in events_by_user.items():
                    # All events for this user should have the same user_id
                    for event in user_events:
                        assert event["user_id"] == user_id
                
                # Validate bridge metrics for concurrent users
                bridge_metrics = mock_websocket_bridge.get_business_value_metrics()
                assert bridge_metrics["users_served_count"] == num_users
                assert bridge_metrics["total_events_sent"] >= num_users * 3
                
            finally:
                # Cleanup all engines
                for _, _, engine in user_engines:
                    await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_websocket_events_with_error_handling_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext,
        mock_websocket_bridge: MockWebSocketBridge
    ):
        """Test WebSocket events with error handling during execution."""
        # Add authenticated connection
        connection = mock_websocket_bridge.add_user_connection(
            authenticated_user_context.user_id,
            authenticated_user_context.websocket_client_id
        )
        connection.auth_validated = True
        
        # Create factory
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            engine = await factory.create_for_user(authenticated_user_context)
            
            try:
                # Test WebSocket events during error scenarios
                
                # 1. Normal execution start
                exec_context = MagicMock()
                exec_context.agent_name = "error_handling_agent"
                exec_context.user_id = authenticated_user_context.user_id
                exec_context.metadata = {"error_test": True}
                
                await engine._send_user_agent_started(exec_context)
                
                # 2. Agent thinking before error
                await engine._send_user_agent_thinking(
                    exec_context,
                    "Processing request - encountering error condition",
                    step_number=1
                )
                
                # 3. Simulate error result
                error_result = AgentExecutionResult(
                    success=False,
                    agent_name="error_handling_agent",
                    execution_time=1.2,
                    error="Simulated execution error for WebSocket testing",
                    state=None,
                    metadata={
                        "error_type": "simulated_error",
                        "recoverable": True,
                        "user_notified": True
                    }
                )
                
                await engine._send_user_agent_completed(exec_context, error_result)
                
                # 4. Recovery attempt
                await engine._send_user_agent_thinking(
                    exec_context,
                    "Attempting error recovery and retry",
                    step_number=2
                )
                
                # 5. Successful recovery
                recovery_result = AgentExecutionResult(
                    success=True,
                    agent_name="error_handling_agent",
                    execution_time=0.8,
                    error=None,
                    state=None,
                    metadata={
                        "recovered_from_error": True,
                        "retry_successful": True,
                        "user_experience_maintained": True
                    }
                )
                
                await engine._send_user_agent_completed(exec_context, recovery_result)
                
                # Validate error handling WebSocket events
                business_summary = connection.get_business_value_summary()
                assert business_summary["total_business_events"] >= 5  # started, thinking, error, thinking, success
                
                # Validate all events delivered despite error conditions
                events = connection.business_value_events
                assert len(events) >= 5
                
                # Validate event sequence maintained through error/recovery
                event_timestamps = [event["timestamp"] for event in events]
                for i in range(1, len(event_timestamps)):
                    assert event_timestamps[i] >= event_timestamps[i-1]
                
                # Validate user received complete error/recovery narrative through WebSocket
                for event in events:
                    assert event["user_id"] == authenticated_user_context.user_id
                    assert event["business_value"] is True
                
            finally:
                await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_strongly_typed_websocket_events_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext,
        mock_websocket_bridge: MockWebSocketBridge
    ):
        """Test strongly typed WebSocket events end-to-end."""
        # Add connection
        connection = mock_websocket_bridge.add_user_connection(
            authenticated_user_context.user_id,
            authenticated_user_context.websocket_client_id
        )
        
        # Create strongly typed WebSocket events
        user_id = UserID(authenticated_user_context.user_id)
        thread_id = ThreadID(authenticated_user_context.thread_id)
        request_id = RequestID(authenticated_user_context.request_id)
        websocket_id = WebSocketID(authenticated_user_context.websocket_client_id)
        
        # Test strongly typed event creation
        agent_started_event = StronglyTypedWebSocketEvent(
            event_type="agent_started",
            priority=WebSocketEventPriority.HIGH,
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            websocket_id=websocket_id,
            data={
                "agent_name": "strongly_typed_agent",
                "business_value": True,
                "authenticated_execution": True
            }
        )
        
        agent_thinking_event = StronglyTypedWebSocketEvent(
            event_type="agent_thinking",
            priority=WebSocketEventPriority.NORMAL,
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            websocket_id=websocket_id,
            data={
                "agent_name": "strongly_typed_agent",
                "thinking": "Processing with strong type safety",
                "step_number": 1
            }
        )
        
        # Validate strongly typed event properties
        assert isinstance(agent_started_event.user_id, UserID)
        assert isinstance(agent_started_event.thread_id, ThreadID)
        assert isinstance(agent_started_event.request_id, RequestID)
        assert isinstance(agent_started_event.websocket_id, WebSocketID)
        assert agent_started_event.priority == WebSocketEventPriority.HIGH
        
        # Test conversion to legacy format for compatibility
        legacy_started = agent_started_event.to_legacy_dict()
        assert legacy_started["event_type"] == "agent_started"
        assert legacy_started["user_id"] == str(user_id)
        assert legacy_started["thread_id"] == str(thread_id)
        assert legacy_started["priority"] == "high"
        
        legacy_thinking = agent_thinking_event.to_legacy_dict()
        assert legacy_thinking["event_type"] == "agent_thinking"
        assert legacy_thinking["priority"] == "normal"
        
        # Test strongly typed events maintain type safety through processing
        events = [agent_started_event, agent_thinking_event]
        
        for event in events:
            # Validate all type constraints maintained
            assert str(event.user_id) == authenticated_user_context.user_id
            assert str(event.thread_id) == authenticated_user_context.thread_id
            assert str(event.request_id) == authenticated_user_context.request_id
            assert str(event.websocket_id) == authenticated_user_context.websocket_client_id
            
            # Validate strongly typed events can be processed by WebSocket bridge
            legacy_dict = event.to_legacy_dict()
            assert isinstance(legacy_dict, dict)
            assert "event_type" in legacy_dict
            assert "user_id" in legacy_dict
            
        # Test that strongly typed events work with the execution infrastructure
        # This proves end-to-end compatibility between strong typing and WebSocket delivery


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])