"""Integration tests for SupplyResearcherSubAgent with REAL LLM usage.

These tests validate actual supply chain research and vendor analysis using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures accurate vendor evaluation and supply chain optimization.
""""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    from netra_backend.app.core.config import get_settings
    settings = get_settings()
    llm_manager = LLMManager(settings)
    yield llm_manager


@pytest.fixture
async def real_tool_dispatcher():
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher()
    return dispatcher


@pytest.fixture
async def real_supply_researcher_agent(real_llm_manager, real_tool_dispatcher):
    """Create real SupplyResearcherAgent instance."""
    agent = SupplyResearcherAgent(
    llm_manager=real_llm_manager,
    tool_dispatcher=real_tool_dispatcher,
    websocket_manager=None  # Real websocket in production
    )
    yield agent
    # Cleanup not needed for tests


class TestSupplyResearcherAgentRealLLM:
    """Test suite for SupplyResearcherAgent with real LLM interactions."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_vendor_capability_assessment_and_scoring(
        self, real_supply_researcher_agent, db_session
    ):
        """Test 1: Assess and score AI vendor capabilities using real LLM."""
        # Vendor evaluation request
        state = DeepAgentState(
            run_id="test_supply_001",
            user_query="Evaluate and compare OpenAI, Anthropic, and Google for enterprise LLM deployment",
            triage_result={
                "intent": "vendor_evaluation",
                "entities": ["openai", "anthropic", "google", "enterprise"],
                "confidence": 0.94
            },
            data_result={
                "vendor_data": {
                    "openai": {
                        "models": ["gpt-4", "gpt-3.5-turbo", "embeddings"],
                        "pricing": {"gpt-4": 0.03, "gpt-3.5": 0.002},
                        "sla": {"uptime": 99.9, "support": "24/7"},
                        "compliance": ["SOC2", "GDPR"],
                        "api_features": ["streaming", "function_calling", "fine_tuning"]
                    },
                    "anthropic": {
                        "models": ["claude-2", "claude-instant"],
                        "pricing": {"claude-2": 0.025, "claude-instant": 0.001},
                        "sla": {"uptime": 99.5, "support": "business_hours"},
                        "compliance": ["SOC2"],
                        "api_features": ["streaming", "constitutional_ai"]
                    },
                    "google": {
                        "models": ["palm-2", "gemini", "embeddings"],
                        "pricing": {"palm-2": 0.02, "gemini": 0.025},
                        "sla": {"uptime": 99.95, "support": "24/7"},
                        "compliance": ["SOC2", "GDPR", "HIPAA"],
                        "api_features": ["streaming", "multimodal", "grounding"]
                    }
                },
                "requirements": {
                    "scale": "10M requests/month",
                    "latency": "< 200ms p95",
                    "compliance_needs": ["SOC2", "GDPR"],
                    "budget": 50000,
                    "use_cases": ["customer_support", "content_generation", "analysis"]
                }
            }
        )
        
        # Execute vendor assessment with real LLM
        await real_supply_researcher_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.supply_result if hasattr(state, 'supply_result') else state.data_result
        
        # Validate assessment structure
        assert result["status"] == "success"
        assert "vendor_assessment" in result
        
        assessment = result["vendor_assessment"]
        assert "vendor_scores" in assessment
        assert len(assessment["vendor_scores"]) == 3
        
        # Verify comprehensive scoring
        for vendor in assessment["vendor_scores"]:
            assert "vendor_name" in vendor
            assert "overall_score" in vendor
            assert 0 <= vendor["overall_score"] <= 100
            assert "category_scores" in vendor
            
            categories = vendor["category_scores"]
            assert "technical_capability" in categories
            assert "pricing_value" in categories
            assert "reliability" in categories
            assert "compliance" in categories
            assert "support" in categories
        
        # Check for recommendations
        assert "recommendations" in result
        recommendations = result["recommendations"]
        assert "primary_vendor" in recommendations
        assert "backup_vendor" in recommendations
        assert "rationale" in recommendations
        
        # Verify risk analysis
        assert "vendor_risks" in result
        risks = result["vendor_risks"]
        assert len(risks) >= 3
        
        for risk in risks:
            assert "vendor" in risk
            assert "risk_factors" in risk
            assert "mitigation_strategies" in risk
        
        # Check for negotiation points
        assert "negotiation_leverage" in result
        assert len(result["negotiation_leverage"]) >= 2
        
        logger.info(f"Assessed {len(assessment['vendor_scores'])] vendors with primary recommendation: {recommendations['primary_vendor']]")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_supply_chain_optimization_recommendations(
        self, real_supply_researcher_agent, db_session
    ):
        """Test 2: Generate supply chain optimization recommendations using real LLM."""
        # Supply chain optimization scenario
        state = DeepAgentState(
            run_id="test_supply_002",
            user_query="Optimize our AI model supply chain for cost and redundancy",
            triage_result={
                "intent": "supply_chain_optimization",
                "entities": ["cost", "redundancy", "ai_models"],
                "confidence": 0.91
            },
            data_result={
                "current_supply_chain": {
                    "primary_providers": [
                        {"vendor": "OpenAI", "dependency": 0.70, "monthly_cost": 35000},
                        {"vendor": "Azure", "dependency": 0.20, "monthly_cost": 10000},
                        {"vendor": "AWS", "dependency": 0.10, "monthly_cost": 5000}
                    ],
                    "service_distribution": {
                        "inference": {"OpenAI": 0.80, "Azure": 0.15, "AWS": 0.05},
                        "embeddings": {"OpenAI": 0.60, "AWS": 0.40},
                        "fine_tuning": {"OpenAI": 1.0}
                    },
                    "failure_history": [
                        {"vendor": "OpenAI", "incidents": 3, "total_downtime_hours": 4.5},
                        {"vendor": "Azure", "incidents": 1, "total_downtime_hours": 0.5}
                    ]
                },
                "constraints": {
                    "max_vendors": 4,
                    "min_redundancy_factor": 2,
                    "budget_ceiling": 55000,
                    "switching_cost_per_vendor": 5000,
                    "implementation_timeline_days": 90
                },
                "performance_requirements": {
                    "min_availability": 0.999,
                    "max_latency_ms": 150,
                    "throughput_rps": 2000
                }
            }
        )
        
        # Execute supply chain optimization with real LLM
        await real_supply_researcher_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.supply_result if hasattr(state, 'supply_result') else state.data_result
        
        assert result["status"] == "success"
        assert "optimization_plan" in result
        
        plan = result["optimization_plan"]
        assert "vendor_mix" in plan
        assert "redundancy_strategy" in plan
        assert "cost_optimization" in plan
        
        # Verify vendor mix recommendations
        vendor_mix = plan["vendor_mix"]
        assert len(vendor_mix) <= 4  # Respects max_vendors constraint
        
        total_allocation = sum(v["recommended_allocation"] for v in vendor_mix)
        assert 0.95 <= total_allocation <= 1.05  # Should sum to ~100%
        
        # Check redundancy implementation
        redundancy = plan["redundancy_strategy"]
        assert "primary_secondary_pairs" in redundancy
        assert "failover_procedures" in redundancy
        assert "redundancy_factor" in redundancy
        assert redundancy["redundancy_factor"] >= 2
        
        # Verify cost projections
        cost_opt = plan["cost_optimization"]
        assert "projected_monthly_cost" in cost_opt
        assert cost_opt["projected_monthly_cost"] <= 55000  # Within budget
        assert "savings_percentage" in cost_opt
        assert "roi_months" in cost_opt
        
        # Check migration plan
        assert "migration_roadmap" in result
        roadmap = result["migration_roadmap"]
        assert len(roadmap) >= 3  # Multiple phases
        
        for phase in roadmap:
            assert "phase_name" in phase
            assert "duration_days" in phase
            assert "actions" in phase
            assert "risk_level" in phase
        
        logger.info(f"Optimized supply chain with {len(vendor_mix)] vendors and {redundancy['redundancy_factor']]x redundancy")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_vendor_risk_assessment_and_mitigation(
        self, real_supply_researcher_agent, db_session
    ):
        """Test 3: Assess vendor risks and generate mitigation strategies using real LLM."""
        # Risk assessment scenario
        state = DeepAgentState(
            run_id="test_supply_003",
            user_query="Assess risks of our current AI vendor dependencies and suggest mitigation strategies",
            triage_result={
                "intent": "risk_assessment",
                "entities": ["vendor_risk", "dependencies", "mitigation"],
                "confidence": 0.93
            },
            data_result={
                "vendor_dependencies": {
                    "critical_services": {
                        "production_inference": {"vendor": "OpenAI", "criticality": "high"},
                        "embeddings": {"vendor": "OpenAI", "criticality": "medium"},
                        "backup_inference": {"vendor": "Anthropic", "criticality": "high"},
                        "monitoring": {"vendor": "Datadog", "criticality": "medium"}
                    },
                    "concentration_risk": {
                        "OpenAI": 0.75,  # 75% of critical services
                        "Anthropic": 0.15,
                        "Others": 0.10
                    }
                },
                "risk_factors": {
                    "geopolitical": {
                        "OpenAI": {"location": "US", "regulatory_risk": "medium"},
                        "Anthropic": {"location": "US", "regulatory_risk": "medium"}
                    },
                    "financial": {
                        "OpenAI": {"stability": "high", "pricing_volatility": "medium"},
                        "Anthropic": {"stability": "medium", "pricing_volatility": "low"}
                    },
                    "technical": {
                        "OpenAI": {"api_stability": 0.995, "feature_deprecation_risk": "low"},
                        "Anthropic": {"api_stability": 0.990, "feature_deprecation_risk": "medium"}
                    }
                },
                "historical_issues": [
                    {"vendor": "OpenAI", "issue": "capacity_limits", "frequency": "monthly"},
                    {"vendor": "OpenAI", "issue": "api_changes", "frequency": "quarterly"}
                ],
                "business_impact": {
                    "revenue_at_risk": 2000000,
                    "customers_affected": 5000,
                    "reputation_score": 8.5
                }
            }
        )
        
        # Execute risk assessment with real LLM
        await real_supply_researcher_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.supply_result if hasattr(state, 'supply_result') else state.data_result
        
        assert result["status"] == "success"
        assert "risk_assessment" in result
        
        assessment = result["risk_assessment"]
        assert "overall_risk_score" in assessment
        assert "risk_categories" in assessment
        
        # Verify risk categorization
        categories = assessment["risk_categories"]
        assert "concentration_risk" in categories
        assert "operational_risk" in categories
        assert "strategic_risk" in categories
        assert "compliance_risk" in categories
        
        for category, details in categories.items():
            assert "severity" in details
            assert "likelihood" in details
            assert "impact" in details
        
        # Check mitigation strategies
        assert "mitigation_strategies" in result
        strategies = result["mitigation_strategies"]
        assert len(strategies) >= 4
        
        for strategy in strategies:
            assert "risk_addressed" in strategy
            assert "action_items" in strategy
            assert "timeline" in strategy
            assert "cost_estimate" in strategy
            assert "effectiveness_score" in strategy
        
        # Verify contingency planning
        assert "contingency_plans" in result
        contingencies = result["contingency_plans"]
        assert len(contingencies) >= 2
        
        for plan in contingencies:
            assert "trigger_event" in plan
            assert "response_actions" in plan
            assert "decision_tree" in plan
            assert "communication_plan" in plan
        
        # Check for monitoring recommendations
        assert "monitoring_framework" in result
        monitoring = result["monitoring_framework"]
        assert "kpis" in monitoring
        assert "alert_thresholds" in monitoring
        assert "review_frequency" in monitoring
        
        logger.info(f"Identified {len(categories)} risk categories with {len(strategies)} mitigation strategies")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_competitive_vendor_analysis_and_benchmarking(
        self, real_supply_researcher_agent, db_session
    ):
        """Test 4: Perform competitive vendor analysis and benchmarking using real LLM."""
        # Competitive analysis request
        state = DeepAgentState(
            run_id="test_supply_004",
            user_query="Benchmark our AI vendor costs and performance against industry standards",
            triage_result={
                "intent": "competitive_benchmarking",
                "entities": ["costs", "performance", "industry_standards"],
                "confidence": 0.90
            },
            data_result={
                "our_metrics": {
                    "avg_cost_per_1k_tokens": 0.025,
                    "avg_latency_ms": 145,
                    "availability": 0.997,
                    "error_rate": 0.003,
                    "vendor_count": 2,
                    "monthly_spend": 45000
                },
                "industry_data": {
                    "peer_companies": [
                        {
                            "company": "Competitor_A",
                            "size": "similar",
                            "cost_per_1k_tokens": 0.022,
                            "latency_ms": 120,
                            "vendor_count": 3
                        },
                        {
                            "company": "Competitor_B",
                            "size": "larger",
                            "cost_per_1k_tokens": 0.018,
                            "latency_ms": 100,
                            "vendor_count": 4
                        },
                        {
                            "company": "Industry_Leader",
                            "size": "larger",
                            "cost_per_1k_tokens": 0.015,
                            "latency_ms": 85,
                            "vendor_count": 5
                        }
                    ],
                    "industry_averages": {
                        "cost_per_1k_tokens": 0.020,
                        "latency_ms": 110,
                        "availability": 0.998,
                        "vendor_count": 3.5
                    },
                    "best_in_class": {
                        "cost_per_1k_tokens": 0.012,
                        "latency_ms": 75,
                        "availability": 0.9995,
                        "vendor_count": 6
                    }
                },
                "market_trends": {
                    "price_trend": "decreasing_5_percent_quarterly",
                    "new_entrants": ["Cohere", "Mistral", "Together"],
                    "consolidation": ["Microsoft-OpenAI", "Google-DeepMind"]
                }
            }
        )
        
        # Execute competitive benchmarking with real LLM
        await real_supply_researcher_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.supply_result if hasattr(state, 'supply_result') else state.data_result
        
        assert result["status"] == "success"
        assert "benchmark_analysis" in result
        
        analysis = result["benchmark_analysis"]
        assert "positioning" in analysis
        assert "gap_analysis" in analysis
        assert "competitive_advantages" in analysis
        assert "improvement_areas" in analysis
        
        # Verify positioning assessment
        positioning = analysis["positioning"]
        assert "overall_ranking" in positioning
        assert "percentile" in positioning
        assert "tier" in positioning  # e.g., "leader", "challenger", "follower"
        
        # Check gap analysis
        gaps = analysis["gap_analysis"]
        for metric in ["cost", "performance", "reliability", "flexibility"]:
            assert metric in gaps
            assert "current_gap" in gaps[metric]
            assert "target_gap" in gaps[metric]
            assert "action_required" in gaps[metric]
        
        # Verify improvement recommendations
        assert "improvement_roadmap" in result
        roadmap = result["improvement_roadmap"]
        assert len(roadmap) >= 3
        
        for improvement in roadmap:
            assert "area" in improvement
            assert "current_state" in improvement
            assert "target_state" in improvement
            assert "expected_impact" in improvement
            assert "implementation_steps" in improvement
        
        # Check market insights
        assert "market_insights" in result
        insights = result["market_insights"]
        assert "emerging_opportunities" in insights
        assert "threats" in insights
        assert "vendor_recommendations" in insights
        
        logger.info(f"Benchmarked against {len(analysis['gap_analysis'])] metrics, positioned at {positioning['percentile']] percentile")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_vendor_contract_optimization_analysis(
        self, real_supply_researcher_agent, db_session
    ):
        """Test 5: Analyze and optimize vendor contracts using real LLM."""
        # Contract optimization scenario
        state = DeepAgentState(
            run_id="test_supply_005",
            user_query="Analyze our AI vendor contracts and suggest optimization opportunities for renewal",
            triage_result={
                "intent": "contract_optimization",
                "entities": ["contracts", "optimization", "renewal"],
                "confidence": 0.92
            },
            data_result={
                "current_contracts": [
                    {
                        "vendor": "OpenAI",
                        "type": "enterprise",
                        "annual_value": 420000,
                        "expiry": "2024-06-30",
                        "terms": {
                            "volume_commitment": "15M tokens/month",
                            "discount": "20%",
                            "sla": "99.9%",
                            "support": "dedicated",
                            "payment": "monthly"
                        },
                        "usage_vs_commitment": 1.15  # 15% over commitment
                    },
                    {
                        "vendor": "Anthropic",
                        "type": "standard",
                        "annual_value": 120000,
                        "expiry": "2024-08-15",
                        "terms": {
                            "volume_commitment": "5M tokens/month",
                            "discount": "10%",
                            "sla": "99.5%",
                            "support": "standard",
                            "payment": "quarterly"
                        },
                        "usage_vs_commitment": 0.75  # 25% under commitment
                    },
                    {
                        "vendor": "Azure",
                        "type": "pay-as-you-go",
                        "annual_value": 60000,
                        "expiry": "2024-12-31",
                        "terms": {
                            "volume_commitment": "none",
                            "discount": "5%",
                            "sla": "99.95%",
                            "support": "included",
                            "payment": "monthly"
                        },
                        "usage_trend": "increasing"
                    }
                ],
                "negotiation_history": {
                    "OpenAI": {
                        "last_negotiation": "2023-06-01",
                        "achieved_savings": "15%",
                        "key_wins": ["dedicated_support", "volume_discount"]
                    },
                    "Anthropic": {
                        "last_negotiation": "2023-08-01",
                        "achieved_savings": "8%",
                        "key_wins": ["flexible_commitment"]
                    }
                },
                "market_intelligence": {
                    "typical_enterprise_discount": "25-35%",
                    "volume_tier_thresholds": {
                        "tier1": "10M tokens",
                        "tier2": "25M tokens",
                        "tier3": "50M tokens"
                    },
                    "competitor_switching_incentives": "3-6 months free"
                },
                "business_projections": {
                    "growth_rate": 0.30,  # 30% YoY
                    "budget_increase": 0.20,  # 20% increase approved
                    "strategic_priorities": ["cost_control", "reliability", "innovation"]
                }
            }
        )
        
        # Execute contract analysis with real LLM
        await real_supply_researcher_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.supply_result if hasattr(state, 'supply_result') else state.data_result
        
        assert result["status"] == "success"
        assert "contract_analysis" in result
        
        analysis = result["contract_analysis"]
        assert "optimization_opportunities" in analysis
        assert len(analysis["optimization_opportunities"]) >= 3
        
        for opportunity in analysis["optimization_opportunities"]:
            assert "vendor" in opportunity
            assert "opportunity_type" in opportunity
            assert "potential_savings" in opportunity
            assert "negotiation_leverage" in opportunity
            assert "recommended_terms" in opportunity
        
        # Verify renewal strategy
        assert "renewal_strategy" in result
        strategy = result["renewal_strategy"]
        
        for vendor in ["OpenAI", "Anthropic", "Azure"]:
            assert vendor in strategy
            vendor_strategy = strategy[vendor]
            assert "recommendation" in vendor_strategy  # renew/renegotiate/replace
            assert "target_terms" in vendor_strategy
            assert "negotiation_timeline" in vendor_strategy
            assert "walk_away_point" in vendor_strategy
        
        # Check consolidation opportunities
        assert "consolidation_analysis" in result
        consolidation = result["consolidation_analysis"]
        assert "potential_savings" in consolidation
        assert "recommended_approach" in consolidation
        assert "risks" in consolidation
        
        # Verify negotiation playbook
        assert "negotiation_playbook" in result
        playbook = result["negotiation_playbook"]
        assert len(playbook) >= 3
        
        for tactic in playbook:
            assert "tactic_name" in tactic
            assert "when_to_use" in tactic
            assert "expected_outcome" in tactic
            assert "fallback_position" in tactic
        
        # Check for contract terms optimization
        assert "optimized_terms" in result
        optimized = result["optimized_terms"]
        assert "payment_structure" in optimized
        assert "volume_commitments" in optimized
        assert "flexibility_clauses" in optimized
        assert "exit_clauses" in optimized
        
        logger.info(f"Identified {len(analysis['optimization_opportunities'])] contract optimization opportunities with potential savings")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))