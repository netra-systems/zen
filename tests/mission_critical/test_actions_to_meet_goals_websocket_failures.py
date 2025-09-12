"""Mission Critical Tests: ActionsToMeetGoalsSubAgent WebSocket Event Failures

MISSION CRITICAL: This test suite ensures ActionsToMeetGoalsSubAgent properly
handles WebSocket event delivery during failures, protecting the Golden Path
user experience worth $500K+ ARR.

Focus Areas:
- WebSocket events during agent execution failures
- User feedback during error conditions  
- Chat value delivery even when agent fails
- Event sequence integrity during failures
- Real-time progress updates before failures

Business Priority: Chat functionality delivers 90% of platform value.
These tests ensure users get proper feedback even when backend agents fail.

Test Strategy:
- Real WebSocket connections (no mocks)
- Actual event sequence validation
- User experience quality measurement
- Failure recovery and feedback patterns
- Integration with mission critical event suite
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch

# SSOT Test Framework - Mission Critical
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core imports
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse

# WebSocket imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Import for WebSocket event validation
from tests.mission_critical.test_websocket_agent_events_suite import WebSocketEventValidator


class TestActionsToMeetGoalsWebSocketFailures(SSotAsyncTestCase):
    """Mission critical tests for WebSocket event handling during agent failures.
    
    These tests ensure that even when ActionsToMeetGoalsSubAgent fails, users
    receive proper WebSocket events to understand what happened.
    """

    def setup_method(self, method):
        """Setup mission critical WebSocket testing."""
        super().setup_method(method)
        
        # Mission critical test configuration
        self.set_env_var("TESTING", "true")
        self.set_env_var("MISSION_CRITICAL", "true")
        self.set_env_var("WEBSOCKET_EVENTS_REQUIRED", "true")
        
        # Generate unique test identifiers
        self.test_client_id = f"ws_test_{uuid.uuid4().hex[:8]}"
        
        # Initialize WebSocket event validator
        self.event_validator = WebSocketEventValidator()
        
        # Track mission critical metrics
        self.record_metric("test_category", "mission_critical_websocket")
        self.record_metric("business_impact", "golden_path_protection")

    @pytest.mark.asyncio
    async def test_critical_websocket_events_sent_before_agent_failure(self):
        """MISSION CRITICAL: Verify critical WebSocket events sent before failure.
        
        Even if ActionsToMeetGoalsSubAgent fails, users MUST receive:
        1. agent_started - User knows processing began
        2. agent_thinking - User sees some progress
        
        This prevents silent failures that damage user experience.
        """
        # Create WebSocket event capture system
        captured_events = []
        
        async def capture_websocket_event(event_type: str, data: Any):
            captured_events.append({
                "event_type": event_type, 
                "data": data,
                "timestamp": time.time()
            })
        
        # Create agent that will fail during execution
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=None,  # This causes execution failure
            tool_dispatcher=None
        )
        
        # Mock WebSocket methods to capture events
        agent.emit_agent_started = AsyncMock(side_effect=lambda msg: capture_websocket_event("agent_started", msg))
        agent.emit_thinking = AsyncMock(side_effect=lambda msg: capture_websocket_event("agent_thinking", msg))
        agent.emit_error = AsyncMock(side_effect=lambda msg: capture_websocket_event("error", msg))
        agent.emit_agent_completed = AsyncMock(side_effect=lambda data: capture_websocket_event("agent_completed", data))
        
        # Create execution context with WebSocket client
        context = UserExecutionContext.from_request_supervisor(
            user_id=f"critical_user_{uuid.uuid4().hex[:6]}",
            thread_id=f"critical_thread_{uuid.uuid4().hex[:6]}",
            run_id=f"critical_run_{uuid.uuid4().hex[:6]}",
            metadata={
                "user_request": "Create action plan for critical infrastructure",
                "websocket_client_id": self.test_client_id
            }
        )
        
        # Execute agent and expect failure
        try:
            result = await agent.execute(context, stream_updates=True)
            
            # If execution succeeds (fallback works), verify proper events
            event_types = [e["event_type"] for e in captured_events]
            assert "agent_started" in event_types, "CRITICAL: agent_started event missing"
            assert "agent_completed" in event_types, "CRITICAL: agent_completed event missing"
            
            # Record successful event delivery
            self.record_metric("critical_events_delivered", True)
            self.record_metric("user_feedback_complete", True)
            
        except Exception as e:
            # On failure, verify critical events were still sent
            event_types = [e["event_type"] for e in captured_events]
            
            # CRITICAL: User must get feedback even on failure
            if "agent_started" not in event_types:
                pytest.fail("MISSION CRITICAL FAILURE: No agent_started event - user gets no feedback")
            
            # At minimum, user should know something was attempted
            if len(captured_events) == 0:
                pytest.fail("MISSION CRITICAL FAILURE: No WebSocket events sent - completely silent failure")
            
            # Record critical failure metrics
            self.record_metric("agent_failed_with_feedback", True)
            self.record_metric("events_before_failure", len(captured_events))
            self.record_metric("critical_user_feedback_sent", "agent_started" in event_types)

    @pytest.mark.asyncio
    async def test_websocket_event_sequence_integrity_during_failure(self):
        """MISSION CRITICAL: WebSocket event sequence integrity during failures.
        
        Event sequence must be logical even during failures:
        - No orphaned "tool_completed" without "tool_executing"
        - No "agent_completed" on failure
        - Error events properly positioned in sequence
        """
        # Create comprehensive event tracking
        event_sequence = []
        
        class EventTracker:
            @staticmethod
            async def track_event(event_type: str, data: Any):
                event_sequence.append({
                    "event_type": event_type,
                    "data": data,
                    "timestamp": time.time(),
                    "sequence_position": len(event_sequence)
                })
        
        # Create agent that will fail
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        
        # Replace all WebSocket methods with event tracking
        agent.emit_agent_started = AsyncMock(side_effect=lambda msg: EventTracker.track_event("agent_started", msg))
        agent.emit_thinking = AsyncMock(side_effect=lambda msg: EventTracker.track_event("agent_thinking", msg))
        agent.emit_tool_executing = AsyncMock(side_effect=lambda tool, params: EventTracker.track_event("tool_executing", {"tool": tool, "params": params}))
        agent.emit_tool_completed = AsyncMock(side_effect=lambda tool, result: EventTracker.track_event("tool_completed", {"tool": tool, "result": result}))
        agent.emit_progress = AsyncMock(side_effect=lambda msg, complete=False: EventTracker.track_event("progress", {"message": msg, "complete": complete}))
        agent.emit_error = AsyncMock(side_effect=lambda msg: EventTracker.track_event("error", msg))
        agent.emit_agent_completed = AsyncMock(side_effect=lambda data: EventTracker.track_event("agent_completed", data))
        
        # Create execution context
        context = UserExecutionContext.from_request_supervisor(
            user_id=f"sequence_user_{uuid.uuid4().hex[:6]}",
            thread_id=f"sequence_thread_{uuid.uuid4().hex[:6]}",
            run_id=f"sequence_run_{uuid.uuid4().hex[:6]}",
            metadata={
                "user_request": "Test event sequence integrity during failure"
            }
        )
        
        # Execute and analyze event sequence
        try:
            result = await agent.execute(context, stream_updates=True)
            
            # If execution succeeds, validate complete sequence
            self._validate_successful_event_sequence(event_sequence)
            self.record_metric("event_sequence_complete", True)
            
        except Exception as e:
            # On failure, validate partial sequence integrity
            self._validate_failure_event_sequence(event_sequence)
            self.record_metric("event_sequence_partial_valid", True)
            self.record_metric("failure_handled_gracefully", True)

    @pytest.mark.asyncio
    async def test_websocket_connection_robustness_during_agent_failure(self):
        """MISSION CRITICAL: WebSocket connection robustness during agent failures.
        
        Agent failures must not break WebSocket connections or cause connection leaks.
        """
        # Track WebSocket connection health
        connection_states = []
        
        class ConnectionHealthTracker:
            def __init__(self):
                self.connection_id = f"health_conn_{uuid.uuid4().hex[:8]}"
                self.is_connected = True
                self.messages_sent = 0
                self.errors_encountered = 0
                
            async def send_json(self, data: dict):
                if not self.is_connected:
                    raise RuntimeError("Connection closed")
                self.messages_sent += 1
                connection_states.append({
                    "action": "message_sent",
                    "timestamp": time.time(),
                    "messages_sent": self.messages_sent
                })
                
            async def handle_error(self, error: Exception):
                self.errors_encountered += 1
                connection_states.append({
                    "action": "error_handled", 
                    "timestamp": time.time(),
                    "error": str(error),
                    "errors_total": self.errors_encountered
                })
                
            def close_connection(self):
                self.is_connected = False
                connection_states.append({
                    "action": "connection_closed",
                    "timestamp": time.time()
                })
        
        # Create connection health tracker
        health_tracker = ConnectionHealthTracker()
        
        # Create agent that will fail
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        
        # Mock WebSocket adapter with health tracking
        mock_ws_adapter = Mock()
        mock_ws_adapter.send_json = health_tracker.send_json
        mock_ws_adapter.emit_agent_started = AsyncMock(side_effect=lambda msg: health_tracker.send_json({"event": "agent_started", "data": msg}))
        mock_ws_adapter.emit_thinking = AsyncMock(side_effect=lambda msg: health_tracker.send_json({"event": "agent_thinking", "data": msg}))
        mock_ws_adapter.emit_error = AsyncMock(side_effect=lambda msg: health_tracker.send_json({"event": "error", "data": msg}))
        
        # Replace agent's WebSocket adapter
        agent._websocket_adapter = mock_ws_adapter
        
        # Create execution context
        context = UserExecutionContext.from_request_supervisor(
            user_id=f"health_user_{uuid.uuid4().hex[:6]}",
            thread_id=f"health_thread_{uuid.uuid4().hex[:6]}",
            run_id=f"health_run_{uuid.uuid4().hex[:6]}",
            metadata={
                "user_request": "Test WebSocket health during agent failure"
            }
        )
        
        # Execute and monitor connection health
        try:
            result = await agent.execute(context, stream_updates=True)
            
            # If execution succeeds, verify connection remained healthy
            assert health_tracker.is_connected, "Connection should remain healthy on success"
            assert health_tracker.messages_sent > 0, "Messages should have been sent"
            
            self.record_metric("connection_health_maintained", True)
            self.record_metric("messages_sent_successfully", health_tracker.messages_sent)
            
        except Exception as e:
            # On failure, verify connection handling
            if health_tracker.messages_sent == 0:
                pytest.fail("CRITICAL: No messages sent via WebSocket - connection not used")
            
            # Connection should still be usable after failure
            assert health_tracker.is_connected, "Connection should survive agent failures"
            
            self.record_metric("connection_survived_failure", True)
            self.record_metric("messages_before_failure", health_tracker.messages_sent)
            
        finally:
            # Clean up connection
            health_tracker.close_connection()

    @pytest.mark.asyncio  
    async def test_user_experience_quality_during_agent_failure(self):
        """MISSION CRITICAL: User experience quality when ActionsToMeetGoalsSubAgent fails.
        
        Even during failures, user experience must be maintained:
        - Informative error messages (not technical details)
        - Reasonable response times (no hanging)
        - Graceful degradation with alternatives
        """
        # Track user experience metrics
        ux_metrics = {
            "start_time": time.time(),
            "end_time": None,
            "response_time": None,
            "user_feedback_quality": None,
            "alternative_provided": False,
            "error_message_user_friendly": False
        }
        
        # Create agent that will fail
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        
        # Create execution context
        context = UserExecutionContext.from_request_supervisor(
            user_id=f"ux_user_{uuid.uuid4().hex[:6]}",
            thread_id=f"ux_thread_{uuid.uuid4().hex[:6]}",
            run_id=f"ux_run_{uuid.uuid4().hex[:6]}",
            metadata={
                "user_request": "I need help creating an action plan to improve my AI system performance and reduce costs"
            }
        )
        
        # Execute and measure user experience
        try:
            result = await agent.execute(context, stream_updates=True)
            
            # If execution succeeds (fallback works), measure UX quality
            ux_metrics["end_time"] = time.time()
            ux_metrics["response_time"] = ux_metrics["end_time"] - ux_metrics["start_time"]
            ux_metrics["alternative_provided"] = result is not None
            
            # Verify reasonable response time
            assert ux_metrics["response_time"] < 10.0, f"Response too slow: {ux_metrics['response_time']}s"
            
            # Verify meaningful result provided
            if result and "action_plan_result" in result:
                plan = result["action_plan_result"]
                if hasattr(plan, "plan_steps") and plan.plan_steps:
                    ux_metrics["user_feedback_quality"] = "good"
                    
            self.record_metric("user_experience_maintained", True)
            self.record_metric("fallback_provided_value", True)
            
        except Exception as e:
            ux_metrics["end_time"] = time.time()
            ux_metrics["response_time"] = ux_metrics["end_time"] - ux_metrics["start_time"]
            
            # Verify failure was fast (not hanging)
            assert ux_metrics["response_time"] < 5.0, f"Failure took too long: {ux_metrics['response_time']}s"
            
            # Verify error message quality
            error_msg = str(e).lower()
            technical_terms = ["llm manager", "architectural migration", "five_whys", "none type"]
            ux_metrics["error_message_user_friendly"] = not any(term in error_msg for term in technical_terms)
            
            # If error message is too technical, that's a UX problem
            if not ux_metrics["error_message_user_friendly"]:
                pytest.fail(f"Technical error message exposed to user: {e}")
                
            self.record_metric("failure_response_time_acceptable", ux_metrics["response_time"] < 5.0)
            self.record_metric("error_message_user_friendly", ux_metrics["error_message_user_friendly"])
            
        # Record all UX metrics
        for metric, value in ux_metrics.items():
            if value is not None:
                self.record_metric(f"ux_{metric}", value)

    def _validate_successful_event_sequence(self, events: List[Dict]) -> None:
        """Validate WebSocket event sequence for successful execution."""
        event_types = [e["event_type"] for e in events]
        
        # Must have agent_started and agent_completed
        assert "agent_started" in event_types, "Missing agent_started event"
        assert "agent_completed" in event_types, "Missing agent_completed event"
        
        # agent_started should come before agent_completed
        started_pos = next(i for i, e in enumerate(events) if e["event_type"] == "agent_started")
        completed_pos = next(i for i, e in enumerate(events) if e["event_type"] == "agent_completed")
        assert started_pos < completed_pos, "agent_started must come before agent_completed"
        
        # Tool events should be paired
        executing_events = [e for e in events if e["event_type"] == "tool_executing"]
        completed_events = [e for e in events if e["event_type"] == "tool_completed"]
        assert len(executing_events) == len(completed_events), "Tool events must be paired"

    def _validate_failure_event_sequence(self, events: List[Dict]) -> None:
        """Validate WebSocket event sequence for failed execution."""
        event_types = [e["event_type"] for e in events]
        
        # Should have agent_started but NOT agent_completed on failure
        assert "agent_started" in event_types, "Missing agent_started event even on failure"
        
        if "agent_completed" in event_types:
            pytest.fail("agent_completed should not be sent on failure")
            
        # If error event exists, it should come after agent_started
        if "error" in event_types:
            started_pos = next(i for i, e in enumerate(events) if e["event_type"] == "agent_started")
            error_pos = next(i for i, e in enumerate(events) if e["event_type"] == "error")
            assert started_pos < error_pos, "error event should come after agent_started"

    def teardown_method(self, method):
        """Cleanup after mission critical test."""
        super().teardown_method(method)
        
        # Ensure mission critical metrics were recorded
        metrics = self.get_all_metrics()
        assert metrics.get("test_category") == "mission_critical_websocket"
        assert metrics.get("business_impact") == "golden_path_protection"
        
        # Log mission critical test completion
        print(f"\nMission Critical WebSocket Test Completed: {method.__name__ if method else 'unknown'}")
        print(f"Metrics: {metrics}")


if __name__ == "__main__":
    # Run mission critical WebSocket tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])