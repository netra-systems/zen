"""Test Modern Supervisor Pattern Compliance.

Comprehensive tests for supervisor pattern implementation.
Business Value: Ensures supervisor reliability and value creation foundation.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.circuit_breaker_integration import (
    SupervisorCircuitBreakerIntegration,
)
from netra_backend.app.agents.supervisor.comprehensive_observability import (
    SupervisorObservability,
)
from netra_backend.app.agents.supervisor.lifecycle_manager import (
    SupervisorLifecycleManager,
)
from netra_backend.app.agents.supervisor.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.core_enums import ExecutionStatus


@pytest.mark.e2e
class TestSupervisorLifecycleManager:
    """Test supervisor lifecycle management."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return SupervisorLifecycleManager()
    
    @pytest.fixture
    def valid_context(self):
        state = DeepAgentState()
        state.user_request = "test request"
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="test_agent",
            state=state,
            user_id="test_user",
            thread_id="test_thread"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validate_entry_conditions_success(self, lifecycle_manager, valid_context):
        """Test successful entry condition validation."""
        result = await lifecycle_manager.validate_entry_conditions(valid_context)
        assert result is True
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validate_entry_conditions_missing_user_request(self, lifecycle_manager):
        """Test entry condition validation with missing user request."""
        state = DeepAgentState()
        # Ensure user_request is truly missing/empty
        state.user_request = None
        context = ExecutionContext(
            run_id="test_run", agent_name="test", state=state,
            user_id="user", thread_id="thread"
        )
        
        with pytest.raises(ValidationError, match="Missing required user_request"):
            await lifecycle_manager.validate_entry_conditions(context)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validate_entry_conditions_missing_user_id(self, lifecycle_manager):
        """Test entry condition validation with missing user_id."""
        state = DeepAgentState()
        state.user_request = "test"
        context = ExecutionContext(
            run_id="test_run", agent_name="test", state=state,
            thread_id="thread"
        )
        
        with pytest.raises(ValidationError, match="Authentication not verified"):
            await lifecycle_manager.validate_entry_conditions(context)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_check_exit_conditions_completed(self, lifecycle_manager, valid_context):
        """Test exit conditions with completed result."""
        result = ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED
        )
        
        should_exit = await lifecycle_manager.check_exit_conditions(valid_context, result)
        assert should_exit is True
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_check_exit_conditions_error_threshold(self, lifecycle_manager, valid_context):
        """Test exit conditions with error threshold exceeded."""
        valid_context.retry_count = 5
        valid_context.max_retries = 3
        
        result = ExecutionResult(
            success=False,
            status=ExecutionStatus.EXECUTING
        )
        
        should_exit = await lifecycle_manager.check_exit_conditions(valid_context, result)
        assert should_exit is True
    
    @pytest.mark.e2e
    def test_register_lifecycle_hook(self, lifecycle_manager):
        """Test lifecycle hook registration."""
        # Mock: Generic component isolation for controlled unit testing
        mock_handler = Mock()
        lifecycle_manager.register_lifecycle_hook("pre_execution", mock_handler)
        
        assert mock_handler in lifecycle_manager._lifecycle_hooks["pre_execution"]
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_execute_lifecycle_hooks(self, lifecycle_manager, valid_context):
        """Test lifecycle hook execution."""
        # Mock: Generic component isolation for controlled unit testing
        mock_handler = AsyncMock()
        lifecycle_manager.register_lifecycle_hook("pre_execution", mock_handler)
        
        await lifecycle_manager.execute_lifecycle_hooks("pre_execution", valid_context)
        
        mock_handler.assert_called_once_with(valid_context)


@pytest.mark.e2e
class TestWorkflowOrchestrator:
    """Test workflow orchestration."""
    
    @pytest.fixture
    def mock_dependencies(self):
        return {
            # Mock: Generic component isolation for controlled unit testing
            "agent_registry": Mock(),
            # Mock: Generic component isolation for controlled unit testing
            "execution_engine": AsyncMock(),
            # Mock: WebSocket connection isolation for testing without network overhead
            "websocket_manager": AsyncMock()
        }
    
    @pytest.fixture
    def orchestrator(self, mock_dependencies):
        return WorkflowOrchestrator(
            mock_dependencies["agent_registry"],
            mock_dependencies["execution_engine"],
            mock_dependencies["websocket_manager"]
        )
    
    @pytest.fixture
    def context(self):
        state = DeepAgentState()
        state.user_request = "test request"
        return ExecutionContext(
            run_id="test_run",
            agent_name="supervisor",
            state=state,
            stream_updates=True,
            user_id="test_user",
            thread_id="test_thread"
        )
    
    @pytest.mark.e2e
    def test_workflow_definition(self, orchestrator):
        """Test workflow definition follows unified spec."""
        definition = orchestrator.get_workflow_definition()
        
        # Verify standard agents are present
        agent_names = [step["agent_name"] for step in definition]
        expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
        
        for agent in expected_agents:
            assert agent in agent_names
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_execute_standard_workflow_success(self, orchestrator, context, mock_dependencies):
        """Test successful workflow execution."""
        # Mock successful agent execution
        mock_result = ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
        mock_dependencies["execution_engine"].execute_agent.return_value = mock_result
        
        results = await orchestrator.execute_standard_workflow(context)
        
        # Verify all steps executed
        assert len(results) == 5  # Standard workflow has 5 steps
        assert all(r.success for r in results)
        
        # Verify WebSocket notifications sent
        mock_dependencies["websocket_manager"].send_agent_update.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_execute_workflow_early_termination(self, orchestrator, context, mock_dependencies):
        """Test workflow early termination on failure."""
        # Mock first step success, second step failure
        success_result = ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
        failure_result = ExecutionResult(success=False, status=ExecutionStatus.FAILED)
        
        mock_dependencies["execution_engine"].execute_agent.side_effect = [
            success_result, failure_result
        ]
        
        results = await orchestrator.execute_standard_workflow(context)
        
        # Should stop after failure
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success


@pytest.mark.e2e
class TestCircuitBreakerIntegration:
    """Test circuit breaker integration."""
    
    @pytest.fixture
    def integration(self):
        return SupervisorCircuitBreakerIntegration()
    
    @pytest.fixture
    def context(self):
        return ExecutionContext(
            run_id="test_run",
            agent_name="test_agent",
            state=DeepAgentState()
        )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_execute_with_circuit_protection_success(self, integration, context):
        """Test successful execution with circuit protection."""
        async def mock_execute():
            return ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
        
        result = await integration.execute_with_circuit_protection(context, mock_execute)
        
        assert result.success
    
    @pytest.mark.e2e
    def test_get_circuit_breaker_status(self, integration):
        """Test circuit breaker status retrieval."""
        status = integration.get_circuit_breaker_status()
        
        assert "supervisor" in status
        assert "agents" in status
        assert "overall_health" in status["supervisor"]
    
    @pytest.mark.e2e
    def test_get_health_summary(self, integration):
        """Test health summary retrieval."""
        summary = integration.get_health_summary()
        
        assert "overall_healthy" in summary
        assert "supervisor_health" in summary
        assert "agent_health" in summary
        assert "total_agents_monitored" in summary


@pytest.mark.e2e
class TestSupervisorObservability:
    """Test supervisor observability."""
    
    @pytest.fixture
    def observability(self):
        return SupervisorObservability()
    
    @pytest.fixture
    def context(self):
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="supervisor",
            state=DeepAgentState(),
            user_id="test_user",
            thread_id="test_thread"
        )
    
    @pytest.mark.e2e
    def test_start_workflow_trace(self, observability, context):
        """Test workflow trace initialization."""
        observability.start_workflow_trace(context)
        
        assert context.run_id in observability._traces
        trace = observability._traces[context.run_id]
        assert trace["trace_id"] == context.run_id
        assert trace["agent_name"] == context.agent_name
        assert trace["status"] == "started"
    
    @pytest.mark.e2e
    def test_add_span(self, observability, context):
        """Test adding span to trace."""
        observability.start_workflow_trace(context)
        
        observability.add_span(
            context.run_id, "test_span", 100.0, {"agent_name": "test"}
        )
        
        trace = observability._traces[context.run_id]
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["span_name"] == "test_span"
        assert trace["spans"][0]["duration_ms"] == 100.0
    
    @pytest.mark.e2e
    def test_complete_workflow_trace(self, observability, context):
        """Test workflow trace completion."""
        observability.start_workflow_trace(context)
        
        result = ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
        observability.complete_workflow_trace(context, result)
        
        # Trace should be cleaned up
        assert context.run_id not in observability._traces
        
        # Metrics should be updated
        metrics = observability.get_metrics_snapshot()
        assert metrics["metrics"]["total_workflows"] == 1
        assert metrics["metrics"]["successful_workflows"] == 1
    
    @pytest.mark.e2e
    def test_record_agent_error(self, observability):
        """Test agent error recording."""
        observability.record_agent_error("test_agent", "test error")
        
        metrics = observability.get_metrics_snapshot()
        assert "test_agent" in metrics["metrics"]["error_counts_by_agent"]
        assert metrics["metrics"]["error_counts_by_agent"]["test_agent"] == 1
    
    @pytest.mark.e2e
    def test_get_metrics_snapshot(self, observability):
        """Test metrics snapshot retrieval."""
        snapshot = observability.get_metrics_snapshot()
        
        assert "timestamp" in snapshot
        assert "metrics" in snapshot
        assert "active_traces" in snapshot
        assert "performance_percentiles" in snapshot


@pytest.mark.e2e
class TestSupervisorAgent:
    """Test modern supervisor agent integration."""
    
    @pytest.fixture
    def mock_dependencies(self):
        return {
            # Mock: Session isolation for controlled testing without external state
            "db_session": AsyncMock(),
            # Mock: LLM provider isolation to prevent external API usage and costs
            "llm_manager": Mock(),
            # Mock: WebSocket connection isolation for testing without network overhead
            "websocket_manager": AsyncMock(),
            # Mock: Tool execution isolation for predictable agent testing
            "tool_dispatcher": Mock()
        }
    
    @pytest.fixture
    def supervisor(self, mock_dependencies):
        return SupervisorAgent(
            mock_dependencies["db_session"],
            mock_dependencies["llm_manager"],
            mock_dependencies["websocket_manager"],
            mock_dependencies["tool_dispatcher"]
        )
    
    @pytest.fixture
    def valid_state(self):
        state = DeepAgentState()
        state.user_request = "Optimize my AI costs"
        state.user_id = "test_user"
        state.chat_thread_id = "test_thread"
        return state
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validate_preconditions_success(self, supervisor, valid_state):
        """Test successful precondition validation."""
        context = ExecutionContext(
            run_id="test", agent_name="supervisor", state=valid_state,
            user_id="test_user", thread_id="test_thread"
        )
        
        result = await supervisor.validate_preconditions(context)
        assert result is True
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_execute_core_logic(self, supervisor, valid_state):
        """Test core logic execution."""
        context = ExecutionContext(
            run_id="test", agent_name="supervisor", state=valid_state,
            user_id="test_user", thread_id="test_thread"
        )
        
        # Mock workflow execution
        with patch.object(supervisor.workflow_orchestrator, 'execute_standard_workflow') as mock_workflow:
            mock_result = ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
            mock_workflow.return_value = [mock_result]
            
            result = await supervisor.execute_core_logic(context)
            
            assert "supervisor_result" in result
            assert "workflow_results" in result
            assert "total_steps" in result
    
    @pytest.mark.e2e
    def test_get_health_status(self, supervisor):
        """Test health status retrieval."""
        health = supervisor.get_health_status()
        
        assert "supervisor_health" in health
        assert "observability_metrics" in health
        assert "active_contexts" in health
        assert "registered_agents" in health
        assert "workflow_definition" in health
    
    @pytest.mark.e2e
    def test_get_performance_metrics(self, supervisor):
        """Test performance metrics retrieval."""
        metrics = supervisor.get_performance_metrics()
        
        assert "timestamp" in metrics
        assert "metrics" in metrics
    
    @pytest.mark.e2e
    def test_get_circuit_breaker_status(self, supervisor):
        """Test circuit breaker status retrieval."""
        status = supervisor.get_circuit_breaker_status()
        
        assert "supervisor" in status
        assert "agents" in status
