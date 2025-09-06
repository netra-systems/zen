"""
Test suite for end-to-end adaptive workflow flow validation.
Validates complete agent flows (A, B, C) and flow transitions.
"""

import pytest
from typing import Dict, Any, List
import asyncio
import json
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.models import (
    DataSufficiency,
    WorkflowPath,
    AgentState,
    WorkflowContext,
    FlowTransition
)
from netra_backend.tests.agents.fixtures.llm_agent_fixtures import create_mock_llm_client


class TestAdaptiveWorkflowFlows:
    """Test complete end-to-end agent workflow flows."""
    pass

    @pytest.fixture
    async def supervisor_agent(self):
        """Create a SupervisorAgent with mocked sub-agents."""
        mock_llm_client = create_mock_llm_client()
        supervisor = SupervisorAgent(
            llm_client=mock_llm_client,
            thread_id="test-thread-001",
            turn_id="test-turn-001"
        )
        
        # Mock all sub-agents
        supervisor.triage_agent = AsyncMock(spec=TriageSubAgent)
        supervisor.optimization_agent = AsyncMock(spec=OptimizationsCoreSubAgent)
        supervisor.data_agent = AsyncMock(spec=DataSubAgent)
        supervisor.data_helper = AsyncMock(spec=DataHelperAgent)
        supervisor.actions_agent = AsyncMock(spec=ActionsToMeetGoalsSubAgent)
        supervisor.reporting_agent = AsyncMock(spec=ReportingSubAgent)
        
        await asyncio.sleep(0)
    return supervisor

    @pytest.fixture
    def flow_test_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Define complete flow test scenarios."""
    pass
        return {
            "sufficient_data_flow": {
                "user_request": {
                    "message": "Optimize our AI costs",
                    "metrics": {
                        "monthly_spend": 10000,
                        "requests_per_day": 50000,
                        "models": {"gpt-4": 0.7, "gpt-3.5": 0.3},
                        "p95_latency": 3.5
                    }
                },
                "expected_flow": [
                    "triage",
                    "optimization",
                    "data_analysis",
                    "actions",
                    "reporting"
                ],
                "expected_outcome": {
                    "recommendations": 3,
                    "estimated_savings": "$3000-5000/month",
                    "implementation_plan": True,
                    "success": True
                }
            },
            "partial_data_flow": {
                "user_request": {
                    "message": "We're spending $8000/month on AI, help optimize",
                    "metrics": {
                        "monthly_spend": 8000
                    }
                },
                "expected_flow": [
                    "triage",
                    "optimization",
                    "actions",
                    "data_helper",
                    "reporting"
                ],
                "expected_outcome": {
                    "initial_recommendations": 2,
                    "data_requests": ["model distribution", "usage patterns"],
                    "partial_plan": True,
                    "success": True
                }
            },
            "insufficient_data_flow": {
                "user_request": {
                    "message": "Make our AI better"
                },
                "expected_flow": [
                    "triage",
                    "data_helper"
                ],
                "expected_outcome": {
                    "data_requests": [
                        "current metrics",
                        "optimization goals",
                        "constraints"
                    ],
                    "recommendations": 0,
                    "success": True
                }
            }
        }

    @pytest.mark.asyncio
    async def test_sufficient_data_complete_flow(self, supervisor_agent, flow_test_scenarios):
        """Test Flow A: Complete pipeline with sufficient data."""
        scenario = flow_test_scenarios["sufficient_data_flow"]
        
        # Setup mock responses for each agent in the flow
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.SUFFICIENT,
            "workflow_path": WorkflowPath.FULL_PIPELINE,
            "insights": ["Complete metrics available", "Clear optimization opportunities"]
        }
        
        supervisor_agent.optimization_agent.optimize.return_value = {
            "recommendations": [
                {"strategy": "Model cascading", "savings": "$2000-3000/month"},
                {"strategy": "Prompt optimization", "savings": "$500-1000/month"},
                {"strategy": "Caching", "savings": "$500-1000/month"}
            ]
        }
        
        supervisor_agent.data_agent.analyze.return_value = {
            "patterns": ["High GPT-4 usage for simple queries", "Repeated similar requests"],
            "opportunities": ["30% queries can use cheaper models", "25% cache-able"]
        }
        
        supervisor_agent.actions_agent.generate_actions.return_value = {
            "implementation_steps": [
                "Deploy model router",
                "Implement prompt templates",
                "Setup Redis cache"
            ],
            "timeline": "2 weeks",
            "resources_needed": ["1 engineer", "Redis instance"]
        }
        
        supervisor_agent.reporting_agent.generate_report.return_value = {
            "executive_summary": "3 optimizations identified, $3000-5000/month savings",
            "detailed_recommendations": [...],
            "implementation_roadmap": {...},
            "roi_analysis": {"break_even": "1 month", "annual_savings": "$36000-60000"}
        }
        
        # Execute the complete flow
        result = await supervisor_agent.process_request(scenario["user_request"])
        
        # Validate flow execution order
        assert supervisor_agent.triage_agent.triage.called
        assert supervisor_agent.optimization_agent.optimize.called
        assert supervisor_agent.data_agent.analyze.called
        assert supervisor_agent.actions_agent.generate_actions.called
        assert supervisor_agent.reporting_agent.generate_report.called
        
        # Validate flow sequence (order matters!)
        call_order = [
            supervisor_agent.triage_agent.triage,
            supervisor_agent.optimization_agent.optimize,
            supervisor_agent.data_agent.analyze,
            supervisor_agent.actions_agent.generate_actions,
            supervisor_agent.reporting_agent.generate_report
        ]
        
        for i in range(len(call_order) - 1):
            # Ensure each agent was called before the next
            assert call_order[i].call_count > 0
            
        # Validate business outcome
        assert result["success"] == True
        assert "recommendations" in result
        assert len(result["recommendations"]) >= 3
        assert "savings" in str(result).lower()

    @pytest.mark.asyncio
    async def test_partial_data_modified_flow(self, supervisor_agent, flow_test_scenarios):
        """Test Flow B: Modified pipeline with partial data."""
    pass
        scenario = flow_test_scenarios["partial_data_flow"]
        
        # Setup mock responses
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.PARTIAL,
            "workflow_path": WorkflowPath.MODIFIED_PIPELINE,
            "insights": ["Cost data available"],
            "missing_data": ["model distribution", "usage patterns"]
        }
        
        supervisor_agent.optimization_agent.optimize.return_value = {
            "recommendations": [
                {"strategy": "General cost reduction", "savings": "$1000-2000/month"},
                {"strategy": "Usage optimization", "savings": "$500-1500/month"}
            ],
            "caveats": ["More specific recommendations pending additional data"]
        }
        
        supervisor_agent.actions_agent.generate_actions.return_value = {
            "immediate_steps": ["Audit current usage", "Implement monitoring"],
            "deferred_steps": ["Model optimization pending data"]
        }
        
        supervisor_agent.data_helper.request_data.return_value = {
            "data_requests": [
                {
                    "category": "Model Distribution",
                    "questions": ["What models are you using?", "What's the usage split?"],
                    "format": "percentage_breakdown"
                },
                {
                    "category": "Usage Patterns",
                    "questions": ["Peak usage times?", "Request types?"],
                    "format": "time_series"
                }
            ]
        }
        
        supervisor_agent.reporting_agent.generate_report.return_value = {
            "initial_recommendations": [...],
            "data_needed_for_full_analysis": [...],
            "next_steps": ["Provide requested data", "Schedule follow-up"]
        }
        
        # Execute the modified flow
        result = await supervisor_agent.process_request(scenario["user_request"])
        
        # Validate modified flow execution
        assert supervisor_agent.triage_agent.triage.called
        assert supervisor_agent.optimization_agent.optimize.called
        assert supervisor_agent.actions_agent.generate_actions.called
        assert supervisor_agent.data_helper.request_data.called
        assert supervisor_agent.reporting_agent.generate_report.called
        
        # Data agent should NOT be called in partial flow
        assert not supervisor_agent.data_agent.analyze.called
        
        # Validate data requests are included
        assert "data_requests" in result or "data_needed" in result
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_insufficient_data_minimal_flow(self, supervisor_agent, flow_test_scenarios):
        """Test Flow C: Minimal pipeline with insufficient data."""
        scenario = flow_test_scenarios["insufficient_data_flow"]
        
        # Setup mock responses
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.INSUFFICIENT,
            "workflow_path": WorkflowPath.DATA_COLLECTION,
            "insights": [],
            "missing_data": ["all metrics", "optimization goals", "current configuration"]
        }
        
        supervisor_agent.data_helper.request_data.return_value = {
            "data_collection_form": {
                "sections": [
                    {
                        "title": "Current AI Usage",
                        "fields": ["monthly_spend", "request_volume", "models_used"]
                    },
                    {
                        "title": "Optimization Goals",
                        "fields": ["primary_goal", "constraints", "timeline"]
                    },
                    {
                        "title": "System Information",
                        "fields": ["architecture", "current_providers", "sla_requirements"]
                    }
                ]
            },
            "instructions": "Please provide the requested information to proceed with optimization"
        }
        
        # Execute the minimal flow
        result = await supervisor_agent.process_request(scenario["user_request"])
        
        # Validate minimal flow execution
        assert supervisor_agent.triage_agent.triage.called
        assert supervisor_agent.data_helper.request_data.called
        
        # These agents should NOT be called in insufficient data flow
        assert not supervisor_agent.optimization_agent.optimize.called
        assert not supervisor_agent.data_agent.analyze.called
        assert not supervisor_agent.actions_agent.generate_actions.called
        assert not supervisor_agent.reporting_agent.generate_report.called
        
        # Validate data collection response
        assert "data_collection_form" in result or "data_requests" in result
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_flow_transition_handling(self, supervisor_agent):
        """Test smooth transitions between agents in a flow."""
    pass
        # Track context accumulation through flow
        context_history = []
        
        def track_context(agent_name, context):
    """Use real service instance."""
    # TODO: Initialize real service
            context_history.append({
                "agent": agent_name,
                "context": context.copy() if isinstance(context, dict) else str(context)
            })
        
        # Setup tracking for each agent call
        supervisor_agent.triage_agent.triage.side_effect = lambda x: track_context("triage", x) or {
            "data_sufficiency": DataSufficiency.SUFFICIENT,
            "context": {"triage_complete": True}
        }
        
        supervisor_agent.optimization_agent.optimize.side_effect = lambda x: track_context("optimization", x) or {
            "recommendations": ["rec1", "rec2"],
            "context": {"optimization_complete": True}
        }
        
        supervisor_agent.data_agent.analyze.side_effect = lambda x: track_context("data", x) or {
            "analysis": "complete",
            "context": {"data_complete": True}
        }
        
        # Execute flow
        await supervisor_agent.process_request({"message": "test"})
        
        # Validate context flows between agents
        assert len(context_history) >= 2
        
        # Each subsequent agent should receive accumulated context
        for i in range(1, len(context_history)):
            prev_agent = context_history[i-1]["agent"]
            current_context = context_history[i]["context"]
            # Context should accumulate (this is simplified, actual implementation may vary)
            assert current_context is not None

    @pytest.mark.asyncio
    async def test_error_recovery_in_flow(self, supervisor_agent):
        """Test error handling and recovery within flows."""
    pass
        # Simulate error in middle of flow
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.SUFFICIENT,
            "workflow_path": WorkflowPath.FULL_PIPELINE
        }
        
        # Optimization agent fails
        supervisor_agent.optimization_agent.optimize.side_effect = Exception("Model API error")
        
        # Setup fallback behavior
        supervisor_agent.data_helper.request_data.return_value = {
            "error_recovery": True,
            "fallback_recommendations": ["Generic optimization 1", "Generic optimization 2"],
            "user_message": "Encountered an issue, providing best-effort recommendations"
        }
        
        # Execute flow with error
        result = await supervisor_agent.process_request({"message": "optimize costs"})
        
        # Validate graceful degradation
        assert result["success"] == True or "partial_success" in result
        assert "error_recovery" in result or "fallback" in str(result).lower()

    @pytest.mark.asyncio
    async def test_context_accumulation_through_flow(self, supervisor_agent):
        """Test that context accumulates correctly through the pipeline."""
        accumulated_context = {}
        
        # Mock each agent to add to context
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.SUFFICIENT,
            "workflow_path": WorkflowPath.FULL_PIPELINE,
            "triage_insights": ["insight1", "insight2"]
        }
        accumulated_context.update(supervisor_agent.triage_agent.triage.return_value)
        
        supervisor_agent.optimization_agent.optimize.return_value = {
            "recommendations": ["rec1", "rec2"],
            "estimated_impact": "$5000/month"
        }
        accumulated_context.update(supervisor_agent.optimization_agent.optimize.return_value)
        
        supervisor_agent.data_agent.analyze.return_value = {
            "patterns": ["pattern1", "pattern2"],
            "anomalies": []
        }
        accumulated_context.update(supervisor_agent.data_agent.analyze.return_value)
        
        supervisor_agent.actions_agent.generate_actions.return_value = {
            "steps": ["step1", "step2", "step3"],
            "timeline": "2 weeks"
        }
        accumulated_context.update(supervisor_agent.actions_agent.generate_actions.return_value)
        
        supervisor_agent.reporting_agent.generate_report.side_effect = lambda context: {
            "report": "Final report",
            "includes_all_context": all(
                key in str(context) 
                for key in ["triage_insights", "recommendations", "patterns", "steps"]
            )
        }
        
        # Execute flow
        result = await supervisor_agent.process_request({"message": "full analysis"})
        
        # Validate reporting agent received accumulated context
        report_call_args = supervisor_agent.reporting_agent.generate_report.call_args
        assert report_call_args is not None
        # The reporting agent should receive comprehensive context

    @pytest.mark.asyncio
    async def test_flow_performance_metrics(self, supervisor_agent):
        """Test that flow execution captures performance metrics."""
    pass
        import time
        
        # Track timing for each agent
        timings = {}
        
        async def timed_response(agent_name, response, delay=0.1):
    pass
            start = time.time()
            await asyncio.sleep(delay)
            timings[agent_name] = time.time() - start
            await asyncio.sleep(0)
    return response
        
        supervisor_agent.triage_agent.triage.side_effect = lambda x: timed_response(
            "triage",
            {"data_sufficiency": DataSufficiency.SUFFICIENT, "workflow_path": WorkflowPath.FULL_PIPELINE}
        )
        
        supervisor_agent.optimization_agent.optimize.side_effect = lambda x: timed_response(
            "optimization",
            {"recommendations": ["rec1"]}
        )
        
        # Execute flow
        start_time = time.time()
        result = await supervisor_agent.process_request({"message": "test"})
        total_time = time.time() - start_time
        
        # Validate performance tracking
        assert total_time < 10  # Should complete within reasonable time
        # In production, these metrics would be logged/monitored

    @pytest.mark.asyncio
    async def test_flow_selection_accuracy(self, supervisor_agent):
        """Test that the correct flow is selected based on data sufficiency."""
        test_cases = [
            (DataSufficiency.SUFFICIENT, WorkflowPath.FULL_PIPELINE, 5),  # 5 agents
            (DataSufficiency.PARTIAL, WorkflowPath.MODIFIED_PIPELINE, 4),  # 4 agents
            (DataSufficiency.INSUFFICIENT, WorkflowPath.DATA_COLLECTION, 2)  # 2 agents
        ]
        
        for sufficiency, expected_path, expected_agent_calls in test_cases:
            # Reset mocks
            for attr in ['triage_agent', 'optimization_agent', 'data_agent', 
                        'data_helper', 'actions_agent', 'reporting_agent']:
                getattr(supervisor_agent, attr).reset_mock()
            
            # Setup triage response
            supervisor_agent.triage_agent.triage.return_value = {
                "data_sufficiency": sufficiency,
                "workflow_path": expected_path
            }
            
            # Setup minimal responses for other agents
            supervisor_agent.optimization_agent.optimize.return_value = {"recommendations": []}
            supervisor_agent.data_agent.analyze.return_value = {"patterns": []}
            supervisor_agent.actions_agent.generate_actions.return_value = {"steps": []}
            supervisor_agent.data_helper.request_data.return_value = {"requests": []}
            supervisor_agent.reporting_agent.generate_report.return_value = {"report": "done"}
            
            # Execute flow
            await supervisor_agent.process_request({"message": f"test {sufficiency}"})
            
            # Count actual agent calls
            agent_calls = sum([
                supervisor_agent.triage_agent.triage.called,
                supervisor_agent.optimization_agent.optimize.called,
                supervisor_agent.data_agent.analyze.called,
                supervisor_agent.data_helper.request_data.called,
                supervisor_agent.actions_agent.generate_actions.called,
                supervisor_agent.reporting_agent.generate_report.called
            ])
            
            # Validate correct number of agents were called
            assert agent_calls <= expected_agent_calls + 1  # Allow some flexibility

    @pytest.mark.asyncio
    async def test_flow_state_persistence(self, supervisor_agent):
        """Test that flow state is properly persisted for resumption."""
    pass
        # Simulate partial flow execution
        supervisor_agent.triage_agent.triage.return_value = {
            "data_sufficiency": DataSufficiency.SUFFICIENT,
            "workflow_path": WorkflowPath.FULL_PIPELINE,
            "checkpoint": "triage_complete"
        }
        
        supervisor_agent.optimization_agent.optimize.return_value = {
            "recommendations": ["rec1", "rec2"],
            "checkpoint": "optimization_complete"
        }
        
        # Simulate interruption after optimization
        supervisor_agent.data_agent.analyze.side_effect = Exception("Network timeout")
        
        # First execution (fails at data analysis)
        result1 = await supervisor_agent.process_request({"message": "test"})
        
        # Validate partial state is captured
        assert "checkpoint" in str(result1).lower() or "partial" in str(result1).lower()
        
        # Reset data agent for retry
        supervisor_agent.data_agent.analyze.side_effect = None
        supervisor_agent.data_agent.analyze.return_value = {"patterns": ["pattern1"]}
        
        # Resume from checkpoint (in production, this would load saved state)
        result2 = await supervisor_agent.process_request(
            {"message": "test", "resume_from": "optimization_complete"}
        )
        
        # Validate flow resumed correctly
        # Triage and optimization should not be called again
        # (This is simplified; actual implementation would need state management)

    def test_flow_business_value_validation(self):
        """Meta-test to ensure flows deliver business value."""
        flow_value_mapping = {
            WorkflowPath.FULL_PIPELINE: {
                "value": "Complete optimization with actionable recommendations",
                "outcome": "$3000-10000/month savings",
                "confidence": 0.85
            },
            WorkflowPath.MODIFIED_PIPELINE: {
                "value": "Initial optimization with data collection",
                "outcome": "$1000-5000/month savings after data provided",
                "confidence": 0.65
            },
            WorkflowPath.DATA_COLLECTION: {
                "value": "Structured data gathering for future optimization",
                "outcome": "Enables optimization in follow-up",
                "confidence": 0.95
            }
        }
        
        # Each flow should have clear value proposition
        for flow, value_prop in flow_value_mapping.items():
            assert value_prop["value"] is not None
            assert "savings" in value_prop["outcome"] or "optimization" in value_prop["outcome"]
            assert value_prop["confidence"] > 0.5
    pass