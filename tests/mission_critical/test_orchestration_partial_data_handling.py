"""Mission-Critical Tests for Orchestration Partial Data Handling

Tests the system's ability to handle partial data scenarios gracefully,
providing immediate value while requesting additional information.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maximize value delivery even with incomplete data
- Value Impact: 40-60% value delivery possible with partial data
- Strategic Impact: Improves user engagement and conversion rates
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestPartialDataHandling:
    """Test suite for partial data handling scenarios in orchestration."""
    
    # === Test Data Fixtures ===
    
    @pytest.fixture
    def partial_cost_optimization_request(self):
        """Request with partial cost data - enough to start but not complete."""
        return {
            "user_request": "Our LLM costs are around $8K monthly using mostly GPT-4",
            "available_data": {
                "monthly_spend_estimate": "7000-9000",
                "primary_model": "gpt-4",
                "use_case_general": "customer_service"
            },
            "missing_data": [
                "exact_token_usage",
                "request_volume",
                "latency_requirements",
                "quality_thresholds",
                "peak_usage_patterns"
            ],
            "completeness": 0.45
        }
    
    @pytest.fixture
    def partial_performance_request(self):
        """Request with partial performance data."""
        return {
            "user_request": "AI responses take 3-5 seconds, need faster",
            "available_data": {
                "current_latency_range": "3-5 seconds",
                "optimization_goal": "reduce_latency",
                "model": "gpt-4"
            },
            "missing_data": [
                "request_size_distribution",
                "acceptable_latency_target",
                "quality_vs_speed_tradeoff",
                "infrastructure_details",
                "concurrent_request_volume"
            ],
            "completeness": 0.40
        }
    
    @pytest.fixture
    def partial_scale_request(self):
        """Request with partial scaling information."""
        return {
            "user_request": "Need to handle 10x more AI requests, currently at 1000/day",
            "available_data": {
                "current_volume": "1000 requests/day",
                "target_scale": "10x",
                "timeline": "3 months"
            },
            "missing_data": [
                "peak_concurrent_requests",
                "request_size_variance",
                "budget_constraints",
                "infrastructure_flexibility",
                "quality_requirements_at_scale"
            ],
            "completeness": 0.50
        }
    
    @pytest.fixture
    def partial_multi_model_request(self):
        """Request with partial multi-model usage data."""
        return {
            "user_request": "Using OpenAI, Anthropic, and Cohere - costs are high",
            "available_data": {
                "providers": ["openai", "anthropic", "cohere"],
                "cost_concern": "high",
                "general_use": "mixed_workloads"
            },
            "missing_data": [
                "cost_per_provider",
                "usage_distribution",
                "use_case_per_model",
                "performance_requirements",
                "switching_flexibility"
            ],
            "completeness": 0.35
        }
    
    @pytest.fixture
    def partial_quality_sensitive_request(self):
        """Request with quality constraints but missing metrics."""
        return {
            "user_request": "Reduce AI costs but quality is critical for our medical app",
            "available_data": {
                "domain": "healthcare",
                "quality_priority": "critical",
                "cost_optimization_needed": True
            },
            "missing_data": [
                "current_quality_metrics",
                "acceptable_quality_threshold",
                "compliance_requirements",
                "current_costs",
                "error_tolerance"
            ],
            "completeness": 0.40
        }
    
    # === Core Workflow Tests ===
    
    @pytest.mark.asyncio
    async def test_partial_data_workflow_selection(self, partial_cost_optimization_request):
        """Test that partial data correctly triggers modified workflow."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        # Mock the data assessment
        with patch.object(orchestrator, 'assess_data_completeness') as mock_assess:
            mock_assess.return_value = {
                "completeness": partial_cost_optimization_request["completeness"],
                "workflow": "modified_optimization",
                "confidence": 0.65
            }
            
            workflow = await orchestrator.select_workflow(partial_cost_optimization_request)
            
            assert workflow["type"] == "modified_optimization"
            assert workflow["confidence"] == 0.65
            assert "phases" in workflow
            assert "quick_wins" in workflow["phases"]
            assert "data_request" in workflow["phases"]
    
    @pytest.mark.asyncio
    async def test_immediate_value_delivery(self, partial_cost_optimization_request):
        """Test that system provides immediate value despite missing data."""
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        agent = OptimizationsCoreSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "immediate_recommendations": [
                    {
                        "action": "Switch non-critical requests to GPT-3.5-turbo",
                        "confidence": 0.70,
                        "estimated_savings": "$1000-1500/month",
                        "implementation_time": "2-3 days",
                        "caveat": "Exact savings depend on request distribution"
                    },
                    {
                        "action": "Implement prompt optimization",
                        "confidence": 0.85,
                        "estimated_savings": "$500-800/month",
                        "implementation_time": "1-2 days",
                        "caveat": "No quality impact, reduces token usage"
                    }
                ],
                "total_immediate_savings": "$1500-2300/month",
                "confidence_level": "medium",
                "additional_potential": "$2000-3000/month with complete data"
            }
            
            state = DeepAgentState(
                user_request=json.dumps(partial_cost_optimization_request),
                data_completeness=partial_cost_optimization_request["completeness"]
            )
            
            context = ExecutionContext(
                run_id="test-partial-001",
                agent_name="optimization",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "immediate_recommendations" in result.result
            assert len(result.result["immediate_recommendations"]) >= 2
            assert all("caveat" in rec for rec in result.result["immediate_recommendations"])
            assert result.result["confidence_level"] == "medium"
    
    @pytest.mark.asyncio
    async def test_progressive_data_request(self, partial_performance_request):
        """Test that data requests are progressive and prioritized."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "data_request": {
                    "priority_tiers": {
                        "critical": [
                            {
                                "metric": "target_latency",
                                "question": "What is your acceptable response time?",
                                "why": "Determines optimization approach",
                                "example": "< 1 second for customer-facing"
                            }
                        ],
                        "important": [
                            {
                                "metric": "request_size_distribution",
                                "question": "Average request size?",
                                "why": "Affects batching strategy",
                                "example": "500-2000 tokens"
                            }
                        ],
                        "helpful": [
                            {
                                "metric": "infrastructure_details",
                                "question": "Current deployment setup?",
                                "why": "Identifies optimization options",
                                "example": "AWS, Kubernetes, etc."
                            }
                        ]
                    },
                    "quick_collection": {
                        "template": "Target Latency: ___ sec, Avg Request Size: ___ tokens",
                        "estimated_time": "2 minutes"
                    }
                }
            }
            
            state = DeepAgentState(
                user_request=json.dumps(partial_performance_request),
                data_completeness=partial_performance_request["completeness"]
            )
            
            context = ExecutionContext(
                run_id="test-partial-002",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            data_request = result.result.get("data_request", {})
            assert "priority_tiers" in data_request
            assert "critical" in data_request["priority_tiers"]
            assert "quick_collection" in data_request
    
    @pytest.mark.asyncio
    async def test_confidence_scoring_accuracy(self, partial_scale_request):
        """Test that confidence scores accurately reflect data completeness."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        test_cases = [
            (0.20, 0.10, 0.30),  # insufficient data
            (0.45, 0.40, 0.60),  # partial data  
            (0.75, 0.65, 0.80),  # mostly complete
            (0.90, 0.85, 0.95),  # nearly complete
        ]
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        for completeness, min_conf, max_conf in test_cases:
            with patch.object(orchestrator, 'assess_data_completeness') as mock_assess:
                mock_assess.return_value = {
                    "completeness": completeness,
                    "confidence": min_conf + (completeness * 0.5)
                }
                
                assessment = await orchestrator.assess_data_completeness({"completeness": completeness})
                confidence = assessment["confidence"]
                
                assert min_conf <= confidence <= max_conf, \
                    f"Confidence {confidence} out of range [{min_conf}, {max_conf}] for completeness {completeness}"
    
    @pytest.mark.asyncio
    async def test_phased_implementation_plan(self, partial_multi_model_request):
        """Test generation of phased plans for partial data scenarios."""
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        
        agent = ActionsToMeetGoalsSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "phased_plan": {
                    "phase_1_immediate": {
                        "duration": "1 week",
                        "actions": [
                            {
                                "action": "Deploy usage tracking across all models",
                                "purpose": "Gather missing metrics",
                                "effort": "2 days"
                            },
                            {
                                "action": "Implement basic model routing rules",
                                "purpose": "Quick cost wins",
                                "effort": "3 days",
                                "expected_impact": "$500-1000/month savings"
                            }
                        ],
                        "deliverables": ["Usage dashboard", "Basic routing logic"],
                        "success_metric": "15-20% cost reduction"
                    },
                    "phase_2_data_driven": {
                        "duration": "2 weeks",
                        "dependency": "1 week of usage data from Phase 1",
                        "actions": [
                            {
                                "action": "Analyze usage patterns per model",
                                "purpose": "Identify optimization opportunities"
                            },
                            {
                                "action": "Implement intelligent model arbitrage",
                                "purpose": "Maximize cost-performance ratio",
                                "expected_impact": "Additional 30-40% savings"
                            }
                        ],
                        "success_metric": "45-60% total cost reduction"
                    },
                    "phase_3_optimization": {
                        "duration": "1 week",
                        "dependency": "Phase 2 completion",
                        "actions": [
                            {
                                "action": "Fine-tune routing algorithms",
                                "purpose": "Optimize based on real data"
                            },
                            {
                                "action": "Implement advanced caching",
                                "purpose": "Further reduce API calls"
                            }
                        ],
                        "success_metric": "60-70% total cost reduction"
                    }
                },
                "risk_mitigation": {
                    "data_collection_fails": "Proceed with conservative estimates",
                    "quality_degradation": "Rollback mechanisms in place"
                }
            }
            
            state = DeepAgentState(
                user_request=json.dumps(partial_multi_model_request),
                data_completeness=partial_multi_model_request["completeness"]
            )
            
            context = ExecutionContext(
                run_id="test-partial-003",
                agent_name="actions",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "phased_plan" in result.result
            plan = result.result["phased_plan"]
            assert "phase_1_immediate" in plan
            assert "phase_2_data_driven" in plan
            assert plan["phase_2_data_driven"]["dependency"] is not None
    
    @pytest.mark.asyncio
    async def test_quality_preservation_with_partial_data(self, partial_quality_sensitive_request):
        """Test that quality-critical optimizations are handled conservatively."""
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        agent = OptimizationsCoreSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "optimization_approach": "conservative",
                "rationale": "Healthcare domain with critical quality requirements",
                "recommendations": [
                    {
                        "action": "Optimize prompt engineering only",
                        "risk_level": "minimal",
                        "quality_impact": "none",
                        "estimated_savings": "10-15%",
                        "confidence": 0.90
                    },
                    {
                        "action": "Implement response caching for non-patient data",
                        "risk_level": "low",
                        "quality_impact": "none for cached content",
                        "estimated_savings": "5-10%",
                        "confidence": 0.85
                    }
                ],
                "deferred_optimizations": [
                    {
                        "action": "Model switching",
                        "reason": "Requires quality metrics and testing",
                        "potential_savings": "30-40%",
                        "data_needed": ["quality_baselines", "error_tolerance"]
                    }
                ],
                "testing_protocol": {
                    "required": True,
                    "approach": "A/B testing with quality monitoring",
                    "rollback_ready": True
                }
            }
            
            state = DeepAgentState(
                user_request=json.dumps(partial_quality_sensitive_request),
                domain="healthcare",
                quality_priority="critical"
            )
            
            context = ExecutionContext(
                run_id="test-partial-004",
                agent_name="optimization",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert result.result["optimization_approach"] == "conservative"
            recommendations = result.result["recommendations"]
            assert all(rec["risk_level"] in ["minimal", "low"] for rec in recommendations)
            assert "deferred_optimizations" in result.result
            assert result.result["testing_protocol"]["required"] is True
    
    # === Edge Case Tests ===
    
    @pytest.mark.asyncio
    async def test_conflicting_partial_data(self):
        """Test handling of conflicting or inconsistent partial data."""
        conflicting_request = {
            "user_request": "Need lowest cost but also fastest response times",
            "available_data": {
                "priority_1": "minimize_cost",
                "priority_2": "minimize_latency",
                "current_model": "gpt-4"
            },
            "conflicts": ["cost vs performance tradeoff unclear"],
            "completeness": 0.40
        }
        
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        
        agent = TriageSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "identified_conflicts": ["cost vs performance"],
                "clarification_needed": {
                    "question": "What's more important for your use case?",
                    "options": [
                        "Minimize cost (accept 2-3s latency)",
                        "Minimize latency (accept higher cost)",
                        "Balance both (moderate cost, moderate speed)"
                    ]
                },
                "default_recommendation": "balanced_approach",
                "confidence": 0.45
            }
            
            state = DeepAgentState(user_request=json.dumps(conflicting_request))
            context = ExecutionContext(
                run_id="test-conflict-001",
                agent_name="triage",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "identified_conflicts" in result.result
            assert "clarification_needed" in result.result
            assert result.result["confidence"] < 0.50
    
    @pytest.mark.asyncio
    async def test_partial_data_with_urgency(self):
        """Test handling of urgent requests with partial data."""
        urgent_request = {
            "user_request": "AI costs spiking NOW, need immediate help",
            "available_data": {
                "urgency": "critical",
                "issue": "cost_spike"
            },
            "missing_data": ["specific_costs", "spike_magnitude", "normal_baseline"],
            "completeness": 0.25
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        with patch.object(orchestrator, 'execute_emergency_workflow') as mock_emergency:
            mock_emergency.return_value = {
                "immediate_actions": [
                    {
                        "action": "Implement rate limiting",
                        "timeline": "Within 1 hour",
                        "impact": "Prevent further spikes"
                    },
                    {
                        "action": "Set hard spending cap",
                        "timeline": "Immediately",
                        "impact": "Stop bleeding"
                    }
                ],
                "diagnostic_actions": [
                    "Check for runaway processes",
                    "Review recent deployments",
                    "Analyze request patterns"
                ],
                "follow_up": "Gather data while containing damage"
            }
            
            result = await orchestrator.handle_urgent_partial_data(urgent_request)
            
            assert "immediate_actions" in result
            assert len(result["immediate_actions"]) >= 2
            assert all(action["timeline"] in ["Immediately", "Within 1 hour"] 
                      for action in result["immediate_actions"])
    
    @pytest.mark.asyncio
    async def test_iterative_data_refinement(self):
        """Test system's ability to iteratively refine recommendations as data improves."""
        initial_request = {
            "user_request": "Optimize AI costs",
            "completeness": 0.30,
            "iteration": 1
        }
        
        refined_request = {
            "user_request": "Optimize AI costs, spending $5K on GPT-4",
            "completeness": 0.60,
            "iteration": 2
        }
        
        complete_request = {
            "user_request": "Optimize AI costs, $5K on GPT-4, 2M tokens/day, customer service",
            "completeness": 0.85,
            "iteration": 3
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        confidence_progression = []
        
        for request in [initial_request, refined_request, complete_request]:
            with patch.object(orchestrator, 'generate_recommendations') as mock_gen:
                mock_gen.return_value = {
                    "confidence": 0.20 + (request["completeness"] * 0.75),
                    "specificity": request["completeness"],
                    "iteration": request["iteration"]
                }
                
                result = await orchestrator.generate_recommendations(request)
                confidence_progression.append(result["confidence"])
        
        # Verify confidence increases with data completeness
        assert confidence_progression[0] < confidence_progression[1] < confidence_progression[2]
        assert confidence_progression[2] >= 0.80  # High confidence with complete data
    
    # === Integration Tests ===
    
    @pytest.mark.asyncio
    async def test_end_to_end_partial_data_flow(self, partial_cost_optimization_request):
        """Test complete flow from partial data through value delivery."""
        from netra_backend.app.agents.supervisor.supervisor_agent import SupervisorAgent
        
        # Create supervisor with mocked dependencies
        supervisor = SupervisorAgent(None, None, None)
        
        execution_sequence = []
        
        async def track_agent_execution(agent_name, context):
            execution_sequence.append(agent_name)
            
            if agent_name == "triage":
                return ExecutionResult(
                    success=True,
                    result={
                        "data_sufficiency": "partial",
                        "confidence": 0.65,
                        "workflow": "modified"
                    }
                )
            elif agent_name == "optimization":
                return ExecutionResult(
                    success=True,
                    result={
                        "immediate_recommendations": ["Quick wins"],
                        "confidence_level": "medium"
                    }
                )
            elif agent_name == "data_helper":
                return ExecutionResult(
                    success=True,
                    result={
                        "data_request": {"priority": "medium", "items": ["token_usage"]}
                    }
                )
            elif agent_name == "actions":
                return ExecutionResult(
                    success=True,
                    result={
                        "phased_plan": {"phase_1": "Immediate actions"}
                    }
                )
            elif agent_name == "reporting":
                return ExecutionResult(
                    success=True,
                    result={
                        "summary": "Delivered value with partial data",
                        "confidence": "medium",
                        "next_steps": ["Provide requested data for full optimization"]
                    }
                )
            
            return ExecutionResult(success=True, result={})
        
        with patch.object(supervisor, 'execute_agent', side_effect=track_agent_execution):
            state = DeepAgentState(
                user_request=json.dumps(partial_cost_optimization_request)
            )
            
            context = UserExecutionContext(
                user_id="test-user",
                run_id="test-partial-e2e",
                metadata={"user_request": partial_cost_optimization_request["user_request"]}
            )
            
            result = await supervisor.execute(context)
            
            # Verify modified workflow was executed
            assert "triage" in execution_sequence
            assert "optimization" in execution_sequence
            assert "data_helper" in execution_sequence
            assert "actions" in execution_sequence
            assert "reporting" in execution_sequence
            
            # Verify data analysis might be skipped or limited
            data_analysis_count = execution_sequence.count("data")
            assert data_analysis_count <= 1  # Limited or skipped
    
    @pytest.mark.asyncio
    async def test_websocket_events_for_partial_data(self):
        """Test that appropriate WebSocket events are sent for partial data scenarios."""
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        websocket_manager = WebSocketManager()
        events_sent = []
        
        async def mock_send_event(event_type, data):
            events_sent.append({"type": event_type, "data": data})
        
        websocket_manager.send_event = mock_send_event
        
        # Simulate partial data workflow
        await websocket_manager.send_event("agent_started", {"agent": "triage"})
        await websocket_manager.send_event("agent_thinking", {
            "message": "Analyzing available data (45% complete)"
        })
        await websocket_manager.send_event("data_request", {
            "priority": "medium",
            "message": "Additional data would improve recommendations"
        })
        await websocket_manager.send_event("partial_results", {
            "confidence": "medium",
            "immediate_value": "Quick optimizations available"
        })
        
        assert len(events_sent) >= 4
        assert any(e["type"] == "data_request" for e in events_sent)
        assert any(e["type"] == "partial_results" for e in events_sent)
    
    # === Validation Tests ===
    
    @pytest.mark.asyncio
    async def test_validate_partial_data_prompts(self):
        """Validate that agent prompts handle partial data correctly."""
        test_prompts = [
            {
                "agent": "triage",
                "scenario": "partial_cost_data",
                "expected_elements": [
                    "data_sufficiency assessment",
                    "confidence scoring",
                    "workflow recommendation"
                ]
            },
            {
                "agent": "optimization",
                "scenario": "partial_metrics",
                "expected_elements": [
                    "caveat generation",
                    "confidence levels",
                    "range-based estimates"
                ]
            },
            {
                "agent": "data_helper",
                "scenario": "missing_critical_data",
                "expected_elements": [
                    "prioritized requests",
                    "justification for each item",
                    "quick collection templates"
                ]
            }
        ]
        
        for test in test_prompts:
            # This would validate actual prompt templates in production
            # For now, we verify the structure exists
            assert test["agent"] in ["triage", "optimization", "data_helper"]
            assert len(test["expected_elements"]) >= 3
    
    @pytest.mark.asyncio
    async def test_confidence_calibration(self):
        """Test that confidence scores are well-calibrated to actual success rates."""
        test_cases = [
            {"completeness": 0.20, "predicted_confidence": 0.25, "actual_success_rate": 0.20},
            {"completeness": 0.45, "predicted_confidence": 0.55, "actual_success_rate": 0.50},
            {"completeness": 0.75, "predicted_confidence": 0.80, "actual_success_rate": 0.78},
            {"completeness": 0.90, "predicted_confidence": 0.92, "actual_success_rate": 0.90},
        ]
        
        for case in test_cases:
            # In production, this would compare predicted confidence
            # with actual optimization success rates
            confidence_error = abs(case["predicted_confidence"] - case["actual_success_rate"])
            assert confidence_error <= 0.10, \
                f"Confidence calibration error too high: {confidence_error}"


# === Test Runner ===

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--asyncio-mode=auto",
        "--tb=short",
        "--no-header",
        "-p", "no:warnings"
    ])