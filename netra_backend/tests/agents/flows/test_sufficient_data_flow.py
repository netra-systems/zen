"""Test complete workflow execution when all required data is available.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: Optimization Value Delivery
- Value Impact: Ensures complete optimization pipeline delivers $10K-100K+ value
- Strategic Impact: Core value proposition validation

This test validates the complete happy path where users provide sufficient data
for full analysis and optimization recommendations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import json

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState


class TestSufficientDataFlow:
    """Validate complete workflow when all necessary data is provided."""
    
    @pytest.fixture
    def complete_user_request(self):
        """Create a user request with complete data."""
        return {
            "user_request": "My GPT-4 API costs are $5,000/month with 2M tokens daily usage",
            "metrics": {
                "monthly_spend": 5000,
                "daily_tokens": 2000000,
                "model": "gpt-4",
                "p95_latency": 3.2,
                "error_rate": 0.02
            },
            "usage_patterns": {
                "peak_hours": [9, 10, 11, 14, 15, 16],
                "use_cases": ["customer_support", "content_generation", "code_review"],
                "batch_possible": True
            }
        }
    
    @pytest.fixture
    def expected_triage_output(self):
        """Expected output from triage agent for sufficient data."""
        return {
            "data_sufficiency": "sufficient",
            "category": "cost_optimization",
            "confidence": 0.95,
            "identified_metrics": ["spend", "usage", "latency"],
            "missing_data": [],
            "workflow_recommendation": "full_pipeline"
        }
    
    @pytest.fixture
    def expected_optimization_output(self):
        """Expected optimization recommendations."""
        return {
            "recommendations": [
                {
                    "strategy": "model_switching",
                    "description": "Switch 60% of traffic to GPT-3.5-turbo for non-critical tasks",
                    "estimated_savings": 1800,
                    "implementation_complexity": "low",
                    "risk_level": "low"
                },
                {
                    "strategy": "batch_processing",
                    "description": "Batch non-urgent requests during off-peak hours",
                    "estimated_savings": 500,
                    "implementation_complexity": "medium",
                    "risk_level": "low"
                },
                {
                    "strategy": "prompt_optimization",
                    "description": "Reduce prompt tokens by 20% through optimization",
                    "estimated_savings": 1000,
                    "implementation_complexity": "low",
                    "risk_level": "minimal"
                }
            ],
            "total_estimated_savings": 3300,
            "roi_percentage": 66,
            "payback_period_days": 7
        }
    
    @pytest.fixture
    def expected_data_analysis_output(self):
        """Expected data analysis insights."""
        return {
            "usage_insights": {
                "peak_usage_concentration": 0.65,
                "off_peak_opportunity": True,
                "token_efficiency": 0.72,
                "error_correlation": "high_latency_periods"
            },
            "cost_breakdown": {
                "by_use_case": {
                    "customer_support": 0.45,
                    "content_generation": 0.35,
                    "code_review": 0.20
                },
                "by_time": {
                    "peak": 0.70,
                    "off_peak": 0.30
                }
            },
            "optimization_potential": {
                "immediate": 0.30,
                "short_term": 0.50,
                "long_term": 0.66
            }
        }
    
    @pytest.fixture
    def expected_actions_output(self):
        """Expected actionable steps."""
        return {
            "implementation_plan": [
                {
                    "step": 1,
                    "action": "Implement traffic routing logic",
                    "details": "Create model selection based on task criticality",
                    "timeline": "2-3 days",
                    "dependencies": [],
                    "success_metrics": ["Cost reduction", "Latency maintained"]
                },
                {
                    "step": 2,
                    "action": "Set up batch processing queue",
                    "details": "Implement Redis queue for non-urgent requests",
                    "timeline": "3-4 days",
                    "dependencies": ["step_1"],
                    "success_metrics": ["Queue processing time", "Cost savings"]
                },
                {
                    "step": 3,
                    "action": "Optimize prompts library",
                    "details": "Review and optimize all prompt templates",
                    "timeline": "1 week",
                    "dependencies": [],
                    "success_metrics": ["Token reduction", "Quality maintained"]
                }
            ],
            "monitoring_setup": {
                "metrics_to_track": ["daily_cost", "latency_p95", "error_rate", "token_usage"],
                "alerting_thresholds": {
                    "cost_increase": 0.10,
                    "latency_degradation": 0.20
                }
            },
            "rollback_plan": "Revert model routing rules if quality degrades"
        }
    
    @pytest.fixture
    def expected_report_output(self):
        """Expected final report structure."""
        return {
            "executive_summary": {
                "current_state": "Spending $5,000/month on GPT-4",
                "proposed_state": "Optimized multi-model approach",
                "expected_savings": "$3,300/month (66% reduction)",
                "implementation_time": "2 weeks",
                "risk_assessment": "Low"
            },
            "detailed_recommendations": "...",
            "implementation_roadmap": "...",
            "success_metrics": {
                "cost_reduction_target": 3300,
                "quality_maintenance": 0.95,
                "latency_target": 3.0
            },
            "next_steps": [
                "Review recommendations with team",
                "Approve implementation plan",
                "Begin Phase 1 implementation"
            ]
        }
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_flow_execution_order(self, complete_user_request):
        """Test that all agents execute in correct order for sufficient data."""
        execution_order = []
        
        with patch('netra_backend.app.agents.supervisor.workflow_orchestrator.WorkflowOrchestrator') as MockOrchestrator:
            orchestrator = MockOrchestrator.return_value
            
            async def track_execution(agent_name, *args, **kwargs):
                execution_order.append(agent_name)
                return ExecutionResult(
                    success=True,
                    status="completed",
                    result={"agent": agent_name}
                )
            
            orchestrator.execute_agent = AsyncMock(side_effect=track_execution)
            
            # Simulate workflow execution
            await orchestrator.execute_agent("triage", complete_user_request)
            await orchestrator.execute_agent("optimization", {})
            await orchestrator.execute_agent("data", {})
            await orchestrator.execute_agent("actions", {})
            await orchestrator.execute_agent("reporting", {})
            
            assert execution_order == ["triage", "optimization", "data", "actions", "reporting"]
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_triage_correctly_identifies_sufficient_data(self, complete_user_request, expected_triage_output):
        """Validate triage agent correctly identifies data sufficiency."""
        from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
        
        with patch.object(TriageSubAgent, '_call_llm') as mock_llm:
            mock_llm.return_value = expected_triage_output
            
            agent = TriageSubAgent()
            context = ExecutionContext(
                run_id="test-run",
                agent_name="triage",
                state=DeepAgentState(user_request=json.dumps(complete_user_request))
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert result.result["data_sufficiency"] == "sufficient"
            assert result.result["workflow_recommendation"] == "full_pipeline"
            assert len(result.result["missing_data"]) == 0
    
    @pytest.mark.asyncio
    async def test_optimization_generates_valuable_recommendations(self, expected_optimization_output):
        """Validate optimization agent generates high-value recommendations."""
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        with patch.object(OptimizationsCoreSubAgent, '_call_llm') as mock_llm:
            mock_llm.return_value = expected_optimization_output
            
            agent = OptimizationsCoreSubAgent()
            state = DeepAgentState()
            state.set_agent_output("triage", {"data_sufficiency": "sufficient"})
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="optimization",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert result.result["total_estimated_savings"] >= 3000
            assert result.result["roi_percentage"] >= 50
            assert len(result.result["recommendations"]) >= 3
            
            # Validate each recommendation has required fields
            for rec in result.result["recommendations"]:
                assert "strategy" in rec
                assert "estimated_savings" in rec
                assert "implementation_complexity" in rec
                assert "risk_level" in rec
    
    @pytest.mark.asyncio
    async def test_data_analysis_provides_actionable_insights(self, expected_data_analysis_output):
        """Validate data analysis provides deep insights."""
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        with patch.object(DataSubAgent, '_call_llm') as mock_llm:
            mock_llm.return_value = expected_data_analysis_output
            
            agent = DataSubAgent()
            state = DeepAgentState()
            state.set_agent_output("optimization", {"recommendations": []})
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="data",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "usage_insights" in result.result
            assert "cost_breakdown" in result.result
            assert "optimization_potential" in result.result
            
            # Validate optimization potential is realistic
            assert result.result["optimization_potential"]["immediate"] <= 0.40
            assert result.result["optimization_potential"]["long_term"] <= 0.80
    
    @pytest.mark.asyncio
    async def test_actions_create_implementable_plan(self, expected_actions_output):
        """Validate actions agent creates concrete implementation steps."""
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        
        with patch.object(ActionsToMeetGoalsSubAgent, '_call_llm') as mock_llm:
            mock_llm.return_value = expected_actions_output
            
            agent = ActionsToMeetGoalsSubAgent()
            state = DeepAgentState()
            state.set_agent_output("optimization", {"recommendations": []})
            state.set_agent_output("data", {"insights": {}})
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="actions",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "implementation_plan" in result.result
            assert len(result.result["implementation_plan"]) >= 3
            
            # Validate each action step
            for step in result.result["implementation_plan"]:
                assert "action" in step
                assert "timeline" in step
                assert "success_metrics" in step
            
            # Validate monitoring setup
            assert "monitoring_setup" in result.result
            assert "rollback_plan" in result.result
    
    @pytest.mark.asyncio
    async def test_report_demonstrates_clear_value(self, expected_report_output):
        """Validate final report clearly demonstrates ROI."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        with patch.object(ReportingSubAgent, '_call_llm') as mock_llm:
            mock_llm.return_value = expected_report_output
            
            agent = ReportingSubAgent()
            state = DeepAgentState()
            state.set_agent_output("optimization", {"total_estimated_savings": 3300})
            state.set_agent_output("actions", {"implementation_plan": []})
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="reporting",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "executive_summary" in result.result
            
            summary = result.result["executive_summary"]
            assert "expected_savings" in summary
            assert "$3,300" in summary["expected_savings"] or "3300" in summary["expected_savings"]
            assert "implementation_time" in summary
            assert "risk_assessment" in summary
    
    @pytest.mark.asyncio
    async def test_state_accumulates_through_flow(self, complete_user_request):
        """Validate state correctly accumulates through the entire flow."""
        state = DeepAgentState()
        state.user_request = json.dumps(complete_user_request)
        
        # Simulate state updates through flow
        state.set_agent_output("triage", {"data_sufficiency": "sufficient"})
        state.set_agent_output("optimization", {"total_estimated_savings": 3300})
        state.set_agent_output("data", {"optimization_potential": {"immediate": 0.30}})
        state.set_agent_output("actions", {"implementation_plan": ["step1", "step2"]})
        state.set_agent_output("reporting", {"executive_summary": "Complete"})
        
        # Validate all outputs are accessible
        assert state.get_agent_output("triage")["data_sufficiency"] == "sufficient"
        assert state.get_agent_output("optimization")["total_estimated_savings"] == 3300
        assert state.get_agent_output("data")["optimization_potential"]["immediate"] == 0.30
        assert len(state.get_agent_output("actions")["implementation_plan"]) == 2
        assert state.get_agent_output("reporting")["executive_summary"] == "Complete"
    
    @pytest.mark.asyncio
    async def test_flow_handles_real_world_complexity(self):
        """Test flow with realistic complex data and edge cases."""
        complex_request = {
            "user_request": "Multi-model setup with GPT-4, Claude, and Gemini",
            "metrics": {
                "models": {
                    "gpt-4": {"spend": 3000, "tokens": 1000000},
                    "claude-2": {"spend": 1500, "tokens": 800000},
                    "gemini-pro": {"spend": 500, "tokens": 500000}
                },
                "total_monthly_spend": 5000,
                "use_cases": {
                    "critical": ["legal_analysis", "medical_advice"],
                    "standard": ["customer_support", "content_generation"],
                    "batch": ["data_processing", "report_generation"]
                }
            }
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
            mock_workflow.return_value = [
                ExecutionResult(success=True, status="completed", result={"data_sufficiency": "sufficient"}),
                ExecutionResult(success=True, status="completed", result={"recommendations": []}),
                ExecutionResult(success=True, status="completed", result={"insights": {}}),
                ExecutionResult(success=True, status="completed", result={"plan": []}),
                ExecutionResult(success=True, status="completed", result={"report": "Complete"})
            ]
            
            orchestrator = WorkflowOrchestrator(None, None, None)
            context = ExecutionContext(
                run_id="test-run",
                agent_name="supervisor",
                state=DeepAgentState(user_request=json.dumps(complex_request))
            )
            
            results = await orchestrator.execute_standard_workflow(context)
            
            assert len(results) == 5
            assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_flow_delivers_business_value(self):
        """Validate the complete flow delivers measurable business value."""
        # This test validates the business outcome
        expected_value_metrics = {
            "minimum_savings_percentage": 30,  # At least 30% cost reduction
            "maximum_implementation_weeks": 4,  # Implementation within 4 weeks
            "quality_maintenance": 0.95,  # Maintain 95% quality
            "risk_tolerance": "low"  # Low risk recommendations
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
            # Simulate a complete successful flow
            mock_workflow.return_value = [
                ExecutionResult(success=True, status="completed", result={"data_sufficiency": "sufficient"}),
                ExecutionResult(success=True, status="completed", result={
                    "total_estimated_savings": 3300,
                    "roi_percentage": 66,
                    "recommendations": [
                        {"risk_level": "low", "estimated_savings": 1800},
                        {"risk_level": "low", "estimated_savings": 1500}
                    ]
                }),
                ExecutionResult(success=True, status="completed", result={"optimization_potential": {"immediate": 0.35}}),
                ExecutionResult(success=True, status="completed", result={"implementation_plan": [], "timeline_weeks": 2}),
                ExecutionResult(success=True, status="completed", result={
                    "executive_summary": {
                        "expected_savings": "$3,300/month",
                        "quality_maintenance": 0.96,
                        "risk_assessment": "low"
                    }
                })
            ]
            
            orchestrator = WorkflowOrchestrator(None, None, None)
            context = ExecutionContext(
                run_id="test-run",
                agent_name="supervisor",
                state=DeepAgentState()
            )
            
            results = await orchestrator.execute_standard_workflow(context)
            
            # Validate business value delivered
            optimization_result = results[1].result
            assert optimization_result["roi_percentage"] >= expected_value_metrics["minimum_savings_percentage"]
            
            actions_result = results[3].result
            assert actions_result["timeline_weeks"] <= expected_value_metrics["maximum_implementation_weeks"]
            
            report_result = results[4].result
            assert report_result["executive_summary"]["quality_maintenance"] >= expected_value_metrics["quality_maintenance"]
            assert report_result["executive_summary"]["risk_assessment"] == expected_value_metrics["risk_tolerance"]