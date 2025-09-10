"""
Unit tests for application state machine logic.

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Reliability & User Experience
- Value Impact: Ensures predictable application behavior and state transitions
- Strategic/Revenue Impact: Prevents state corruption that could lose user work or break workflows

The state machine is critical for maintaining application consistency across user sessions,
agent executions, and system operations. Proper state management directly impacts user
trust and system reliability.
"""

import pytest
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockApplicationState:
    """Mock implementation of application state for testing business logic."""
    
    def __init__(self):
        self.current_state = "idle"
        self.previous_state = None
        self.state_history = ["idle"]
        self.state_data = {}
        self.transition_callbacks = {}
        self.valid_transitions = {
            "idle": ["loading", "executing", "error"],
            "loading": ["idle", "executing", "error"],
            "executing": ["idle", "completed", "error"],
            "completed": ["idle", "loading"],
            "error": ["idle", "loading"]
        }
    
    def transition_to(self, new_state, data=None):
        """Transition to new state with validation."""
        if new_state not in self.valid_transitions.get(self.current_state, []):
            raise ValueError(f"Invalid transition from {self.current_state} to {new_state}")
        
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_history.append(new_state)
        
        if data:
            self.state_data.update(data)
        
        # Execute callbacks
        if new_state in self.transition_callbacks:
            for callback in self.transition_callbacks[new_state]:
                callback(self.previous_state, new_state, data)
    
    def get_current_state(self):
        """Get current state."""
        return self.current_state
    
    def get_state_data(self, key=None):
        """Get state data."""
        if key:
            return self.state_data.get(key)
        return self.state_data.copy()
    
    def register_callback(self, state, callback):
        """Register callback for state transition."""
        if state not in self.transition_callbacks:
            self.transition_callbacks[state] = []
        self.transition_callbacks[state].append(callback)
    
    def reset(self):
        """Reset to initial state."""
        self.current_state = "idle"
        self.previous_state = None
        self.state_history = ["idle"]
        self.state_data.clear()


class MockUserStateMachine:
    """Mock implementation of user-specific state machine."""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.app_state = MockApplicationState()
        self.user_context = {}
        self.active_agents = set()
        self.execution_queue = []
    
    def start_agent_execution(self, agent_id, agent_config):
        """Start agent execution with state transition."""
        if self.app_state.current_state != "idle":
            raise ValueError("Cannot start agent execution in current state")
        
        self.app_state.transition_to("executing", {
            "agent_id": agent_id,
            "agent_config": agent_config,
            "execution_start": "2024-01-01T00:00:00Z"
        })
        self.active_agents.add(agent_id)
    
    def complete_agent_execution(self, agent_id, result):
        """Complete agent execution with state transition."""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} not in active execution")
        
        self.app_state.transition_to("completed", {
            "agent_id": agent_id,
            "result": result,
            "execution_end": "2024-01-01T00:01:00Z"
        })
        self.active_agents.remove(agent_id)
    
    def handle_error(self, error_type, error_message):
        """Handle error with state transition."""
        self.app_state.transition_to("error", {
            "error_type": error_type,
            "error_message": error_message,
            "error_time": "2024-01-01T00:00:30Z"
        })
        # Clear active agents on error
        self.active_agents.clear()


@pytest.mark.unit
class TestApplicationStateMachine(SSotBaseTestCase):
    """Test ApplicationStateMachine business logic and state transitions."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.state_machine = MockApplicationState()
        self.record_metric("test_setup", "state_machine_tests", 1)
    
    def teardown_method(self, method):
        """Clean up test environment."""
        super().teardown_method(method)
        self.record_metric("test_cleanup", "state_machine_tests", 1)
    
    def test_initial_state(self):
        """Test state machine starts in correct initial state."""
        # Test business logic: System starts in predictable state
        assert self.state_machine.get_current_state() == "idle"
        assert self.state_machine.previous_state is None
        assert len(self.state_machine.state_history) == 1
        assert self.state_machine.state_history[0] == "idle"
        
        self.record_metric("initial_state_validation", "state_machine", 1)
    
    def test_valid_state_transitions(self):
        """Test valid state transitions work correctly."""
        # Test business logic: Valid workflow transitions
        
        # idle -> loading
        self.state_machine.transition_to("loading")
        assert self.state_machine.get_current_state() == "loading"
        assert self.state_machine.previous_state == "idle"
        
        # loading -> executing
        self.state_machine.transition_to("executing", {"task": "data_analysis"})
        assert self.state_machine.get_current_state() == "executing"
        assert self.state_machine.get_state_data("task") == "data_analysis"
        
        # executing -> completed
        self.state_machine.transition_to("completed")
        assert self.state_machine.get_current_state() == "completed"
        
        # completed -> idle
        self.state_machine.transition_to("idle")
        assert self.state_machine.get_current_state() == "idle"
        
        self.record_metric("valid_transitions", "state_machine", 4)
    
    def test_invalid_state_transitions(self):
        """Test invalid state transitions are rejected."""
        # Test business logic: System prevents invalid workflow states
        
        # Cannot go from idle directly to completed
        with pytest.raises(ValueError, match="Invalid transition from idle to completed"):
            self.state_machine.transition_to("completed")
        
        # Cannot go from completed to executing
        self.state_machine.transition_to("loading")
        self.state_machine.transition_to("executing")
        self.state_machine.transition_to("completed")
        
        with pytest.raises(ValueError, match="Invalid transition from completed to executing"):
            self.state_machine.transition_to("executing")
        
        self.record_metric("invalid_transitions_blocked", "state_machine", 2)
    
    def test_state_data_management(self):
        """Test state data is properly managed."""
        # Test business logic: State context is preserved correctly
        
        # Add data during transition
        self.state_machine.transition_to("loading", {"user_id": "user123", "task_type": "analysis"})
        
        assert self.state_machine.get_state_data("user_id") == "user123"
        assert self.state_machine.get_state_data("task_type") == "analysis"
        
        # Add more data
        self.state_machine.transition_to("executing", {"start_time": "2024-01-01T00:00:00Z"})
        
        # Previous data should be preserved
        assert self.state_machine.get_state_data("user_id") == "user123"
        assert self.state_machine.get_state_data("start_time") == "2024-01-01T00:00:00Z"
        
        # Get all data
        all_data = self.state_machine.get_state_data()
        assert len(all_data) >= 3
        assert "user_id" in all_data
        assert "task_type" in all_data
        assert "start_time" in all_data
        
        self.record_metric("state_data_operations", "state_machine", 6)
    
    def test_state_history_tracking(self):
        """Test state history is properly tracked."""
        # Test business logic: System maintains audit trail of state changes
        
        # Perform several transitions
        self.state_machine.transition_to("loading")
        self.state_machine.transition_to("executing")
        self.state_machine.transition_to("error")
        self.state_machine.transition_to("idle")
        
        expected_history = ["idle", "loading", "executing", "error", "idle"]
        assert self.state_machine.state_history == expected_history
        
        self.record_metric("state_history_entries", "state_machine", len(expected_history))
    
    def test_state_callbacks(self):
        """Test state transition callbacks work correctly."""
        # Test business logic: System can trigger actions on state changes
        
        callback_results = []
        
        def loading_callback(prev_state, new_state, data):
            callback_results.append(f"entered_loading_from_{prev_state}")
        
        def executing_callback(prev_state, new_state, data):
            callback_results.append(f"started_execution_with_{data.get('agent_type', 'unknown')}")
        
        # Register callbacks
        self.state_machine.register_callback("loading", loading_callback)
        self.state_machine.register_callback("executing", executing_callback)
        
        # Trigger transitions
        self.state_machine.transition_to("loading")
        self.state_machine.transition_to("executing", {"agent_type": "data_analyzer"})
        
        assert "entered_loading_from_idle" in callback_results
        assert "started_execution_with_data_analyzer" in callback_results
        
        self.record_metric("state_callbacks_executed", "state_machine", 2)
    
    def test_state_reset(self):
        """Test state machine can be reset to initial state."""
        # Test business logic: System can recover from any state
        
        # Get into complex state
        self.state_machine.transition_to("loading", {"complex": "data"})
        self.state_machine.transition_to("executing")
        self.state_machine.transition_to("error", {"error": "something failed"})
        
        # Reset
        self.state_machine.reset()
        
        # Should be back to initial state
        assert self.state_machine.get_current_state() == "idle"
        assert self.state_machine.previous_state is None
        assert self.state_machine.state_history == ["idle"]
        assert len(self.state_machine.get_state_data()) == 0
        
        self.record_metric("state_reset_operations", "state_machine", 1)


@pytest.mark.unit
class TestUserStateMachine(SSotBaseTestCase):
    """Test UserStateMachine business logic and user isolation."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.user_state = MockUserStateMachine("user123")
        self.record_metric("test_setup", "user_state_machine_tests", 1)
    
    def teardown_method(self, method):
        """Clean up test environment."""
        super().teardown_method(method)
        self.record_metric("test_cleanup", "user_state_machine_tests", 1)
    
    def test_agent_execution_lifecycle(self):
        """Test complete agent execution lifecycle."""
        # Test business logic: Agent execution follows proper state flow
        
        agent_id = "data_analyzer_001"
        agent_config = {"type": "data_analysis", "timeout": 300}
        
        # Start execution
        self.user_state.start_agent_execution(agent_id, agent_config)
        
        assert self.user_state.app_state.get_current_state() == "executing"
        assert agent_id in self.user_state.active_agents
        assert self.user_state.app_state.get_state_data("agent_id") == agent_id
        
        # Complete execution
        result = {"insights": ["insight1", "insight2"], "status": "success"}
        self.user_state.complete_agent_execution(agent_id, result)
        
        assert self.user_state.app_state.get_current_state() == "completed"
        assert agent_id not in self.user_state.active_agents
        assert self.user_state.app_state.get_state_data("result") == result
        
        self.record_metric("agent_execution_cycles", "user_state_machine", 1)
    
    def test_agent_execution_state_validation(self):
        """Test agent execution state validation."""
        # Test business logic: System prevents invalid agent operations
        
        agent_id = "test_agent"
        
        # Start first agent
        self.user_state.start_agent_execution(agent_id, {"type": "test"})
        
        # Cannot start another agent while one is executing
        with pytest.raises(ValueError, match="Cannot start agent execution in current state"):
            self.user_state.start_agent_execution("another_agent", {"type": "test"})
        
        # Cannot complete non-active agent
        with pytest.raises(ValueError, match="Agent non_existent not in active execution"):
            self.user_state.complete_agent_execution("non_existent", {"result": "test"})
        
        self.record_metric("agent_validation_checks", "user_state_machine", 2)
    
    def test_error_handling_clears_state(self):
        """Test error handling properly clears execution state."""
        # Test business logic: Errors don't leave system in inconsistent state
        
        # Start multiple agents (in reality this might be queued)
        agent_id = "test_agent"
        self.user_state.start_agent_execution(agent_id, {"type": "test"})
        
        # Simulate error
        self.user_state.handle_error("execution_timeout", "Agent execution timed out")
        
        assert self.user_state.app_state.get_current_state() == "error"
        assert len(self.user_state.active_agents) == 0  # Cleared on error
        assert self.user_state.app_state.get_state_data("error_type") == "execution_timeout"
        
        self.record_metric("error_recovery_operations", "user_state_machine", 1)
    
    def test_user_isolation(self):
        """Test user state machines are properly isolated."""
        # Test business logic: Multi-user system maintains separate states
        
        user1_state = MockUserStateMachine("user1")
        user2_state = MockUserStateMachine("user2")
        
        # User 1 starts execution
        user1_state.start_agent_execution("agent1", {"type": "analysis"})
        
        # User 2 should still be in idle state
        assert user1_state.app_state.get_current_state() == "executing"
        assert user2_state.app_state.get_current_state() == "idle"
        
        # User 2 can start their own execution
        user2_state.start_agent_execution("agent2", {"type": "processing"})
        
        # Both should be executing independently
        assert user1_state.app_state.get_current_state() == "executing"
        assert user2_state.app_state.get_current_state() == "executing"
        assert user1_state.user_id != user2_state.user_id
        
        self.record_metric("user_isolation_validations", "user_state_machine", 4)
    
    def test_state_persistence_data(self):
        """Test state data can be used for persistence."""
        # Test business logic: State contains data needed for recovery
        
        agent_config = {
            "type": "data_analysis",
            "parameters": {"dataset": "customer_data", "model": "regression"},
            "timeout": 600
        }
        
        self.user_state.start_agent_execution("persistent_agent", agent_config)
        
        # State should contain all necessary data for recovery
        state_data = self.user_state.app_state.get_state_data()
        
        assert "agent_id" in state_data
        assert "agent_config" in state_data
        assert "execution_start" in state_data
        assert state_data["agent_config"]["type"] == "data_analysis"
        assert state_data["agent_config"]["parameters"]["dataset"] == "customer_data"
        
        self.record_metric("state_persistence_fields", "user_state_machine", len(state_data))