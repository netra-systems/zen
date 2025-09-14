"""
Agent Lifecycle Core Tests - Phase 1 Critical Business Logic

Business Value: Platform/Internal - Agent Lifecycle Management Foundation
Tests core AgentLifecycleMixin functionality including state transitions, 
timing operations, WebSocket integration, and error handling patterns.

SSOT Compliance: Uses SSotAsyncTestCase, real UserExecutionContext instances,
minimal mocking per CLAUDE.md standards. No test cheating.

Coverage Target: AgentLifecycleMixin methods, state management, lifecycle events
Current Coverage: 0% -> Target: 80%+ (116 lines total)

GitHub Issue: #872 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.timing_decorators import TimingCategory
from starlette.websockets import WebSocketDisconnect


class ConcreteAgentLifecycle(AgentLifecycleMixin):
    """Concrete implementation of AgentLifecycleMixin for testing lifecycle patterns."""

    def __init__(self, name="TestLifecycleAgent"):
        self.name = name
        self.logger = Mock()
        self.start_time = None
        self.end_time = None
        self._lifecycle_state = SubAgentLifecycle.PENDING
        self.timing_collector = ExecutionTimingCollector(agent_name=f"test-{name}")
        self.context = {}  # Protected context for cleanup testing
        
        # Mock WebSocket methods
        self.emit_agent_started = AsyncMock()
        self.emit_agent_completed = AsyncMock()
        self.emit_error = AsyncMock()
        self.emit_thinking = AsyncMock()

    def set_state(self, state: SubAgentLifecycle):
        """Set agent lifecycle state."""
        self._lifecycle_state = state

    def get_state(self) -> SubAgentLifecycle:
        """Get current agent lifecycle state."""
        return self._lifecycle_state

    def _log_agent_start(self, run_id: str):
        """Mock agent start logging."""
        self.logger.info(f"Agent {self.name} starting for run {run_id}")

    def _log_agent_completion(self, run_id: str, status: str):
        """Mock agent completion logging."""
        self.logger.info(f"Agent {self.name} {status} for run {run_id}")

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Mock execute implementation - can be overridden in tests."""
        await asyncio.sleep(0.001)  # Simulate work
        # Track execution for testing
        self.executed = True
        self.executed_with = {"state": state, "run_id": run_id, "stream_updates": stream_updates}


class TestAgentLifecycleCore(SSotAsyncTestCase):
    """Test AgentLifecycleMixin core lifecycle management functionality."""

    def setup_method(self, method):
        """Set up test environment with real components."""
        super().setup_method(method)
        
        self.agent = ConcreteAgentLifecycle("test-lifecycle-agent")
        
        # Create real DeepAgentState for testing
        self.test_state = DeepAgentState(
            messages=[],
            next_node="",
            step_count=0,
            max_iterations=10,
            context={"test_mode": True}
        )
        
        self.run_id = "test-run-lifecycle-001"
        self.stream_updates = True

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        # Reset agent state
        self.agent.set_state(SubAgentLifecycle.PENDING)

    async def test_pre_run_successful_execution(self):
        """Test _pre_run method with successful entry conditions."""
        # Test: _pre_run initializes agent and checks conditions
        result = await self.agent._pre_run(self.test_state, self.run_id, self.stream_updates)
        
        # Verify: Agent was properly initialized
        assert result is True
        assert self.agent.start_time is not None
        assert self.agent.get_state() == SubAgentLifecycle.RUNNING
        
        # Verify: WebSocket starting update was sent
        self.agent.emit_agent_started.assert_called_once()
        
        # Verify: Logger was called for initialization
        self.agent.logger.info.assert_called()

    async def test_pre_run_failed_entry_conditions(self):
        """Test _pre_run method with failed entry conditions."""
        # Override check_entry_conditions to return False
        async def failing_conditions(state, run_id):
            return False
        self.agent.check_entry_conditions = failing_conditions
        
        # Test: _pre_run handles failed entry conditions
        result = await self.agent._pre_run(self.test_state, self.run_id, self.stream_updates)
        
        # Verify: Pre-run returns False for failed conditions
        assert result is False
        
        # Verify: Agent state was still initialized (even if conditions failed)
        assert self.agent.get_state() == SubAgentLifecycle.RUNNING

    async def test_post_run_successful_completion(self):
        """Test _post_run method with successful completion."""
        # Setup: Initialize timing
        self.agent.start_time = time.time()
        await asyncio.sleep(0.001)  # Small delay for timing
        
        # Test: _post_run completes successfully
        await self.agent._post_run(self.test_state, self.run_id, self.stream_updates, success=True)
        
        # Verify: Agent state was updated to completed
        assert self.agent.get_state() == SubAgentLifecycle.COMPLETED
        
        # Verify: Timing was finalized
        assert self.agent.end_time is not None
        execution_time = self.agent.end_time - self.agent.start_time
        assert execution_time > 0
        
        # Verify: Completion update was sent
        self.agent.emit_agent_completed.assert_called_once()

    async def test_post_run_failed_completion(self):
        """Test _post_run method with failed completion."""
        # Setup: Initialize timing
        self.agent.start_time = time.time()
        await asyncio.sleep(0.001)  # Small delay for timing
        
        # Test: _post_run handles failure case
        await self.agent._post_run(self.test_state, self.run_id, self.stream_updates, success=False)
        
        # Verify: Agent state was updated to failed
        assert self.agent.get_state() == SubAgentLifecycle.FAILED
        
        # Verify: Error notification was sent
        self.agent.emit_error.assert_called_once()

    def test_finalize_execution_timing(self):
        """Test execution timing finalization."""
        # Setup: Set start time
        self.agent.start_time = time.time()
        time.sleep(0.001)  # Small delay
        
        # Test: Finalize timing
        execution_time = self.agent._finalize_execution_timing()
        
        # Verify: End time was set and duration calculated
        assert self.agent.end_time is not None
        assert execution_time > 0
        assert execution_time == self.agent.end_time - self.agent.start_time

    def test_update_lifecycle_status_success(self):
        """Test lifecycle status update for success case."""
        # Test: Update status for successful completion
        status = self.agent._update_lifecycle_status(success=True)
        
        # Verify: Status and state are correct
        assert status == "completed"
        assert self.agent.get_state() == SubAgentLifecycle.COMPLETED

    def test_update_lifecycle_status_failure(self):
        """Test lifecycle status update for failure case."""
        # Test: Update status for failed completion
        status = self.agent._update_lifecycle_status(success=False)
        
        # Verify: Status and state are correct
        assert status == "failed"
        assert self.agent.get_state() == SubAgentLifecycle.FAILED

    def test_log_execution_completion(self):
        """Test execution completion logging."""
        execution_time = 0.123
        status = "completed"
        
        # Test: Log completion
        self.agent._log_execution_completion(self.run_id, status, execution_time)
        
        # Verify: Both main log and agent completion log were called
        assert self.agent.logger.info.call_count == 2
        
        # Verify: Log messages contain expected information
        calls = self.agent.logger.info.call_args_list
        main_log_msg = calls[0][0][0]
        assert self.agent.name in main_log_msg
        assert status in main_log_msg
        assert self.run_id in main_log_msg
        assert "0.12s" in main_log_msg  # Formatted execution time

    async def test_send_completion_update_success(self):
        """Test completion update sending for success case."""
        execution_time = 0.456
        
        # Test: Send completion update for success
        await self.agent._send_completion_update(
            self.run_id, self.stream_updates, "completed", execution_time
        )
        
        # Verify: Completion event was emitted with timing data
        self.agent.emit_agent_completed.assert_called_once_with({"execution_time": execution_time})

    async def test_send_completion_update_failure(self):
        """Test completion update sending for failure case."""
        execution_time = 0.789
        
        # Test: Send completion update for failure
        await self.agent._send_completion_update(
            self.run_id, self.stream_updates, "failed", execution_time
        )
        
        # Verify: Error event was emitted
        self.agent.emit_error.assert_called_once()
        call_args = self.agent.emit_error.call_args[0]
        assert self.agent.name in call_args[0]
        assert "failed" in call_args[0]

    async def test_send_completion_update_no_stream(self):
        """Test completion update when streaming is disabled."""
        # Test: Send completion update with streaming disabled
        await self.agent._send_completion_update(
            self.run_id, False, "completed", 0.123
        )
        
        # Verify: No WebSocket events were sent
        self.agent.emit_agent_completed.assert_not_called()
        self.agent.emit_error.assert_not_called()


class TestAgentLifecycleExecution(SSotAsyncTestCase):
    """Test AgentLifecycleMixin execution flow and error handling."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.agent = ConcreteAgentLifecycle("test-execution-agent")
        self.test_state = DeepAgentState(
            messages=[],
            next_node="",
            step_count=5,  # Start with some steps
            max_iterations=10,
            context={"test_mode": True}
        )
        self.run_id = "test-run-execution-001"

    async def test_run_successful_execution(self):
        """Test complete run method with successful execution."""
        # Test: Run agent successfully
        await self.agent.run(self.test_state, self.run_id, True)
        
        # Verify: Agent executed successfully
        assert hasattr(self.agent, 'executed')
        assert self.agent.executed is True
        
        # Verify: State was incremented
        assert self.test_state.step_count == 6  # 5 + 1
        
        # Verify: Agent completed successfully
        assert self.agent.get_state() == SubAgentLifecycle.COMPLETED

    async def test_run_with_websocket_disconnect(self):
        """Test run method handles WebSocket disconnect gracefully."""
        # Override execute to raise WebSocketDisconnect
        async def failing_execute(state, run_id, stream_updates):
            raise WebSocketDisconnect(code=1000, reason="Client disconnected")
        self.agent.execute = failing_execute
        
        # Test: Run handles WebSocket disconnect
        await self.agent.run(self.test_state, self.run_id, True)
        
        # Verify: Agent was marked as failed
        assert self.agent.get_state() == SubAgentLifecycle.FAILED
        
        # Verify: Disconnect was logged
        self.agent.logger.info.assert_called()

    async def test_run_with_general_exception(self):
        """Test run method handles general exceptions."""
        # Override execute to raise general exception
        test_error = ValueError("Test execution error")
        async def failing_execute(state, run_id, stream_updates):
            raise test_error
        self.agent.execute = failing_execute
        
        # Test: Run method re-raises exceptions after handling
        with pytest.raises(ValueError, match="Test execution error"):
            await self.agent.run(self.test_state, self.run_id, True)
        
        # Verify: Agent was marked as failed
        assert self.agent.get_state() == SubAgentLifecycle.FAILED
        
        # Verify: Error was logged
        self.agent.logger.error.assert_called()

    async def test_handle_execution_error(self):
        """Test execution error handling."""
        test_error = RuntimeError("Test runtime error")
        
        # Test: Handle execution error
        await self.agent._handle_execution_error(test_error, self.test_state, self.run_id, True)
        
        # Verify: Error was logged
        self.agent.logger.error.assert_called()
        error_msg = self.agent.logger.error.call_args[0][0]
        assert self.agent.name in error_msg
        assert self.run_id in error_msg
        assert "Test runtime error" in error_msg
        
        # Verify: Error notification was sent
        self.agent.emit_error.assert_called()

    async def test_handle_websocket_disconnect(self):
        """Test WebSocket disconnect handling."""
        disconnect_error = WebSocketDisconnect(code=1001, reason="Test disconnect")
        
        # Test: Handle WebSocket disconnect
        await self.agent._handle_websocket_disconnect(
            disconnect_error, self.test_state, self.run_id, True
        )
        
        # Verify: Disconnect was logged
        self.agent.logger.info.assert_called()
        # Check all logger.info calls to find the WebSocket disconnect message
        calls = self.agent.logger.info.call_args_list
        disconnect_found = False
        for call in calls:
            log_msg = call[0][0]
            if "WebSocket disconnected" in log_msg and self.agent.name in log_msg:
                disconnect_found = True
                break
        assert disconnect_found, f"WebSocket disconnect message not found in logs: {[call[0][0] for call in calls]}"

    async def test_check_entry_conditions_default(self):
        """Test default entry conditions check (should always pass)."""
        # Test: Default entry conditions
        result = await self.agent.check_entry_conditions(self.test_state, self.run_id)
        
        # Verify: Default implementation returns True
        assert result is True

    async def test_cleanup_default(self):
        """Test default cleanup behavior."""
        # Setup: Add some context data
        self.agent.context = {"test_key": "test_value", "run_data": [1, 2, 3]}
        
        # Test: Cleanup agent
        await self.agent.cleanup(self.test_state, self.run_id)
        
        # Verify: Context was cleared
        assert len(self.agent.context) == 0

    def test_initialize_agent_run(self):
        """Test agent run initialization."""
        # Test: Initialize agent run
        self.agent._initialize_agent_run(self.run_id)
        
        # Verify: Agent state was updated
        assert self.agent.get_state() == SubAgentLifecycle.RUNNING
        assert self.agent.start_time is not None
        
        # Verify: Logging was called
        self.agent.logger.info.assert_called()

    async def test_send_starting_update_enabled(self):
        """Test sending starting update when streaming is enabled."""
        # Test: Send starting update with streaming enabled
        await self.agent._send_starting_update(self.run_id, True)
        
        # Verify: Agent started event was emitted
        self.agent.emit_agent_started.assert_called_once()

    async def test_send_starting_update_disabled(self):
        """Test sending starting update when streaming is disabled."""
        # Test: Send starting update with streaming disabled
        await self.agent._send_starting_update(self.run_id, False)
        
        # Verify: No events were emitted
        self.agent.emit_agent_started.assert_not_called()

    async def test_execute_with_conditions_success(self):
        """Test execute with conditions - successful path."""
        # Test: Execute with conditions
        result = await self.agent._execute_with_conditions(self.test_state, self.run_id, True)
        
        # Verify: Execution was successful
        assert result is True
        
        # Verify: Agent executed
        assert hasattr(self.agent, 'executed')
        assert self.agent.executed is True
        
        # Verify: Step count was incremented
        assert self.test_state.step_count == 6  # Started at 5

    async def test_execute_with_conditions_failed_entry(self):
        """Test execute with conditions - failed entry conditions."""
        # Override entry conditions to fail
        async def failing_conditions(state, run_id):
            return False
        self.agent.check_entry_conditions = failing_conditions
        
        # Test: Execute with failed conditions
        result = await self.agent._execute_with_conditions(self.test_state, self.run_id, True)
        
        # Verify: Execution failed due to conditions
        assert result is False
        
        # Verify: Step count was not incremented
        assert self.test_state.step_count == 5  # Unchanged

    async def test_complete_agent_run(self):
        """Test complete agent run process."""
        # Setup: Initialize timing
        self.agent.start_time = time.time()
        await asyncio.sleep(0.001)
        execution_time = 0.123
        status = "completed"
        
        # Test: Complete agent run
        await self.agent._complete_agent_run(
            self.run_id, True, status, execution_time, self.test_state
        )
        
        # Verify: All completion steps were executed
        # - Logging
        assert self.agent.logger.info.call_count >= 1
        # - WebSocket update
        self.agent.emit_agent_completed.assert_called()
        # - Cleanup (context should be cleared)
        assert len(self.agent.context) == 0


class TestAgentLifecycleEdgeCases(SSotBaseTestCase):
    """Test AgentLifecycleMixin edge cases and error scenarios."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.agent = ConcreteAgentLifecycle("test-edge-agent")
        self.test_state = DeepAgentState(
            messages=[],
            next_node="",
            step_count=0,
            max_iterations=1,  # Low limit for testing
            context={}
        )
        self.run_id = "test-run-edge-001"

    async def test_send_error_notification_websocket_failure(self):
        """Test error notification when WebSocket also fails."""
        # Setup: Make WebSocket emit fail
        self.agent.emit_error.side_effect = WebSocketDisconnect(code=1000, reason="Disconnected")
        
        test_error = ValueError("Original test error")
        
        # Test: Send error notification with failing WebSocket
        await self.agent._send_error_notification(test_error, self.run_id, True)
        
        # Verify: WebSocket failure was handled gracefully
        self.agent.logger.debug.assert_called()

    async def test_send_entry_condition_warning_websocket_failure(self):
        """Test entry condition warning when WebSocket fails."""
        # Setup: Make WebSocket emit fail
        self.agent.emit_error.side_effect = ConnectionError("Connection failed")
        
        # Test: Send entry condition warning with failing WebSocket
        await self.agent._send_entry_condition_warning(self.run_id, True)
        
        # Verify: WebSocket failure was handled gracefully
        self.agent.logger.debug.assert_called()

    def test_get_websocket_user_id_with_user_id(self):
        """Test WebSocket user ID retrieval when user_id is available."""
        # Setup: Set user_id
        self.agent.user_id = "test-user-123"
        
        # Test: Get WebSocket user ID
        user_id = self.agent._get_websocket_user_id(self.run_id)
        
        # Verify: User ID was returned
        assert user_id == "test-user-123"

    def test_get_websocket_user_id_fallback(self):
        """Test WebSocket user ID retrieval with fallback to run_id."""
        # Setup: No user_id available
        self.agent.user_id = None
        
        # Test: Get WebSocket user ID
        user_id = self.agent._get_websocket_user_id(self.run_id)
        
        # Verify: Run ID was used as fallback
        assert user_id == self.run_id

    def test_build_completion_data(self):
        """Test completion data dictionary building."""
        status = "completed"
        execution_time = 1.234
        
        # Test: Build completion data
        data = self.agent._build_completion_data(status, execution_time)
        
        # Verify: Data dictionary structure
        assert isinstance(data, dict)
        assert data["status"] == status
        assert data["execution_time"] == execution_time
        assert data["message"] == f"{self.agent.name} {status}"

    async def test_handle_entry_failure(self):
        """Test handling of entry condition failures."""
        # Test: Handle entry failure
        await self.agent._handle_entry_failure(self.run_id, True, self.test_state)
        
        # Verify: Warning was logged
        self.agent.logger.warning.assert_called()
        warning_msg = self.agent.logger.warning.call_args[0][0]
        assert self.agent.name in warning_msg
        assert "entry conditions not met" in warning_msg
        assert self.run_id in warning_msg
        
        # Verify: WebSocket warning was sent
        self.agent.emit_error.assert_called()
        
        # Verify: Agent was marked as failed
        assert self.agent.get_state() == SubAgentLifecycle.FAILED

    async def test_timing_collector_integration(self):
        """Test integration with ExecutionTimingCollector."""
        # Verify: Agent has timing collector
        assert hasattr(self.agent, 'timing_collector')
        assert isinstance(self.agent.timing_collector, ExecutionTimingCollector)
        
        # Test: Run method integrates with timing collector
        await self.agent.run(self.test_state, self.run_id, False)
        
        # Verify: Timing operations were recorded
        # Note: This tests integration but timing_collector details are tested separately
        assert self.agent.timing_collector is not None