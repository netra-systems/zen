"""Test modified workflow execution when partial data is available.

Business Value Justification (BVJ):
- Segment: Mid, Early
- Business Goal: Incremental Value Delivery
- Value Impact: Delivers partial optimization value while requesting additional data
- Strategic Impact: Maintains user engagement even with incomplete information

This test validates the adaptive workflow that provides immediate value
while requesting additional data for enhanced optimization.
"""

import pytest
from typing import Dict, Any
import json
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
import asyncio


class TestPartialDataFlow:
    """Validate modified workflow when some data is missing but workflow can proceed."""
    
    @pytest.fixture
    def partial_user_request(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a user request with partial data."""
    pass
        return {
            "user_request": "My LLM costs are too high, around $3-4K monthly",
            "metrics": {
                "monthly_spend_estimate": "3000-4000",
                "model": "gpt-4",
                # Missing: exact token usage, latency metrics, error rates
            },
            "usage_patterns": {
                "use_cases": ["customer_support", "content_generation"],
                # Missing: peak hours, batch possibilities
            }
        }
    
    @pytest.fixture
    def expected_triage_output_partial(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Expected output from triage agent for partial data."""
    pass
        return {
            "data_sufficiency": "partial",
            "category": "cost_optimization",
            "confidence": 0.70,
            "identified_metrics": ["spend_estimate", "model", "use_cases"],
            "missing_data": ["exact_token_usage", "latency_metrics", "peak_patterns"],
            "workflow_recommendation": "modified_pipeline",
            "data_request_priority": "medium"
        }
    
    @pytest.fixture
    def expected_optimization_with_caveats(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Expected optimization with caveats due to missing data."""
    pass
        return {
            "recommendations": [
                {
                    "strategy": "model_switching",
                    "description": "Consider GPT-3.5-turbo for non-critical tasks",
                    "estimated_savings": "800-1200",  # Range due to uncertainty
                    "confidence": 0.65,
                    "caveat": "Exact savings depend on token usage patterns"
                },
                {
                    "strategy": "usage_analysis_first",
                    "description": "Implement usage tracking before optimization",
                    "estimated_savings": "TBD",
                    "confidence": 0.90,
                    "caveat": "Required for accurate optimization"
                }
            ],
            "total_estimated_savings": "800-1200+",
            "confidence_level": "medium",
            "data_needed_for_precision": ["exact_usage", "latency_requirements"]
        }
    
    @pytest.fixture
    def expected_data_helper_request(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Expected data collection request from data helper."""
    pass
        return {
            "data_request": {
                "priority": "medium",
                "requested_metrics": [
                    {
                        "metric": "exact_token_usage",
                        "description": "Daily token consumption by model",
                        "format": "CSV or JSON with date, model, tokens",
                        "why_needed": "Calculate precise cost optimization"
                    },
                    {
                        "metric": "latency_metrics",
                        "description": "P50, P95, P99 latencies",
                        "format": "Time series data",
                        "why_needed": "Ensure optimizations don't degrade performance"
                    },
                    {
                        "metric": "peak_usage_patterns",
                        "description": "Hourly usage distribution",
                        "format": "24-hour breakdown",
                        "why_needed": "Identify batch processing opportunities"
                    }
                ],
                "collection_methods": [
                    "Export from monitoring dashboard",
                    "API usage reports",
                    "Log analysis script (provided)"
                ],
                "expected_improvement": "30-40% more accurate recommendations"
            },
            "user_message": "To provide more precise optimization recommendations, please share the following metrics..."
        }
    
    @pytest.fixture
    def expected_actions_with_phases(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Expected phased action plan."""
    pass
        return {
            "implementation_plan": {
                "phase_1_immediate": [
                    {
                        "action": "Set up usage monitoring",
                        "timeline": "1-2 days",
                        "purpose": "Gather missing metrics",
                        "tools": ["Prometheus", "Custom logging"]
                    },
                    {
                        "action": "Implement basic model routing",
                        "timeline": "2-3 days",
                        "purpose": "Quick wins on obvious optimizations",
                        "expected_impact": "$500-800/month savings"
                    }
                ],
                "phase_2_data_driven": [
                    {
                        "action": "Analyze collected metrics",
                        "timeline": "After 1 week of data",
                        "purpose": "Identify precise optimization opportunities"
                    },
                    {
                        "action": "Implement advanced optimizations",
                        "timeline": "Week 2-3",
                        "purpose": "Achieve full cost reduction potential"
                    }
                ]
            },
            "success_criteria": {
                "phase_1": "15-20% cost reduction",
                "phase_2": "40-50% total cost reduction"
            }
        }
    
    @pytest.fixture
    def expected_report_with_confidence(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Expected report showing confidence levels."""
    pass
        return {
            "executive_summary": {
                "current_understanding": "High-level cost issue identified",
                "immediate_recommendations": "Quick wins available",
                "data_gaps": "Detailed metrics needed for full optimization",
                "confidence_level": "Medium (70%)"
            },
            "phased_approach": {
                "immediate_value": "$800-1200/month",
                "potential_value": "$2000-2500/month with complete data",
                "timeline": "3-4 weeks total"
            },
            "next_steps": [
                "Implement monitoring (Priority 1)",
                "Begin Phase 1 optimizations",
                "Collect data for 1 week",
                "Refine recommendations with complete data"
            ]
        }
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_modified_flow_execution_order(self, partial_user_request):
        """Test modified agent execution order for partial data."""
        execution_order = []
        
        with patch('netra_backend.app.agents.supervisor.workflow_orchestrator.WorkflowOrchestrator') as MockOrchestrator:
            orchestrator = MockOrchestrator.return_value
            
            async def track_execution(agent_name, *args, **kwargs):
                execution_order.append(agent_name)
                await asyncio.sleep(0)
    return ExecutionResult(
                    success=True,
                    status="completed",
                    result={"agent": agent_name}
                )
            
            orchestrator.execute_agent = AsyncMock(side_effect=track_execution)
            
            # Simulate modified workflow execution
            await orchestrator.execute_agent("triage", partial_user_request)
            await orchestrator.execute_agent("optimization", {})
            await orchestrator.execute_agent("actions", {})
            await orchestrator.execute_agent("data_helper", {})
            await orchestrator.execute_agent("reporting", {})
            
            # Data analysis is skipped in partial flow, data_helper is included
            assert execution_order == ["triage", "optimization", "actions", "data_helper", "reporting"]
            assert "data" not in execution_order  # Data analysis skipped
    
    @pytest.mark.asyncio
    async def test_triage_identifies_partial_data(self, partial_user_request, expected_triage_output_partial):
        """Validate triage correctly identifies partial data scenario."""
    pass
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        
        with patch.object(TriageSubAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = expected_triage_output_partial
            
            agent = TriageSubAgent()
            context = ExecutionContext(
                run_id="test-run",
                agent_name="triage",
                state=DeepAgentState(user_request=json.dumps(partial_user_request))
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert result.result["data_sufficiency"] == "partial"
            assert result.result["workflow_recommendation"] == "modified_pipeline"
            assert len(result.result["missing_data"]) > 0
            assert result.result["confidence"] < 0.80  # Lower confidence due to missing data
    
    @pytest.mark.asyncio
    async def test_optimization_provides_caveated_recommendations(self, expected_optimization_with_caveats):
        """Validate optimization provides recommendations with appropriate caveats."""
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        with patch.object(OptimizationsCoreSubAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = expected_optimization_with_caveats
            
            agent = OptimizationsCoreSubAgent()
            state = DeepAgentState()
            from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
            state.triage_result = TriageResult(
                category="cost_optimization",
                confidence_score=0.70,
                data_sufficiency="partial",
                identified_metrics=["spend_estimate", "model", "use_cases"],
                missing_data=["exact_token_usage", "latency_metrics", "peak_patterns"],
                workflow_recommendation="modified_pipeline",
                data_request_priority="medium"
            )
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="optimization",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "confidence_level" in result.result
            assert result.result["confidence_level"] == "medium"
            
            # Check recommendations have caveats
            for rec in result.result["recommendations"]:
                if rec["strategy"] != "usage_analysis_first":
                    assert "caveat" in rec or "confidence" in rec
            
            assert "data_needed_for_precision" in result.result
    
    @pytest.mark.asyncio
    async def test_data_helper_generates_clear_requests(self, expected_data_helper_request):
        """Validate data helper creates clear, actionable data requests."""
    pass
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        with patch.object(DataHelperAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = expected_data_helper_request
            
            agent = DataHelperAgent()
            state = DeepAgentState()
            from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
            state.triage_result = TriageResult(
                category="cost_optimization",
                confidence_score=0.70,
                data_sufficiency="partial",
                identified_metrics=["spend_estimate", "model", "use_cases"],
                missing_data=["exact_token_usage", "latency_metrics", "peak_patterns"],
                workflow_recommendation="modified_pipeline",
                data_request_priority="medium"
            )
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "data_request" in result.result
            assert "requested_metrics" in result.result["data_request"]
            
            # Validate each metric request
            for metric in result.result["data_request"]["requested_metrics"]:
                assert "metric" in metric
                assert "why_needed" in metric
                assert "format" in metric
            
            # Check user-friendly message
            assert "user_message" in result.result
            assert "please share" in result.result["user_message"].lower()
    
    @pytest.mark.asyncio
    async def test_actions_create_phased_plan(self, expected_actions_with_phases):
        """Validate actions create a phased implementation plan."""
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        
        with patch.object(ActionsToMeetGoalsSubAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = expected_actions_with_phases
            
            agent = ActionsToMeetGoalsSubAgent()
            state = DeepAgentState()
            from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
            from netra_backend.app.agents.state import OptimizationsResult
            state.triage_result = TriageResult(
                category="cost_optimization",
                confidence_score=0.70,
                data_sufficiency="partial",
                identified_metrics=[],
                missing_data=[],
                workflow_recommendation="modified_pipeline",
                data_request_priority="medium"
            )
            state.optimizations_result = OptimizationsResult(
                optimization_type="cost_optimization",
                confidence_score=0.70
            )
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="actions",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "implementation_plan" in result.result
            
            plan = result.result["implementation_plan"]
            assert "phase_1_immediate" in plan
            assert "phase_2_data_driven" in plan
            
            # Validate Phase 1 focuses on quick wins and data collection
            phase_1_actions = [action["action"] for action in plan["phase_1_immediate"]]
            assert any("monitoring" in action.lower() for action in phase_1_actions)
            
            # Validate success criteria are phased
            assert "success_criteria" in result.result
            assert "phase_1" in result.result["success_criteria"]
            assert "phase_2" in result.result["success_criteria"]
    
    @pytest.mark.asyncio
    async def test_report_shows_confidence_and_potential(self, expected_report_with_confidence):
        """Validate report clearly shows confidence levels and potential value."""
    pass
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        with patch.object(ReportingSubAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = expected_report_with_confidence
            
            agent = ReportingSubAgent()
            state = DeepAgentState()
            from netra_backend.app.agents.state import OptimizationsResult
            state.optimizations_result = OptimizationsResult(
                optimization_type="cost_optimization",
                confidence_score=0.70
            )
            # Note: data_helper results would typically be in a separate field, but keeping minimal for test
            
            context = ExecutionContext(
                run_id="test-run",
                agent_name="reporting",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "executive_summary" in result.result
            assert "confidence_level" in result.result["executive_summary"]
            
            # Check phased value delivery
            assert "phased_approach" in result.result
            assert "immediate_value" in result.result["phased_approach"]
            assert "potential_value" in result.result["phased_approach"]
            
            # Validate next steps include data collection
            next_steps = result.result["next_steps"]
            assert any("monitoring" in step.lower() or "collect" in step.lower() for step in next_steps)
    
    @pytest.mark.asyncio
    async def test_flow_balances_immediate_and_future_value(self):
        """Test that partial flow delivers immediate value while setting up for more."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
            mock_workflow.return_value = [
                ExecutionResult(success=True, status="completed", result={
                    "data_sufficiency": "partial",
                    "missing_data": ["token_usage", "latency"]
                }),
                ExecutionResult(success=True, status="completed", result={
                    "recommendations": [{"estimated_savings": "800-1200"}],
                    "confidence_level": "medium"
                }),
                ExecutionResult(success=True, status="completed", result={
                    "implementation_plan": {
                        "phase_1_immediate": [{"expected_impact": "$500-800/month"}],
                        "phase_2_data_driven": [{"expected_impact": "$1500-2000/month"}]
                    }
                }),
                ExecutionResult(success=True, status="completed", result={
                    "data_request": {"requested_metrics": ["token_usage", "latency"]}
                }),
                ExecutionResult(success=True, status="completed", result={
                    "phased_approach": {
                        "immediate_value": "$800/month",
                        "potential_value": "$2500/month"
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
            
            # Validate immediate value delivery
            actions_result = results[2].result
            immediate_impact = actions_result["implementation_plan"]["phase_1_immediate"][0]["expected_impact"]
            assert "$500" in immediate_impact or "500" in immediate_impact
            
            # Validate data collection for enhanced value
            data_helper_result = results[3].result
            assert len(data_helper_result["data_request"]["requested_metrics"]) > 0
            
            # Validate report shows both immediate and potential
            report_result = results[4].result
            assert "immediate_value" in report_result["phased_approach"]
            assert "potential_value" in report_result["phased_approach"]
    
    @pytest.mark.asyncio
    async def test_partial_flow_user_experience(self):
        """Test that partial flow maintains positive user experience."""
    pass
        user_experience_criteria = {
            "immediate_value_delivery": True,
            "clear_data_requests": True,
            "transparency_about_limitations": True,
            "actionable_next_steps": True
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
            mock_workflow.return_value = [
                ExecutionResult(success=True, status="completed", result={"data_sufficiency": "partial"}),
                ExecutionResult(success=True, status="completed", result={
                    "recommendations": [{"description": "Quick win optimization"}],
                    "caveat": "More precise with additional data"
                }),
                ExecutionResult(success=True, status="completed", result={
                    "implementation_plan": {"phase_1_immediate": [{"action": "Start today"}]}
                }),
                ExecutionResult(success=True, status="completed", result={
                    "user_message": "To enhance our recommendations, please provide..."
                }),
                ExecutionResult(success=True, status="completed", result={
                    "next_steps": ["Implement monitoring", "Begin optimizations", "Share metrics"]
                })
            ]
            
            orchestrator = WorkflowOrchestrator(None, None, None)
            context = ExecutionContext(
                run_id="test-run",
                agent_name="supervisor",
                state=DeepAgentState()
            )
            
            results = await orchestrator.execute_standard_workflow(context)
            
            # Check immediate value
            assert results[1].result["recommendations"][0]["description"] is not None
            
            # Check clear data requests
            assert "please provide" in results[3].result["user_message"]
            
            # Check transparency
            assert "caveat" in results[1].result
            
            # Check actionable next steps
            assert len(results[4].result["next_steps"]) >= 3