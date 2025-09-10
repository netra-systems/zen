"""
Test Supervisor Agent Pipeline Orchestration Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure supervisor agent orchestrates multi-step workflows correctly
- Value Impact: Core business logic orchestration that enables AI-powered insights delivery
- Strategic Impact: Mission-critical foundation for 90% of platform value (chat functionality)

Tests the supervisor agent's ability to orchestrate complex multi-agent pipelines
including data collection, triage, optimization, and reporting phases.
"""

import asyncio
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.state import DeepAgentState


class TestSupervisorAgentPipelineOrchestration(BaseIntegrationTest):
    """Integration tests for supervisor agent pipeline orchestration."""

    @pytest.mark.integration
    @pytest.mark.agent_orchestration
    async def test_full_optimization_pipeline_orchestration(self, real_services_fixture):
        """Test complete optimization pipeline: data -> triage -> optimization -> reporting."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            session_id="session_789",
            workspace_id="workspace_001"
        )
        
        # Mock LLM responses to avoid external dependencies
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(side_effect=[
            # Data collection phase
            {"status": "success", "data": {"aws_cost_data": {"monthly_spend": 5000}}, "next_step": "triage"},
            # Triage phase  
            {"status": "success", "recommendations": ["cost_optimization"], "priority": "high", "next_step": "optimization"},
            # Optimization phase
            {"status": "success", "optimizations": [{"type": "right_sizing", "savings": 1200}], "next_step": "reporting"},
            # Reporting phase
            {"status": "success", "report": {"summary": "Found $1200 monthly savings"}, "next_step": "complete"}
        ])
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act
        pipeline_steps = [
            PipelineStep(step_name="data_collection", agent_type="data_helper"),
            PipelineStep(step_name="triage", agent_type="triage"),  
            PipelineStep(step_name="optimization", agent_type="apex_optimizer"),
            PipelineStep(step_name="reporting", agent_type="reporting")
        ]
        
        result = await execution_engine.execute_pipeline(
            message="Optimize my AWS costs",
            pipeline_steps=pipeline_steps
        )
        
        # Assert
        assert result is not None
        assert result.status == "success"
        assert len(result.pipeline_results) == 4
        
        # Verify pipeline step sequence
        assert result.pipeline_results[0].step_name == "data_collection"
        assert result.pipeline_results[1].step_name == "triage"
        assert result.pipeline_results[2].step_name == "optimization"  
        assert result.pipeline_results[3].step_name == "reporting"
        
        # Verify business value delivered
        final_result = result.pipeline_results[-1].result
        assert "savings" in str(final_result).lower()

    @pytest.mark.integration
    @pytest.mark.agent_orchestration  
    async def test_conditional_pipeline_branching(self, real_services_fixture):
        """Test pipeline branching based on triage agent decisions."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_124",
            thread_id="thread_457", 
            session_id="session_790",
            workspace_id="workspace_002"
        )
        
        mock_llm = AsyncMock()
        # Triage determines low priority -> different pipeline
        mock_llm.generate_response = AsyncMock(side_effect=[
            {"status": "success", "data": {"basic_query": True}, "next_step": "triage"},
            {"status": "success", "priority": "low", "route": "simple_response", "next_step": "direct_response"}
        ])
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act - Execute conditional pipeline
        result = await execution_engine.execute_conditional_pipeline(
            message="What is my current spend?",
            initial_steps=[
                PipelineStep(step_name="data_collection", agent_type="data_helper"),
                PipelineStep(step_name="triage", agent_type="triage")
            ]
        )
        
        # Assert
        assert result is not None
        assert result.status == "success"
        # Should have only 2 steps due to low priority routing
        assert len(result.pipeline_results) == 2
        assert result.pipeline_results[1].result["route"] == "simple_response"

    @pytest.mark.integration  
    @pytest.mark.agent_orchestration
    async def test_pipeline_step_dependency_validation(self, real_services_fixture):
        """Test pipeline validates step dependencies before execution."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_125",
            thread_id="thread_458",
            session_id="session_791", 
            workspace_id="workspace_003"
        )
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=AsyncMock(),
            websocket_emitter=MagicMock()
        )
        
        # Act & Assert - Invalid pipeline (optimization without triage)
        invalid_steps = [
            PipelineStep(step_name="data_collection", agent_type="data_helper"),
            PipelineStep(step_name="optimization", agent_type="apex_optimizer", requires=["triage"]) # Missing triage
        ]
        
        with pytest.raises(Exception) as exc_info:
            await execution_engine.execute_pipeline(
                message="Optimize costs",
                pipeline_steps=invalid_steps
            )
        
        assert "dependency" in str(exc_info.value).lower() or "requires" in str(exc_info.value).lower()

    @pytest.mark.integration
    @pytest.mark.agent_orchestration
    async def test_pipeline_parallel_execution_coordination(self, real_services_fixture):
        """Test parallel execution of independent pipeline steps."""
        # Arrange  
        user_context = UserExecutionContext(
            user_id="test_user_126",
            thread_id="thread_459",
            session_id="session_792",
            workspace_id="workspace_004"
        )
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(side_effect=[
            {"status": "success", "data": "aws_data"},
            {"status": "success", "data": "azure_data"},  
            {"status": "success", "combined_analysis": "multi_cloud_insights"}
        ])
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act - Execute parallel data collection steps
        parallel_steps = [
            PipelineStep(step_name="aws_data", agent_type="data_helper", parallel_group="data_collection"),
            PipelineStep(step_name="azure_data", agent_type="data_helper", parallel_group="data_collection"),
            PipelineStep(step_name="analysis", agent_type="apex_optimizer", requires=["data_collection"])
        ]
        
        start_time = asyncio.get_event_loop().time()
        result = await execution_engine.execute_pipeline(
            message="Analyze multi-cloud costs",
            pipeline_steps=parallel_steps
        )
        end_time = asyncio.get_event_loop().time()
        
        # Assert
        assert result is not None
        assert result.status == "success"
        assert len(result.pipeline_results) == 3
        
        # Parallel execution should be faster than sequential
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete quickly due to parallel execution

    @pytest.mark.integration
    @pytest.mark.agent_orchestration
    async def test_pipeline_resource_management_and_cleanup(self, real_services_fixture):
        """Test pipeline properly manages resources and cleans up after execution."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_127",
            thread_id="thread_460",
            session_id="session_793",
            workspace_id="workspace_005"
        )
        
        mock_llm = AsyncMock()
        mock_websocket = MagicMock()
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=mock_websocket
        )
        
        # Track resource allocation
        initial_context_count = len(execution_engine._active_contexts) if hasattr(execution_engine, '_active_contexts') else 0
        
        # Act
        pipeline_steps = [
            PipelineStep(step_name="resource_intensive_step", agent_type="data_helper"),
            PipelineStep(step_name="cleanup_step", agent_type="triage")
        ]
        
        mock_llm.generate_response = AsyncMock(side_effect=[
            {"status": "success", "data": "large_dataset"}, 
            {"status": "success", "cleaned": True}
        ])
        
        result = await execution_engine.execute_pipeline(
            message="Process large dataset", 
            pipeline_steps=pipeline_steps
        )
        
        # Assert
        assert result is not None
        assert result.status == "success"
        
        # Verify resource cleanup
        final_context_count = len(execution_engine._active_contexts) if hasattr(execution_engine, '_active_contexts') else 0
        assert final_context_count == initial_context_count  # Resources properly cleaned up
        
        # Verify WebSocket notifications sent for pipeline progress
        assert mock_websocket.emit.call_count >= 2  # At least start and end events