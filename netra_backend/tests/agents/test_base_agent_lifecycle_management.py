"""
Base Agent Lifecycle Management Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Agent System Reliability & State Management
Tests agent lifecycle state transitions, reset patterns, shutdown procedures, and
circuit breaker integration that ensures production stability.

SSOT Compliance: Uses SSotAsyncTestCase, tests real state transitions,
follows BaseAgent architecture patterns per CLAUDE.md standards.

Coverage Target: BaseAgent lifecycle methods, state management, reset patterns
Current BaseAgent Lifecycle Coverage: ~2% -> Target: 15%+

Critical Patterns Tested:
- State transition validation (PENDING -> RUNNING -> COMPLETED/FAILED)
- Agent reset and cleanup procedures
- Circuit breaker integration and recovery
- Resource management and memory cleanup
- Graceful shutdown patterns
- Error state recovery

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, Any, Optional, List

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.monitoring import ExecutionMonitor


class LifecycleTestAgent(BaseAgent):
    """Agent implementation for testing lifecycle management patterns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "lifecycle_test_agent"
        self.execution_history = []
        self.state_transitions = []

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Implementation that tracks execution and state changes."""
        # Track execution
        self.execution_history.append({
            "user_id": context.user_id,
            "run_id": context.run_id,
            "timestamp": time.time(),
            "initial_state": self.state
        })

        # Transition to running
        self.set_state(SubAgentLifecycle.RUNNING)
        self.state_transitions.append(("RUNNING", time.time()))

        # Simulate some processing time
        await asyncio.sleep(0.01)

        # Simulate completion
        self.set_state(SubAgentLifecycle.COMPLETED)
        self.state_transitions.append(("COMPLETED", time.time()))

        return {
            "status": "success",
            "result": "lifecycle test completed",
            "agent_type": self.agent_type,
            "final_state": self.state.value
        }

    def get_state_history(self) -> List[tuple]:
        """Get history of state transitions for testing."""
        return self.state_transitions.copy()


class FailingLifecycleAgent(BaseAgent):
    """Agent that simulates failures for testing error recovery."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "failing_lifecycle_agent"
        self.failure_count = 0

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Implementation that fails on first attempt, succeeds on retry."""
        self.failure_count += 1

        if self.failure_count == 1:
            self.set_state(SubAgentLifecycle.FAILED)
            raise RuntimeError("Simulated agent execution failure")

        # Succeed on retry
        self.set_state(SubAgentLifecycle.RUNNING)
        await asyncio.sleep(0.01)
        self.set_state(SubAgentLifecycle.COMPLETED)

        return {
            "status": "success",
            "result": "recovered after failure",
            "failure_count": self.failure_count
        }


class BaseAgentLifecycleManagementTests(SSotAsyncTestCase):
    """Test BaseAgent lifecycle management and state transitions."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()

        # Create test context
        self.test_context = UserExecutionContext(
            user_id="lifecycle-test-user-001",
            thread_id="lifecycle-test-thread-001",
            run_id="lifecycle-test-run-001",
            agent_context={
                "user_request": "lifecycle management test"
            }
        ).with_db_session(AsyncMock())

    def test_agent_initial_state_is_pending(self):
        """Test agent starts in PENDING state."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)

        # Verify: Initial state is PENDING
        assert agent.get_state() == SubAgentLifecycle.PENDING
        assert agent.state == SubAgentLifecycle.PENDING

    def test_agent_state_transitions_validation(self):
        """Test valid state transitions are allowed and invalid ones are rejected."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)

        # Test: Valid transitions from PENDING
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.get_state() == SubAgentLifecycle.RUNNING

        # Test: Valid transitions from RUNNING
        agent.set_state(SubAgentLifecycle.COMPLETED)
        assert agent.get_state() == SubAgentLifecycle.COMPLETED

        # Test: Invalid transition from COMPLETED to RUNNING should raise error
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.RUNNING)

    def test_agent_state_transitions_all_valid_paths(self):
        """Test all valid state transition paths."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)

        # Path 1: PENDING -> RUNNING -> COMPLETED -> SHUTDOWN
        assert agent.get_state() == SubAgentLifecycle.PENDING
        agent.set_state(SubAgentLifecycle.RUNNING)
        agent.set_state(SubAgentLifecycle.COMPLETED)
        agent.set_state(SubAgentLifecycle.SHUTDOWN)

        # Reset for next path
        agent.state = SubAgentLifecycle.PENDING

        # Path 2: PENDING -> FAILED -> RUNNING -> COMPLETED
        agent.set_state(SubAgentLifecycle.FAILED)
        agent.set_state(SubAgentLifecycle.RUNNING)  # Retry from failed
        agent.set_state(SubAgentLifecycle.COMPLETED)

        # Path 3: Test shutdown from any state
        agent.state = SubAgentLifecycle.RUNNING
        agent.set_state(SubAgentLifecycle.SHUTDOWN)

    async def test_agent_lifecycle_execution_flow(self):
        """Test complete agent execution flow with proper state transitions."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-test-001")

        # Verify: Initial state
        assert agent.get_state() == SubAgentLifecycle.PENDING

        # Execute agent
        result = await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: Final state is COMPLETED
        assert agent.get_state() == SubAgentLifecycle.COMPLETED
        assert result["final_state"] == "completed"  # Enum value is lowercase

        # Verify: State transition history
        state_history = agent.get_state_history()
        assert len(state_history) == 2
        assert state_history[0][0] == "RUNNING"
        assert state_history[1][0] == "COMPLETED"

        # Verify: Execution was recorded
        assert len(agent.execution_history) == 1
        assert agent.execution_history[0]["user_id"] == "lifecycle-test-user-001"

    async def test_agent_reset_state_comprehensive(self):
        """Test agent reset_state method clears all state properly."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-reset-001")

        # Execute to build up state
        await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: State was built up
        assert agent.get_state() == SubAgentLifecycle.COMPLETED
        assert len(agent.execution_history) > 0
        assert len(agent.get_state_history()) > 0

        # Add some additional context
        agent.context["test_data"] = "should_be_cleared"

        # Reset state
        await agent.reset_state()

        # Verify: State was reset to PENDING
        assert agent.get_state() == SubAgentLifecycle.PENDING

        # Verify: Context was cleared
        assert "test_data" not in agent.context

        # Verify: Start/end times were reset
        assert agent.start_time is None
        assert agent.end_time is None

    async def test_agent_reset_state_circuit_breaker_integration(self):
        """Test agent reset properly handles circuit breaker state."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-circuit-001")

        # Verify: Circuit breaker exists
        assert agent.circuit_breaker is not None

        # Get initial circuit breaker status
        initial_status = agent.circuit_breaker.get_status()

        # Reset agent state
        await agent.reset_state()

        # Verify: Circuit breaker status after reset
        post_reset_status = agent.circuit_breaker.get_status()

        # Circuit breaker should still exist and be functional
        assert agent.circuit_breaker is not None
        assert post_reset_status is not None

    async def test_agent_shutdown_graceful(self):
        """Test agent graceful shutdown procedure."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-shutdown-001")

        # Build up some state
        agent.context["temp_data"] = "test_value"
        agent.set_state(SubAgentLifecycle.RUNNING)

        # Shutdown agent
        await agent.shutdown()

        # Verify: State is SHUTDOWN
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN

        # Verify: Context was cleared
        assert len(agent.context) == 0

    async def test_agent_shutdown_idempotent(self):
        """Test agent shutdown is idempotent (can be called multiple times)."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-shutdown-idempotent-001")

        # First shutdown
        await agent.shutdown()
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN

        # Second shutdown should not raise error
        await agent.shutdown()
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN

        # Third shutdown should also be safe
        await agent.shutdown()
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN

    async def test_agent_error_state_recovery(self):
        """Test agent can recover from error states."""
        agent = FailingLifecycleAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-error-recovery-001")

        # First execution should fail
        with pytest.raises(RuntimeError, match="Simulated agent execution failure"):
            await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: Agent is in FAILED state
        assert agent.get_state() == SubAgentLifecycle.FAILED

        # Reset from failed state
        agent.set_state(SubAgentLifecycle.PENDING)

        # Second execution should succeed
        result = await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: Recovery successful
        assert result["status"] == "success"
        assert result["failure_count"] == 2
        assert agent.get_state() == SubAgentLifecycle.COMPLETED

    def test_agent_health_status_comprehensive(self):
        """Test agent health status reporting includes lifecycle information."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-health-001")

        # Get health status
        health = agent.get_health_status()

        # Verify: Health status includes lifecycle information
        assert "agent_name" in health
        assert "state" in health
        assert health["state"] == SubAgentLifecycle.PENDING.value

        # Verify: Health status includes infrastructure components
        assert "circuit_breaker" in health or "circuit_breaker_state" in health
        assert "overall_status" in health or "status" in health

        # Change state and verify health reflects it
        agent.set_state(SubAgentLifecycle.RUNNING)
        health_running = agent.get_health_status()
        assert health_running["state"] == SubAgentLifecycle.RUNNING.value

    def test_agent_circuit_breaker_status(self):
        """Test agent circuit breaker status reporting."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-circuit-status-001")

        # Get circuit breaker status
        cb_status = agent.get_circuit_breaker_status()

        # Verify: Circuit breaker status is available
        assert isinstance(cb_status, dict)
        assert "state" in cb_status or "status" in cb_status

        # Should indicate healthy/closed state initially
        if "state" in cb_status:
            assert cb_status["state"] in ["closed", "CLOSED", "healthy"]
        elif "status" in cb_status:
            assert cb_status["status"] in ["closed", "CLOSED", "healthy", "not_available"]

    async def test_agent_timing_collector_lifecycle(self):
        """Test timing collector is properly managed during lifecycle."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-timing-001")

        # Verify: Timing collector exists
        assert hasattr(agent, 'timing_collector')
        assert agent.timing_collector is not None

        # Execute agent to generate timing data
        await agent.execute_with_context(self.test_context, stream_updates=False)

        # Reset state which should handle timing collector
        await agent.reset_state()

        # Verify: Timing collector still exists after reset
        assert agent.timing_collector is not None

    async def test_agent_memory_isolation_after_reset(self):
        """Test agent memory isolation is maintained after reset."""
        agent1 = LifecycleTestAgent(llm_manager=self.llm_manager, name="Agent1")
        agent2 = LifecycleTestAgent(llm_manager=self.llm_manager, name="Agent2")

        agent1.set_websocket_bridge(self.websocket_bridge, "lifecycle-memory-1")
        agent2.set_websocket_bridge(self.websocket_bridge, "lifecycle-memory-2")

        # Add distinct data to each agent
        agent1.context["agent1_data"] = "unique_value_1"
        agent2.context["agent2_data"] = "unique_value_2"

        # Reset only agent1
        await agent1.reset_state()

        # Verify: Agent1 data was cleared, Agent2 data preserved
        assert "agent1_data" not in agent1.context
        assert agent2.context["agent2_data"] == "unique_value_2"

        # Verify: Agents remain isolated
        assert agent1 is not agent2
        assert agent1.timing_collector is not agent2.timing_collector

    async def test_agent_reliability_manager_lifecycle(self):
        """Test reliability manager integration during lifecycle operations."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-reliability-001")

        # Verify: Reliability manager exists
        reliability_manager = agent.reliability_manager
        assert reliability_manager is not None
        assert isinstance(reliability_manager, ReliabilityManager)

        # Execute agent
        result = await agent.execute_with_context(self.test_context, stream_updates=False)
        assert result["status"] == "success"

        # Reset and verify reliability manager still functional
        await agent.reset_state()
        reliability_manager_after_reset = agent.reliability_manager
        assert reliability_manager_after_reset is not None

        # Should be same instance (not recreated)
        assert reliability_manager_after_reset is reliability_manager

    async def test_agent_execution_monitor_lifecycle(self):
        """Test execution monitor integration during lifecycle operations."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-monitor-001")

        # Verify: Execution monitor exists
        monitor = agent.execution_monitor
        assert monitor is not None
        assert isinstance(monitor, ExecutionMonitor)

        # Execute agent to generate monitoring data
        await agent.execute_with_context(self.test_context, stream_updates=False)

        # Reset and verify monitor state
        await agent.reset_state()
        monitor_after_reset = agent.execution_monitor
        assert monitor_after_reset is not None

        # Monitor should still be functional
        health = monitor_after_reset.get_health_status()
        assert isinstance(health, dict)

    def test_agent_legacy_compatibility_methods(self):
        """Test agent maintains backward compatibility for lifecycle methods."""
        agent = LifecycleTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "lifecycle-legacy-001")

        # Test: cleanup method exists for Golden Path compatibility
        assert hasattr(agent, 'cleanup')
        assert callable(agent.cleanup)

        # Test: WebSocket test mode method exists
        assert hasattr(agent, 'enable_websocket_test_mode')
        assert callable(agent.enable_websocket_test_mode)

        # Test: Health status methods
        assert hasattr(agent, 'get_health_status')
        assert hasattr(agent, 'get_circuit_breaker_status')