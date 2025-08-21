"""Integration tests for supervisor observability.

Tests end-to-end flow logging during supervisor execution with inter-agent communication.
Each test must be concise and focused as per architecture requirements.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.supervisor.flow_logger import SupervisorPipelineLogger, FlowState, TodoState
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (

# Add project root to path
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.agents.state import DeepAgentState


class MockAgent:
    """Mock agent for testing supervisor interactions."""
    
    def __init__(self, name: str, success: bool = True):
        self.name = name
        self.success = success
        self.execution_count = 0

    async def execute(self, context: AgentExecutionContext, state: DeepAgentState) -> AgentExecutionResult:
        """Mock agent execution."""
        self.execution_count += 1
        await asyncio.sleep(0.1)  # Simulate work
        return AgentExecutionResult(
            success=self.success,
            state=state,
            duration=0.1
        )


class MockAgentRegistry:
    """Mock agent registry for testing."""
    
    def __init__(self):
        self.agents: Dict[str, MockAgent] = {}

    def register_agent(self, name: str, agent: MockAgent) -> None:
        """Register a mock agent."""
        self.agents[name] = agent

    def get_agent(self, name: str) -> MockAgent:
        """Get a registered agent."""
        return self.agents.get(name)


class TestSupervisorObservabilityIntegration:
    """Integration tests for supervisor observability features."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return MagicMock()

    @pytest.fixture
    def mock_registry(self):
        """Create mock agent registry with test agents."""
        registry = MockAgentRegistry()
        registry.register_agent("agent1", MockAgent("agent1", True))
        registry.register_agent("agent2", MockAgent("agent2", True))
        registry.register_agent("failing_agent", MockAgent("failing_agent", False))
        return registry

    @pytest.fixture
    def execution_context(self):
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test-run-123",
            thread_id="test-thread-456",
            user_id="test-user-789",
            agent_name="test_agent"
        )

    @pytest.fixture
    def test_state(self):
        """Create test agent state."""
        return DeepAgentState(user_request="Test request")

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_end_to_end_flow_logging(self, mock_logger, mock_registry, mock_websocket_manager):
        """Test complete flow logging during supervisor execution."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Simulate complete supervisor flow
        steps = ["agent1", "agent2"]
        flow_logger.log_flow_start("test_pipeline", steps)
        
        for i, step in enumerate(steps, 1):
            flow_logger.log_agent_start(step, i)
            flow_logger.log_agent_completion(step, True, 0.5)
        
        flow_logger.log_flow_completion(True, len(steps), 0)
        
        # Verify all flow stages were logged
        assert mock_logger.info.call_count >= 5  # start + 2*(agent_start+completion) + completion

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_inter_agent_communication_logging(self, mock_logger, mock_registry):
        """Test inter-agent communication is properly logged."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Test different types of inter-agent communication
        flow_logger.log_inter_agent_communication("agent1", "agent2", "data_handoff")
        flow_logger.log_inter_agent_communication("agent2", "agent1", "status_update")
        flow_logger.log_inter_agent_communication("supervisor", "agent1", "task_assignment")
        
        # Verify communication events were logged
        assert mock_logger.info.call_count == 3
        for call in mock_logger.info.call_args_list:
            call_data = call[0][0]
            assert "supervisor_inter_agent_comm" in call_data

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_pipeline_execution_logging_with_metrics(self, mock_logger):
        """Test pipeline execution logging with performance metrics."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Log various pipeline steps with different metrics
        test_cases = [
            ("data_preprocessing", "success", {"duration": 1.2, "records_processed": 1000}),
            ("llm_processing", "success", {"duration": 5.7, "tokens_used": 2500}),
            ("result_validation", "failed", {"duration": 0.3, "validation_errors": 2})
        ]
        
        for step_name, status, metrics in test_cases:
            flow_logger.log_pipeline_execution(step_name, status, metrics)
        
        # Verify all pipeline steps were logged with metrics
        assert mock_logger.info.call_count == 3

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_todo_lifecycle_during_execution(self, mock_logger):
        """Test TODO lifecycle management during supervisor execution."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Create multiple TODOs and track their lifecycle
        todos = [
            ("todo1", "Initialize data pipeline", "agent1"),
            ("todo2", "Process user request", "agent2"),
            ("todo3", "Generate response", "agent1")
        ]
        
        # Create all TODOs
        for todo_id, description, agent in todos:
            flow_logger.create_todo(todo_id, description, agent)
        
        # Progress through lifecycle
        flow_logger.update_todo_state("todo1", TodoState.IN_PROGRESS)
        flow_logger.update_todo_state("todo1", TodoState.COMPLETED)
        flow_logger.update_todo_state("todo2", TodoState.IN_PROGRESS)
        flow_logger.update_todo_state("todo3", TodoState.FAILED)
        
        # Verify TODO lifecycle was properly logged
        assert mock_logger.info.call_count >= 7  # 3 creates + 4 state changes

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_observability_with_agent_failures(self, mock_logger, mock_registry):
        """Test observability logging handles agent failures gracefully."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Simulate pipeline with failing agent
        steps = ["agent1", "failing_agent", "agent2"]
        flow_logger.log_flow_start("test_pipeline", steps)
        
        # Log successful agent
        flow_logger.log_agent_start("agent1", 1)
        flow_logger.log_agent_completion("agent1", True, 0.5)
        
        # Log failing agent
        flow_logger.log_agent_start("failing_agent", 2)
        flow_logger.log_agent_completion("failing_agent", False, 0.2)
        
        # Log final completion with failure
        flow_logger.log_flow_completion(False, 3, 1)
        
        # Verify failure scenarios are properly logged
        logged_data = []
        for call in mock_logger.info.call_args_list:
            call_data = call[0][0]
            json_part = call_data.split("SupervisorFlow: ")[1]
            logged_data.append(json.loads(json_part))
        
        # Find completion log and verify failure tracking
        completion_log = next(log for log in logged_data if log["type"] == "supervisor_flow_completion")
        assert completion_log["success"] is False
        assert completion_log["failed_steps"] == 1

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_correlation_tracking_across_agents(self, mock_logger):
        """Test correlation ID tracking across multiple agent executions."""
        correlation_id = "correlation-abc-123"
        flow_logger = SupervisorPipelineLogger(correlation_id, "run-456")
        
        # Simulate multiple agent interactions
        agents = ["agent1", "agent2", "agent3"]
        flow_logger.log_flow_start("multi_agent_pipeline", agents)
        
        for i, agent in enumerate(agents, 1):
            flow_logger.log_agent_start(agent, i)
            flow_logger.log_inter_agent_communication("supervisor", agent, "task_dispatch")
            flow_logger.log_agent_completion(agent, True, 1.0)
        
        # Verify all logs contain the same correlation ID
        for call in mock_logger.info.call_args_list:
            call_data = call[0][0]
            assert correlation_id in call_data

    @patch('app.agents.supervisor.flow_logger.logger')
    async def test_performance_metrics_collection(self, mock_logger):
        """Test collection and logging of performance metrics."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Log performance metrics for different scenarios
        performance_scenarios = [
            ("fast_execution", "success", {"duration": 0.5, "cpu_usage": 15.2}),
            ("slow_execution", "success", {"duration": 10.8, "cpu_usage": 85.7}),
            ("memory_intensive", "success", {"duration": 3.2, "memory_mb": 512}),
            ("high_throughput", "success", {"duration": 2.1, "items_processed": 5000})
        ]
        
        for scenario, status, metrics in performance_scenarios:
            flow_logger.log_pipeline_execution(scenario, status, metrics)
        
        # Verify performance data is captured in logs
        assert mock_logger.info.call_count == 4

    async def test_flow_state_progression_validation(self):
        """Test that flow state progresses correctly through execution phases."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Verify initial state
        assert flow_logger.flow_state == FlowState.PENDING
        
        # Test state progression
        flow_logger.log_flow_start("test_pipeline", ["agent1"])
        assert flow_logger.flow_state == FlowState.STARTED
        
        flow_logger.log_agent_start("agent1", 1)
        assert flow_logger.flow_state == FlowState.AGENT_EXECUTING
        
        flow_logger.log_agent_completion("agent1", True, 1.0)
        assert flow_logger.flow_state == FlowState.AGENT_COMPLETED
        
        flow_logger.log_flow_completion(True, 1, 0)
        assert flow_logger.flow_state == FlowState.COMPLETED

    async def test_summary_generation_accuracy(self):
        """Test that flow summaries contain accurate execution data."""
        flow_logger = SupervisorPipelineLogger("correlation-123", "run-456")
        
        # Create some activity
        flow_logger.create_todo("todo1", "Test task", "agent1")
        flow_logger.create_todo("todo2", "Another task", "agent2")
        flow_logger.log_flow_start("test_pipeline", ["agent1"])
        
        summary = flow_logger.get_flow_summary()
        
        # Verify summary accuracy
        assert summary["correlation_id"] == "correlation-123"
        assert summary["run_id"] == "run-456"
        assert summary["todo_count"] == 2
        assert summary["current_state"] == FlowState.STARTED.value
        assert "duration_seconds" in summary