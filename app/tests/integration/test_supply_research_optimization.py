"""
Supply Research Cost Optimization Integration Test

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Growth & Enterprise customers optimizing AI costs
2. **Business Goal**: Maximize customer cost savings through intelligent model routing
3. **Value Impact**: 15-25% cost savings for customers = higher satisfaction + retention  
4. **Revenue Impact**: More savings = higher 20% performance fees = +$15K ARR per optimized customer
5. **Competitive Advantage**: Advanced model routing = key differentiator vs. generic AI platforms

Tests intelligent model routing (GPT-4 vs Gemini vs Claude) with real-time cost calculations
and optimization recommendations. Core value proposition for Netra Apex.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Tuple

from app.agents.supply_researcher.research_engine import SupplyResearchEngine
from app.agents.supply_researcher.data_extractor import SupplyDataExtractor
from app.agents.supply_researcher.parsers import SupplyRequestParser
from app.services.supply_research.schedule_manager import ScheduleManager
from app.agents.supply_researcher.models import ResearchType
# Note: CostImpactSimulator is mocked in tests and doesn't need to be imported
from app.db.models_user import User, ToolUsageLog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile


class TestSupplyResearchOptimization:
    """E2E tests for supply research and cost optimization"""

    @pytest.fixture
    async def optimization_test_setup(self):
        """Setup test environment for cost optimization testing"""
        return await self._create_optimization_test_env()

    @pytest.fixture
    def supply_research_components(self):
        """Setup supply research and optimization components"""
        return self._init_supply_research_components()

    @pytest.fixture
    def cost_optimization_scenarios(self):
        """Setup various cost optimization test scenarios"""
        return self._create_cost_optimization_scenarios()

    async def _create_optimization_test_env(self):
        """Create isolated test environment for optimization testing"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_url = f"sqlite+aiosqlite:///{db_file.name}"
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        
        return {"session": session, "engine": engine, "db_file": db_file.name}

    def _init_supply_research_components(self):
        """Initialize supply research and optimization components"""
        # Research engine with mock data sources
        research_engine = Mock(spec=SupplyResearchEngine)
        research_engine.research_model_pricing = AsyncMock(side_effect=self._mock_pricing_research)
        research_engine.research_model_capabilities = AsyncMock(side_effect=self._mock_capability_research)
        
        # Data extractor for processing research results
        data_extractor = Mock(spec=SupplyDataExtractor)
        data_extractor.extract_pricing_data = Mock(side_effect=self._mock_extract_pricing)
        data_extractor.extract_performance_metrics = Mock(side_effect=self._mock_extract_performance)
        
        # Cost impact simulator (mocked without spec)
        cost_simulator = Mock()
        cost_simulator.simulate_cost_impact = AsyncMock(side_effect=self._mock_cost_simulation)
        
        # Schedule manager for research automation
        schedule_manager = ScheduleManager()
        
        return {
            "research_engine": research_engine,
            "data_extractor": data_extractor,
            "cost_simulator": cost_simulator,
            "schedule_manager": schedule_manager
        }

    async def _mock_pricing_research(self, provider: str, model: str):
        """Mock pricing research results for different providers"""
        pricing_data = {
            "openai": {
                "gpt-4": {"input_cost": 0.03, "output_cost": 0.06, "currency": "USD", "per_1k_tokens": True},
                "gpt-3.5-turbo": {"input_cost": 0.0015, "output_cost": 0.002, "currency": "USD", "per_1k_tokens": True}
            },
            "google": {
                "gemini-2.5-flash": {"input_cost": 0.0005, "output_cost": 0.0015, "currency": "USD", "per_1k_tokens": True},
                "gemini-pro": {"input_cost": 0.0025, "output_cost": 0.0075, "currency": "USD", "per_1k_tokens": True}
            },
            "anthropic": {
                "claude-3-5-sonnet": {"input_cost": 0.003, "output_cost": 0.015, "currency": "USD", "per_1k_tokens": True},
                "claude-3-haiku": {"input_cost": 0.00025, "output_cost": 0.00125, "currency": "USD", "per_1k_tokens": True}
            }
        }
        
        return pricing_data.get(provider, {}).get(model, {})

    async def _mock_capability_research(self, provider: str, model: str):
        """Mock capability research for model performance comparison"""
        capability_data = {
            "openai": {
                "gpt-4": {"reasoning": 95, "coding": 90, "analysis": 92, "speed": 70},
                "gpt-3.5-turbo": {"reasoning": 80, "coding": 75, "analysis": 78, "speed": 90}
            },
            "google": {
                "gemini-2.5-flash": {"reasoning": 85, "coding": 82, "analysis": 88, "speed": 95},
                "gemini-pro": {"reasoning": 88, "coding": 85, "analysis": 90, "speed": 80}
            },
            "anthropic": {
                "claude-3-5-sonnet": {"reasoning": 93, "coding": 88, "analysis": 94, "speed": 75},
                "claude-3-haiku": {"reasoning": 78, "coding": 72, "analysis": 80, "speed": 92}
            }
        }
        
        return capability_data.get(provider, {}).get(model, {})

    def _mock_extract_pricing(self, research_data):
        """Mock pricing data extraction"""
        return {
            "input_cost_per_1k": research_data.get("input_cost", 0),
            "output_cost_per_1k": research_data.get("output_cost", 0),
            "currency": research_data.get("currency", "USD"),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def _mock_extract_performance(self, capability_data):
        """Mock performance metrics extraction"""
        return {
            "overall_score": sum(capability_data.values()) / len(capability_data),
            "strengths": [k for k, v in capability_data.items() if v >= 85],
            "weaknesses": [k for k, v in capability_data.items() if v < 75],
            "speed_rating": capability_data.get("speed", 0)
        }

    async def _mock_cost_simulation(self, current_usage, alternative_models):
        """Mock cost simulation for different model alternatives"""
        base_cost = current_usage.get("monthly_cost", 1000)
        
        simulations = {}
        for model_name, model_data in alternative_models.items():
            # Simulate cost based on pricing differences
            cost_multiplier = model_data.get("cost_multiplier", 1.0)
            projected_cost = base_cost * cost_multiplier
            savings = base_cost - projected_cost
            
            simulations[model_name] = {
                "projected_monthly_cost": projected_cost,
                "cost_savings": savings,
                "savings_percentage": (savings / base_cost) * 100,
                "confidence": 0.85
            }
        
        return simulations

    def _create_cost_optimization_scenarios(self):
        """Create various cost optimization test scenarios"""
        return {
            "high_volume_analysis": {
                "current_model": "gpt-4",
                "usage_pattern": "analysis_heavy",
                "monthly_tokens": 2000000,
                "cost_sensitivity": "high",
                "performance_requirements": "medium"
            },
            "real_time_optimization": {
                "current_model": "claude-3-5-sonnet", 
                "usage_pattern": "real_time_queries",
                "monthly_tokens": 500000,
                "cost_sensitivity": "medium",
                "performance_requirements": "high"
            },
            "batch_processing": {
                "current_model": "gemini-pro",
                "usage_pattern": "batch_processing",
                "monthly_tokens": 5000000,
                "cost_sensitivity": "very_high",
                "performance_requirements": "low"
            }
        }

    async def test_1_intelligent_model_routing_optimization(
        self, optimization_test_setup, supply_research_components, cost_optimization_scenarios
    ):
        """
        Test intelligent model routing for cost optimization across providers.
        
        BVJ: Core value proposition - intelligent model selection saves customers 15-25%
        on AI costs. Higher savings = larger performance fees = direct revenue growth.
        Each optimized customer represents $5-15K additional annual revenue.
        """
        db_setup = optimization_test_setup
        components = supply_research_components
        scenarios = cost_optimization_scenarios
        
        # Phase 1: Research current market pricing
        market_data = await self._research_current_market_pricing(components)
        
        # Phase 2: Analyze customer usage patterns
        usage_analysis = await self._analyze_customer_usage_patterns(
            db_setup, scenarios["high_volume_analysis"]
        )
        
        # Phase 3: Generate optimization recommendations
        optimization_results = await self._generate_optimization_recommendations(
            components, market_data, usage_analysis
        )
        
        # Phase 4: Simulate cost impact and savings
        cost_impact = await self._simulate_cost_impact_and_savings(
            components, optimization_results, usage_analysis
        )
        
        # Phase 5: Verify optimization effectiveness
        await self._verify_optimization_effectiveness(cost_impact, scenarios)
        
        await self._cleanup_optimization_test(db_setup)

    async def _research_current_market_pricing(self, components):
        """Research current market pricing across all major providers"""
        providers = ["openai", "google", "anthropic"]
        models = {
            "openai": ["gpt-4", "gpt-3.5-turbo"],
            "google": ["gemini-2.5-flash", "gemini-pro"],
            "anthropic": ["claude-3-5-sonnet", "claude-3-haiku"]
        }
        
        market_data = {}
        
        for provider in providers:
            market_data[provider] = {}
            for model in models[provider]:
                pricing = await components["research_engine"].research_model_pricing(provider, model)
                capabilities = await components["research_engine"].research_model_capabilities(provider, model)
                
                market_data[provider][model] = {
                    "pricing": components["data_extractor"].extract_pricing_data(pricing),
                    "performance": components["data_extractor"].extract_performance_metrics(capabilities)
                }
        
        return market_data

    async def _analyze_customer_usage_patterns(self, db_setup, scenario):
        """Analyze customer usage patterns to understand optimization opportunities"""
        # Create realistic usage logs for analysis
        usage_logs = await self._create_usage_logs_for_analysis(db_setup, scenario)
        
        # Analyze usage patterns
        usage_analysis = {
            "total_tokens": sum(log.tokens_used or 0 for log in usage_logs),
            "total_cost": sum(log.cost_cents or 0 for log in usage_logs) / 100,
            "avg_tokens_per_request": sum(log.tokens_used or 0 for log in usage_logs) / len(usage_logs),
            "usage_pattern": scenario["usage_pattern"],
            "current_model": scenario["current_model"],
            "performance_requirements": scenario["performance_requirements"]
        }
        
        return usage_analysis

    async def _create_usage_logs_for_analysis(self, db_setup, scenario):
        """Create realistic usage logs for cost analysis"""
        user = User(
            id=str(uuid.uuid4()),
            email="optimization@customer.com",
            plan_tier="enterprise"
        )
        db_setup["session"].add(user)
        await db_setup["session"].commit()
        
        usage_logs = []
        monthly_tokens = scenario["monthly_tokens"]
        daily_tokens = monthly_tokens // 30
        
        for day in range(30):
            log = ToolUsageLog(
                user_id=user.id,
                tool_name=f"{scenario['current_model']}_query",
                category="optimization",
                tokens_used=daily_tokens // 10,  # 10 requests per day
                cost_cents=self._calculate_daily_cost(scenario["current_model"], daily_tokens // 10),
                status="success",
                plan_tier="enterprise",
                created_at=datetime.now(timezone.utc) - timedelta(days=30-day)
            )
            usage_logs.append(log)
            db_setup["session"].add(log)
        
        await db_setup["session"].commit()
        return usage_logs

    def _calculate_daily_cost(self, model, tokens):
        """Calculate daily cost based on model and token usage"""
        # Simplified cost calculation for testing
        cost_per_1k = {
            "gpt-4": 45,  # $0.045 per 1k tokens average
            "claude-3-5-sonnet": 30,  # $0.030 per 1k tokens average
            "gemini-pro": 10,  # $0.010 per 1k tokens average
            "gemini-2.5-flash": 2   # $0.002 per 1k tokens average
        }
        
        return int((tokens / 1000) * cost_per_1k.get(model, 20))

    async def _generate_optimization_recommendations(self, components, market_data, usage_analysis):
        """Generate model optimization recommendations based on analysis"""
        current_model = usage_analysis["current_model"]
        performance_req = usage_analysis["performance_requirements"]
        
        # Find optimal alternatives based on cost and performance
        recommendations = []
        
        for provider, models in market_data.items():
            for model, data in models.items():
                if model == current_model:
                    continue
                
                # Check if performance meets requirements
                if self._meets_performance_requirements(data["performance"], performance_req):
                    cost_comparison = self._calculate_cost_comparison(
                        data["pricing"], usage_analysis
                    )
                    
                    if cost_comparison["savings_percentage"] > 5:  # At least 5% savings
                        recommendations.append({
                            "model": model,
                            "provider": provider,
                            "cost_savings": cost_comparison,
                            "performance": data["performance"],
                            "confidence": 0.85
                        })
        
        # Sort by savings potential
        recommendations.sort(key=lambda x: x["cost_savings"]["savings_percentage"], reverse=True)
        
        return recommendations[:3]  # Top 3 recommendations

    def _meets_performance_requirements(self, performance, requirements):
        """Check if model performance meets customer requirements"""
        overall_score = performance["overall_score"]
        
        thresholds = {
            "low": 70,
            "medium": 80,
            "high": 85
        }
        
        return overall_score >= thresholds.get(requirements, 80)

    def _calculate_cost_comparison(self, pricing, usage_analysis):
        """Calculate cost comparison between models"""
        current_monthly_cost = usage_analysis["total_cost"]
        
        # Simplified cost calculation based on input/output costs
        new_cost_per_1k = (pricing["input_cost_per_1k"] + pricing["output_cost_per_1k"]) / 2
        current_cost_per_1k = 0.045  # Average current cost
        
        cost_multiplier = new_cost_per_1k / current_cost_per_1k
        projected_cost = current_monthly_cost * cost_multiplier
        savings = current_monthly_cost - projected_cost
        
        return {
            "current_cost": current_monthly_cost,
            "projected_cost": projected_cost,
            "cost_savings": savings,
            "savings_percentage": (savings / current_monthly_cost) * 100
        }

    async def _simulate_cost_impact_and_savings(self, components, recommendations, usage_analysis):
        """Simulate cost impact of implementing recommendations"""
        current_usage = {
            "monthly_cost": usage_analysis["total_cost"],
            "monthly_tokens": usage_analysis["total_tokens"]
        }
        
        alternative_models = {}
        for rec in recommendations:
            alternative_models[rec["model"]] = {
                "cost_multiplier": 1 - (rec["cost_savings"]["savings_percentage"] / 100),
                "performance_score": rec["performance"]["overall_score"]
            }
        
        cost_simulations = await components["cost_simulator"].simulate_cost_impact(
            current_usage, alternative_models
        )
        
        return cost_simulations

    async def _verify_optimization_effectiveness(self, cost_impact, scenarios):
        """Verify optimization recommendations are effective"""
        # Verify at least one model offers significant savings
        best_savings = max(
            sim["savings_percentage"] for sim in cost_impact.values()
            if sim["savings_percentage"] > 0
        )
        
        assert best_savings >= 10, "Should find at least 10% cost savings"
        
        # Verify cost impact simulation data is realistic
        for model, simulation in cost_impact.items():
            assert "projected_monthly_cost" in simulation
            assert "cost_savings" in simulation
            assert "confidence" in simulation
            assert simulation["confidence"] > 0.7

    async def _cleanup_optimization_test(self, db_setup):
        """Cleanup optimization test environment"""
        await db_setup["session"].close()
        await db_setup["engine"].dispose()

    async def test_2_real_time_cost_monitoring_and_alerts(
        self, optimization_test_setup, supply_research_components
    ):
        """
        Test real-time cost monitoring and optimization alerts.
        
        BVJ: Proactive cost monitoring prevents customer bill shock and maintains
        trust. Early optimization alerts = higher customer satisfaction = reduced churn.
        Each retained customer = $1-50K ARR depending on tier.
        """
        db_setup = optimization_test_setup
        components = supply_research_components
        
        # Setup cost monitoring scenario
        monitoring_scenario = await self._setup_cost_monitoring_scenario(db_setup)
        
        # Simulate cost threshold breaches
        alert_triggers = await self._simulate_cost_threshold_breaches(
            components, monitoring_scenario
        )
        
        # Test optimization alert generation
        optimization_alerts = await self._test_optimization_alert_generation(
            components, alert_triggers
        )
        
        # Verify alert accuracy and recommendations
        await self._verify_alert_accuracy_and_recommendations(optimization_alerts)
        
        await self._cleanup_optimization_test(db_setup)

    async def _setup_cost_monitoring_scenario(self, db_setup):
        """Setup cost monitoring test scenario"""
        user = User(
            id=str(uuid.uuid4()),
            email="monitoring@customer.com",
            plan_tier="growth"
        )
        db_setup["session"].add(user)
        await db_setup["session"].commit()
        
        return {
            "user": user,
            "cost_threshold": 500.00,  # $500 monthly threshold
            "current_usage": 450.00,   # Near threshold
            "usage_trend": "increasing"
        }

    async def _simulate_cost_threshold_breaches(self, components, scenario):
        """Simulate various cost threshold breach scenarios"""
        alert_triggers = []
        
        # Simulate approaching threshold
        alert_triggers.append({
            "type": "approaching_threshold",
            "current_cost": 475.00,
            "threshold": scenario["cost_threshold"],
            "percentage": 95
        })
        
        # Simulate exceeded threshold
        alert_triggers.append({
            "type": "threshold_exceeded",
            "current_cost": 525.00,
            "threshold": scenario["cost_threshold"],
            "percentage": 105
        })
        
        return alert_triggers

    async def _test_optimization_alert_generation(self, components, alert_triggers):
        """Test generation of optimization alerts"""
        optimization_alerts = []
        
        for trigger in alert_triggers:
            # Generate optimization recommendations for each alert
            alert = {
                "trigger": trigger,
                "recommendations": await self._generate_emergency_optimizations(components, trigger),
                "estimated_savings": self._calculate_emergency_savings(trigger),
                "urgency": "high" if trigger["percentage"] > 100 else "medium"
            }
            optimization_alerts.append(alert)
        
        return optimization_alerts

    async def _generate_emergency_optimizations(self, components, trigger):
        """Generate emergency optimization recommendations"""
        # Simulate fast optimization recommendations for cost alerts
        return [
            {
                "action": "switch_to_gemini_flash",
                "estimated_savings": "40%",
                "implementation_time": "immediate"
            },
            {
                "action": "enable_batch_processing",
                "estimated_savings": "25%", 
                "implementation_time": "1_hour"
            }
        ]

    def _calculate_emergency_savings(self, trigger):
        """Calculate potential emergency savings"""
        excess_cost = max(0, trigger["current_cost"] - trigger["threshold"])
        potential_savings = excess_cost * 0.6  # 60% potential savings
        
        return {
            "immediate_savings": potential_savings,
            "monthly_impact": potential_savings * 1.5,
            "confidence": 0.8
        }

    async def _verify_alert_accuracy_and_recommendations(self, optimization_alerts):
        """Verify alert accuracy and recommendation quality"""
        for alert in optimization_alerts:
            # Verify alert has required components
            assert "trigger" in alert
            assert "recommendations" in alert
            assert "estimated_savings" in alert
            assert "urgency" in alert
            
            # Verify recommendations are actionable
            assert len(alert["recommendations"]) > 0
            for rec in alert["recommendations"]:
                assert "action" in rec
                assert "estimated_savings" in rec
                assert "implementation_time" in rec

    async def test_3_automated_optimization_scheduling_and_execution(
        self, optimization_test_setup, supply_research_components
    ):
        """
        Test automated optimization scheduling and execution.
        
        BVJ: Automated optimization reduces manual overhead and ensures consistent
        cost savings. Automation enables scalable optimization for 100+ enterprise
        customers without proportional support staff increase.
        """
        components = supply_research_components
        
        # Test optimization schedule management
        await self._test_optimization_schedule_management(components)
        
        # Test automated research execution
        await self._test_automated_research_execution(components)
        
        # Test optimization result processing
        await self._test_optimization_result_processing(components)

    async def _test_optimization_schedule_management(self, components):
        """Test optimization schedule management and automation"""
        schedule_manager = components["schedule_manager"]
        
        # Test default schedules are created
        schedules = schedule_manager.get_schedule_status()
        assert len(schedules) > 0
        
        # Test schedule modification
        schedule_manager.disable_schedule("weekly_capability_scan")
        disabled_schedule = schedule_manager.get_schedule_by_name("weekly_capability_scan")
        assert disabled_schedule.enabled == False

    async def _test_automated_research_execution(self, components):
        """Test automated research execution for optimization"""
        research_engine = components["research_engine"]
        
        # Test automated pricing research
        pricing_result = await research_engine.research_model_pricing("openai", "gpt-4")
        assert "input_cost" in pricing_result
        assert "output_cost" in pricing_result
        
        # Test automated capability research
        capability_result = await research_engine.research_model_capabilities("google", "gemini-2.5-flash")
        assert "reasoning" in capability_result
        assert "speed" in capability_result

    async def _test_optimization_result_processing(self, components):
        """Test processing and analysis of optimization results"""
        data_extractor = components["data_extractor"]
        
        # Test pricing data extraction
        mock_pricing = {"input_cost": 0.03, "output_cost": 0.06, "currency": "USD"}
        extracted_pricing = data_extractor.extract_pricing_data(mock_pricing)
        
        assert "input_cost_per_1k" in extracted_pricing
        assert "last_updated" in extracted_pricing
        
        # Test performance metrics extraction
        mock_capabilities = {"reasoning": 90, "coding": 85, "analysis": 88, "speed": 75}
        extracted_performance = data_extractor.extract_performance_metrics(mock_capabilities)
        
        assert "overall_score" in extracted_performance
        assert "strengths" in extracted_performance
        assert "weaknesses" in extracted_performance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])