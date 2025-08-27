"""Comprehensive tests for AgentLifecycleMixin functionality.

BUSINESS VALUE: Ensures reliable agent execution and proper error handling,
directly protecting customer AI operations and preventing service disruptions
that could impact business-critical agent workflows.

Tests critical paths including lifecycle management, WebSocket integration,
error handling, and state transitions.
"""

import sys
from pathlib import Path

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
        # Mock: Generic component isolation for controlled unit testing
        self.logger = Mock()
        # Mock: WebSocket connection isolation for testing without network overhead
        self.websocket_manager = Mock()
        self.user_id = "test_user"
        self.start_time = time.time()
        self.end_time = None
        self.state = SubAgentLifecycle.PENDING
        # Mock: Generic component isolation for controlled unit testing
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
    # Mock: Agent service isolation for testing without LLM agent execution
    state = Mock(spec=DeepAgentState)
    state.step_count = 0
    return state

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    # Mock: Generic component isolation for controlled unit testing
    manager = Mock()
    # Mock: Generic component isolation for controlled unit testing
    manager.send_agent_log = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
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
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: Generic component isolation for controlled unit testing
        test_agent._send_entry_condition_warning = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_entry_failure("test_run", False, deep_agent_state)
        test_agent._post_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_condition_warning_sent(self, test_agent):
        """Entry condition warning is sent when streaming."""
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: Generic component isolation for controlled unit testing
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_websocket_disconnect(disconnect_error, deep_agent_state, "test_run", True)
        test_agent._post_run.assert_called_once_with(deep_agent_state, "test_run", True, success=False)

    @pytest.mark.asyncio
    async def test_websocket_error_notification(self, test_agent):
        """WebSocket error notification is sent."""
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager.send_agent_log = AsyncMock()
        
        await test_agent._send_websocket_warning("test_run")
        test_agent.websocket_manager.send_agent_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_sent(self, test_agent):
        """WebSocket error is sent correctly."""
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: WebSocket connection isolation for testing without network overhead
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
        # Mock: Generic component isolation for controlled unit testing
        test_agent._send_error_notification = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        test_agent._post_run = AsyncMock()
        
        await test_agent._handle_execution_error(error, deep_agent_state, "test_run", True)
        test_agent._send_error_notification.assert_called_once()
        test_agent._post_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_and_reraise_error(self, test_agent, deep_agent_state):
        """Error is handled and reraised."""
        error = RuntimeError("Test error")
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: WebSocket connection isolation for testing without network overhead
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
        # Mock: Generic component isolation for controlled unit testing
        test_agent._log_execution_completion = Mock()
        # Mock: Generic component isolation for controlled unit testing
        test_agent._send_completion_update = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        test_agent._send_update = AsyncMock()
        
        await test_agent._send_completion_update("test_run", True, "completed", 1.5)
        test_agent._send_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_completion_update_without_streaming(self, test_agent):
        """Completion update is skipped without streaming."""
        # Mock: Generic component isolation for controlled unit testing
        test_agent._send_update = AsyncMock()
        
        await test_agent._send_completion_update("test_run", False, "completed", 1.5)
        test_agent._send_update.assert_not_called()

class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_full_successful_lifecycle(self, test_agent, deep_agent_state):
        """Full successful lifecycle works end-to-end."""
        # Mock: WebSocket connection isolation for testing without network overhead
        test_agent.websocket_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
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


class TestSupervisorAgentCoordination:
    """Test supervisor agent coordination and multi-agent state management."""
    
    class MockSupervisorAgent(AgentLifecycleMixin):
        """Mock supervisor agent for testing coordination patterns."""
        
        def __init__(self, name="supervisor_agent"):
            self.name = name
            self.logger = Mock()
            self.websocket_manager = Mock()
            self.user_id = "test_supervisor_user"
            self.start_time = time.time()
            self.end_time = None
            self.state = SubAgentLifecycle.PENDING
            self.context = Mock()
            
            # Supervisor-specific attributes
            self.supervised_agents = []
            self.coordination_state = "idle"
            self.agent_status_map = {}
            self.task_queue = []
            self.coordination_results = {}
            
        async def execute(self, state, run_id, stream_updates):
            """Supervisor execute implementation."""
            # Simulate supervisor coordination logic
            self.coordination_state = "coordinating"
            
            # Process task queue
            for task in self.task_queue:
                result = await self._process_coordination_task(task)
                self.coordination_results[task["id"]] = result
                
            # Update supervised agent states
            for agent in self.supervised_agents:
                self.agent_status_map[agent["id"]] = agent.get("status", "unknown")
            
            self.coordination_state = "completed"
            
        async def check_entry_conditions(self, state, run_id):
            """Check supervisor entry conditions."""
            # Supervisor needs at least one supervised agent
            return len(self.supervised_agents) > 0
        
        async def _process_coordination_task(self, task):
            """Process a coordination task."""
            await asyncio.sleep(0.01)  # Simulate processing time
            return {
                "task_id": task["id"],
                "status": "completed",
                "result": f"processed_{task['type']}"
            }
        
        def add_supervised_agent(self, agent_info):
            """Add an agent to supervision."""
            self.supervised_agents.append(agent_info)
            
        def add_coordination_task(self, task):
            """Add a coordination task."""
            self.task_queue.append(task)
        
        def set_state(self, state):
            """Set supervisor agent state."""
            self.state = state
        
        def _log_agent_start(self, run_id):
            """Mock log supervisor start."""
            pass
            
        def _log_agent_completion(self, run_id, status):
            """Mock log supervisor completion."""
            pass
            
        async def _send_update(self, run_id, data):
            """Mock send supervisor update."""
            pass
    
    @pytest.fixture
    def supervisor_agent(self):
        """Create supervisor agent instance."""
        return self.MockSupervisorAgent()
    
    @pytest.fixture
    def deep_agent_state(self):
        """Mock DeepAgentState for supervisor testing."""
        state = Mock(spec=DeepAgentState)
        state.step_count = 0
        state.supervisor_context = {
            "active_agents": [],
            "coordination_mode": "sequential",
            "error_handling": "fail_fast"
        }
        return state
    
    @pytest.mark.asyncio
    async def test_supervisor_basic_coordination(self, supervisor_agent, deep_agent_state):
        """Test basic supervisor agent coordination."""
        # Setup supervised agents
        supervisor_agent.add_supervised_agent({
            "id": "agent_1", 
            "type": "data_agent",
            "status": "pending"
        })
        supervisor_agent.add_supervised_agent({
            "id": "agent_2", 
            "type": "analysis_agent",
            "status": "pending"
        })
        
        # Add coordination tasks
        supervisor_agent.add_coordination_task({
            "id": "task_1",
            "type": "data_collection",
            "priority": 1
        })
        supervisor_agent.add_coordination_task({
            "id": "task_2",
            "type": "analysis_prep",
            "priority": 2
        })
        
        # Execute supervisor coordination
        await supervisor_agent.run(deep_agent_state, "supervisor_run_1", stream_updates=False)
        
        # Verify coordination completed
        assert supervisor_agent.state == SubAgentLifecycle.COMPLETED
        assert supervisor_agent.coordination_state == "completed"
        assert len(supervisor_agent.coordination_results) == 2
        
        # Verify tasks were processed
        assert "task_1" in supervisor_agent.coordination_results
        assert "task_2" in supervisor_agent.coordination_results
        assert supervisor_agent.coordination_results["task_1"]["status"] == "completed"
        
        # Verify agent status tracking
        assert len(supervisor_agent.agent_status_map) == 2
        assert "agent_1" in supervisor_agent.agent_status_map
        assert "agent_2" in supervisor_agent.agent_status_map
    
    @pytest.mark.asyncio
    async def test_supervisor_entry_conditions_no_agents(self, supervisor_agent, deep_agent_state):
        """Test supervisor entry conditions fail with no supervised agents."""
        # No agents added - should fail entry conditions
        await supervisor_agent.run(deep_agent_state, "supervisor_run_fail", stream_updates=False)
        
        # Should fail due to entry conditions
        assert supervisor_agent.state == SubAgentLifecycle.FAILED
        assert deep_agent_state.step_count == 0  # No execution happened
    
    @pytest.mark.asyncio
    async def test_supervisor_multi_agent_state_coordination(self, supervisor_agent, deep_agent_state):
        """Test supervisor coordination of multiple agent states."""
        import uuid
        
        # Create mock agent states with different statuses
        agent_states = [
            {"id": str(uuid.uuid4()), "type": "data_agent", "status": "pending", "progress": 0},
            {"id": str(uuid.uuid4()), "type": "analysis_agent", "status": "running", "progress": 50},
            {"id": str(uuid.uuid4()), "type": "output_agent", "status": "completed", "progress": 100},
            {"id": str(uuid.uuid4()), "type": "cleanup_agent", "status": "failed", "progress": 25}
        ]
        
        # Add all agents to supervision
        for agent_state in agent_states:
            supervisor_agent.add_supervised_agent(agent_state)
        
        # Add state management tasks
        coordination_tasks = [
            {"id": "state_sync", "type": "synchronize_states", "priority": 1},
            {"id": "progress_check", "type": "check_progress", "priority": 2},
            {"id": "error_handle", "type": "handle_failures", "priority": 3},
            {"id": "resource_alloc", "type": "allocate_resources", "priority": 4}
        ]
        
        for task in coordination_tasks:
            supervisor_agent.add_coordination_task(task)
        
        # Execute coordination
        await supervisor_agent.run(deep_agent_state, "multi_agent_coord", stream_updates=True)
        
        # Verify all coordination tasks completed
        assert len(supervisor_agent.coordination_results) == 4
        for task_id in ["state_sync", "progress_check", "error_handle", "resource_alloc"]:
            assert task_id in supervisor_agent.coordination_results
            assert supervisor_agent.coordination_results[task_id]["status"] == "completed"
        
        # Verify all agent states are tracked
        assert len(supervisor_agent.agent_status_map) == 4
        for agent_state in agent_states:
            assert agent_state["id"] in supervisor_agent.agent_status_map
            # Status should be tracked (mock returns agent status or 'unknown')
            tracked_status = supervisor_agent.agent_status_map[agent_state["id"]]
            expected_status = agent_state.get("status", "unknown")
            assert tracked_status == expected_status
    
    @pytest.mark.asyncio
    async def test_supervisor_error_recovery_coordination(self, supervisor_agent, deep_agent_state):
        """Test supervisor coordination during error recovery scenarios."""
        
        # Setup agents with error states
        supervisor_agent.add_supervised_agent({
            "id": "failing_agent_1",
            "type": "data_agent", 
            "status": "failed",
            "error": "connection_timeout"
        })
        supervisor_agent.add_supervised_agent({
            "id": "recovering_agent_2",
            "type": "analysis_agent",
            "status": "recovering", 
            "retry_count": 2
        })
        supervisor_agent.add_supervised_agent({
            "id": "healthy_agent_3",
            "type": "output_agent",
            "status": "running"
        })
        
        # Add error recovery coordination tasks
        recovery_tasks = [
            {"id": "assess_failures", "type": "failure_assessment", "priority": 1},
            {"id": "restart_failed", "type": "restart_agents", "priority": 2}, 
            {"id": "rebalance_load", "type": "load_rebalancing", "priority": 3}
        ]
        
        for task in recovery_tasks:
            supervisor_agent.add_coordination_task(task)
        
        # Execute error recovery coordination
        await supervisor_agent.run(deep_agent_state, "error_recovery_coord", stream_updates=True)
        
        # Verify recovery coordination completed
        assert supervisor_agent.state == SubAgentLifecycle.COMPLETED
        assert supervisor_agent.coordination_state == "completed"
        
        # Verify all recovery tasks were processed
        for task in recovery_tasks:
            task_id = task["id"]
            assert task_id in supervisor_agent.coordination_results
            result = supervisor_agent.coordination_results[task_id]
            assert result["status"] == "completed"
            assert "processed_" in result["result"]
        
        # Verify all agents were tracked during recovery
        assert len(supervisor_agent.agent_status_map) == 3
        expected_agents = ["failing_agent_1", "recovering_agent_2", "healthy_agent_3"]
        for agent_id in expected_agents:
            assert agent_id in supervisor_agent.agent_status_map
    
    @pytest.mark.asyncio 
    async def test_supervisor_concurrent_coordination_patterns(self, supervisor_agent, deep_agent_state):
        """Test supervisor handling concurrent coordination patterns."""
        import asyncio
        
        # Setup multiple agent groups for concurrent coordination
        agent_groups = {
            "data_pipeline": [
                {"id": "data_collector_1", "type": "collector", "status": "pending"},
                {"id": "data_collector_2", "type": "collector", "status": "pending"},
                {"id": "data_validator", "type": "validator", "status": "pending"}
            ],
            "analysis_pipeline": [
                {"id": "analyzer_1", "type": "analyzer", "status": "pending"},
                {"id": "analyzer_2", "type": "analyzer", "status": "pending"}
            ],
            "output_pipeline": [
                {"id": "formatter", "type": "formatter", "status": "pending"},
                {"id": "publisher", "type": "publisher", "status": "pending"}
            ]
        }
        
        # Add all agents from all groups
        for group_name, agents in agent_groups.items():
            for agent in agents:
                agent["group"] = group_name
                supervisor_agent.add_supervised_agent(agent)
        
        # Add concurrent coordination tasks
        concurrent_tasks = [
            {"id": "init_data_pipeline", "type": "pipeline_init", "priority": 1, "target": "data_pipeline"},
            {"id": "init_analysis_pipeline", "type": "pipeline_init", "priority": 1, "target": "analysis_pipeline"},
            {"id": "init_output_pipeline", "type": "pipeline_init", "priority": 1, "target": "output_pipeline"},
            {"id": "sync_pipelines", "type": "cross_pipeline_sync", "priority": 2, "target": "all"},
            {"id": "monitor_resources", "type": "resource_monitoring", "priority": 3, "target": "all"}
        ]
        
        for task in concurrent_tasks:
            supervisor_agent.add_coordination_task(task)
        
        # Execute concurrent coordination
        start_time = time.time()
        await supervisor_agent.run(deep_agent_state, "concurrent_coord", stream_updates=True)
        execution_time = time.time() - start_time
        
        # Verify coordination completed efficiently
        assert supervisor_agent.state == SubAgentLifecycle.COMPLETED
        assert execution_time < 1.0  # Should complete quickly due to mocking
        
        # Verify all concurrent tasks were processed
        assert len(supervisor_agent.coordination_results) == 5
        for task in concurrent_tasks:
            task_id = task["id"]
            assert task_id in supervisor_agent.coordination_results
            
        # Verify all agents from all groups are tracked
        total_agents = sum(len(agents) for agents in agent_groups.values())
        assert len(supervisor_agent.agent_status_map) == total_agents
        
        # Verify group-specific coordination
        data_agents = [a for a in supervisor_agent.supervised_agents if a.get("group") == "data_pipeline"]
        analysis_agents = [a for a in supervisor_agent.supervised_agents if a.get("group") == "analysis_pipeline"]
        output_agents = [a for a in supervisor_agent.supervised_agents if a.get("group") == "output_pipeline"]
        
        assert len(data_agents) == 3
        assert len(analysis_agents) == 2  
        assert len(output_agents) == 2
        
        # Verify all agents have been status-tracked
        for group_agents in [data_agents, analysis_agents, output_agents]:
            for agent in group_agents:
                assert agent["id"] in supervisor_agent.agent_status_map