"""
Test Data Helper Agent Coordination Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data helper agent properly coordinates with other agents in workflow
- Value Impact: Enables reliable data collection and preparation for AI-powered analysis workflows
- Strategic Impact: Foundation for data-driven insights that provide core business value to customers

Tests the data helper agent's coordination with supervisor and other agents,
including data collection, validation, and handoff to analysis agents.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)


class TestDataHelperAgentCoordination(BaseIntegrationTest):
    """Integration tests for data helper agent coordination."""

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_data_helper_supervisor_coordination(self, real_services_fixture):
        """Test coordination between data helper agent and supervisor agent."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_500",
            thread_id="thread_800",
            session_id="session_1100",
            workspace_id="workspace_400"
        )
        
        # Mock supervisor's coordination with data helper
        mock_supervisor = MagicMock()
        mock_supervisor.coordinate_data_collection = AsyncMock()
        
        # Mock LLM responses for data collection
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(side_effect=[
            # Data helper identifies required data
            {"status": "success", "required_data": ["aws_costs", "usage_metrics"], "collection_plan": "parallel"},
            # Data helper collects AWS costs
            {"status": "success", "data": {"aws_costs": {"monthly": 5000, "services": ["ec2", "s3"]}}},
            # Data helper collects usage metrics  
            {"status": "success", "data": {"usage_metrics": {"cpu": 65, "memory": 80}}},
            # Data helper consolidates and validates
            {"status": "success", "validated_data": {"costs": 5000, "usage": {"cpu": 65, "memory": 80}}, "ready_for_analysis": True}
        ])
        
        data_helper = DataHelperAgent(
            user_context=user_context,
            llm_client=mock_llm,
            supervisor_coordinator=mock_supervisor
        )
        
        # Act - Execute data collection with supervisor coordination
        result = await data_helper.execute_coordinated_collection(
            request="Collect data for AWS cost optimization",
            coordination_mode="supervisor_guided"
        )
        
        # Assert - Verify coordination
        assert result is not None
        assert result.status == "success"
        assert "validated_data" in result.result
        
        # Verify supervisor coordination was called
        mock_supervisor.coordinate_data_collection.assert_called()
        
        # Verify data structure is ready for analysis
        validated_data = result.result["validated_data"]
        assert "costs" in validated_data
        assert "usage" in validated_data
        assert result.result.get("ready_for_analysis") is True

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_data_helper_triage_agent_handoff(self, real_services_fixture):
        """Test data handoff from data helper to triage agent."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_501",
            thread_id="thread_801", 
            session_id="session_1101",
            workspace_id="workspace_401"
        )
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=AsyncMock(),
            websocket_emitter=MagicMock()
        )
        
        # Mock data helper result
        data_helper_result = {
            "status": "success",
            "collected_data": {
                "infrastructure": {"servers": 50, "cost": 8000},
                "performance": {"avg_cpu": 45, "avg_memory": 70},
                "alerts": ["high_memory_usage", "underutilized_instances"]
            },
            "data_quality_score": 0.95,
            "collection_metadata": {
                "sources": ["aws_api", "monitoring_tools"],
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }
        
        # Mock triage agent to receive handoff
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "triage_result": {
                "priority": "high",
                "analysis_type": "cost_optimization",
                "recommended_agent": "apex_optimizer",
                "confidence": 0.88
            },
            "handoff_acknowledged": True
        })
        
        execution_engine.llm_client = mock_llm
        
        # Act - Execute data collection followed by triage handoff
        triage_result = await execution_engine.execute_agent_handoff(
            source_agent="data_helper",
            target_agent="triage",
            handoff_data=data_helper_result,
            message="Analyze collected infrastructure data"
        )
        
        # Assert - Verify handoff
        assert triage_result is not None
        assert triage_result.status == "success"
        assert "triage_result" in triage_result.result
        
        triage_data = triage_result.result["triage_result"]
        assert triage_data["priority"] == "high"
        assert triage_data["recommended_agent"] == "apex_optimizer"
        assert triage_result.result.get("handoff_acknowledged") is True

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_data_helper_parallel_collection_coordination(self, real_services_fixture):
        """Test data helper coordination of parallel data collection tasks."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_502",
            thread_id="thread_802",
            session_id="session_1102",
            workspace_id="workspace_402"
        )
        
        mock_llm = AsyncMock()
        # Different response times to simulate parallel collection
        collection_responses = {
            "aws_costs": {"data": {"monthly_cost": 12000}, "collection_time": 0.2},
            "azure_costs": {"data": {"monthly_cost": 8000}, "collection_time": 0.3}, 
            "usage_metrics": {"data": {"total_instances": 75}, "collection_time": 0.1}
        }
        
        async def parallel_collection_response(*args, **kwargs):
            # Simulate variable collection times
            if "aws_costs" in str(kwargs):
                await asyncio.sleep(0.2)
                return collection_responses["aws_costs"]
            elif "azure_costs" in str(kwargs):
                await asyncio.sleep(0.3) 
                return collection_responses["azure_costs"]
            else:
                await asyncio.sleep(0.1)
                return collection_responses["usage_metrics"]
        
        mock_llm.generate_response = parallel_collection_response
        
        data_helper = DataHelperAgent(
            user_context=user_context,
            llm_client=mock_llm,
            parallel_collection_enabled=True
        )
        
        # Act - Execute parallel data collection
        start_time = asyncio.get_event_loop().time()
        
        collection_tasks = [
            "collect aws costs",
            "collect azure costs", 
            "collect usage metrics"
        ]
        
        result = await data_helper.execute_parallel_collection(
            collection_tasks=collection_tasks,
            max_concurrency=3
        )
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Assert - Parallel execution should be faster than sequential
        assert result is not None
        assert result.status == "success"
        assert len(result.collection_results) == 3
        
        # Should complete in max time, not sum of all times
        assert total_time < 0.6  # Max individual time (0.3) + overhead, not 0.6 total
        
        # Verify all collections completed
        collected_data_types = [r.data_type for r in result.collection_results]
        assert "aws_costs" in collected_data_types
        assert "azure_costs" in collected_data_types
        assert "usage_metrics" in collected_data_types

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_data_helper_validation_coordination_with_quality_checks(self, real_services_fixture):
        """Test data helper coordination with validation agents for quality checks."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_503",
            thread_id="thread_803",
            session_id="session_1103", 
            workspace_id="workspace_403"
        )
        
        # Mock validation agent coordination
        mock_validator = AsyncMock()
        mock_validator.validate_data_quality = AsyncMock(return_value={
            "validation_result": "passed",
            "quality_score": 0.92,
            "issues": [],
            "recommendations": ["add_metadata_tags"]
        })
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(side_effect=[
            # Data collection
            {"status": "success", "raw_data": {"metrics": [1, 2, 3, 4, 5]}, "needs_validation": True},
            # Post-validation processing
            {"status": "success", "validated_data": {"metrics": [1, 2, 3, 4, 5], "quality_assured": True}}
        ])
        
        data_helper = DataHelperAgent(
            user_context=user_context,
            llm_client=mock_llm,
            validation_coordinator=mock_validator
        )
        
        # Act - Execute data collection with validation coordination
        result = await data_helper.execute_with_validation(
            collection_request="Collect performance metrics",
            validation_required=True,
            quality_threshold=0.9
        )
        
        # Assert - Verify validation coordination
        assert result is not None
        assert result.status == "success"
        
        # Verify validator was called
        mock_validator.validate_data_quality.assert_called_once()
        
        # Verify data passed validation
        assert result.result.get("quality_assured") is True
        assert "validated_data" in result.result

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_data_helper_error_recovery_coordination(self, real_services_fixture):
        """Test data helper coordination with error recovery mechanisms."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_504",
            thread_id="thread_804",
            session_id="session_1104",
            workspace_id="workspace_404"
        )
        
        # Mock error recovery coordinator
        mock_recovery = AsyncMock()
        mock_recovery.handle_collection_failure = AsyncMock()
        mock_recovery.suggest_alternative_source = AsyncMock(return_value={
            "alternative_source": "backup_api",
            "expected_reliability": 0.95
        })
        
        mock_llm = AsyncMock()
        call_count = 0
        
        async def failing_then_succeeding_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise Exception("Primary data source unavailable")
            elif call_count == 2:
                # Recovery attempt with alternative source
                return {
                    "status": "success", 
                    "data": {"backup_data": "retrieved_successfully"},
                    "source": "backup_api",
                    "recovered": True
                }
            else:
                return {"status": "success", "data": "normal_response"}
        
        mock_llm.generate_response = failing_then_succeeding_response
        
        data_helper = DataHelperAgent(
            user_context=user_context,
            llm_client=mock_llm,
            error_recovery_coordinator=mock_recovery
        )
        
        # Act - Execute data collection with error recovery
        result = await data_helper.execute_with_recovery(
            collection_request="Collect critical business data",
            recovery_enabled=True,
            max_recovery_attempts=2
        )
        
        # Assert - Verify error recovery coordination
        assert result is not None
        assert result.status == "success"
        assert result.result.get("recovered") is True
        
        # Verify recovery coordinator was used
        mock_recovery.handle_collection_failure.assert_called()
        mock_recovery.suggest_alternative_source.assert_called()
        
        # Verify successful data retrieval after recovery
        assert "backup_data" in result.result["data"]
        assert result.result["source"] == "backup_api"