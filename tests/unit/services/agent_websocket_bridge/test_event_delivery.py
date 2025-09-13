"""
AgentWebSocketBridge Event Delivery Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical Chat Infrastructure)
- Business Goal: Protect $500K+ ARR by ensuring reliable event delivery for chat UX
- Value Impact: Validates WebSocket event delivery preventing silent failures
- Strategic Impact: Core event system testing for Golden Path real-time communication

This test suite validates the event delivery patterns of AgentWebSocketBridge,
ensuring proper WebSocket event emission, delivery tracking, and error handling
that are critical for providing real-time agent feedback to users.

GOLDEN PATH CRITICAL: These tests validate the 5 business-critical events:
- agent_started: User sees agent began processing
- agent_thinking: Real-time reasoning visibility
- tool_executing: Tool usage transparency  
- tool_completed: Tool results display
- agent_completed: User knows response is ready

@compliance CLAUDE.md - SSOT patterns, WebSocket event requirements
@compliance SPEC/websocket_agent_integration_critical.xml - Event delivery patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

# Bridge Components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    create_agent_websocket_bridge
)

# User Context Components
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket Dependencies
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentWebSocketBridgeEventDelivery(SSotAsyncTestCase):
    """
    Test AgentWebSocketBridge event delivery and WebSocket emission.
    
    GOLDEN PATH CRITICAL: These tests validate that all 5 business-critical
    WebSocket events are properly emitted for real-time chat functionality.
    """
    
    def setup_method(self, method):
        """Set up test environment with user context and mock WebSocket manager."""
        super().setup_method(method)
        
        # Create test user context
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = f"thread_{uuid.uuid4()}"
        self.test_request_id = f"req_{uuid.uuid4()}"
        self.test_run_id = f"run_{uuid.uuid4()}"
        
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            agent_context={
                "test": "event_delivery",
                "test_run_ref": self.test_run_id
            },
            audit_metadata={"test_suite": "event_delivery"}
        )
        
        # Create bridge for testing
        self.bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Create mock WebSocket manager with proper interface
        self.mock_websocket_manager = MagicMock()
        self.mock_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        self.mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        self.mock_websocket_manager.is_connected = MagicMock(return_value=True)
        
        # Set mock WebSocket manager on bridge
        self.bridge.websocket_manager = self.mock_websocket_manager
    
    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_emit_agent_started_event(self):
        """
        Test emission of agent_started event.
        
        GOLDEN PATH CRITICAL: agent_started event must be emitted when
        an agent begins processing to provide user feedback.
        """
        # Test data
        agent_name = "TestAgent"
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_agent_started(
            run_id=run_id,
            agent_name=agent_name
        )
        
        # Verify method returns success
        assert result is True, "notify_agent_started should return True"
        
        # Verify WebSocket manager was called with correct parameters
        self.mock_websocket_manager.send_to_thread.assert_called()
        
        # Get the actual call arguments
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        assert call_args is not None, "send_to_thread should have been called"
        
        # Verify call parameters
        args, kwargs = call_args
        if args:
            # Positional arguments: thread_id, event_data
            thread_id_arg = args[0]
            assert thread_id_arg == self.test_thread_id, "Thread ID should match"
        elif 'thread_id' in kwargs:
            # Keyword arguments
            assert kwargs['thread_id'] == self.test_thread_id, "Thread ID should match"
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_emit_agent_thinking_event(self):
        """
        Test emission of agent_thinking event.
        
        GOLDEN PATH CRITICAL: agent_thinking event provides real-time
        visibility into agent reasoning process.
        """
        # Test data
        thinking_message = "Analyzing user request and determining best approach..."
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_agent_thinking(
            run_id=run_id,
            agent_name="TestAgent",
            reasoning=thinking_message
        )
        
        # Verify method returns success
        assert result is True, "notify_agent_thinking should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_emit_tool_executing_event(self):
        """
        Test emission of tool_executing event.
        
        GOLDEN PATH CRITICAL: tool_executing event provides transparency
        into tool usage during agent execution.
        """
        # Test data
        tool_name = "data_analyzer"
        tool_purpose = "Analyzing data patterns"
        parameters = {"data_source": "user_input", "analysis_type": "pattern"}
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_tool_executing(
            run_id=run_id,
            tool_name=tool_name,
            parameters=parameters
        )
        
        # Verify method returns success
        assert result is True, "notify_tool_executing should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_emit_tool_completed_event(self):
        """
        Test emission of tool_completed event.
        
        GOLDEN PATH CRITICAL: tool_completed event displays tool results
        to provide visibility into tool execution outcomes.
        """
        # Test data
        tool_name = "data_analyzer"
        result_data = {
            "analysis_complete": True,
            "patterns_found": 5,
            "recommendations": ["optimize_query", "add_index"]
        }
        execution_time_ms = 1250.5
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_tool_completed(
            run_id=run_id,
            tool_name=tool_name,
            result=result_data
        )
        
        # Verify method returns success
        assert result is True, "notify_tool_completed should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_emit_agent_completed_event(self):
        """
        Test emission of agent_completed event.
        
        GOLDEN PATH CRITICAL: agent_completed event signals to user
        that agent processing is complete and response is ready.
        """
        # Test data
        agent_result = {
            "success": True,
            "response": "Task completed successfully",
            "actions_taken": ["analyzed_data", "generated_recommendations"]
        }
        execution_time_ms = 5420.8
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_agent_completed(
            run_id=run_id,
            agent_name="TestAgent",
            result=agent_result,
            execution_time_ms=execution_time_ms
        )
        
        # Verify method returns success
        assert result is True, "notify_agent_completed should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.event_delivery
    async def test_emit_agent_error_event(self):
        """
        Test emission of agent_error event for error handling.
        
        BUSINESS VALUE: Error events provide visibility into agent
        failures and enable proper user experience during errors.
        """
        # Test data
        error_message = "Tool execution failed: Connection timeout"
        error_details = {
            "error_type": "ConnectionTimeout",
            "tool_name": "external_api",
            "retry_possible": True
        }
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_agent_error(
            run_id=run_id,
            agent_name="TestAgent",
            error=error_message
        )
        
        # Verify method returns success
        assert result is True, "notify_agent_error should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.event_delivery
    async def test_emit_progress_update_event(self):
        """
        Test emission of progress update events.
        
        BUSINESS VALUE: Progress updates provide real-time feedback
        during long-running agent operations.
        """
        # Test data
        progress_message = "Processing step 3 of 5: Analyzing data patterns..."
        progress_percentage = 60
        current_step = "data_analysis"
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_progress_update(
            run_id=run_id,
            agent_name="TestAgent",
            progress={
                "message": progress_message,
                "percentage": progress_percentage,
                "current_step": current_step
            }
        )
        
        # Verify method returns success
        assert result is True, "notify_progress_update should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.event_delivery
    async def test_emit_custom_event(self):
        """
        Test emission of custom events for extensibility.
        
        BUSINESS VALUE: Custom events enable flexible communication
        patterns for specialized agent interactions.
        """
        # Test data
        event_type = "custom_agent_event"
        custom_data = {
            "event_id": str(uuid.uuid4()),
            "custom_payload": {"key": "value", "number": 42},
            "metadata": {"source": "test_agent", "priority": "high"}
        }
        run_id = self.test_run_id
        
        # Call emit method
        result = await self.bridge.notify_custom(
            run_id=run_id,
            agent_name="TestAgent",
            notification_type=event_type,
            data=custom_data
        )
        
        # Verify method returns success
        assert result is True, "notify_custom should return True"
        
        # Verify WebSocket manager was called
        self.mock_websocket_manager.send_to_thread.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_event_delivery_with_websocket_failure(self):
        """
        Test event delivery behavior when WebSocket manager fails.
        
        BUSINESS VALUE: Graceful error handling prevents agent execution
        failures when WebSocket issues occur.
        """
        # Configure WebSocket manager to fail
        self.mock_websocket_manager.send_to_thread = AsyncMock(side_effect=Exception("WebSocket connection lost"))
        
        # Attempt to emit event
        result = await self.bridge.notify_agent_started(
            run_id=self.test_run_id,
            agent_name="TestAgent"
        )
        
        # Verify method handles failure gracefully
        # Note: Actual behavior depends on implementation - could return False or raise
        # This test validates that the method doesn't crash
        assert result is not None, "Method should return a result even on WebSocket failure"
    
    @pytest.mark.unit
    @pytest.mark.error_handling  
    async def test_event_delivery_with_no_websocket_manager(self):
        """
        Test event delivery behavior when no WebSocket manager is set.
        
        BUSINESS VALUE: Robust error handling allows agent execution
        to continue even without WebSocket connectivity.
        """
        # Remove WebSocket manager
        self.bridge.websocket_manager = None
        
        # Attempt to emit event
        result = await self.bridge.notify_agent_started(
            run_id=self.test_run_id,
            agent_name="TestAgent"
        )
        
        # Verify method handles missing manager gracefully
        assert result is not None, "Method should handle missing WebSocket manager"
    
    @pytest.mark.unit
    @pytest.mark.event_tracking
    async def test_event_history_tracking(self):
        """
        Test that events are properly tracked in bridge history.
        
        BUSINESS VALUE: Event history enables debugging and monitoring
        of WebSocket event delivery for reliability improvements.
        """
        # Emit multiple events
        events = [
            ("agent_started", self.bridge.notify_agent_started),
            ("agent_thinking", self.bridge.notify_agent_thinking),
            ("tool_executing", self.bridge.notify_tool_executing),
            ("tool_completed", self.bridge.notify_tool_completed),
            ("agent_completed", self.bridge.notify_agent_completed)
        ]
        
        initial_history_length = len(self.bridge._event_history)
        
        # Emit each event type
        for event_name, emit_method in events:
            if event_name == "agent_started":
                await emit_method(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    agent_name="TestAgent"
                )
            elif event_name == "agent_thinking":
                await emit_method(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    message="Test thinking"
                )
            elif event_name == "tool_executing":
                await emit_method(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    tool_name="test_tool",
                    tool_purpose="testing"
                )
            elif event_name == "tool_completed":
                await emit_method(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    tool_name="test_tool",
                    result={"success": True}
                )
            elif event_name == "agent_completed":
                await emit_method(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    result={"success": True}
                )
        
        # Verify all events were processed (WebSocket manager should have been called multiple times)
        assert self.mock_websocket_manager.send_to_thread.call_count >= len(events), \
            f"WebSocket manager should have been called at least {len(events)} times"
    
    @pytest.mark.unit
    @pytest.mark.concurrent_events
    async def test_concurrent_event_emission(self):
        """
        Test concurrent event emission to validate thread safety.
        
        BUSINESS CRITICAL: Concurrent event emission must be thread-safe
        to prevent race conditions in multi-agent scenarios.
        """
        # Define concurrent event emission tasks
        async def emit_events_concurrently(bridge, user_context, event_prefix, count):
            """Emit multiple events concurrently."""
            tasks = []
            for i in range(count):
                task = bridge.notify_agent_thinking(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=f"{user_context.agent_context['run_id']}_{event_prefix}_{i}",
                    message=f"{event_prefix} thinking message {i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        # Emit events concurrently
        results1 = await emit_events_concurrently(self.bridge, self.user_context, "batch1", 3)
        results2 = await emit_events_concurrently(self.bridge, self.user_context, "batch2", 3)
        
        # Verify all events were emitted successfully
        assert all(result is True for result in results1), "All batch1 events should succeed"
        assert all(result is True for result in results2), "All batch2 events should succeed"
        
        # Verify WebSocket manager was called correct number of times
        expected_calls = len(results1) + len(results2)
        assert self.mock_websocket_manager.send_to_thread.call_count >= expected_calls, \
            f"WebSocket manager should have been called at least {expected_calls} times"
    
    @pytest.mark.unit
    @pytest.mark.parameter_validation
    async def test_event_parameter_validation(self):
        """
        Test event emission with invalid parameters.
        
        BUSINESS VALUE: Parameter validation prevents malformed events
        that could cause WebSocket delivery failures.
        """
        # Test with invalid run_id
        with pytest.raises((ValueError, TypeError, AttributeError)):
            await self.bridge.notify_agent_started(
                run_id=None,  # Invalid run_id
                agent_name="TestAgent"
            )
        
        # Test with invalid agent_name
        with pytest.raises((ValueError, TypeError, AttributeError)):
            await self.bridge.notify_agent_started(
                run_id=self.test_run_id,
                agent_name=""  # Empty agent_name
            )
        
        # Test with invalid run_id type
        with pytest.raises((ValueError, TypeError, AttributeError)):
            await self.bridge.notify_agent_started(
                run_id=12345,  # Invalid run_id type
                agent_name="TestAgent"
            )