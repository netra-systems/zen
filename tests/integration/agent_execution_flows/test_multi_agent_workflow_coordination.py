"""
Test Multi-Agent Workflow Coordination Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless coordination across multiple agents in complex workflows  
- Value Impact: Enables sophisticated AI-powered analysis that delivers comprehensive business insights
- Strategic Impact: Core platform capability that differentiates Netra from simple chatbots

Tests the coordination between multiple agents in complex workflows including
data flow, handoffs, synchronization, and error recovery across agent boundaries.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)


@dataclass
class WorkflowStep:
    """Represents a step in a multi-agent workflow."""
    agent_type: str
    task_description: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    dependencies: List[str] = None


class TestMultiAgentWorkflowCoordination(BaseIntegrationTest):
    """Integration tests for multi-agent workflow coordination."""

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_end_to_end_optimization_workflow_coordination(self, real_services_fixture):
        """Test complete end-to-end optimization workflow with all agent types."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="workflow_user_900",
            thread_id="thread_1200",
            session_id="session_1500",
            workspace_id="workflow_workspace_800"
        )
        
        # Define complete optimization workflow
        workflow_steps = [
            WorkflowStep(
                agent_type="data_helper",
                task_description="Collect comprehensive cost and usage data",
                input_data={"scope": "all_cloud_services", "timeframe": "last_3_months"},
                expected_output={"cost_data": dict, "usage_metrics": dict, "trends": dict}
            ),
            WorkflowStep(
                agent_type="triage",
                task_description="Analyze data and prioritize optimization opportunities",
                input_data={},  # Will receive from data_helper
                expected_output={"priority_areas": list, "urgency_level": str, "recommended_approach": str},
                dependencies=["data_helper"]
            ),
            WorkflowStep(
                agent_type="apex_optimizer",
                task_description="Generate detailed optimization recommendations",
                input_data={},  # Will receive from triage
                expected_output={"recommendations": list, "savings_potential": float, "implementation_plan": dict},
                dependencies=["triage"]
            ),
            WorkflowStep(
                agent_type="reporting",
                task_description="Create executive summary and technical documentation",
                input_data={},  # Will receive from apex_optimizer
                expected_output={"executive_summary": str, "technical_details": dict, "action_plan": dict},
                dependencies=["apex_optimizer"]
            )
        ]
        
        # Mock LLM responses for each agent
        workflow_responses = {
            "data_helper": {
                "status": "success",
                "cost_data": {"total_monthly": 35000, "growth_rate": 0.15},
                "usage_metrics": {"avg_utilization": 45, "peak_usage": 85},
                "trends": {"increasing_waste": True, "underutilized_resources": 0.6}
            },
            "triage": {
                "status": "success", 
                "priority_areas": ["compute_optimization", "storage_optimization"],
                "urgency_level": "high",
                "recommended_approach": "phased_implementation"
            },
            "apex_optimizer": {
                "status": "success",
                "recommendations": [
                    {"type": "rightsizing", "savings": 12000, "complexity": "medium"},
                    {"type": "reserved_instances", "savings": 8000, "complexity": "low"}
                ],
                "savings_potential": 20000,
                "implementation_plan": {"phase_1": "rightsizing", "phase_2": "reserved_instances"}
            },
            "reporting": {
                "status": "success",
                "executive_summary": "Identified $240k annual savings opportunity with medium implementation complexity",
                "technical_details": {"implementation_steps": ["analyze", "plan", "execute", "monitor"]},
                "action_plan": {"immediate": ["rightsizing"], "strategic": ["reserved_instances"]}
            }
        }
        
        mock_llm = AsyncMock()
        call_count = 0
        agent_sequence = ["data_helper", "triage", "apex_optimizer", "reporting"]
        
        async def workflow_response(*args, **kwargs):
            nonlocal call_count
            agent_type = agent_sequence[call_count % len(agent_sequence)]
            call_count += 1
            return workflow_responses[agent_type]
        
        mock_llm.generate_response = workflow_response
        
        workflow_orchestrator = WorkflowOrchestrator(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act - Execute complete workflow
        result = await workflow_orchestrator.execute_multi_agent_workflow(
            workflow_name="comprehensive_cost_optimization",
            workflow_steps=workflow_steps,
            coordination_mode="sequential_with_handoffs"
        )
        
        # Assert - Verify complete workflow coordination
        assert result is not None
        assert result.status == "success"
        assert len(result.step_results) == 4
        
        # Verify workflow progression
        step_names = [step.step_name for step in result.step_results]
        assert "data_helper" in step_names
        assert "triage" in step_names
        assert "apex_optimizer" in step_names  
        assert "reporting" in step_names
        
        # Verify final business value
        final_result = result.step_results[-1]  # Reporting agent result
        assert "executive_summary" in final_result.result
        assert "240k" in final_result.result["executive_summary"]  # Savings amount

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_parallel_agent_coordination_with_synchronization(self, real_services_fixture):
        """Test parallel agent execution with synchronization points."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="parallel_user_901",
            thread_id="thread_1201",
            session_id="session_1501",
            workspace_id="parallel_workspace_801"
        )
        
        # Define parallel workflow with sync points
        parallel_workflow = {
            "phase_1_parallel": [
                {
                    "agent_type": "data_helper",
                    "task": "collect_aws_data",
                    "parallel_group": "data_collection"
                },
                {
                    "agent_type": "data_helper", 
                    "task": "collect_azure_data",
                    "parallel_group": "data_collection"
                }
            ],
            "sync_point_1": {
                "agent_type": "triage",
                "task": "analyze_combined_data",
                "depends_on": ["data_collection"]
            },
            "phase_2_parallel": [
                {
                    "agent_type": "apex_optimizer",
                    "task": "optimize_aws",
                    "parallel_group": "optimization"
                },
                {
                    "agent_type": "apex_optimizer",
                    "task": "optimize_azure", 
                    "parallel_group": "optimization"
                }
            ],
            "sync_point_2": {
                "agent_type": "reporting",
                "task": "create_unified_report",
                "depends_on": ["optimization"]
            }
        }
        
        # Mock responses with timing simulation
        response_data = {
            "collect_aws_data": {"aws_costs": 20000, "collection_time": 0.2},
            "collect_azure_data": {"azure_costs": 15000, "collection_time": 0.3},
            "analyze_combined_data": {"combined_analysis": "multi_cloud_opportunities", "sync_complete": True},
            "optimize_aws": {"aws_savings": 8000, "optimization_time": 0.4},
            "optimize_azure": {"azure_savings": 6000, "optimization_time": 0.3},
            "create_unified_report": {"unified_report": "cross_platform_optimization", "total_savings": 14000}
        }
        
        mock_llm = AsyncMock()
        
        async def parallel_response(*args, **kwargs):
            task = kwargs.get('task', 'unknown')
            if task in response_data:
                # Simulate actual work time
                if 'collection_time' in response_data[task]:
                    await asyncio.sleep(response_data[task]['collection_time'])
                elif 'optimization_time' in response_data[task]:
                    await asyncio.sleep(response_data[task]['optimization_time'])
                return {"status": "success", **response_data[task]}
            return {"status": "success", "generic_response": True}
        
        mock_llm.generate_response = parallel_response
        
        workflow_orchestrator = WorkflowOrchestrator(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act - Execute parallel workflow with sync points
        start_time = asyncio.get_event_loop().time()
        
        result = await workflow_orchestrator.execute_parallel_workflow_with_sync(
            workflow_definition=parallel_workflow,
            max_parallel_agents=4,
            sync_timeout=5.0
        )
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Assert - Verify parallel coordination with synchronization
        assert result is not None
        assert result.status == "success"
        
        # Parallel execution should be faster than sequential
        # Sequential would be: 0.2 + 0.3 + sync + 0.4 + 0.3 + sync = ~1.2+ seconds
        # Parallel should be: max(0.2,0.3) + sync + max(0.4,0.3) + sync = ~0.7+ seconds
        assert total_time < 1.0  # Should be significantly faster than sequential
        
        # Verify sync points were reached
        assert "unified_report" in str(result.final_result)
        assert result.sync_points_completed >= 2

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_workflow_error_recovery_coordination(self, real_services_fixture):
        """Test workflow coordination with error recovery and fallback agents."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="recovery_user_902",
            thread_id="thread_1202",
            session_id="session_1502",
            workspace_id="recovery_workspace_802"
        )
        
        # Mock error recovery coordinator
        mock_recovery_coordinator = AsyncMock()
        mock_recovery_coordinator.handle_agent_failure = AsyncMock(return_value={
            "recovery_strategy": "fallback_agent",
            "fallback_agent_type": "data_helper_backup",
            "estimated_recovery_time": "30 seconds"
        })
        
        # Workflow with intentional failure and recovery
        error_prone_workflow = [
            {
                "agent_type": "data_helper",
                "task": "collect_primary_data",
                "fallback_agent": "data_helper_backup",
                "retry_attempts": 2
            },
            {
                "agent_type": "apex_optimizer",
                "task": "generate_optimizations", 
                "depends_on": ["data_helper"],
                "error_handling": "graceful_degradation"
            }
        ]
        
        mock_llm = AsyncMock()
        call_count = 0
        
        async def failing_then_recovery_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Primary data helper fails
                raise Exception("Primary data source unavailable")
            elif call_count == 2:
                # Fallback data helper succeeds
                return {
                    "status": "success",
                    "data_source": "fallback", 
                    "recovery_successful": True,
                    "data": {"costs": 25000, "usage": "moderate"}
                }
            else:
                # Optimizer works with recovered data
                return {
                    "status": "success",
                    "optimizations": [{"savings": 5000, "confidence": "medium"}],
                    "based_on_recovered_data": True
                }
        
        mock_llm.generate_response = failing_then_recovery_response
        
        workflow_orchestrator = WorkflowOrchestrator(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock(),
            recovery_coordinator=mock_recovery_coordinator
        )
        
        # Act - Execute workflow with error recovery
        result = await workflow_orchestrator.execute_resilient_workflow(
            workflow_steps=error_prone_workflow,
            error_recovery_enabled=True,
            max_recovery_attempts=2
        )
        
        # Assert - Verify error recovery coordination
        assert result is not None
        assert result.status == "success"
        assert result.recovery_events > 0
        
        # Verify recovery was used
        data_step_result = next(
            (step for step in result.step_results if step.agent_type == "data_helper"), 
            None
        )
        assert data_step_result is not None
        assert data_step_result.result.get("recovery_successful") is True
        
        # Verify workflow continued after recovery
        optimizer_result = next(
            (step for step in result.step_results if step.agent_type == "apex_optimizer"),
            None
        )
        assert optimizer_result is not None
        assert optimizer_result.result.get("based_on_recovered_data") is True
        
        # Verify recovery coordinator was used
        mock_recovery_coordinator.handle_agent_failure.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_dynamic_workflow_adaptation_coordination(self, real_services_fixture):
        """Test dynamic workflow adaptation based on intermediate results."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="adaptive_user_903", 
            thread_id="thread_1203",
            session_id="session_1503",
            workspace_id="adaptive_workspace_803"
        )
        
        # Mock adaptive coordinator
        mock_adaptive_coordinator = AsyncMock()
        mock_adaptive_coordinator.analyze_intermediate_results = AsyncMock(return_value={
            "adaptation_needed": True,
            "adaptation_type": "additional_analysis",
            "new_steps": [
                {"agent_type": "specialized_analyzer", "task": "deep_dive_analysis"}
            ]
        })
        
        # Initial workflow that will adapt
        base_workflow = [
            {
                "agent_type": "data_helper",
                "task": "initial_data_collection"
            },
            {
                "agent_type": "triage", 
                "task": "assess_complexity",
                "adaptation_trigger": True  # This step can trigger workflow changes
            }
        ]
        
        mock_llm = AsyncMock()
        call_count = 0
        
        async def adaptive_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Data collection
                return {
                    "status": "success",
                    "data": {"complexity_indicators": {"high_variance": True, "anomalies": 5}}
                }
            elif call_count == 2:
                # Triage identifies need for additional analysis
                return {
                    "status": "success",
                    "complexity_assessment": "high",
                    "additional_analysis_needed": True,
                    "workflow_adaptation_recommended": True
                }
            else:
                # Additional specialized analysis
                return {
                    "status": "success",
                    "specialized_findings": {"root_cause": "infrastructure_drift", "impact": "significant"},
                    "adaptation_successful": True
                }
        
        mock_llm.generate_response = adaptive_response
        
        workflow_orchestrator = WorkflowOrchestrator(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock(),
            adaptive_coordinator=mock_adaptive_coordinator
        )
        
        # Act - Execute adaptive workflow
        result = await workflow_orchestrator.execute_adaptive_workflow(
            base_workflow=base_workflow,
            adaptation_enabled=True,
            adaptation_triggers=["complexity_assessment"]
        )
        
        # Assert - Verify dynamic adaptation coordination
        assert result is not None
        assert result.status == "success"
        assert result.workflow_adapted is True
        
        # Verify additional steps were added and executed
        assert len(result.step_results) > len(base_workflow)
        
        # Check for specialized analysis results
        specialized_result = next(
            (step for step in result.step_results if step.agent_type == "specialized_analyzer"),
            None
        )
        assert specialized_result is not None
        assert specialized_result.result.get("adaptation_successful") is True
        
        # Verify adaptive coordinator was consulted
        mock_adaptive_coordinator.analyze_intermediate_results.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_cross_workflow_state_management(self, real_services_fixture):
        """Test state management across complex multi-agent workflows."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="state_mgmt_user_904",
            thread_id="thread_1204",
            session_id="session_1504", 
            workspace_id="state_mgmt_workspace_804"
        )
        
        # Mock state manager for cross-workflow coordination
        mock_state_manager = AsyncMock()
        mock_state_manager.persist_workflow_state = AsyncMock()
        mock_state_manager.retrieve_workflow_state = AsyncMock()
        mock_state_manager.merge_workflow_states = AsyncMock(return_value={
            "merged_state": {
                "accumulated_data": {"total_analyzed_cost": 45000, "total_savings": 15000},
                "cross_workflow_insights": ["multi_service_optimization_opportunity"],
                "state_consistency": "validated"
            }
        })
        
        # Multiple interconnected workflows
        workflows = {
            "workflow_1": [
                {"agent_type": "data_helper", "task": "collect_ec2_data"},
                {"agent_type": "apex_optimizer", "task": "optimize_ec2"}
            ],
            "workflow_2": [
                {"agent_type": "data_helper", "task": "collect_storage_data"},
                {"agent_type": "apex_optimizer", "task": "optimize_storage"}
            ],
            "workflow_3": [
                {"agent_type": "reporting", "task": "create_combined_report", "depends_on": ["workflow_1", "workflow_2"]}
            ]
        }
        
        workflow_responses = {
            "collect_ec2_data": {"ec2_costs": 25000, "utilization": 0.4},
            "optimize_ec2": {"ec2_savings": 10000},
            "collect_storage_data": {"storage_costs": 20000, "efficiency": 0.6},
            "optimize_storage": {"storage_savings": 5000},
            "create_combined_report": {"total_savings": 15000, "combined_analysis": True}
        }
        
        mock_llm = AsyncMock()
        
        async def workflow_state_response(*args, **kwargs):
            task = kwargs.get('task', 'unknown')
            if task in workflow_responses:
                return {"status": "success", **workflow_responses[task]}
            return {"status": "success"}
        
        mock_llm.generate_response = workflow_state_response
        
        workflow_orchestrator = WorkflowOrchestrator(
            user_context=user_context,
            llm_client=mock_llm,
            websocket_emitter=MagicMock(),
            state_manager=mock_state_manager
        )
        
        # Act - Execute interconnected workflows with state management
        result = await workflow_orchestrator.execute_interconnected_workflows(
            workflows=workflows,
            state_management_enabled=True,
            cross_workflow_dependencies=True
        )
        
        # Assert - Verify cross-workflow state management
        assert result is not None
        assert result.status == "success"
        assert result.workflows_completed == 3
        
        # Verify state management was used
        mock_state_manager.persist_workflow_state.assert_called()
        mock_state_manager.merge_workflow_states.assert_called()
        
        # Verify cross-workflow coordination
        assert "combined_analysis" in str(result.final_result)
        assert result.cross_workflow_insights is not None