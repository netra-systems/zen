"""Comprehensive tests for AgentLifecycleMixin functionality.

BUSINESS VALUE: Ensures reliable agent execution and proper error handling,
directly protecting customer AI operations and preventing service disruptions
that could impact business-critical agent workflows.

Tests critical paths including lifecycle management, WebSocket integration,
error handling, and state transitions.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.Agent import SubAgentLifecycle

# Test implementation of AgentLifecycleMixin
class TestAgent(AgentLifecycleMixin):
    """Test implementation of AgentLifecycleMixin."""
    
    def __init__(self, name="test_agent"):
        self.name = name
        self.logger = Mock()
        self.websocket_manager = Mock()
        self.user_id = "test_user"
        self.start_time = time.time()
        self.end_time = None
        self.state = SubAgentLifecycle.PENDING
        self.context = Mock()
        self.should_fail_execute = False
        self.should_fail_entry = False
        
    def set_state(self, state):
        """Set agent state."""
        self.state = state
        
    async def execute(self, state, run_id, stream_updates):
        """Test execute implementation."""
        if self.should_fail_execute:
            raise RuntimeError("Execute failed")
        await asyncio.sleep(0.01)
        
    async def check_entry_conditions(self, state, run_id):
        """Test entry conditions implementation."""
        return not self.should_fail_entry
        
    def _log_agent_start(self, run_id):
        """Mock log agent start."""
        pass
        
    def _log_agent_completion(self, run_id, status):
        """Mock log agent completion."""
        pass
        
    async def _send_update(self, run_id, data):
        """Mock send update."""
        pass

# Test fixtures for setup
@pytest.fixture
def test_agent():
    """Test agent instance."""
    return TestAgent()

@pytest.fixture
def deep_agent_state():
    """Mock DeepAgentState."""
    state = Mock(spec=DeepAgentState)
    state.step_count = 0
    return state

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    manager = Mock()
    manager.send_agent_log = AsyncMock()
    manager.send_error = AsyncMock()
    return manager

# Helper functions for 25-line compliance
def assert_agent_state(agent, expected_state):
    """Assert agent is in expected state."""
    assert agent.state == expected_state

def assert_execution_time_set(agent):
    """Assert agent execution time is set."""
    assert agent.end_time is not None
    assert agent.end_time >= agent.start_time

def setup_agent_for_success(agent):
    """Set up agent for successful execution."""
    agent.should_fail_execute = False
    agent.should_fail_entry = False

def setup_agent_for_failure(agent):
    """Set up agent for failed execution."""
    agent.should_fail_execute = True

def setup_agent_for_entry_failure(agent):
    """Set up agent for failed entry conditions."""
    agent.should_fail_entry = True

async def run_agent_successfully(agent, state, run_id="test_run"):
    """Run agent successfully."""
    setup_agent_for_success(agent)
    await agent.run(state, run_id, stream_updates=False)

async def run_agent_with_failure(agent, state, run_id="test_run"):
    """Run agent with execution failure."""
    setup_agent_for_failure(agent)
    with pytest.raises(RuntimeError):
        await agent.run(state, run_id, stream_updates=False)

# Core lifecycle functionality tests
class TestLifecycleBasics:
    """Test basic lifecycle management."""

    @pytest.mark.asyncio
    async def test_pre_run_initialization(self, test_agent, deep_agent_state):
        """_pre_run initializes agent correctly."""
        result = await test_agent._pre_run(deep_agent_state, "test_run", False)
        assert result is True
        assert_agent_state(test_agent, SubAgentLifecycle.RUNNING)

    @pytest.mark.asyncio
    async def test_pre_run_with_streaming(self, test_agent, deep_agent_state):
        """_pre_run handles streaming updates."""
        test_agent.websocket_manager = Mock()
        test_agent._send_update = AsyncMock()
        result = await test_agent._pre_run(deep_agent_state, "test_run", True)
        assert result is True

    @pytest.mark.asyncio
    async def test_post_run_completion(self, test_agent, deep_agent_state):
        """_post_run handles completion correctly."""
        await test_agent._post_run(deep_agent_state, "test_run", False, success=True)
        assert_agent_state(test_agent, SubAgentLifecycle.COMPLETED)
        assert_execution_time_set(test_agent)

    @pytest.mark.asyncio
    async def test_post_run_failure(self, test_agent, deep_agent_state):
        """_post_run handles failure correctly."""
        await test_agent._post_run(deep_agent_state, "test_run", False, success=False)
        assert_agent_state(test_agent, SubAgentLifecycle.FAILED)

    def test_execution_timing_calculation(self, test_agent):
        """Execution timing is calculated correctly."""
        test_agent.start_time = time.time() - 1.0  # 1 second ago
        duration = test_agent._finalize_execution_timing()
        assert 0.9 <= duration <= 1.1  # Allow for timing variance

    def test_lifecycle_status_update_success(self, test_agent):
        """Lifecycle status updates correctly for success."""
        status = test_agent._update_lifecycle_status(success=True)
        assert status == "completed"
        assert_agent_state(test_agent, SubAgentLifecycle.COMPLETED)

    def test_lifecycle_status_update_failure(self, test_agent):
        """Lifecycle status updates correctly for failure."""
        status = test_agent._update_lifecycle_status(success=False)
        assert status == "failed" 
        assert_agent_state(test_agent, SubAgentLifecycle.FAILED)

class TestEntryConditions:
    """Test entry condition handling."""

    @pytest.mark.asyncio
    async def test_entry_conditions_pass(self, test_agent, deep_agent_state):
        """Entry conditions pass when expected."""
        setup_agent_for_success(test_agent)
        result = await test_agent._handle_entry_conditions(deep_agent_state, "test_run", False)
        assert result is True

    @pytest.mark.asyncio
    async def test_entry_conditions_fail(self, test_agent, deep_agent_state):
        """Entry conditions fail when expected."""
        setup_agent_for_entry_failure(test_agent)
        result = await test_agent._handle_entry_conditions(deep_agent_state, "test_run", False)
        assert result is False

    @pytest.mark.asyncio
    async def test_entry_failure_handling(self, test_agent, deep_agent_state):
        """Entry failure is handled correctly."""
        setup_agent_for_entry_failure(test_agent)
        test_agent._send_entry_condition_warning = AsyncMock()
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_entry_failure("test_run", False, deep_agent_state)
        test_agent._post_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_condition_warning_sent(self, test_agent):
        """Entry condition warning is sent when streaming."""
        test_agent.websocket_manager = Mock()
        test_agent._send_websocket_warning = AsyncMock()
        
        await test_agent._send_entry_condition_warning("test_run", True)
        test_agent._send_websocket_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_condition_warning_without_websocket(self, test_agent):
        """Entry condition warning handles missing WebSocket."""
        test_agent.websocket_manager = None
        # Should not raise exception
        await test_agent._send_entry_condition_warning("test_run", True)

class TestExecutionFlow:
    """Test main execution flow."""

    @pytest.mark.asyncio
    async def test_successful_execution_flow(self, test_agent, deep_agent_state):
        """Successful execution flow works end-to-end."""
        await run_agent_successfully(test_agent, deep_agent_state)
        assert_agent_state(test_agent, SubAgentLifecycle.COMPLETED)
        assert deep_agent_state.step_count == 1

    @pytest.mark.asyncio
    async def test_failed_execution_flow(self, test_agent, deep_agent_state):
        """Failed execution flow handles errors correctly."""
        test_agent._handle_execution_error = AsyncMock()
        await run_agent_with_failure(test_agent, deep_agent_state)
        test_agent._handle_execution_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_conditions_success(self, test_agent, deep_agent_state):
        """_execute_with_conditions works for successful case."""
        setup_agent_for_success(test_agent)
        result = await test_agent._execute_with_conditions(deep_agent_state, "test_run", False)
        assert result is True
        assert deep_agent_state.step_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_conditions_entry_fail(self, test_agent, deep_agent_state):
        """_execute_with_conditions handles entry condition failure."""
        setup_agent_for_entry_failure(test_agent)
        result = await test_agent._execute_with_conditions(deep_agent_state, "test_run", False)
        assert result is False
        assert deep_agent_state.step_count == 0

    @pytest.mark.asyncio
    async def test_execution_updates_step_count(self, test_agent, deep_agent_state):
        """Execution increments step count."""
        initial_count = deep_agent_state.step_count
        await run_agent_successfully(test_agent, deep_agent_state)
        assert deep_agent_state.step_count == initial_count + 1

class TestWebSocketIntegration:
    """Test WebSocket communication integration."""

    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self, test_agent, deep_agent_state):
        """WebSocket disconnect is handled gracefully."""
        disconnect_error = WebSocketDisconnect(code=1000, reason="Normal closure")
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_websocket_disconnect(disconnect_error, deep_agent_state, "test_run", True)
        test_agent._post_run.assert_called_once_with(deep_agent_state, "test_run", True, success=False)

    @pytest.mark.asyncio
    async def test_websocket_error_notification(self, test_agent):
        """WebSocket error notification is sent."""
        test_agent.websocket_manager = Mock()
        test_agent._send_websocket_error = AsyncMock()
        error = RuntimeError("Test error")
        
        await test_agent._send_error_notification(error, "test_run", True)
        test_agent._send_websocket_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_without_manager(self, test_agent):
        """WebSocket error handling without manager."""
        test_agent.websocket_manager = None
        error = RuntimeError("Test error")
        
        # Should not raise exception
        await test_agent._send_error_notification(error, "test_run", True)

    @pytest.mark.asyncio
    async def test_websocket_warning_sent(self, test_agent):
        """WebSocket warning is sent correctly."""
        test_agent.websocket_manager = Mock()
        test_agent.websocket_manager.send_agent_log = AsyncMock()
        
        await test_agent._send_websocket_warning("test_run")
        test_agent.websocket_manager.send_agent_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_sent(self, test_agent):
        """WebSocket error is sent correctly."""
        test_agent.websocket_manager = Mock()
        test_agent.websocket_manager.send_error = AsyncMock()
        error = RuntimeError("Test error")
        
        await test_agent._send_websocket_error(error, "test_run")
        test_agent.websocket_manager.send_error.assert_called_once()

    def test_websocket_user_id_retrieval(self, test_agent):
        """WebSocket user ID is retrieved correctly."""
        user_id = test_agent._get_websocket_user_id("test_run")
        assert user_id == "test_user"

    def test_websocket_user_id_fallback(self, test_agent):
        """WebSocket user ID falls back to run_id."""
        test_agent.user_id = None
        user_id = test_agent._get_websocket_user_id("test_run")
        assert user_id == "test_run"

class TestErrorHandling:
    """Test error handling mechanisms."""

    @pytest.mark.asyncio
    async def test_execution_error_handling(self, test_agent, deep_agent_state):
        """Execution error is handled correctly."""
        error = RuntimeError("Execution failed")
        test_agent._send_error_notification = AsyncMock()
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_execution_error(error, deep_agent_state, "test_run", True)
        test_agent._send_error_notification.assert_called_once()
        test_agent._post_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_and_reraise_error(self, test_agent, deep_agent_state):
        """Error is handled and reraised."""
        error = RuntimeError("Test error")
        test_agent._handle_execution_error = AsyncMock()
        
        # Test the method within a proper exception context as it would be used in production
        with pytest.raises(RuntimeError, match="Test error"):
            try:
                raise error
            except RuntimeError as e:
                await test_agent._handle_and_reraise_error(e, deep_agent_state, "test_run", True)
        test_agent._handle_execution_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_disconnect_in_run(self, test_agent, deep_agent_state):
        """WebSocket disconnect during run is handled."""
        test_agent._handle_websocket_disconnect = AsyncMock()
        
        # Mock execution to raise WebSocketDisconnect
        async def failing_execute(state, run_id, stream_updates):
            raise WebSocketDisconnect(code=1000)
        test_agent.execute = failing_execute
        
        await test_agent.run(deep_agent_state, "test_run", True)
        test_agent._handle_websocket_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_connection_handling(self, test_agent):
        """WebSocket connection errors are handled."""
        test_agent.websocket_manager = Mock()
        test_agent.websocket_manager.send_agent_log = AsyncMock(side_effect=ConnectionError())
        
        # Should not raise exception
        await test_agent._send_websocket_warning("test_run")

class TestCleanupAndFinalization:
    """Test cleanup and finalization procedures."""

    @pytest.mark.asyncio
    async def test_cleanup_basic(self, test_agent, deep_agent_state):
        """Basic cleanup works correctly."""
        await test_agent.cleanup(deep_agent_state, "test_run")
        test_agent.context.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_agent_run(self, test_agent, deep_agent_state):
        """Complete agent run performs all finalization."""
        test_agent._log_execution_completion = Mock()
        test_agent._send_completion_update = AsyncMock()
        test_agent.cleanup = AsyncMock()
        
        await test_agent._complete_agent_run("test_run", False, "completed", 1.5, deep_agent_state)
        test_agent._log_execution_completion.assert_called_once()
        test_agent.cleanup.assert_called_once()

    def test_build_completion_data(self, test_agent):
        """Completion data is built correctly."""
        data = test_agent._build_completion_data("completed", 1.5)
        assert data["status"] == "completed"
        assert data["execution_time"] == 1.5
        assert "test_agent" in data["message"]

    @pytest.mark.asyncio
    async def test_send_completion_update(self, test_agent):
        """Completion update is sent via WebSocket."""
        test_agent.websocket_manager = Mock()
        test_agent._send_update = AsyncMock()
        
        await test_agent._send_completion_update("test_run", True, "completed", 1.5)
        test_agent._send_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_completion_update_without_streaming(self, test_agent):
        """Completion update is skipped without streaming."""
        test_agent._send_update = AsyncMock()
        
        await test_agent._send_completion_update("test_run", False, "completed", 1.5)
        test_agent._send_update.assert_not_called()

class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_full_successful_lifecycle(self, test_agent, deep_agent_state):
        """Full successful lifecycle works end-to-end."""
        test_agent.websocket_manager = Mock()
        test_agent._send_update = AsyncMock()
        
        await test_agent.run(deep_agent_state, "test_run", True)
        assert_agent_state(test_agent, SubAgentLifecycle.COMPLETED)
        assert deep_agent_state.step_count == 1

    @pytest.mark.asyncio
    async def test_multiple_runs(self, test_agent, deep_agent_state):
        """Multiple runs work correctly."""
        # First run
        await run_agent_successfully(test_agent, deep_agent_state)
        first_count = deep_agent_state.step_count
        
        # Reset agent state
        test_agent.state = SubAgentLifecycle.PENDING
        
        # Second run
        await run_agent_successfully(test_agent, deep_agent_state)
        assert deep_agent_state.step_count == first_count + 1

    @pytest.mark.asyncio
    async def test_run_with_entry_conditions_failure(self, test_agent, deep_agent_state):
        """Run with failed entry conditions handles correctly."""
        setup_agent_for_entry_failure(test_agent)
        
        await test_agent.run(deep_agent_state, "test_run", False)
        assert_agent_state(test_agent, SubAgentLifecycle.FAILED)
        assert deep_agent_state.step_count == 0

    @pytest.mark.asyncio
    async def test_agent_with_custom_user_id(self, deep_agent_state):
        """Agent with custom user ID works correctly."""
        agent = TestAgent()
        agent.user_id = "custom_user"
        user_id = agent._get_websocket_user_id("test_run")
        assert user_id == "custom_user"