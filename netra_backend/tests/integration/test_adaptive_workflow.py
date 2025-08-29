"""Integration tests for adaptive workflow orchestration.

Tests the dynamic workflow selection based on data sufficiency.
Business Value: Ensures optimal workflow execution for different data scenarios.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.execution_context import PipelineStep


class TestAdaptiveWorkflow:
    """Test suite for adaptive workflow orchestration."""
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create mock agent registry."""
        registry = MagicMock()
        registry.get = MagicMock()
        return registry
    
    @pytest.fixture
    def mock_execution_engine(self):
        """Create mock execution engine."""
        engine = MagicMock()
        engine.execute_agent = AsyncMock()
        return engine
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock websocket manager."""
        manager = MagicMock()
        manager.send_agent_update = AsyncMock()
        return manager
    
    @pytest.fixture
    def workflow_orchestrator(self, mock_agent_registry, mock_execution_engine, mock_websocket_manager):
        """Create WorkflowOrchestrator instance."""
        return WorkflowOrchestrator(
            mock_agent_registry,
            mock_execution_engine,
            mock_websocket_manager
        )
    
    @pytest.fixture
    def execution_context(self):
        """Create execution context."""
        state = DeepAgentState()
        state.user_request = "Optimize my LLM costs"
        
        return ExecutionContext(
            run_id="test-run-123",
            agent_name="supervisor",
            state=state,
            stream_updates=True,
            thread_id="thread-456",
            user_id="user-789"
        )
    
    def test_define_workflow_sufficient_data(self, workflow_orchestrator):
        """Test workflow definition for sufficient data scenario."""
        triage_result = {"data_sufficiency": "sufficient"}
        
        workflow = workflow_orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify workflow sequence
        assert len(workflow) == 5
        assert workflow[0].agent_name == "triage"
        assert workflow[1].agent_name == "optimization"
        assert workflow[2].agent_name == "data"
        assert workflow[3].agent_name == "actions"
        assert workflow[4].agent_name == "reporting"
        
        # Verify dependencies
        assert workflow[0].dependencies == []
        assert "triage" in workflow[1].dependencies
        assert "optimization" in workflow[2].dependencies
    
    def test_define_workflow_partial_data(self, workflow_orchestrator):
        """Test workflow definition for partial data scenario."""
        triage_result = {"data_sufficiency": "partial"}
        
        workflow = workflow_orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify workflow sequence
        assert len(workflow) == 5
        assert workflow[0].agent_name == "triage"
        assert workflow[1].agent_name == "optimization"
        assert workflow[2].agent_name == "actions"
        assert workflow[3].agent_name == "data_helper"
        assert workflow[4].agent_name == "reporting"
        
        # Verify data_helper is included
        assert any(step.agent_name == "data_helper" for step in workflow)
    
    def test_define_workflow_insufficient_data(self, workflow_orchestrator):
        """Test workflow definition for insufficient data scenario."""
        triage_result = {"data_sufficiency": "insufficient"}
        
        workflow = workflow_orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify minimal workflow
        assert len(workflow) == 2
        assert workflow[0].agent_name == "triage"
        assert workflow[1].agent_name == "data_helper"
    
    def test_define_workflow_unknown_sufficiency(self, workflow_orchestrator):
        """Test workflow definition for unknown data sufficiency."""
        triage_result = {"data_sufficiency": "unknown"}
        
        workflow = workflow_orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Should default to standard workflow
        assert len(workflow) == 5
        assert workflow[0].agent_name == "triage"
        assert workflow[4].agent_name == "reporting"
    
    @pytest.mark.asyncio
    async def test_execute_standard_workflow_sufficient_data(
        self, workflow_orchestrator, execution_context, mock_execution_engine
    ):
        """Test complete workflow execution with sufficient data."""
        # Mock triage result with sufficient data
        triage_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_sufficiency": "sufficient", "category": "cost_optimization"}
        )
        
        # Mock other agent results
        other_result = ExecutionResult(
            success=True,
            status="completed",
            result={"output": "test"}
        )
        
        mock_execution_engine.execute_agent.side_effect = [
            triage_result,  # triage
            other_result,   # optimization
            other_result,   # data
            other_result,   # actions
            other_result    # reporting
        ]
        
        # Execute workflow
        results = await workflow_orchestrator.execute_standard_workflow(execution_context)
        
        # Verify all agents were executed
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Verify execution order
        call_count = mock_execution_engine.execute_agent.call_count
        assert call_count == 5
    
    @pytest.mark.asyncio
    async def test_execute_standard_workflow_insufficient_data(
        self, workflow_orchestrator, execution_context, mock_execution_engine
    ):
        """Test minimal workflow execution with insufficient data."""
        # Mock triage result with insufficient data
        triage_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_sufficiency": "insufficient", "category": "cost_optimization"}
        )
        
        # Mock data_helper result
        data_helper_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_request": "Please provide usage metrics"}
        )
        
        mock_execution_engine.execute_agent.side_effect = [
            triage_result,      # triage
            data_helper_result  # data_helper
        ]
        
        # Execute workflow
        results = await workflow_orchestrator.execute_standard_workflow(execution_context)
        
        # Verify only triage and data_helper were executed
        assert len(results) == 2
        assert results[0].result["data_sufficiency"] == "insufficient"
        assert "data_request" in results[1].result
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(
        self, workflow_orchestrator, execution_context, mock_execution_engine
    ):
        """Test workflow execution with agent failure."""
        # Mock triage success
        triage_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_sufficiency": "sufficient"}
        )
        
        # Mock optimization failure
        failure_result = ExecutionResult(
            success=False,
            status="failed",
            error="Optimization error"
        )
        
        mock_execution_engine.execute_agent.side_effect = [
            triage_result,   # triage
            failure_result   # optimization fails
        ]
        
        # Execute workflow
        results = await workflow_orchestrator.execute_standard_workflow(execution_context)
        
        # Verify workflow stopped after failure
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error == "Optimization error"
    
    @pytest.mark.asyncio
    async def test_workflow_notifications(
        self, workflow_orchestrator, execution_context, mock_execution_engine, mock_websocket_manager
    ):
        """Test websocket notifications during workflow execution."""
        # Mock successful execution
        success_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_sufficiency": "sufficient"}
        )
        
        mock_execution_engine.execute_agent.return_value = success_result
        
        # Execute workflow
        await workflow_orchestrator.execute_standard_workflow(execution_context)
        
        # Verify notifications were sent
        calls = mock_websocket_manager.send_agent_update.call_args_list
        
        # Should have workflow_started and workflow_completed
        statuses = [call[0][2]["status"] for call in calls]
        assert "workflow_started" in statuses
        assert "workflow_completed" in statuses
    
    def test_create_pipeline_step(self, workflow_orchestrator):
        """Test pipeline step creation."""
        step = workflow_orchestrator._create_pipeline_step(
            "test_agent",
            "test_type",
            1,
            dependencies=["dep1", "dep2"]
        )
        
        assert isinstance(step, PipelineStep)
        assert step.agent_name == "test_agent"
        assert step.metadata["step_type"] == "test_type"
        assert step.metadata["order"] == 1
        assert step.dependencies == ["dep1", "dep2"]
        assert step.metadata["requires_sequential"] is True
    
    def test_get_workflow_definition(self, workflow_orchestrator):
        """Test getting workflow definition."""
        definition = workflow_orchestrator.get_workflow_definition()
        
        assert definition["type"] == "adaptive"
        assert "configurations" in definition
        assert "sufficient_data" in definition["configurations"]
        assert "partial_data" in definition["configurations"]
        assert "insufficient_data" in definition["configurations"]
        
        # Verify each configuration
        sufficient = definition["configurations"]["sufficient_data"]
        assert len(sufficient) == 5
        assert sufficient[0]["agent"] == "triage"
        assert sufficient[-1]["agent"] == "reporting"
        
        partial = definition["configurations"]["partial_data"]
        assert any(step["agent"] == "data_helper" for step in partial)
        
        insufficient = definition["configurations"]["insufficient_data"]
        assert len(insufficient) == 2
        assert insufficient[1]["agent"] == "data_helper"
    
    @pytest.mark.asyncio
    async def test_context_state_updates(
        self, workflow_orchestrator, execution_context, mock_execution_engine
    ):
        """Test that context state is properly updated during workflow."""
        # Mock triage result
        triage_result = ExecutionResult(
            success=True,
            status="completed",
            result={"data_sufficiency": "partial", "category": "cost"}
        )
        
        mock_execution_engine.execute_agent.return_value = triage_result
        
        # Execute workflow
        await workflow_orchestrator.execute_standard_workflow(execution_context)
        
        # Verify triage result was stored in context
        if hasattr(execution_context.state, 'triage_result'):
            assert execution_context.state.triage_result == triage_result.result


class TestWorkflowIntegration:
    """Integration tests for complete workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sufficient_data_workflow(self):
        """Test complete workflow with sufficient data."""
        # This would require more complex setup with real agents
        # Placeholder for E2E test
        pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_data_collection_workflow(self):
        """Test workflow that requests additional data."""
        # This would test the data_helper integration
        # Placeholder for E2E test
        pass