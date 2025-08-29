"""Integration tests for ActionsToMeetGoalsSubAgent with REAL LLM usage.

These tests validate actual action planning and goal achievement using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures strategic action planning delivers measurable outcomes.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db_session
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    llm_manager = LLMManager()
    await llm_manager.initialize()
    yield llm_manager
    await llm_manager.cleanup()


@pytest.fixture
async def real_tool_dispatcher(db_session: AsyncSession):
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher()
    await dispatcher.initialize_tools(db_session)
    return dispatcher


@pytest.fixture
async def real_actions_agent(real_llm_manager, real_tool_dispatcher):
    """Create real ActionsToMeetGoalsSubAgent instance."""
    agent = ActionsToMeetGoalsSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        websocket_manager=None  # Real websocket in production
    )
    yield agent
    await agent.cleanup()


class TestActionsToMeetGoalsAgentRealLLM:
    """Test suite for ActionsToMeetGoalsSubAgent with real LLM interactions."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_strategic_cost_reduction_action_plan(
        self, real_actions_agent, db_session
    ):
        """Test 1: Generate strategic action plan for cost reduction goals using real LLM."""
        # Cost reduction goal with constraints
        state = DeepAgentState(
            run_id="test_actions_001",
            user_query="Create an action plan to reduce AI costs by 30% within 3 months without impacting quality",
            triage_result={
                "intent": "goal_planning",
                "entities": ["cost_reduction", "30%", "3_months", "quality"],
                "confidence": 0.95
            },
            data_result={
                "current_state": {
                    "monthly_cost": 150000,
                    "model_distribution": {
                        "gpt-4": 0.60,
                        "gpt-3.5-turbo": 0.30,
                        "embeddings": 0.10
                    },
                    "quality_metrics": {
                        "accuracy": 0.94,
                        "user_satisfaction": 4.7,
                        "response_time_ms": 150
                    }
                },
                "constraints": {
                    "min_accuracy": 0.92,
                    "min_satisfaction": 4.5,
                    "max_response_time_ms": 200,
                    "team_capacity": "limited",
                    "budget_for_changes": 10000
                },
                "available_resources": {
                    "engineering_hours": 320,
                    "can_modify_architecture": True,
                    "can_change_models": True,
                    "can_implement_caching": True
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_actions_001",
            user_id="strategy_team_001"
        )
        
        # Execute action planning with real LLM
        result = await real_actions_agent.execute(context)
        
        # Validate action plan structure
        assert result["status"] == "success"
        assert "action_plan" in result
        
        plan = result["action_plan"]
        assert "phases" in plan
        assert len(plan["phases"]) >= 2  # Multiple phases for 3-month timeline
        
        # Verify each phase has concrete actions
        for phase in plan["phases"]:
            assert "name" in phase
            assert "duration" in phase
            assert "actions" in phase
            assert len(phase["actions"]) >= 2
            
            for action in phase["actions"]:
                assert "task" in action
                assert "owner" in action
                assert "priority" in action
                assert "expected_impact" in action
                assert "success_criteria" in action
        
        # Check for risk mitigation
        assert "risk_mitigation" in result
        risks = result["risk_mitigation"]
        assert len(risks) >= 2
        
        for risk in risks:
            assert "risk_description" in risk
            assert "likelihood" in risk
            assert "impact" in risk
            assert "mitigation_strategy" in risk
        
        # Verify cost projections
        assert "projected_outcomes" in result
        outcomes = result["projected_outcomes"]
        assert "cost_reduction_percentage" in outcomes
        assert outcomes["cost_reduction_percentage"] >= 25  # Close to 30% target
        assert "quality_impact" in outcomes
        assert outcomes["quality_impact"]["accuracy"] >= 0.92
        
        # Check for quick wins
        assert "quick_wins" in result
        assert len(result["quick_wins"]) >= 2
        
        logger.info(f"Generated {len(plan['phases'])} phase action plan with {sum(len(p['actions']) for p in plan['phases'])} total actions")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_performance_improvement_action_sequencing(
        self, real_actions_agent, db_session
    ):
        """Test 2: Generate sequenced actions for performance improvement using real LLM."""
        # Performance improvement goal
        state = DeepAgentState(
            run_id="test_actions_002",
            user_query="Plan actions to improve API response time from 500ms to 100ms for real-time applications",
            triage_result={
                "intent": "performance_optimization",
                "entities": ["response_time", "500ms", "100ms", "real-time"],
                "confidence": 0.93
            },
            data_result={
                "performance_baseline": {
                    "current_latency_ms": 500,
                    "p50_latency": 450,
                    "p95_latency": 750,
                    "p99_latency": 1200,
                    "throughput_rps": 500
                },
                "bottleneck_analysis": {
                    "model_inference": 300,  # ms
                    "network_latency": 80,
                    "preprocessing": 50,
                    "postprocessing": 30,
                    "database_queries": 40
                },
                "infrastructure": {
                    "current_setup": "single_region",
                    "gpu_enabled": False,
                    "caching_enabled": False,
                    "load_balancing": "round_robin"
                },
                "dependencies": {
                    "can_modify_model": True,
                    "can_add_gpu": True,
                    "can_implement_edge": True,
                    "requires_backwards_compatibility": True
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_actions_002",
            user_id="platform_team_002"
        )
        
        # Execute performance action planning
        result = await real_actions_agent.execute(context)
        
        assert result["status"] == "success"
        assert "action_sequence" in result
        
        sequence = result["action_sequence"]
        assert len(sequence) >= 4  # Multiple steps needed for 5x improvement
        
        # Verify action dependencies
        for i, action in enumerate(sequence):
            assert "step_number" in action
            assert action["step_number"] == i + 1
            assert "action_name" in action
            assert "dependencies" in action
            assert "estimated_improvement_ms" in action
            assert "implementation_time" in action
            
            # Check if dependencies reference earlier steps
            for dep in action["dependencies"]:
                if isinstance(dep, int):
                    assert dep < action["step_number"]
        
        # Verify cumulative improvements
        assert "cumulative_improvements" in result
        cumulative = result["cumulative_improvements"]
        assert len(cumulative) == len(sequence)
        assert cumulative[-1]["total_latency"] <= 120  # Should approach 100ms target
        
        # Check for parallel execution opportunities
        assert "parallelization_opportunities" in result
        parallel = result["parallelization_opportunities"]
        assert len(parallel) > 0
        
        # Verify rollback plan
        assert "rollback_procedures" in result
        rollback = result["rollback_procedures"]
        assert len(rollback) >= len(sequence)
        
        logger.info(f"Generated {len(sequence)} step action sequence with {cumulative[-1]['total_latency']}ms final latency")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_multi_stakeholder_goal_alignment_actions(
        self, real_actions_agent, db_session
    ):
        """Test 3: Generate actions aligning multiple stakeholder goals using real LLM."""
        # Multiple conflicting goals
        state = DeepAgentState(
            run_id="test_actions_003",
            user_query="Create action plan balancing engineering velocity, cost control, and compliance requirements",
            triage_result={
                "intent": "multi_goal_planning",
                "entities": ["velocity", "cost", "compliance"],
                "confidence": 0.91
            },
            data_result={
                "stakeholder_goals": {
                    "engineering": {
                        "priority": "deployment_frequency",
                        "target": "10_deploys_per_day",
                        "current": "2_deploys_per_day"
                    },
                    "finance": {
                        "priority": "cost_reduction",
                        "target": "20_percent_reduction",
                        "current": "5_percent_over_budget"
                    },
                    "compliance": {
                        "priority": "audit_readiness",
                        "requirements": ["SOC2", "GDPR", "HIPAA"],
                        "current_gaps": ["logging", "encryption", "access_controls"]
                    }
                },
                "conflicts": [
                    "Fast deployment vs thorough testing",
                    "Cost reduction vs compliance tooling",
                    "Automation vs audit trails"
                ],
                "resources": {
                    "team_size": 15,
                    "budget": 50000,
                    "timeline_months": 6
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_actions_003",
            user_id="leadership_team_003"
        )
        
        # Execute multi-stakeholder planning
        result = await real_actions_agent.execute(context)
        
        assert result["status"] == "success"
        assert "balanced_action_plan" in result
        
        plan = result["balanced_action_plan"]
        assert "stakeholder_alignment" in plan
        
        # Verify each stakeholder's needs are addressed
        alignment = plan["stakeholder_alignment"]
        assert "engineering" in alignment
        assert "finance" in alignment
        assert "compliance" in alignment
        
        # Check for trade-off analysis
        assert "trade_offs" in result
        trade_offs = result["trade_offs"]
        assert len(trade_offs) >= 2
        
        for trade_off in trade_offs:
            assert "decision" in trade_off
            assert "rationale" in trade_off
            assert "impact_on_stakeholders" in trade_off
        
        # Verify win-win actions
        assert "win_win_actions" in result
        win_wins = result["win_win_actions"]
        assert len(win_wins) >= 3
        
        for action in win_wins:
            assert "action" in action
            assert "benefits" in action
            assert len(action["benefits"]) >= 2  # Benefits multiple stakeholders
        
        # Check for phased approach
        assert "implementation_phases" in plan
        phases = plan["implementation_phases"]
        
        for phase in phases:
            assert "focus_area" in phase
            assert "stakeholder_wins" in phase
            assert len(phase["stakeholder_wins"]) >= 1
        
        # Verify success metrics for each stakeholder
        assert "success_metrics" in result
        metrics = result["success_metrics"]
        assert len(metrics) >= 3
        
        logger.info(f"Generated balanced plan with {len(win_wins)} win-win actions across {len(phases)} phases")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_crisis_response_action_prioritization(
        self, real_actions_agent, db_session
    ):
        """Test 4: Generate prioritized crisis response actions using real LLM."""
        # Crisis scenario requiring immediate action
        state = DeepAgentState(
            run_id="test_actions_004",
            user_query="Production is down, costs are spiking, and customers are complaining. Need immediate action plan.",
            triage_result={
                "intent": "crisis_management",
                "entities": ["production_down", "cost_spike", "customer_complaints"],
                "confidence": 0.97,
                "urgency": "critical"
            },
            data_result={
                "incident_details": {
                    "start_time": "2024-01-20T14:30:00Z",
                    "duration_minutes": 45,
                    "services_affected": ["api", "webhooks", "dashboard"],
                    "error_rate": 0.78,
                    "availability": 0.22
                },
                "cost_spike": {
                    "normal_hourly_cost": 500,
                    "current_hourly_cost": 8500,
                    "cause": "retry_storms_and_fallback_to_expensive_models"
                },
                "customer_impact": {
                    "affected_customers": 1250,
                    "tier_distribution": {
                        "enterprise": 45,
                        "mid_market": 380,
                        "startup": 825
                    },
                    "complaint_volume": 450,
                    "social_media_mentions": 120
                },
                "available_responders": {
                    "on_call_engineers": 2,
                    "available_engineers": 5,
                    "management": 3,
                    "customer_success": 8
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_actions_004",
            user_id="incident_commander_004"
        )
        
        # Execute crisis response planning
        result = await real_actions_agent.execute(context)
        
        assert result["status"] == "success"
        assert "immediate_actions" in result
        assert "war_room_structure" in result
        
        # Verify immediate actions are prioritized
        immediate = result["immediate_actions"]
        assert len(immediate) >= 3
        
        for action in immediate:
            assert "priority" in action
            assert action["priority"] in ["P0", "P1", "P2"]
            assert "action" in action
            assert "owner" in action
            assert "eta_minutes" in action
            assert action["eta_minutes"] <= 30  # All immediate actions within 30 min
        
        # Check for parallel workstreams
        assert "workstreams" in result
        workstreams = result["workstreams"]
        assert "technical_recovery" in workstreams
        assert "cost_mitigation" in workstreams
        assert "customer_communication" in workstreams
        
        # Verify communication plan
        assert "communication_plan" in result
        comm_plan = result["communication_plan"]
        assert "internal_updates" in comm_plan
        assert "customer_updates" in comm_plan
        assert "status_page_updates" in comm_plan
        
        # Check for escalation triggers
        assert "escalation_criteria" in result
        escalations = result["escalation_criteria"]
        assert len(escalations) >= 2
        
        # Verify post-incident actions
        assert "post_incident_actions" in result
        post_actions = result["post_incident_actions"]
        assert any("retrospective" in str(a).lower() for a in post_actions)
        assert any("rca" in str(a).lower() or "root cause" in str(a).lower() for a in post_actions)
        
        logger.info(f"Generated crisis response with {len(immediate)} immediate actions across {len(workstreams)} workstreams")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_innovation_and_growth_initiative_actions(
        self, real_actions_agent, db_session
    ):
        """Test 5: Generate innovation and growth initiative actions using real LLM."""
        # Growth and innovation goals
        state = DeepAgentState(
            run_id="test_actions_005",
            user_query="Plan actions to launch AI-powered features that can increase revenue by 50% and user engagement by 2x",
            triage_result={
                "intent": "growth_planning",
                "entities": ["ai_features", "revenue_50%", "engagement_2x"],
                "confidence": 0.92
            },
            data_result={
                "current_metrics": {
                    "monthly_revenue": 500000,
                    "daily_active_users": 25000,
                    "engagement_rate": 0.35,
                    "feature_adoption_rate": 0.42,
                    "churn_rate": 0.08
                },
                "market_analysis": {
                    "competitor_features": [
                        "personalized_recommendations",
                        "predictive_analytics",
                        "automated_workflows",
                        "natural_language_interface"
                    ],
                    "customer_requests": [
                        "better_insights",
                        "automation",
                        "integrations",
                        "mobile_experience"
                    ],
                    "market_gaps": [
                        "vertical_specific_solutions",
                        "real_time_collaboration",
                        "advanced_customization"
                    ]
                },
                "capabilities": {
                    "ai_expertise": "high",
                    "data_availability": "comprehensive",
                    "development_capacity": "moderate",
                    "go_to_market": "established"
                },
                "constraints": {
                    "development_budget": 200000,
                    "time_to_market_months": 4,
                    "technical_debt": "moderate",
                    "regulatory_requirements": ["data_privacy", "ai_transparency"]
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_actions_005",
            user_id="product_innovation_005"
        )
        
        # Execute innovation planning
        result = await real_actions_agent.execute(context)
        
        assert result["status"] == "success"
        assert "innovation_roadmap" in result
        
        roadmap = result["innovation_roadmap"]
        assert "feature_initiatives" in roadmap
        
        initiatives = roadmap["feature_initiatives"]
        assert len(initiatives) >= 3
        
        for initiative in initiatives:
            assert "feature_name" in initiative
            assert "ai_components" in initiative
            assert "revenue_impact" in initiative
            assert "engagement_impact" in initiative
            assert "development_effort" in initiative
            assert "time_to_market" in initiative
        
        # Verify MVP approach
        assert "mvp_strategy" in result
        mvp = result["mvp_strategy"]
        assert "phase_1_features" in mvp
        assert len(mvp["phase_1_features"]) >= 2
        
        # Check for experimentation plan
        assert "experimentation_plan" in result
        experiments = result["experimentation_plan"]
        assert len(experiments) >= 2
        
        for exp in experiments:
            assert "hypothesis" in exp
            assert "success_metrics" in exp
            assert "sample_size" in exp
            assert "duration_days" in exp
        
        # Verify go-to-market actions
        assert "go_to_market_actions" in result
        gtm = result["go_to_market_actions"]
        assert "launch_sequence" in gtm
        assert "pricing_strategy" in gtm
        assert "customer_segments" in gtm
        
        # Check for growth flywheel
        assert "growth_flywheel" in result
        flywheel = result["growth_flywheel"]
        assert "acquisition" in flywheel
        assert "activation" in flywheel
        assert "retention" in flywheel
        assert "revenue" in flywheel
        
        # Verify projected outcomes
        assert "projected_outcomes" in result
        outcomes = result["projected_outcomes"]
        assert "revenue_increase_percentage" in outcomes
        assert outcomes["revenue_increase_percentage"] >= 40  # Close to 50% target
        assert "engagement_multiplier" in outcomes
        assert outcomes["engagement_multiplier"] >= 1.8  # Close to 2x target
        
        logger.info(f"Generated innovation roadmap with {len(initiatives)} initiatives and {len(experiments)} experiments")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))