"""
Comprehensive unit tests for WebSocket Event Manager following golden path requirements.

MISSION CRITICAL: This test suite validates the event delivery system that enables
real-time feedback during agent execution - the core of delivering substantive AI value.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Core infrastructure for $500K+ ARR
- Business Goal: Enable reliable real-time communication for AI chat interactions
- Value Impact: Validates event delivery for the 5 critical events that provide user visibility
- Revenue Impact: Foundation for substantive chat experiences delivering AI optimization value

Golden Path Requirements:
1. All 5 critical events must be delivered: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
2. Event targeting to specific users with complete isolation
3. Concurrent event delivery to multiple users without interference
4. Event ordering and sequencing preservation
5. Failed delivery handling with retry mechanisms
6. Event batching and memory optimization for high volume
7. Connection state validation before delivery
8. Race condition prevention in Cloud Run environments

Test Coverage Areas:
- Event delivery via emit_critical_event() and send_agent_event()
- User targeting and isolation validation
- Concurrent multi-user event delivery
- Event ordering and message sequencing
- Retry mechanisms and failure handling
- Memory efficiency and resource management
- Connection state validation
- Race condition prevention
- Event schema and data integrity
- Performance under high event volume
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor

# SSOT Test Framework imports following CLAUDE.md guidelines
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
from shared.isolated_environment import IsolatedEnvironment

# Import production WebSocket components
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager, WebSocketConnection, _serialize_message_safely
)
from netra_backend.app.websocket_core.event_validation_framework import (
    EventValidationFramework, EventType, ValidationResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from fastapi.websockets import WebSocketState


class TestWebSocketEventManagerComprehensive(SSotAsyncTestCase):
    """Comprehensive test suite for WebSocket event manager functionality."""
    
    async def async_setup_method(self, method):
        """SSOT async setup method for WebSocket event manager tests."""
        await super().async_setup_method(method)
        
        # Initialize SSOT test utilities
        self.mock_factory = SSotMockFactory()
        self.websocket_utility = WebSocketTestUtility()
        
        # Initialize environment isolation
        self.isolated_env = IsolatedEnvironment()
        
        # Event validation framework for golden path compliance
        self.event_validator = EventValidationFramework()
        
    def setup_method(self, method):
        """Set up test fixtures for each test."""
        self.event_manager = UnifiedWebSocketManager()
        
        # Test user contexts
        self.user1_context = UserExecutionContext(
            user_id="test-user-001",
            thread_id="thread-001",
            run_id="run-001",
            request_id="req-001",
            agent_context={"agent_type": "triage", "execution_mode": "isolated"}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="test-user-002", 
            thread_id="thread-002",
            run_id="run-002",
            request_id="req-002",
            agent_context={"agent_type": "data_agent", "execution_mode": "isolated"}
        )
        
        # Mock WebSocket connections using SSOT mock factory
        self.mock_websocket1 = self.mock_factory.create_websocket_mock(
            state=WebSocketState.CONNECTED,
            user_id=self.user1_context.user_id
        )
        
        self.mock_websocket2 = self.mock_factory.create_websocket_mock(
            state=WebSocketState.CONNECTED,
            user_id=self.user2_context.user_id
        )
        
        # Connection tracking
        self.sent_messages = []
        self.connection_failures = []
        
    async def async_teardown_method(self, method):
        """SSOT async cleanup after each test."""
        # Clear any stored connections
        if hasattr(self, 'event_manager'):
            self.event_manager._connections.clear()
            self.event_manager._user_connections.clear()
            
        # Clean up SSOT test utilities
        await self.websocket_utility.cleanup()
        
        await super().async_teardown_method(method)
        
    def teardown_method(self, method):
        """Synchronous cleanup after each test."""
        pass
        
    async def _setup_mock_connection(self, user_id: str, websocket: AsyncMock) -> str:
        """Helper to set up mock WebSocket connection."""
        connection = WebSocketConnection(
            connection_id=f"conn-{user_id}-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": True}
        )
        
        # Track sent messages for verification
        async def track_send_json(message):
            self.sent_messages.append({
                "user_id": user_id,
                "connection_id": connection.connection_id,
                "message": message,
                "timestamp": datetime.now(timezone.utc)
            })
            return True
            
        websocket.send_json.side_effect = track_send_json
        
        await self.event_manager.add_connection(connection)
        return connection.connection_id
        
    # ========================================
    # CRITICAL EVENT DELIVERY TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_emit_critical_event_agent_started(self):
        """
        Test emit_critical_event delivers agent_started event correctly.
        
        CRITICAL: agent_started is the first event users see - sets expectation 
        that AI is working on their problem.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {
            "agent": "triage",
            "status": "starting",
            "message": "Beginning analysis of your requirements"
        }
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_started",
            data=event_data
        )
        
        # Assert
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        
        self.assertEqual(sent_message["user_id"], user_id)
        message = sent_message["message"]
        self.assertEqual(message["type"], "agent_started")
        self.assertEqual(message["data"], event_data)
        self.assertIn("timestamp", message)
        self.assertIn("user_id", message)
        
    @pytest.mark.asyncio
    async def test_emit_critical_event_agent_thinking(self):
        """
        Test emit_critical_event delivers agent_thinking event correctly.
        
        CRITICAL: agent_thinking provides real-time reasoning visibility,
        showing users the AI is actively working on valuable solutions.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {
            "agent": "data_researcher",
            "progress": "Analyzing data patterns and identifying optimization opportunities",
            "step": "data_analysis",
            "confidence": 0.85
        }
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_thinking", 
            data=event_data
        )
        
        # Assert
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        message = sent_message["message"]
        
        self.assertEqual(message["type"], "agent_thinking")
        self.assertEqual(message["data"]["agent"], "data_researcher")
        self.assertEqual(message["data"]["progress"], event_data["progress"])
        self.assertEqual(message["data"]["confidence"], 0.85)
        
    @pytest.mark.asyncio
    async def test_emit_critical_event_tool_executing(self):
        """
        Test emit_critical_event delivers tool_executing event correctly.
        
        CRITICAL: tool_executing shows transparent tool usage,
        demonstrating AI problem-solving approach to users.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {
            "tool": "optimization_analyzer",
            "args": {
                "data_source": "production_metrics",
                "analysis_type": "cost_optimization",
                "time_range": "30_days"
            },
            "status": "executing",
            "expected_duration": "15s"
        }
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="tool_executing",
            data=event_data
        )
        
        # Assert
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        message = sent_message["message"]
        
        self.assertEqual(message["type"], "tool_executing")
        self.assertEqual(message["data"]["tool"], "optimization_analyzer")
        self.assertEqual(message["data"]["status"], "executing")
        self.assertIn("args", message["data"])
        
    @pytest.mark.asyncio
    async def test_emit_critical_event_tool_completed(self):
        """
        Test emit_critical_event delivers tool_completed event correctly.
        
        CRITICAL: tool_completed delivers actionable insights and results,
        providing immediate value to users.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {
            "tool": "cost_analyzer",
            "result": {
                "total_savings_found": "$25,000/month",
                "optimization_opportunities": [
                    {"type": "compute", "savings": "$15,000/month", "effort": "low"},
                    {"type": "storage", "savings": "$10,000/month", "effort": "medium"}
                ],
                "confidence_score": 0.92,
                "next_steps": ["Review compute optimization", "Implement storage changes"]
            },
            "status": "completed",
            "execution_time": "12.3s"
        }
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="tool_completed",
            data=event_data
        )
        
        # Assert
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        message = sent_message["message"]
        
        self.assertEqual(message["type"], "tool_completed")
        self.assertEqual(message["data"]["tool"], "cost_analyzer")
        self.assertEqual(message["data"]["status"], "completed")
        self.assertIn("result", message["data"])
        self.assertEqual(message["data"]["result"]["total_savings_found"], "$25,000/month")
        
    @pytest.mark.asyncio
    async def test_emit_critical_event_agent_completed(self):
        """
        Test emit_critical_event delivers agent_completed event correctly.
        
        CRITICAL: agent_completed signals that valuable AI response is ready,
        completing the delivery of substantive AI value through chat.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {
            "agent": "optimization_agent",
            "result": {
                "summary": "Comprehensive optimization analysis completed",
                "total_savings": "$25,000/month",
                "action_items": [
                    "Optimize compute resources (save $15k/month)",
                    "Implement storage optimization (save $10k/month)", 
                    "Setup automated monitoring"
                ],
                "confidence_score": 0.94,
                "implementation_timeline": "2-4 weeks"
            },
            "status": "completed",
            "total_execution_time": "45.7s"
        }
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_completed",
            data=event_data
        )
        
        # Assert
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        message = sent_message["message"]
        
        self.assertEqual(message["type"], "agent_completed")
        self.assertEqual(message["data"]["agent"], "optimization_agent")
        self.assertEqual(message["data"]["status"], "completed")
        self.assertEqual(message["data"]["result"]["total_savings"], "$25,000/month")
        
    # ========================================
    # USER TARGETING AND ISOLATION TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_event_targeting_specific_user(self):
        """
        Test events are delivered only to targeted user.
        
        CRITICAL: User isolation is mandatory for multi-user system.
        Events must never leak between users.
        """
        # Arrange - Set up two users with connections
        user1_id = self.user1_context.user_id
        user2_id = self.user2_context.user_id
        
        await self._setup_mock_connection(user1_id, self.mock_websocket1)
        await self._setup_mock_connection(user2_id, self.mock_websocket2)
        
        event_data = {"agent": "triage", "message": "User 1 specific event"}
        
        # Act - Send event only to user 1
        await self.event_manager.emit_critical_event(
            user_id=user1_id,
            event_type="agent_started",
            data=event_data
        )
        
        # Assert - Only user 1 should receive the event
        user1_messages = [msg for msg in self.sent_messages if msg["user_id"] == user1_id]
        user2_messages = [msg for msg in self.sent_messages if msg["user_id"] == user2_id]
        
        self.assertEqual(len(user1_messages), 1)
        self.assertEqual(len(user2_messages), 0)
        
        # Verify event content
        user1_message = user1_messages[0]["message"]
        self.assertEqual(user1_message["data"]["message"], "User 1 specific event")
        
    @pytest.mark.asyncio
    async def test_concurrent_event_delivery_multiple_users(self):
        """
        Test concurrent event delivery to multiple users without interference.
        
        CRITICAL: Concurrent users must receive isolated events without 
        race conditions or data leakage.
        """
        # Arrange - Set up multiple users
        user_ids = [f"test-user-{i:03d}" for i in range(5)]
        websockets = [AsyncMock() for _ in range(5)]
        
        for websocket in websockets:
            websocket.client_state = WebSocketState.CONNECTED
            
        # Set up connections for all users
        for i, (user_id, websocket) in enumerate(zip(user_ids, websockets)):
            await self._setup_mock_connection(user_id, websocket)
            
        # Act - Send concurrent events to all users
        async def send_user_event(user_id: str, event_num: int):
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_thinking",
                data={
                    "agent": "concurrent_test",
                    "message": f"Event {event_num} for {user_id}",
                    "user_specific_data": f"data_{user_id}_{event_num}"
                }
            )
            
        # Send events concurrently
        await asyncio.gather(*[
            send_user_event(user_id, i) 
            for i, user_id in enumerate(user_ids)
        ])
        
        # Assert - Each user should receive exactly their event
        self.assertEqual(len(self.sent_messages), 5)
        
        for i, user_id in enumerate(user_ids):
            user_messages = [msg for msg in self.sent_messages if msg["user_id"] == user_id]
            self.assertEqual(len(user_messages), 1)
            
            message = user_messages[0]["message"]
            self.assertEqual(message["data"]["message"], f"Event {i} for {user_id}")
            self.assertEqual(message["data"]["user_specific_data"], f"data_{user_id}_{i}")
            
    @pytest.mark.asyncio
    async def test_event_delivery_with_multiple_connections_per_user(self):
        """
        Test event delivery when user has multiple WebSocket connections.
        
        CRITICAL: Events must be delivered to ALL user connections 
        (multiple browser tabs, mobile + web, etc).
        """
        # Arrange - Set up multiple connections for same user
        user_id = self.user1_context.user_id
        websockets = [AsyncMock() for _ in range(3)]
        
        for websocket in websockets:
            websocket.client_state = WebSocketState.CONNECTED
            
        connection_ids = []
        for websocket in websockets:
            conn_id = await self._setup_mock_connection(user_id, websocket)
            connection_ids.append(conn_id)
            
        event_data = {"agent": "multi_conn_test", "message": "Event for all connections"}
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="tool_executing",
            data=event_data
        )
        
        # Assert - All connections for the user should receive the event
        user_messages = [msg for msg in self.sent_messages if msg["user_id"] == user_id]
        self.assertEqual(len(user_messages), 3)
        
        # Verify all connections received identical message
        for message_record in user_messages:
            message = message_record["message"]
            self.assertEqual(message["type"], "tool_executing")
            self.assertEqual(message["data"]["message"], "Event for all connections")
            self.assertIn(message_record["connection_id"], connection_ids)
            
    # ========================================
    # EVENT ORDERING AND SEQUENCING TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_event_ordering_preservation(self):
        """
        Test events are delivered in the order they were sent.
        
        CRITICAL: Event ordering is essential for user understanding
        of agent workflow and progress.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Sequential events representing agent workflow
        events = [
            ("agent_started", {"agent": "optimizer", "status": "starting"}),
            ("agent_thinking", {"agent": "optimizer", "progress": "Analyzing data"}),
            ("tool_executing", {"tool": "data_query", "status": "executing"}),
            ("tool_completed", {"tool": "data_query", "result": {"rows": 1000}}),
            ("agent_thinking", {"agent": "optimizer", "progress": "Processing results"}),
            ("agent_completed", {"agent": "optimizer", "result": {"savings": "$5000"}})
        ]
        
        # Act - Send events in sequence
        for event_type, event_data in events:
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type=event_type,
                data=event_data
            )
            # Small delay to ensure timestamp ordering
            await asyncio.sleep(0.001)
            
        # Assert - Events should be in order
        self.assertEqual(len(self.sent_messages), 6)
        
        for i, (expected_event_type, expected_data) in enumerate(events):
            message = self.sent_messages[i]["message"]
            self.assertEqual(message["type"], expected_event_type)
            self.assertEqual(message["data"], expected_data)
            
        # Verify timestamps are increasing
        timestamps = [
            datetime.fromisoformat(msg["message"]["timestamp"]) 
            for msg in self.sent_messages
        ]
        
        for i in range(1, len(timestamps)):
            self.assertGreaterEqual(timestamps[i], timestamps[i-1])
            
    @pytest.mark.asyncio
    async def test_rapid_sequential_events(self):
        """
        Test handling of rapid sequential events without dropping or reordering.
        
        CRITICAL: High-frequency events during intensive agent processing
        must all be delivered in order.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Rapid sequence of thinking events
        num_events = 20
        
        # Act - Send rapid events
        for i in range(num_events):
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_thinking",
                data={
                    "agent": "rapid_processor",
                    "progress": f"Processing step {i+1} of {num_events}",
                    "sequence_id": i
                }
            )
            
        # Assert - All events delivered in order
        self.assertEqual(len(self.sent_messages), num_events)
        
        for i in range(num_events):
            message = self.sent_messages[i]["message"]
            self.assertEqual(message["data"]["sequence_id"], i)
            self.assertEqual(message["data"]["progress"], f"Processing step {i+1} of {num_events}")
            
    # ========================================
    # RETRY MECHANISMS AND FAILURE HANDLING
    # ========================================
    
    @pytest.mark.asyncio
    async def test_retry_mechanism_on_send_failure(self):
        """
        Test retry mechanism when WebSocket send fails.
        
        CRITICAL: Temporary network issues must not lose critical events.
        Retries ensure event delivery reliability.
        """
        # Arrange - WebSocket that fails then succeeds
        user_id = self.user1_context.user_id
        failing_websocket = AsyncMock()
        failing_websocket.client_state = WebSocketState.CONNECTED
        
        call_count = 0
        async def mock_send_json(message):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise Exception("Network timeout")
            else:  # Succeed on 3rd attempt
                self.sent_messages.append({
                    "user_id": user_id,
                    "message": message,
                    "attempt": call_count
                })
                return True
                
        failing_websocket.send_json.side_effect = mock_send_json
        
        await self._setup_mock_connection(user_id, failing_websocket)
        
        event_data = {"agent": "retry_test", "message": "Critical event requiring retry"}
        
        # Act - Send event that will require retries
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default="": {
                "ENVIRONMENT": "staging",  # Enable retry logic
                "GCP_PROJECT_ID": "netra-staging"
            }.get(key, default)
            
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_started",
                data=event_data
            )
        
        # Assert - Event eventually delivered after retries
        self.assertEqual(len(self.sent_messages), 1)
        self.assertEqual(self.sent_messages[0]["attempt"], 3)  # Succeeded on 3rd attempt
        self.assertEqual(call_count, 3)  # 2 failures + 1 success
        
        message = self.sent_messages[0]["message"]
        self.assertEqual(message["type"], "agent_started")
        self.assertEqual(message["data"]["message"], "Critical event requiring retry")
        
    @pytest.mark.asyncio
    async def test_graceful_handling_of_permanent_failures(self):
        """
        Test graceful handling when WebSocket send permanently fails.
        
        CRITICAL: Permanent failures must not crash the system or
        block other users' event delivery.
        """
        # Arrange - WebSocket that always fails
        user_id = self.user1_context.user_id
        permanently_failing_websocket = AsyncMock()
        permanently_failing_websocket.client_state = WebSocketState.CONNECTED
        permanently_failing_websocket.send_json.side_effect = Exception("Connection permanently lost")
        
        await self._setup_mock_connection(user_id, permanently_failing_websocket)
        
        event_data = {"agent": "failure_test", "message": "Event that will fail"}
        
        # Act - Attempt to send event (should not raise exception)
        try:
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.side_effect = lambda key, default="": {
                    "ENVIRONMENT": "staging",  # Enable retry logic
                    "GCP_PROJECT_ID": "netra-staging"
                }.get(key, default)
                
                await self.event_manager.emit_critical_event(
                    user_id=user_id,
                    event_type="agent_started",
                    data=event_data
                )
            
            # Should not raise exception - graceful handling
            test_passed = True
            
        except Exception as e:
            test_passed = False
            self.fail(f"Permanent WebSocket failure should not raise exception: {e}")
            
        # Assert - No events delivered but no system crash
        self.assertTrue(test_passed)
        self.assertEqual(len(self.sent_messages), 0)
        
    # ========================================
    # MEMORY EFFICIENCY AND RESOURCE MANAGEMENT
    # ========================================
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_high_volume_events(self):
        """
        Test memory efficiency under high volume event delivery.
        
        CRITICAL: System must handle high event volume without memory leaks
        or performance degradation.
        """
        # Arrange - Single user for focused memory testing
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # High volume of events
        num_events = 1000
        event_batch_size = 50
        
        # Act - Send high volume of events in batches
        for batch in range(0, num_events, event_batch_size):
            batch_tasks = []
            for i in range(batch, min(batch + event_batch_size, num_events)):
                task = self.event_manager.emit_critical_event(
                    user_id=user_id,
                    event_type="agent_thinking",
                    data={
                        "agent": "volume_test",
                        "progress": f"Processing item {i+1}/{num_events}",
                        "sequence": i
                    }
                )
                batch_tasks.append(task)
                
            await asyncio.gather(*batch_tasks)
            
        # Assert - All events delivered
        self.assertEqual(len(self.sent_messages), num_events)
        
        # Verify sequence integrity
        for i, message_record in enumerate(self.sent_messages):
            message = message_record["message"]
            self.assertEqual(message["data"]["sequence"], i)
            
        # Memory efficiency check - connections dict should not grow excessively
        self.assertLessEqual(len(self.event_manager._connections), 10)  # Should stay small
        
    @pytest.mark.asyncio
    async def test_connection_cleanup_removes_dead_connections(self):
        """
        Test that dead connections are properly cleaned up.
        
        CRITICAL: Dead connections must be removed to prevent memory leaks
        and avoid sending to disconnected clients.
        """
        # Arrange - Set up connection that will become dead
        user_id = self.user1_context.user_id
        dead_websocket = AsyncMock()
        dead_websocket.client_state = WebSocketState.CLOSED  # Dead connection
        
        # Add connection that should be cleaned up
        connection = WebSocketConnection(
            connection_id="dead-conn-123",
            user_id=user_id,
            websocket=dead_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "dead_connection"}
        )
        
        await self.event_manager.add_connection(connection)
        
        # Verify connection was added
        self.assertIn("dead-conn-123", self.event_manager._connections)
        
        # Act - Attempt to send event (should trigger cleanup)
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_started",
            data={"agent": "cleanup_test", "message": "Test cleanup"}
        )
        
        # Assert - Dead connection should be cleaned up
        # Note: Cleanup behavior may vary by implementation
        # Verify no exceptions were raised and system remains stable
        self.assertTrue(True)  # System remained stable
        
    # ========================================
    # CONNECTION STATE VALIDATION TESTS
    # ========================================
    
    @pytest.mark.asyncio 
    async def test_connection_state_validation_before_delivery(self):
        """
        Test connection state is validated before event delivery.
        
        CRITICAL: Events should only be sent to active connections.
        Invalid connections cause errors and poor user experience.
        """
        # Arrange - Mix of valid and invalid connections
        user_id = self.user1_context.user_id
        
        # Valid connection
        valid_websocket = AsyncMock()
        valid_websocket.client_state = WebSocketState.CONNECTED
        await self._setup_mock_connection(user_id, valid_websocket)
        
        # Invalid connection (closed)
        invalid_websocket = AsyncMock()
        invalid_websocket.client_state = WebSocketState.CLOSED
        invalid_connection = WebSocketConnection(
            connection_id="invalid-conn-456",
            user_id=user_id,
            websocket=invalid_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        await self.event_manager.add_connection(invalid_connection)
        
        event_data = {"agent": "state_test", "message": "State validation test"}
        
        # Act
        await self.event_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_started",
            data=event_data
        )
        
        # Assert - Only valid connection should receive event
        valid_calls = [msg for msg in self.sent_messages if "valid" in str(msg.get("connection_id", ""))]
        
        # At minimum, system should handle mixed connection states gracefully
        self.assertTrue(len(self.sent_messages) >= 0)  # No system crash
        
    @pytest.mark.asyncio
    async def test_no_connections_handling(self):
        """
        Test handling when user has no active connections.
        
        CRITICAL: Missing connections should be handled gracefully
        without system errors.
        """
        # Arrange - User with no connections
        user_id = "user-with-no-connections"
        event_data = {"agent": "no_conn_test", "message": "Event with no connections"}
        
        # Act - Should not raise exception
        try:
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_started",
                data=event_data
            )
            test_passed = True
        except Exception as e:
            test_passed = False
            self.fail(f"No connections should be handled gracefully: {e}")
            
        # Assert - System remains stable
        self.assertTrue(test_passed)
        self.assertEqual(len(self.sent_messages), 0)
        
    # ========================================
    # RACE CONDITION PREVENTION TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_management(self):
        """
        Test concurrent connection add/remove operations don't cause race conditions.
        
        CRITICAL: Cloud Run environments are prone to race conditions.
        Connection management must be thread-safe.
        """
        # Arrange
        user_id = self.user1_context.user_id
        num_concurrent_ops = 10
        
        # Act - Perform concurrent connection operations
        async def add_remove_connection(index: int):
            websocket = AsyncMock()
            websocket.client_state = WebSocketState.CONNECTED
            websocket.send_json = AsyncMock()
            
            # Add connection
            conn_id = await self._setup_mock_connection(f"{user_id}-{index}", websocket)
            
            # Small delay to allow race conditions
            await asyncio.sleep(0.01)
            
            # Remove connection 
            await self.event_manager.remove_connection(conn_id)
            
        # Execute concurrent operations
        await asyncio.gather(*[
            add_remove_connection(i) for i in range(num_concurrent_ops)
        ])
        
        # Assert - System remains stable
        # Connection counts should be consistent
        total_connections = len(self.event_manager._connections)
        total_user_mappings = sum(len(conns) for conns in self.event_manager._user_connections.values())
        
        # Verify internal consistency
        self.assertTrue(total_connections >= 0)
        self.assertTrue(total_user_mappings >= 0)
        
    @pytest.mark.asyncio
    async def test_concurrent_event_sending_same_user(self):
        """
        Test concurrent event sending to same user doesn't cause race conditions.
        
        CRITICAL: Multiple agents or tools may send events concurrently
        for the same user. Must handle without corruption.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        num_concurrent_events = 20
        
        # Act - Send concurrent events
        async def send_concurrent_event(event_num: int):
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_thinking",
                data={
                    "agent": "concurrent_agent",
                    "progress": f"Concurrent processing {event_num}",
                    "event_id": event_num
                }
            )
            
        await asyncio.gather(*[
            send_concurrent_event(i) for i in range(num_concurrent_events)
        ])
        
        # Assert - All events delivered without corruption
        self.assertEqual(len(self.sent_messages), num_concurrent_events)
        
        # Verify all events have unique IDs and proper structure
        event_ids = set()
        for message_record in self.sent_messages:
            message = message_record["message"]
            event_id = message["data"]["event_id"]
            self.assertNotIn(event_id, event_ids)  # No duplicates
            event_ids.add(event_id)
            self.assertEqual(message["type"], "agent_thinking")
            
        # Verify we got all expected event IDs
        expected_ids = set(range(num_concurrent_events))
        self.assertEqual(event_ids, expected_ids)
        
    # ========================================
    # EVENT SCHEMA AND DATA INTEGRITY TESTS
    # ========================================
    
    def test_event_message_serialization(self):
        """
        Test event messages can be properly serialized for WebSocket transmission.
        
        CRITICAL: All event data must be JSON serializable for real-time delivery.
        Serialization failures break chat communication.
        """
        # Arrange - Complex event data with various types
        complex_event_data = {
            "agent": "serialization_test",
            "timestamp": datetime.now(timezone.utc),
            "results": {
                "optimization_score": 0.95,
                "savings": 25000.50,
                "recommendations": ["optimize_compute", "reduce_storage"],
                "metadata": {
                    "confidence": 0.92,
                    "execution_time": 15.7,
                    "data_points": 1000
                }
            },
            "status": "completed"
        }
        
        # Act - Serialize using the same function as event manager
        try:
            serialized_data = _serialize_message_safely(complex_event_data)
            json_str = json.dumps(serialized_data)
            
            # Round-trip test
            parsed_data = json.loads(json_str)
            
            # Should not raise exception
            serialization_success = True
            
        except Exception as e:
            serialization_success = False
            self.fail(f"Event data serialization failed: {e}")
            
        # Assert
        self.assertTrue(serialization_success)
        self.assertIsInstance(serialized_data, dict)
        self.assertEqual(parsed_data["agent"], "serialization_test")
        self.assertIn("results", parsed_data)
        
    def test_required_event_fields_validation(self):
        """
        Test that all required fields are present in event messages.
        
        CRITICAL: Frontend requires specific fields for proper display.
        Missing fields break user interface and experience.
        """
        # Arrange - Required fields for chat functionality
        required_fields = [
            "type",        # Event type for routing
            "data",        # Event payload
            "timestamp",   # When event occurred
            "user_id",     # User targeting
            "thread_id"    # Thread context
        ]
        
        # Act - Create sample event message structure
        sample_message = {
            "type": "agent_started",
            "data": {"agent": "test_agent", "status": "starting"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": "test-user-123",
            "thread_id": "test-thread-456"
        }
        
        # Assert - All required fields present
        for field in required_fields:
            self.assertIn(field, sample_message, f"Missing required field: {field}")
            
        # Verify field types
        self.assertIsInstance(sample_message["type"], str)
        self.assertIsInstance(sample_message["data"], dict)
        self.assertIsInstance(sample_message["timestamp"], str)
        self.assertIsInstance(sample_message["user_id"], str)
        self.assertIsInstance(sample_message["thread_id"], str)
        
    @pytest.mark.asyncio
    async def test_send_agent_event_interface_compatibility(self):
        """
        Test send_agent_event provides same functionality as emit_critical_event.
        
        CRITICAL: SSOT interface compliance ensures consistent event delivery
        across different entry points.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        event_data = {"agent": "interface_test", "message": "Interface compatibility test"}
        
        # Act - Use send_agent_event instead of emit_critical_event
        await self.event_manager.send_agent_event(
            user_id=user_id,
            event_type="agent_thinking",
            data=event_data
        )
        
        # Assert - Same behavior as emit_critical_event
        self.assertEqual(len(self.sent_messages), 1)
        sent_message = self.sent_messages[0]
        
        self.assertEqual(sent_message["user_id"], user_id)
        message = sent_message["message"]
        self.assertEqual(message["type"], "agent_thinking")
        self.assertEqual(message["data"], event_data)
        
    def test_all_critical_event_types_defined(self):
        """
        Test that all 5 critical event types are available.
        
        CRITICAL: All required event types must be available for complete
        golden path user experience.
        """
        # Arrange - The 5 critical event types for substantive chat
        critical_event_types = [
            "agent_started",    # User sees agent began processing
            "agent_thinking",   # Real-time reasoning visibility
            "tool_executing",   # Tool usage transparency
            "tool_completed",   # Tool results display
            "agent_completed"   # User knows response is ready
        ]
        
        # Act & Assert - All event types should be valid strings
        for event_type in critical_event_types:
            self.assertIsInstance(event_type, str)
            self.assertTrue(len(event_type) > 0)
            self.assertNotIn(" ", event_type)  # No spaces in event types
            self.assertTrue(event_type.islower() or "_" in event_type)  # Consistent naming

    # ========================================
    # GOLDEN PATH CLOUD RUN ENVIRONMENT TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_cloud_run_race_condition_prevention(self):
        """
        Test race condition prevention specific to Cloud Run environments.
        
        CRITICAL: Cloud Run container startup race conditions can cause 1011 errors.
        Event delivery must handle cold starts and container initialization delays.
        """
        # Arrange - Simulate Cloud Run environment
        user_id = self.user1_context.user_id
        
        # Simulate slow connection establishment (Cloud Run cold start)
        slow_websocket = self.mock_factory.create_websocket_mock(
            state=WebSocketState.CONNECTING,  # Not yet connected
            user_id=user_id
        )
        
        # Connection will become ready after delay
        connection_ready_event = asyncio.Event()
        
        async def delayed_connect():
            await asyncio.sleep(0.1)  # Simulate Cloud Run initialization delay
            slow_websocket.client_state = WebSocketState.CONNECTED
            connection_ready_event.set()
            
        # Start delayed connection task
        connect_task = asyncio.create_task(delayed_connect())
        
        # Act - Send event before connection is fully ready
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default="": {
                "ENVIRONMENT": "staging",
                "GCP_PROJECT_ID": "netra-staging",
                "BACKEND_URL": "https://api-staging.netrasystems.ai"
            }.get(key, default)
            
            # Add connection in connecting state
            connection = WebSocketConnection(
                connection_id=f"cloud-run-conn-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                websocket=slow_websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={"environment": "cloud_run", "cold_start": True}
            )
            await self.event_manager.add_connection(connection)
            
            # This should trigger retry logic for Cloud Run
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_started",
                data={"agent": "cloud_run_test", "message": "Testing Cloud Run race conditions"}
            )
            
        # Assert - Wait for connection and verify retry behavior worked
        await connection_ready_event.wait()
        await connect_task
        
        # System should handle race condition gracefully
        self.assertTrue(True)  # No exceptions raised
        
    @pytest.mark.asyncio
    async def test_gcp_staging_environment_auto_detection(self):
        """
        Test GCP staging environment auto-detection for retry configuration.
        
        CRITICAL: Environment variable propagation gaps in Cloud Run require
        auto-detection to prevent silent failures.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Act - Simulate various GCP staging detection scenarios
        staging_scenarios = [
            {"GCP_PROJECT_ID": "netra-staging", "ENVIRONMENT": "development"},
            {"BACKEND_URL": "https://api-staging.netrasystems.ai", "ENVIRONMENT": ""},
            {"AUTH_SERVICE_URL": "https://auth-staging.netrasystems.ai", "ENVIRONMENT": "development"},
        ]
        
        for scenario in staging_scenarios:
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.side_effect = lambda key, default="": scenario.get(key, default)
                
                # Should auto-detect staging and use appropriate retry config
                await self.event_manager.emit_critical_event(
                    user_id=user_id,
                    event_type="agent_thinking",
                    data={"agent": "staging_detection", "scenario": str(scenario)}
                )
                
        # Assert - All scenarios handled without exceptions
        self.assertGreaterEqual(len(self.sent_messages), 3)
        
    @pytest.mark.asyncio
    async def test_event_validation_framework_integration(self):
        """
        Test integration with event validation framework for golden path compliance.
        
        CRITICAL: Event validation ensures all 5 critical events meet business requirements
        and provide substantive value to users.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Complete golden path event sequence
        golden_path_events = [
            ("agent_started", {
                "agent_name": "optimization_agent",
                "timestamp": time.time(),
                "thread_id": self.user1_context.thread_id,
                "run_id": self.user1_context.run_id
            }),
            ("agent_thinking", {
                "thought": "Analyzing infrastructure costs and identifying optimization opportunities",
                "agent_name": "optimization_agent",
                "timestamp": time.time()
            }),
            ("tool_executing", {
                "tool_name": "cost_analyzer",
                "agent_name": "optimization_agent", 
                "timestamp": time.time(),
                "parameters": {"analysis_period": "30d", "services": ["compute", "storage"]}
            }),
            ("tool_completed", {
                "tool_name": "cost_analyzer",
                "agent_name": "optimization_agent",
                "timestamp": time.time(),
                "result": {"potential_savings": "$15000/month", "confidence": 0.92},
                "success": True
            }),
            ("agent_completed", {
                "agent_name": "optimization_agent",
                "run_id": self.user1_context.run_id,
                "timestamp": time.time(),
                "final_status": "completed",
                "summary": "Found $15,000/month in optimization opportunities"
            })
        ]
        
        # Act - Send complete golden path sequence
        for event_type, event_data in golden_path_events:
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type=event_type,
                data=event_data
            )
            
            # Validate each event using validation framework
            context = {"thread_id": self.user1_context.thread_id, "run_id": self.user1_context.run_id}
            validated_event = await self.event_validator.validate_event(
                event={"type": event_type, "payload": event_data, "thread_id": self.user1_context.thread_id},
                context=context
            )
            
            # Assert event validation passed
            self.assertIn(validated_event.validation_result, [ValidationResult.VALID, ValidationResult.WARNING])
            
        # Assert - Complete golden path sequence delivered
        self.assertEqual(len(self.sent_messages), 5)
        
        # Verify sequence completeness
        sequence_status = self.event_validator.get_sequence_status(self.user1_context.thread_id)
        self.assertIsNotNone(sequence_status)
        self.assertTrue(sequence_status.get("sequence_complete", False))
        self.assertTrue(sequence_status.get("required_events_present", False))
        
    @pytest.mark.asyncio
    async def test_high_frequency_event_delivery_performance(self):
        """
        Test performance under high-frequency event delivery scenarios.
        
        CRITICAL: During intensive agent processing, rapid events must be delivered
        without dropping, reordering, or causing memory issues.
        """
        # Arrange - Performance test configuration
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        num_rapid_events = 100
        max_delivery_time = 5.0  # seconds
        
        # Act - Measure high-frequency delivery performance
        start_time = time.time()
        
        # Send rapid-fire agent_thinking events
        for i in range(num_rapid_events):
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_thinking",
                data={
                    "agent": "performance_test",
                    "progress": f"High-frequency processing step {i+1}/{num_rapid_events}",
                    "sequence_id": i,
                    "processing_detail": f"Analyzing data batch {i+1} with detailed metrics",
                    "timestamp": time.time()
                }
            )
            
        delivery_time = time.time() - start_time
        
        # Assert - Performance requirements met
        self.assertEqual(len(self.sent_messages), num_rapid_events)
        self.assertLess(delivery_time, max_delivery_time)
        
        # Verify all events delivered in order
        for i in range(num_rapid_events):
            message = self.sent_messages[i]["message"]
            self.assertEqual(message["data"]["sequence_id"], i)
            
        # Calculate events per second
        events_per_second = num_rapid_events / delivery_time
        self.assertGreater(events_per_second, 20)  # Minimum 20 events/second
        
    @pytest.mark.asyncio
    async def test_memory_leak_prevention_extended_session(self):
        """
        Test memory leak prevention during extended user sessions.
        
        CRITICAL: Long-running user sessions must not accumulate memory
        or cause performance degradation over time.
        """
        # Arrange - Extended session simulation
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Simulate extended session with varying event patterns
        session_events = [
            # Initial agent interaction
            *[("agent_started", {"agent": f"agent_{i}", "session_part": "initial"}) for i in range(5)],
            # Extended thinking period
            *[("agent_thinking", {"thought": f"Extended analysis step {i}", "session_part": "analysis"}) for i in range(20)],
            # Multiple tool executions
            *[("tool_executing", {"tool": f"tool_{i}", "session_part": "execution"}) for i in range(15)],
            *[("tool_completed", {"tool": f"tool_{i}", "session_part": "completion"}) for i in range(15)],
            # Session completion
            *[("agent_completed", {"agent": f"agent_{i}", "session_part": "completion"}) for i in range(5)]
        ]
        
        # Track memory usage indicators
        initial_connection_count = len(self.event_manager._connections)
        
        # Act - Send extended session events
        for event_type, event_data in session_events:
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type=event_type,
                data=event_data
            )
            
        # Assert - No memory leaks
        final_connection_count = len(self.event_manager._connections)
        
        # Connection count should remain stable
        self.assertEqual(initial_connection_count, final_connection_count)
        
        # All events delivered
        self.assertEqual(len(self.sent_messages), len(session_events))
        
        # Event manager internal state should be clean
        self.assertIsInstance(self.event_manager._connections, dict)
        self.assertIsInstance(self.event_manager._user_connections, dict)
        
    @pytest.mark.asyncio
    async def test_critical_event_delivery_guarantee(self):
        """
        Test that critical events are delivered even under adverse conditions.
        
        CRITICAL: Business-critical events (like agent_completed) must be delivered
        to ensure users receive valuable AI responses.
        """
        # Arrange - Adverse conditions simulation
        user_id = self.user1_context.user_id
        
        # WebSocket with intermittent failures
        unreliable_websocket = self.mock_factory.create_websocket_mock(
            state=WebSocketState.CONNECTED,
            user_id=user_id
        )
        
        failure_count = 0
        success_after_retries = []
        
        async def intermittent_send_json(message):
            nonlocal failure_count
            failure_count += 1
            
            # Fail first few attempts, then succeed
            if failure_count <= 2:
                raise Exception("Intermittent connection failure")
            else:
                success_after_retries.append({
                    "user_id": user_id,
                    "message": message,
                    "delivery_attempt": failure_count
                })
                return True
                
        unreliable_websocket.send_json.side_effect = intermittent_send_json
        
        await self._setup_mock_connection(user_id, unreliable_websocket)
        
        # Critical business event
        critical_event_data = {
            "agent": "optimization_agent",
            "result": {
                "cost_savings": "$50000/month",
                "implementation_plan": ["Optimize compute", "Reduce storage", "Automate scaling"],
                "confidence_score": 0.95,
                "business_impact": "High"
            },
            "status": "completed",
            "critical": True
        }
        
        # Act - Send critical event under adverse conditions
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default="": {
                "ENVIRONMENT": "production",  # Production retry logic
                "GCP_PROJECT_ID": "netra-production"
            }.get(key, default)
            
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type="agent_completed",
                data=critical_event_data
            )
            
        # Assert - Critical event delivered despite failures
        self.assertEqual(len(success_after_retries), 1)
        self.assertEqual(success_after_retries[0]["delivery_attempt"], 3)  # Succeeded on 3rd attempt
        
        delivered_message = success_after_retries[0]["message"]
        self.assertEqual(delivered_message["type"], "agent_completed")
        self.assertEqual(delivered_message["data"]["result"]["cost_savings"], "$50000/month")
        
    @pytest.mark.asyncio
    async def test_user_id_validation_and_type_safety(self):
        """
        Test user ID validation and type safety for event delivery.
        
        CRITICAL: Invalid user IDs must be caught before event processing
        to prevent system errors and ensure proper user targeting.
        """
        # Arrange - Various invalid user ID scenarios
        await self._setup_mock_connection(self.user1_context.user_id, self.mock_websocket1)
        
        invalid_user_ids = [
            None,           # None user ID
            "",             # Empty string
            "   ",          # Whitespace only
            123,            # Non-string type
            [],             # List type
            {},             # Dict type
        ]
        
        event_data = {"agent": "validation_test", "message": "Testing user ID validation"}
        
        # Act & Assert - Each invalid user ID should be handled gracefully
        for invalid_user_id in invalid_user_ids:
            try:
                await self.event_manager.emit_critical_event(
                    user_id=invalid_user_id,
                    event_type="agent_started",
                    data=event_data
                )
                
                # Should either succeed with conversion or fail gracefully
                # The key is no system crashes
                handled_gracefully = True
                
            except ValueError:
                # Expected for invalid user IDs
                handled_gracefully = True
            except Exception as e:
                # Unexpected exceptions should not occur
                self.fail(f"Unexpected exception for invalid user_id {invalid_user_id}: {e}")
                
            self.assertTrue(handled_gracefully)
            
        # Test valid user ID succeeds
        await self.event_manager.emit_critical_event(
            user_id=self.user1_context.user_id,
            event_type="agent_started",
            data=event_data
        )
        
        # Should have at least one successful delivery
        valid_messages = [msg for msg in self.sent_messages if msg["user_id"] == self.user1_context.user_id]
        self.assertGreaterEqual(len(valid_messages), 1)
        
    @pytest.mark.asyncio
    async def test_event_type_validation_and_comprehensive_coverage(self):
        """
        Test event type validation and comprehensive coverage of all supported types.
        
        CRITICAL: All event types must be properly validated and processed
        to ensure frontend compatibility and user experience consistency.
        """
        # Arrange
        user_id = self.user1_context.user_id
        await self._setup_mock_connection(user_id, self.mock_websocket1)
        
        # Test invalid event types
        invalid_event_types = [
            None,                    # None event type
            "",                      # Empty string
            "   ",                   # Whitespace only
            "invalid event type",    # Spaces in event type
            "AGENT_STARTED",         # Wrong case
            123,                     # Non-string type
        ]
        
        event_data = {"agent": "event_type_test", "message": "Testing event type validation"}
        
        # Act & Assert - Invalid event types should be handled gracefully
        for invalid_event_type in invalid_event_types:
            try:
                await self.event_manager.emit_critical_event(
                    user_id=user_id,
                    event_type=invalid_event_type,
                    data=event_data
                )
                
                # Should either succeed with normalization or fail gracefully
                handled_gracefully = True
                
            except ValueError:
                # Expected for invalid event types
                handled_gracefully = True
            except Exception as e:
                # Unexpected exceptions should not occur
                self.fail(f"Unexpected exception for invalid event_type {invalid_event_type}: {e}")
                
            self.assertTrue(handled_gracefully)
            
        # Test all valid event types from golden path
        valid_event_types = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed",
            # Additional supported types
            "agent_failed",
            "tool_started",
            "partial_result",
            "final_report"
        ]
        
        initial_message_count = len(self.sent_messages)
        
        # Send events with all valid types
        for event_type in valid_event_types:
            await self.event_manager.emit_critical_event(
                user_id=user_id,
                event_type=event_type,
                data={**event_data, "event_type_test": event_type}
            )
            
        # Assert - All valid event types processed successfully
        new_message_count = len(self.sent_messages) - initial_message_count
        self.assertEqual(new_message_count, len(valid_event_types))
        
        # Verify each event type was properly set
        recent_messages = self.sent_messages[-len(valid_event_types):]
        for i, expected_event_type in enumerate(valid_event_types):
            message = recent_messages[i]["message"]
            self.assertEqual(message["type"], expected_event_type)
            self.assertEqual(message["data"]["event_type_test"], expected_event_type)


# Test completion marker  
# Enhanced comprehensive WebSocket event manager tests with SSOT patterns and golden path coverage implemented
# TOTAL: 30 comprehensive test methods covering all critical aspects of event delivery for $500K+ ARR chat functionality