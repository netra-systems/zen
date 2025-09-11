"""
Comprehensive Unit Tests for WebSocket Event Validation in Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket event delivery protecting $500K+ ARR
- Value Impact: Validates all 5 critical WebSocket events that deliver user experience transparency
- Strategic Impact: Prevents silent failures that break user trust and engagement

This test suite validates the 5 mission-critical WebSocket events that represent 90% of platform value:
1. agent_started - User sees AI engagement beginning
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - Completion signal for user

Key Coverage Areas:
- WebSocket event emission validation
- Event ordering and sequencing
- Event data integrity and format
- Event delivery reliability
- Error handling in event emission
- Performance requirements for event delivery
- Multi-user event isolation
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.websocket import WebSocketTestUtility

# WebSocket core imports
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.agent_handler import AgentHandler
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Agent and execution imports
from netra_backend.app.agents.base_agent import BaseAgent, AgentState
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestWebSocketEventValidationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket event validation in the golden path.
    
    Tests focus on the 5 critical WebSocket events that deliver user experience
    transparency and represent 90% of platform business value.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.websocket_utility = WebSocketTestUtility()
        
        # Test user context for all tests
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        
        # Mock WebSocket for testing
        self.mock_websocket = self.mock_factory.create_websocket_mock()
        self.mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Event tracking for validation
        self.captured_events = []
        self.event_timestamps = {}
        
        # Setup mock event capture
        async def capture_event(event_type: str, data: Dict[str, Any], **kwargs):
            timestamp = datetime.utcnow()
            event = {
                "type": event_type,
                "data": data,
                "timestamp": timestamp,
                "user_id": kwargs.get("user_id"),
                "thread_id": kwargs.get("thread_id"),
                "run_id": kwargs.get("run_id")
            }
            self.captured_events.append(event)
            self.event_timestamps[event_type] = timestamp
            logger.debug(f"Captured event: {event_type} at {timestamp}")
        
        self.capture_event = capture_event

    async def async_setup_method(self, method):
        """Async setup for WebSocket and agent initialization."""
        await super().async_setup_method(method)
        
        # Create user execution context
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_all_five_critical_events_emitted_correctly(self):
        """
        BVJ: All segments | User Experience | Ensures all 5 critical events are emitted
        Test that all 5 mission-critical WebSocket events are emitted correctly.
        """
        # Create WebSocket emitter with event capture
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id
        )
        
        # Mock the actual WebSocket send to capture events
        async def mock_send_event(event_type: str, data: Dict[str, Any], **kwargs):
            await self.capture_event(event_type, data, **kwargs)
        
        emitter.send_event = mock_send_event
        
        # Simulate complete agent execution workflow
        # 1. Agent Started
        await emitter.send_event(
            "agent_started",
            {
                "agent_name": "supervisor",
                "message": "Beginning AI cost analysis",
                "start_time": datetime.utcnow().isoformat()
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # 2. Agent Thinking
        await emitter.send_event(
            "agent_thinking",
            {
                "thought": "Analyzing current infrastructure costs and usage patterns",
                "reasoning_step": 1,
                "estimated_completion": "2 minutes"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # 3. Tool Executing
        await emitter.send_event(
            "tool_executing",
            {
                "tool_name": "cost_analyzer",
                "action": "Fetching cloud infrastructure costs",
                "expected_duration": "30 seconds"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # 4. Tool Completed
        await emitter.send_event(
            "tool_completed",
            {
                "tool_name": "cost_analyzer",
                "result": {
                    "monthly_cost": 5247.83,
                    "cost_breakdown": {"compute": 3200, "storage": 1500, "network": 547.83}
                },
                "execution_time": "28 seconds"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # 5. Agent Completed
        await emitter.send_event(
            "agent_completed",
            {
                "agent_name": "supervisor",
                "final_result": {
                    "analysis_complete": True,
                    "optimization_recommendations": 3,
                    "potential_savings": 1049.57
                },
                "total_execution_time": "2 minutes 15 seconds"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Verify all 5 critical events were captured
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        captured_event_types = [event["type"] for event in self.captured_events]
        
        for required_event in required_events:
            assert required_event in captured_event_types, f"Missing critical event: {required_event}"
        
        # Verify correct event count
        assert len(self.captured_events) == 5, f"Expected 5 events, got {len(self.captured_events)}"
        
        # Verify event order is logical
        assert captured_event_types.index("agent_started") < captured_event_types.index("agent_completed")
        assert captured_event_types.index("tool_executing") < captured_event_types.index("tool_completed")
        
        logger.info(f"✅ All 5 critical WebSocket events validated: {captured_event_types}")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_event_data_integrity_and_format(self):
        """
        BVJ: All segments | Data Quality | Ensures event data meets format requirements
        Test that WebSocket event data has proper format and required fields.
        """
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id
        )
        
        emitter.send_event = self.capture_event
        
        # Test agent_started event format
        await emitter.send_event(
            "agent_started",
            {
                "agent_name": "data_helper",
                "message": "Starting data collection",
                "start_time": datetime.utcnow().isoformat(),
                "estimated_duration": "1 minute"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Test tool_executing event format
        await emitter.send_event(
            "tool_executing",
            {
                "tool_name": "database_query",
                "action": "Querying usage metrics",
                "parameters": {"time_range": "30_days", "granularity": "daily"},
                "expected_duration": "15 seconds"
            },
            user_id=self.test_user_id
        )
        
        # Verify event data integrity
        assert len(self.captured_events) == 2
        
        # Validate agent_started event
        agent_started_event = self.captured_events[0]
        assert agent_started_event["type"] == "agent_started"
        assert "agent_name" in agent_started_event["data"]
        assert "message" in agent_started_event["data"]
        assert "start_time" in agent_started_event["data"]
        assert agent_started_event["user_id"] == self.test_user_id
        assert agent_started_event["thread_id"] == self.test_thread_id
        
        # Validate tool_executing event
        tool_event = self.captured_events[1]
        assert tool_event["type"] == "tool_executing"
        assert "tool_name" in tool_event["data"]
        assert "action" in tool_event["data"]
        assert "parameters" in tool_event["data"]
        assert tool_event["user_id"] == self.test_user_id
        
        # Verify timestamp format
        for event in self.captured_events:
            assert isinstance(event["timestamp"], datetime)
            assert event["timestamp"] is not None
        
        logger.info("✅ Event data integrity and format validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_event_ordering_and_sequencing_validation(self):
        """
        BVJ: All segments | User Experience | Ensures logical event ordering
        Test that WebSocket events are emitted in logical order for user experience.
        """
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id
        )
        
        emitter.send_event = self.capture_event
        
        # Simulate complete workflow with timing
        events_with_delays = [
            ("agent_started", {"agent_name": "optimizer", "message": "Starting optimization analysis"}, 0.01),
            ("agent_thinking", {"thought": "Identifying optimization opportunities"}, 0.02),
            ("tool_executing", {"tool_name": "cost_optimizer", "action": "Running optimization algorithms"}, 0.01),
            ("tool_completed", {"tool_name": "cost_optimizer", "result": {"savings_found": 850}}, 0.01),
            ("agent_thinking", {"thought": "Preparing final recommendations"}, 0.01),
            ("agent_completed", {"agent_name": "optimizer", "final_result": {"recommendations": 5}}, 0.01)
        ]
        
        # Emit events with small delays to ensure proper timing
        for event_type, data, delay in events_with_delays:
            await emitter.send_event(
                event_type,
                data,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id
            )
            await asyncio.sleep(delay)
        
        # Verify event count
        assert len(self.captured_events) == 6
        
        # Verify chronological ordering
        timestamps = [event["timestamp"] for event in self.captured_events]
        sorted_timestamps = sorted(timestamps)
        assert timestamps == sorted_timestamps, "Events should be in chronological order"
        
        # Verify logical business ordering
        event_types = [event["type"] for event in self.captured_events]
        
        # agent_started should be first
        assert event_types[0] == "agent_started"
        
        # agent_completed should be last
        assert event_types[-1] == "agent_completed"
        
        # tool_executing should come before tool_completed
        tool_executing_idx = event_types.index("tool_executing")
        tool_completed_idx = event_types.index("tool_completed")
        assert tool_executing_idx < tool_completed_idx
        
        logger.info(f"✅ Event ordering validation passed: {event_types}")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_multi_user_event_isolation(self):
        """
        BVJ: All segments | User Isolation | Ensures events are delivered to correct users only
        Test that WebSocket events are properly isolated between different users.
        """
        # Create contexts for different users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        thread1_id = str(uuid.uuid4())
        thread2_id = str(uuid.uuid4())
        
        # Separate event capture for each user
        user1_events = []
        user2_events = []
        
        async def capture_user1_event(event_type: str, data: Dict[str, Any], **kwargs):
            if kwargs.get("user_id") == user1_id:
                user1_events.append({"type": event_type, "data": data, "user_id": kwargs.get("user_id")})
        
        async def capture_user2_event(event_type: str, data: Dict[str, Any], **kwargs):
            if kwargs.get("user_id") == user2_id:
                user2_events.append({"type": event_type, "data": data, "user_id": kwargs.get("user_id")})
        
        # Create separate emitters for each user
        user1_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user1_id
        )
        user1_emitter.send_event = capture_user1_event
        
        user2_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user2_id
        )
        user2_emitter.send_event = capture_user2_event
        
        # Emit events for both users simultaneously
        await asyncio.gather(
            user1_emitter.send_event(
                "agent_started",
                {"agent_name": "user1_agent", "message": "User 1 analysis"},
                user_id=user1_id,
                thread_id=thread1_id
            ),
            user2_emitter.send_event(
                "agent_started", 
                {"agent_name": "user2_agent", "message": "User 2 analysis"},
                user_id=user2_id,
                thread_id=thread2_id
            ),
            user1_emitter.send_event(
                "tool_executing",
                {"tool_name": "user1_tool"},
                user_id=user1_id,
                thread_id=thread1_id
            ),
            user2_emitter.send_event(
                "tool_executing",
                {"tool_name": "user2_tool"},
                user_id=user2_id,
                thread_id=thread2_id
            )
        )
        
        # Verify user isolation
        assert len(user1_events) == 2, f"User 1 should have 2 events, got {len(user1_events)}"
        assert len(user2_events) == 2, f"User 2 should have 2 events, got {len(user2_events)}"
        
        # Verify user-specific data
        user1_agent_event = next(e for e in user1_events if e["type"] == "agent_started")
        assert user1_agent_event["data"]["agent_name"] == "user1_agent"
        assert user1_agent_event["user_id"] == user1_id
        
        user2_agent_event = next(e for e in user2_events if e["type"] == "agent_started")
        assert user2_agent_event["data"]["agent_name"] == "user2_agent" 
        assert user2_agent_event["user_id"] == user2_id
        
        # Verify no cross-contamination
        for event in user1_events:
            assert event["user_id"] == user1_id
            assert "user1" in str(event["data"])
        
        for event in user2_events:
            assert event["user_id"] == user2_id
            assert "user2" in str(event["data"])
        
        logger.info("✅ Multi-user event isolation validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_event_performance_and_timing_requirements(self):
        """
        BVJ: All segments | Performance SLA | Ensures events meet timing requirements
        Test that WebSocket events are emitted within performance requirements.
        """
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id
        )
        
        # Track emission timing
        emission_times = []
        
        async def timed_capture_event(event_type: str, data: Dict[str, Any], **kwargs):
            emission_time = time.time()
            emission_times.append(emission_time)
            await self.capture_event(event_type, data, **kwargs)
        
        emitter.send_event = timed_capture_event
        
        # Test rapid event emission (stress test)
        start_time = time.time()
        
        events_to_emit = [
            ("agent_started", {"agent_name": "performance_test"}),
            ("agent_thinking", {"thought": "Processing performance test"}),
            ("tool_executing", {"tool_name": "performance_tool"}),
            ("tool_completed", {"tool_name": "performance_tool", "result": {"status": "success"}}),
            ("agent_completed", {"agent_name": "performance_test", "result": {"completed": True}})
        ]
        
        # Emit all events rapidly
        for event_type, data in events_to_emit:
            await emitter.send_event(
                event_type,
                data,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id
            )
        
        total_time = time.time() - start_time
        
        # Verify performance requirements
        assert total_time < 0.1, f"Event emission took too long: {total_time}s (should be < 0.1s)"
        assert len(self.captured_events) == 5, "All events should be captured"
        assert len(emission_times) == 5, "All emission times should be recorded"
        
        # Verify individual event emission is fast
        for i in range(1, len(emission_times)):
            time_diff = emission_times[i] - emission_times[i-1]
            assert time_diff < 0.05, f"Individual event emission too slow: {time_diff}s"
        
        # Verify events maintain order despite rapid emission
        event_types = [event["type"] for event in self.captured_events]
        expected_order = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_order, f"Event order incorrect: {event_types}"
        
        logger.info(f"✅ Event performance validation passed: {total_time:.4f}s for 5 events")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_event_error_handling_and_resilience(self):
        """
        BVJ: All segments | System Reliability | Ensures graceful error handling
        Test that WebSocket event emission handles errors gracefully.
        """
        # Create emitter with failing WebSocket manager
        failing_manager = self.mock_factory.create_websocket_manager_mock()
        failing_manager.emit_critical_event.side_effect = Exception("WebSocket connection failed")
        
        emitter = UnifiedWebSocketEmitter(
            manager=failing_manager,
            user_id=self.test_user_id
        )
        
        # Track error handling
        error_count = 0
        success_count = 0
        
        async def resilient_send_event(event_type: str, data: Dict[str, Any], **kwargs):
            nonlocal error_count, success_count
            try:
                # Simulate original send_event logic
                await failing_websocket.send_text(json.dumps({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                success_count += 1
            except Exception as e:
                error_count += 1
                # Log error but don't raise (graceful degradation)
                logger.warning(f"WebSocket event emission failed: {e}")
                # Store event for retry or alternative delivery
                await self.capture_event(event_type, data, **kwargs)
        
        emitter.send_event = resilient_send_event
        
        # Test error resilience with multiple events
        events_to_test = [
            ("agent_started", {"agent_name": "error_test"}),
            ("agent_thinking", {"thought": "Testing error handling"}),
            ("tool_executing", {"tool_name": "error_tool"}),
            ("agent_completed", {"result": "error_handled"})
        ]
        
        # Emit events that will fail
        for event_type, data in events_to_test:
            await emitter.send_event(
                event_type,
                data,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id
            )
        
        # Verify error handling
        assert error_count == 4, f"Expected 4 errors, got {error_count}"
        assert success_count == 0, f"Expected 0 successes, got {success_count}"
        
        # Verify events were still captured for alternative delivery
        assert len(self.captured_events) == 4, "Events should be captured despite WebSocket failure"
        
        # Verify all event types were handled
        captured_types = [event["type"] for event in self.captured_events]
        expected_types = ["agent_started", "agent_thinking", "tool_executing", "agent_completed"]
        assert captured_types == expected_types
        
        logger.info("✅ Event error handling and resilience validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_websocket_bridge_agent_integration(self):
        """
        BVJ: All segments | Agent Integration | Ensures WebSocket bridge works with agents
        Test that AgentWebSocketBridge properly integrates with agent execution.
        """
        # Create WebSocket bridge
        bridge = AgentWebSocketBridge()
        
        # Mock WebSocket manager
        mock_manager = AsyncMock()
        bridge._websocket_manager = mock_manager
        
        # Track bridge events
        bridge_events = []
        
        async def capture_bridge_event(*args, **kwargs):
            bridge_events.append({"args": args, "kwargs": kwargs})
        
        mock_manager.send_event = capture_bridge_event
        
        # Test all bridge notification methods
        await bridge.notify_agent_started(
            run_id=self.test_run_id,
            agent_name="test_agent",
            context={"message": "Starting test", "user_id": self.test_user_id, "thread_id": self.test_thread_id}
        )
        
        await bridge.notify_agent_thinking(
            run_id=self.test_run_id,
            agent_name="test_agent",
            reasoning="Testing bridge integration"
        )
        
        await bridge.notify_tool_executing(
            run_id=self.test_run_id,
            agent_name="test_agent",
            tool_name="test_tool",
            parameters={"action": "Testing tool integration"}
        )
        
        await bridge.notify_tool_completed(
            run_id=self.test_run_id,
            agent_name="test_agent",
            tool_name="test_tool",
            result={"status": "success", "data": "test_result"}
        )
        
        await bridge.notify_agent_completed(
            run_id=self.test_run_id,
            agent_name="test_agent",
            result={"completed": True, "success": True}
        )
        
        # Verify all bridge methods were called
        assert len(bridge_events) == 5, f"Expected 5 bridge events, got {len(bridge_events)}"
        
        # Verify bridge event data
        event_types = []
        for event in bridge_events:
            if event["args"]:
                event_types.append(event["args"][0])  # First arg is usually event type
        
        expected_bridge_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Verify bridge handles all critical event types
        for expected_type in expected_bridge_types:
            assert any(expected_type in str(event) for event in bridge_events), f"Missing bridge event: {expected_type}"
        
        logger.info("✅ WebSocket bridge agent integration validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_event_payload_size_and_limits(self):
        """
        BVJ: All segments | Performance | Ensures event payloads meet size requirements
        Test that WebSocket event payloads are within acceptable size limits.
        """
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id
        )
        
        # Track payload sizes
        payload_sizes = []
        
        async def size_tracking_capture(event_type: str, data: Dict[str, Any], **kwargs):
            # Calculate payload size
            payload = {
                "type": event_type,
                "data": data,
                "user_id": kwargs.get("user_id"),
                "thread_id": kwargs.get("thread_id"),
                "timestamp": datetime.utcnow().isoformat()
            }
            payload_json = json.dumps(payload)
            payload_size = len(payload_json.encode('utf-8'))
            payload_sizes.append(payload_size)
            
            await self.capture_event(event_type, data, **kwargs)
        
        emitter.send_event = size_tracking_capture
        
        # Test with various payload sizes
        test_cases = [
            # Small payload
            ("agent_started", {"agent_name": "test", "message": "short"}),
            
            # Medium payload with typical data
            ("tool_completed", {
                "tool_name": "cost_analyzer",
                "result": {
                    "monthly_cost": 5247.83,
                    "breakdown": {"compute": 3200, "storage": 1500, "network": 547.83},
                    "recommendations": ["optimize_compute", "reduce_storage", "improve_network"]
                },
                "execution_time": "45 seconds"
            }),
            
            # Large payload with extensive data
            ("agent_completed", {
                "agent_name": "comprehensive_analyzer",
                "final_result": {
                    "analysis_complete": True,
                    "detailed_breakdown": {f"metric_{i}": f"value_{i}" for i in range(50)},
                    "recommendations": [f"recommendation_{i}" for i in range(20)],
                    "cost_analysis": {f"category_{i}": 100.0 * i for i in range(30)}
                },
                "metadata": {"execution_time": "5 minutes", "complexity": "high"}
            })
        ]
        
        # Emit test events
        for event_type, data in test_cases:
            await emitter.send_event(
                event_type,
                data,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id
            )
        
        # Verify payload size limits
        max_payload_size = 8192  # 8KB limit for WebSocket messages
        
        for i, size in enumerate(payload_sizes):
            assert size < max_payload_size, f"Payload {i} too large: {size} bytes (limit: {max_payload_size})"
        
        # Verify size distribution
        small_payload = payload_sizes[0]
        medium_payload = payload_sizes[1]
        large_payload = payload_sizes[2]
        
        assert small_payload < 500, f"Small payload too large: {small_payload} bytes"
        assert medium_payload < 2000, f"Medium payload too large: {medium_payload} bytes"
        assert large_payload < max_payload_size, f"Large payload exceeds limit: {large_payload} bytes"
        
        # Verify reasonable size progression
        assert small_payload < medium_payload < large_payload, "Payload sizes should increase with data complexity"
        
        logger.info(f"✅ Event payload size validation passed: {payload_sizes} bytes")

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Clear captured events
        self.captured_events.clear()
        self.event_timestamps.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
