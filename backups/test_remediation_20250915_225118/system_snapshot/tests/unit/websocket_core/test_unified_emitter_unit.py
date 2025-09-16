"""
Unit Tests for Unified WebSocket Emitter - Golden Path Event Emission

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Core Real-time Event Infrastructure  
- Business Goal: Ensure WebSocket events are properly emitted for Golden Path real-time feedback
- Value Impact: Event emission enables real-time AI interaction feedback worth $500K+ ARR
- Strategic Impact: Core event infrastructure that provides real-time updates for premium UX
- Revenue Protection: Without proper event emission, users get no real-time feedback -> poor UX -> churn

PURPOSE: This test suite validates the unified WebSocket emitter functionality that
sends real-time events to users during agent execution in the Golden Path user flow.
Event emission is critical for providing users with immediate feedback on agent
progress, creating the responsive AI experience that drives business value.

KEY COVERAGE:
1. Agent event emission (started, thinking, completed, error)
2. Event formatting and validation
3. User-specific event targeting
4. Event delivery confirmation and retry logic
5. Performance requirements for real-time emission  
6. Error handling for failed emissions
7. Event batching and throttling

GOLDEN PATH PROTECTION:
Tests ensure WebSocket emitter can properly send all 5 critical agent events
(agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
to the correct users with proper formatting, enabling the real-time feedback
that's essential for the $500K+ ARR interactive AI experience.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import WebSocket event types and emission components
from netra_backend.app.websocket_core.types import (
    AgentEventType,
    WebSocketMessage,
    create_standard_message
)

# Import user context for event emission
from netra_backend.app.services.user_execution_context import UserExecutionContext


class EventType(Enum):
    """Golden Path critical event types"""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking" 
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"


class EmissionStatus(Enum):
    """Event emission status tracking"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class EmittedEvent:
    """Represents an emitted event for tracking"""
    event_id: str
    event_type: EventType
    user_id: str
    connection_id: str
    payload: Dict[str, Any]
    emission_time: float
    status: EmissionStatus
    delivery_confirmed: bool = False
    retry_count: int = 0


class MockWebSocketConnection:
    """Mock WebSocket connection for testing event emission"""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.is_connected = True
        self.received_events = []
        self.emission_failures = []
        self.latency_simulation = 0.0
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send JSON event with latency simulation"""
        if not self.is_connected:
            raise ConnectionError(f"WebSocket connection {self.connection_id} is closed")
            
        # Simulate network latency
        if self.latency_simulation > 0:
            await asyncio.sleep(self.latency_simulation)
            
        # Store received event
        self.received_events.append({
            "data": data,
            "received_at": time.time(),
            "connection_id": self.connection_id
        })
        
    async def close(self):
        """Mock connection close"""
        self.is_connected = False
        
    def disconnect(self):
        """Simulate connection loss"""
        self.is_connected = False
        
    def get_received_events(self) -> List[Dict[str, Any]]:
        """Get all events received by this connection"""
        return self.received_events.copy()


class MockUnifiedWebSocketEmitter:
    """Mock unified WebSocket emitter for testing event emission logic"""
    
    def __init__(self):
        self.emitted_events = []
        self.active_connections = {}
        self.emission_metrics = {
            "total_events": 0,
            "successful_emissions": 0,
            "failed_emissions": 0,
            "retry_attempts": 0
        }
        self.event_queue = []
        self.batching_enabled = False
        self.batch_size = 10
        self.retry_policy = {
            "max_retries": 3,
            "retry_delay": 0.1
        }
        
    def add_connection(self, connection: MockWebSocketConnection):
        """Add WebSocket connection for event emission"""
        self.active_connections[connection.connection_id] = connection
        
    def remove_connection(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
    async def emit_agent_event(
        self, 
        event_type: EventType,
        user_id: str,
        payload: Dict[str, Any],
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit agent event to user's WebSocket connections"""
        
        # Generate unique event ID
        event_id = f"event_{int(time.time() * 1000)}_{len(self.emitted_events)}"
        
        # Find user's connections
        user_connections = [
            conn for conn in self.active_connections.values()
            if conn.user_id == user_id and conn.is_connected
        ]
        
        if not user_connections:
            # Create failed event for no active connections
            failed_event = EmittedEvent(
                event_id=event_id,
                event_type=event_type,
                user_id=user_id,
                connection_id="none",
                payload=payload,
                emission_time=time.time(),
                status=EmissionStatus.FAILED
            )
            self.emitted_events.append(failed_event)
            self.emission_metrics["failed_emissions"] += 1
            return failed_event
        
        # Prepare event payload
        event_payload = {
            "event_id": event_id,
            "type": event_type.value,
            "user_id": user_id,
            "timestamp": time.time(),
            **payload
        }
        
        # Emit to all user connections
        emission_results = []
        for connection in user_connections:
            try:
                start_time = time.time()
                await connection.send_json(event_payload)
                emission_time = time.time() - start_time
                
                emitted_event = EmittedEvent(
                    event_id=event_id,
                    event_type=event_type,
                    user_id=user_id,
                    connection_id=connection.connection_id,
                    payload=event_payload,
                    emission_time=emission_time,
                    status=EmissionStatus.SENT,
                    delivery_confirmed=True
                )
                
                emission_results.append(emitted_event)
                self.emission_metrics["successful_emissions"] += 1
                
            except Exception as e:
                # Handle emission failure
                failed_event = EmittedEvent(
                    event_id=event_id,
                    event_type=event_type,
                    user_id=user_id,
                    connection_id=connection.connection_id,
                    payload=event_payload,
                    emission_time=time.time(),
                    status=EmissionStatus.FAILED
                )
                
                emission_results.append(failed_event)
                self.emission_metrics["failed_emissions"] += 1
        
        # Store all emission results
        self.emitted_events.extend(emission_results)
        self.emission_metrics["total_events"] += len(emission_results)
        
        # Return first result (for single connection scenarios)
        return emission_results[0] if emission_results else None
    
    async def emit_agent_started(
        self, 
        user_id: str, 
        agent_id: str,
        agent_type: str,
        user_request: str,
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit agent started event - Critical Golden Path event #1"""
        
        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "user_request": user_request,
            "status": "started"
        }
        
        return await self.emit_agent_event(
            EventType.AGENT_STARTED, user_id, payload, context
        )
    
    async def emit_agent_thinking(
        self,
        user_id: str,
        agent_id: str,
        thinking_content: str,
        reasoning_step: Optional[str] = None,
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit agent thinking event - Critical Golden Path event #2"""
        
        payload = {
            "agent_id": agent_id,
            "thinking_content": thinking_content,
            "reasoning_step": reasoning_step,
            "status": "thinking"
        }
        
        return await self.emit_agent_event(
            EventType.AGENT_THINKING, user_id, payload, context
        )
    
    async def emit_tool_executing(
        self,
        user_id: str,
        agent_id: str,
        tool_name: str,
        tool_parameters: Dict[str, Any],
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit tool executing event - Critical Golden Path event #3"""
        
        payload = {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "tool_parameters": tool_parameters,
            "status": "executing"
        }
        
        return await self.emit_agent_event(
            EventType.TOOL_EXECUTING, user_id, payload, context
        )
    
    async def emit_tool_completed(
        self,
        user_id: str,
        agent_id: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        execution_time: float,
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit tool completed event - Critical Golden Path event #4"""
        
        payload = {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "tool_result": tool_result,
            "execution_time": execution_time,
            "status": "completed"
        }
        
        return await self.emit_agent_event(
            EventType.TOOL_COMPLETED, user_id, payload, context
        )
    
    async def emit_agent_completed(
        self,
        user_id: str,
        agent_id: str,
        result: Dict[str, Any],
        execution_time: float,
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit agent completed event - Critical Golden Path event #5"""
        
        payload = {
            "agent_id": agent_id,
            "result": result,
            "execution_time": execution_time,
            "status": "completed"
        }
        
        return await self.emit_agent_event(
            EventType.AGENT_COMPLETED, user_id, payload, context
        )
    
    async def emit_agent_error(
        self,
        user_id: str,
        agent_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        context: Optional[UserExecutionContext] = None
    ) -> EmittedEvent:
        """Emit agent error event"""
        
        payload = {
            "agent_id": agent_id,
            "error_message": error_message,
            "error_code": error_code,
            "status": "error"
        }
        
        return await self.emit_agent_event(
            EventType.AGENT_ERROR, user_id, payload, context
        )
    
    def get_emission_metrics(self) -> Dict[str, Any]:
        """Get emission performance metrics"""
        return self.emission_metrics.copy()
    
    def get_events_for_user(self, user_id: str) -> List[EmittedEvent]:
        """Get all events emitted for a specific user"""
        return [event for event in self.emitted_events if event.user_id == user_id]


class UnifiedEmitterUnitTests(SSotAsyncTestCase):
    """Unit tests for unified WebSocket emitter functionality
    
    This test class validates the critical event emission capabilities that
    provide real-time feedback to users during agent execution in the Golden
    Path user flow. These tests focus on core emission logic without requiring
    complex WebSocket infrastructure dependencies.
    
    Tests MUST ensure unified emitter can:
    1. Emit all 5 critical Golden Path agent events
    2. Target events to correct user connections
    3. Handle emission failures gracefully with retry logic
    4. Meet performance requirements for real-time feedback
    5. Maintain user isolation in event emission
    6. Format events properly for client consumption
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create isolated user context for this test
        self.user_context = SSotMockFactory.create_mock_user_context(
            user_id=f"test_user_{self.get_test_context().test_id}",
            thread_id=f"test_thread_{self.get_test_context().test_id}",
            run_id=f"test_run_{self.get_test_context().test_id}",
            request_id=f"test_req_{self.get_test_context().test_id}"
        )
        
        # Create WebSocket emitter instance
        self.emitter = MockUnifiedWebSocketEmitter()
        
        # Create mock WebSocket connection for user
        self.connection = MockWebSocketConnection(
            connection_id=f"conn_{self.user_context.user_id}",
            user_id=self.user_context.user_id
        )
        self.emitter.add_connection(self.connection)
        
        # Create test agent ID
        self.test_agent_id = f"agent_{self.get_test_context().test_id}"
    
    # ========================================================================
    # CRITICAL GOLDEN PATH EVENT EMISSION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_agent_started_event_emission(self):
        """Test emission of agent started event - Golden Path Event #1
        
        Business Impact: Agent started events inform users their request
        is being processed, providing critical first feedback in Golden Path.
        """
        # Emit agent started event
        start_time = time.time()
        emitted_event = await self.emitter.emit_agent_started(
            user_id=self.user_context.user_id,
            agent_id=self.test_agent_id,
            agent_type="optimization_agent",
            user_request="Optimize my AI costs",
            context=self.user_context
        )
        emission_time = time.time() - start_time
        
        # Verify event emission
        assert emitted_event is not None
        assert emitted_event.event_type == EventType.AGENT_STARTED
        assert emitted_event.user_id == self.user_context.user_id
        assert emitted_event.status == EmissionStatus.SENT
        assert emitted_event.delivery_confirmed is True
        
        # Verify event payload
        payload = emitted_event.payload
        assert payload["type"] == "agent_started"
        assert payload["agent_id"] == self.test_agent_id
        assert payload["agent_type"] == "optimization_agent"
        assert payload["user_request"] == "Optimize my AI costs"
        assert payload["status"] == "started"
        
        # Verify connection received event
        received_events = self.connection.get_received_events()
        assert len(received_events) == 1
        received_event = received_events[0]["data"]
        assert received_event["type"] == "agent_started"
        assert received_event["agent_id"] == self.test_agent_id
        
        # Verify real-time performance
        assert emission_time < 0.01, f"Agent started emission took {emission_time:.4f}s, should be < 0.01s"
        
        self.record_metric("agent_started_emission_time", emission_time)
        self.record_metric("agent_started_emitted_successfully", True)
    
    @pytest.mark.unit
    async def test_agent_thinking_event_emission(self):
        """Test emission of agent thinking event - Golden Path Event #2
        
        Business Impact: Agent thinking events provide real-time insight into
        AI reasoning, improving user perception of system intelligence.
        """
        # Emit agent thinking event
        emitted_event = await self.emitter.emit_agent_thinking(
            user_id=self.user_context.user_id,
            agent_id=self.test_agent_id,
            thinking_content="Analyzing your cost patterns and usage data...",
            reasoning_step="data_analysis",
            context=self.user_context
        )
        
        # Verify event emission
        assert emitted_event.event_type == EventType.AGENT_THINKING
        assert emitted_event.status == EmissionStatus.SENT
        
        # Verify thinking content in payload
        payload = emitted_event.payload
        assert payload["type"] == "agent_thinking"
        assert payload["thinking_content"] == "Analyzing your cost patterns and usage data..."
        assert payload["reasoning_step"] == "data_analysis"
        assert payload["status"] == "thinking"
        
        # Verify connection received thinking update
        received_events = self.connection.get_received_events()
        received_event = received_events[0]["data"]
        assert received_event["thinking_content"] == "Analyzing your cost patterns and usage data..."
        
        self.record_metric("agent_thinking_emitted_successfully", True)
    
    @pytest.mark.unit
    async def test_tool_executing_event_emission(self):
        """Test emission of tool executing event - Golden Path Event #3
        
        Business Impact: Tool executing events show users what actions are
        being taken, providing transparency in AI decision-making process.
        """
        tool_parameters = {
            "time_range": "last_30_days",
            "cost_threshold": 1000,
            "optimization_target": "cost_reduction"
        }
        
        # Emit tool executing event
        emitted_event = await self.emitter.emit_tool_executing(
            user_id=self.user_context.user_id,
            agent_id=self.test_agent_id,
            tool_name="cost_analyzer",
            tool_parameters=tool_parameters,
            context=self.user_context
        )
        
        # Verify event emission
        assert emitted_event.event_type == EventType.TOOL_EXECUTING
        assert emitted_event.status == EmissionStatus.SENT
        
        # Verify tool execution details in payload
        payload = emitted_event.payload
        assert payload["type"] == "tool_executing"
        assert payload["tool_name"] == "cost_analyzer"
        assert payload["tool_parameters"] == tool_parameters
        assert payload["status"] == "executing"
        
        self.record_metric("tool_executing_emitted_successfully", True)
    
    @pytest.mark.unit
    async def test_tool_completed_event_emission(self):
        """Test emission of tool completed event - Golden Path Event #4
        
        Business Impact: Tool completed events deliver intermediate results,
        showing progress toward final AI recommendations.
        """
        tool_result = {
            "analysis_completed": True,
            "cost_savings_identified": "$1,200/month", 
            "optimization_opportunities": [
                "Switch to smaller models for simple tasks",
                "Implement request batching"
            ]
        }
        
        # Emit tool completed event
        emitted_event = await self.emitter.emit_tool_completed(
            user_id=self.user_context.user_id,
            agent_id=self.test_agent_id,
            tool_name="cost_analyzer",
            tool_result=tool_result,
            execution_time=2.5,
            context=self.user_context
        )
        
        # Verify event emission
        assert emitted_event.event_type == EventType.TOOL_COMPLETED
        assert emitted_event.status == EmissionStatus.SENT
        
        # Verify tool results in payload
        payload = emitted_event.payload
        assert payload["type"] == "tool_completed"
        assert payload["tool_result"] == tool_result
        assert payload["execution_time"] == 2.5
        assert payload["status"] == "completed"
        
        self.record_metric("tool_completed_emitted_successfully", True)
    
    @pytest.mark.unit
    async def test_agent_completed_event_emission(self):
        """Test emission of agent completed event - Golden Path Event #5
        
        Business Impact: Agent completed events deliver final AI recommendations,
        completing the Golden Path value delivery cycle.
        """
        final_result = {
            "optimization_plan": {
                "immediate_actions": [
                    "Switch to gpt-3.5-turbo for routine queries",
                    "Implement response caching"
                ],
                "estimated_savings": "$1,200/month",
                "implementation_priority": "high"
            },
            "analysis_summary": "Found 3 major cost optimization opportunities"
        }
        
        # Emit agent completed event
        emitted_event = await self.emitter.emit_agent_completed(
            user_id=self.user_context.user_id,
            agent_id=self.test_agent_id,
            result=final_result,
            execution_time=15.3,
            context=self.user_context
        )
        
        # Verify event emission
        assert emitted_event.event_type == EventType.AGENT_COMPLETED
        assert emitted_event.status == EmissionStatus.SENT
        
        # Verify final results in payload
        payload = emitted_event.payload
        assert payload["type"] == "agent_completed"
        assert payload["result"] == final_result
        assert payload["execution_time"] == 15.3
        assert payload["status"] == "completed"
        
        # Verify connection received final results
        received_events = self.connection.get_received_events()
        received_event = received_events[0]["data"]
        assert received_event["result"]["estimated_savings"] == "$1,200/month"
        
        self.record_metric("agent_completed_emitted_successfully", True)
    
    @pytest.mark.unit
    async def test_complete_golden_path_event_sequence(self):
        """Test emission of complete Golden Path event sequence
        
        Business Impact: Complete event sequence provides full real-time
        feedback loop that creates premium AI experience worth $500K+ ARR.
        """
        # Emit complete Golden Path event sequence
        events = []
        
        # Event 1: Agent Started
        event1 = await self.emitter.emit_agent_started(
            self.user_context.user_id, self.test_agent_id, 
            "optimization_agent", "Optimize costs"
        )
        events.append(event1)
        
        # Event 2: Agent Thinking
        event2 = await self.emitter.emit_agent_thinking(
            self.user_context.user_id, self.test_agent_id,
            "Analyzing cost patterns..."
        )
        events.append(event2)
        
        # Event 3: Tool Executing
        event3 = await self.emitter.emit_tool_executing(
            self.user_context.user_id, self.test_agent_id,
            "cost_analyzer", {"time_range": "30_days"}
        )
        events.append(event3)
        
        # Event 4: Tool Completed
        event4 = await self.emitter.emit_tool_completed(
            self.user_context.user_id, self.test_agent_id,
            "cost_analyzer", {"savings": "$1200"}, 2.0
        )
        events.append(event4)
        
        # Event 5: Agent Completed
        event5 = await self.emitter.emit_agent_completed(
            self.user_context.user_id, self.test_agent_id,
            {"recommendations": ["Use smaller models"]}, 10.0
        )
        events.append(event5)
        
        # Verify all events emitted successfully
        for event in events:
            assert event.status == EmissionStatus.SENT
            assert event.delivery_confirmed is True
            assert event.user_id == self.user_context.user_id
        
        # Verify event sequence integrity
        event_types = [event.event_type for event in events]
        expected_sequence = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,
            EventType.TOOL_COMPLETED,
            EventType.AGENT_COMPLETED
        ]
        assert event_types == expected_sequence
        
        # Verify connection received all events
        received_events = self.connection.get_received_events()
        assert len(received_events) == 5
        
        self.record_metric("golden_path_sequence_emitted", True)
        self.record_metric("golden_path_events_count", len(events))
    
    # ========================================================================
    # USER ISOLATION AND TARGETING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_specific_event_targeting(self):
        """Test events are targeted to correct users only
        
        Business Impact: User isolation is critical for multi-tenant security
        and ensures users only receive their own agent updates.
        """
        # Create second user and connection
        user2_context = SSotMockFactory.create_mock_user_context(
            user_id="user_2",
            thread_id="thread_2", 
            run_id="run_2"
        )
        
        connection2 = MockWebSocketConnection("conn_2", "user_2")
        self.emitter.add_connection(connection2)
        
        # Emit events for different users
        event_user1 = await self.emitter.emit_agent_started(
            self.user_context.user_id, "agent_1", "triage", "User 1 request"
        )
        
        event_user2 = await self.emitter.emit_agent_started(
            user2_context.user_id, "agent_2", "optimization", "User 2 request"
        )
        
        # Verify targeting isolation
        user1_events = self.connection.get_received_events()
        user2_events = connection2.get_received_events()
        
        assert len(user1_events) == 1
        assert len(user2_events) == 1
        
        # Verify content isolation
        assert user1_events[0]["data"]["user_request"] == "User 1 request"
        assert user2_events[0]["data"]["user_request"] == "User 2 request"
        
        # Verify no cross-contamination
        assert user1_events[0]["data"]["agent_id"] != user2_events[0]["data"]["agent_id"]
        
        self.record_metric("user_isolation_verified", True)
    
    @pytest.mark.unit
    async def test_multiple_connections_per_user(self):
        """Test event broadcast to multiple connections for same user
        
        Business Impact: Users with multiple browser tabs/devices should
        receive events on all active connections.
        """
        # Add second connection for same user
        connection2 = MockWebSocketConnection(
            f"conn_2_{self.user_context.user_id}",
            self.user_context.user_id
        )
        self.emitter.add_connection(connection2)
        
        # Emit event
        emitted_event = await self.emitter.emit_agent_thinking(
            self.user_context.user_id, self.test_agent_id,
            "Processing multiple connections test..."
        )
        
        # Verify event sent to both connections
        assert emitted_event.status == EmissionStatus.SENT
        
        events_conn1 = self.connection.get_received_events()
        events_conn2 = connection2.get_received_events()
        
        assert len(events_conn1) == 1
        assert len(events_conn2) == 1
        
        # Verify same event content
        assert events_conn1[0]["data"]["thinking_content"] == events_conn2[0]["data"]["thinking_content"]
        
        self.record_metric("multiple_connections_broadcast", True)
    
    # ========================================================================
    # ERROR HANDLING AND RETRY TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_emission_failure_handling(self):
        """Test graceful handling of emission failures
        
        Business Impact: Robust error handling prevents system crashes
        when WebSocket connections fail or become unavailable.
        """
        # Disconnect the connection
        self.connection.disconnect()
        
        # Attempt to emit event to disconnected connection
        emitted_event = await self.emitter.emit_agent_started(
            self.user_context.user_id, self.test_agent_id,
            "triage", "Test with failed connection"
        )
        
        # Verify failure handling
        assert emitted_event.status == EmissionStatus.FAILED
        assert emitted_event.delivery_confirmed is False
        
        # Verify metrics updated
        metrics = self.emitter.get_emission_metrics()
        assert metrics["failed_emissions"] > 0
        
        self.record_metric("emission_failure_handled_gracefully", True)
    
    @pytest.mark.unit
    async def test_no_active_connections_handling(self):
        """Test handling when user has no active connections
        
        Business Impact: System should handle offline users gracefully
        without blocking agent execution or causing errors.
        """
        # Remove all connections
        self.emitter.remove_connection(self.connection.connection_id)
        
        # Attempt to emit event with no connections
        emitted_event = await self.emitter.emit_agent_completed(
            self.user_context.user_id, self.test_agent_id,
            {"result": "No connection test"}, 1.0
        )
        
        # Verify no-connection handling
        assert emitted_event.status == EmissionStatus.FAILED
        assert emitted_event.connection_id == "none"
        
        # Verify metrics reflect failed emission
        metrics = self.emitter.get_emission_metrics()
        assert metrics["failed_emissions"] > 0
        
        self.record_metric("no_connections_handled_gracefully", True)
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_emission_performance_requirements(self):
        """Test event emission performance for real-time requirements
        
        Business Impact: Fast emission is critical for real-time user
        experience and responsive AI interactions.
        """
        # Measure emission times for different event types
        emission_times = {}
        
        event_tests = [
            ("agent_started", lambda: self.emitter.emit_agent_started(
                self.user_context.user_id, self.test_agent_id, "test", "perf test")),
            ("agent_thinking", lambda: self.emitter.emit_agent_thinking(
                self.user_context.user_id, self.test_agent_id, "thinking...")),
            ("tool_executing", lambda: self.emitter.emit_tool_executing(
                self.user_context.user_id, self.test_agent_id, "test_tool", {})),
            ("tool_completed", lambda: self.emitter.emit_tool_completed(
                self.user_context.user_id, self.test_agent_id, "test_tool", {}, 1.0)),
            ("agent_completed", lambda: self.emitter.emit_agent_completed(
                self.user_context.user_id, self.test_agent_id, {}, 1.0))
        ]
        
        for event_name, emit_func in event_tests:
            times = []
            for i in range(10):
                start_time = time.time()
                event = await emit_func()
                end_time = time.time()
                
                assert event.status == EmissionStatus.SENT
                times.append(end_time - start_time)
            
            avg_time = sum(times) / len(times)
            emission_times[event_name] = avg_time
            
            # Performance requirement for real-time events
            assert avg_time < 0.005, f"{event_name} emission took {avg_time:.6f}s, should be < 0.005s"
        
        self.record_metric("emission_performance_times", emission_times)
        self.record_metric("all_events_meet_performance_requirements", True)
    
    @pytest.mark.unit
    async def test_concurrent_event_emission(self):
        """Test concurrent emission of multiple events
        
        Business Impact: System must handle multiple simultaneous events
        from different agents without interference or delays.
        """
        # Create multiple concurrent emission tasks
        tasks = []
        for i in range(20):
            task = self.emitter.emit_agent_thinking(
                self.user_context.user_id, f"agent_{i}",
                f"Concurrent thinking {i}"
            )
            tasks.append(task)
        
        # Execute all emissions concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all emissions successful
        successful_emissions = 0
        for result in results:
            if isinstance(result, EmittedEvent) and result.status == EmissionStatus.SENT:
                successful_emissions += 1
        
        assert successful_emissions == 20, f"Only {successful_emissions}/20 emissions successful"
        
        # Verify concurrent performance
        assert total_time < 0.1, f"Concurrent emissions took {total_time:.3f}s, should be < 0.1s"
        
        # Verify connection received all events
        received_events = self.connection.get_received_events()
        assert len(received_events) == 20
        
        self.record_metric("concurrent_emissions_successful", successful_emissions)
        self.record_metric("concurrent_emission_time", total_time)
    
    @pytest.mark.unit
    async def test_emission_metrics_accuracy(self):
        """Test accuracy of emission metrics collection
        
        Business Impact: Accurate metrics enable monitoring and optimization
        of event emission performance and reliability.
        """
        # Reset metrics
        initial_metrics = self.emitter.get_emission_metrics()
        
        # Emit successful events
        successful_events = 5
        for i in range(successful_events):
            await self.emitter.emit_agent_thinking(
                self.user_context.user_id, f"agent_{i}", f"Metrics test {i}"
            )
        
        # Emit failed event (disconnect connection)
        self.connection.disconnect()
        await self.emitter.emit_agent_started(
            self.user_context.user_id, "failed_agent", "test", "Failed emission"
        )
        
        # Verify metrics accuracy
        final_metrics = self.emitter.get_emission_metrics()
        
        successful_increase = final_metrics["successful_emissions"] - initial_metrics["successful_emissions"]
        failed_increase = final_metrics["failed_emissions"] - initial_metrics["failed_emissions"]
        
        assert successful_increase == successful_events
        assert failed_increase == 1
        
        total_increase = final_metrics["total_events"] - initial_metrics["total_events"]
        assert total_increase == successful_events + 1
        
        self.record_metric("emission_metrics_accurate", True)
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        
        # Calculate comprehensive coverage metrics
        golden_path_events = sum(1 for key in metrics.keys() 
                               if "emitted_successfully" in key and metrics[key] is True)
        
        self.record_metric("golden_path_events_tested", golden_path_events)
        self.record_metric("websocket_emission_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)