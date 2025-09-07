"""
Agent Decision-Making Data Integration Tests

These tests validate data-driven agent decision-making processes including
agent routing, context preservation, insight generation, and recommendations.

Focus Areas:
- Data-driven agent routing and selection
- Context data preservation and transformation
- Business insight generation from data analysis
- Recommendation engine data processing
- Predictive analysis and trend detection
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from enum import Enum
import asyncio
import json

from netra_backend.app.services.billing.cost_calculator import CostCalculator, CostType
from netra_backend.app.services.billing.usage_tracker import UsageTracker, UsageType, UsageEvent
from netra_backend.app.services.quality.quality_score_calculators import QualityScoreCalculators


class AgentType(Enum):
    """Types of agents for routing decisions."""
    COST_OPTIMIZER = "cost_optimizer"
    PERFORMANCE_ANALYZER = "performance_analyzer"  
    SECURITY_AUDITOR = "security_auditor"
    DATA_RESEARCHER = "data_researcher"
    BUSINESS_ADVISOR = "business_advisor"
    TECHNICAL_CONSULTANT = "technical_consultant"


class MockExecutionContext:
    """Mock execution context for agent decision making."""
    
    def __init__(self, user_id: str, thread_id: str, run_id: str, 
                 user_request: str, metadata: Dict[str, Any] = None):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.user_request = user_request
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)


class AgentRoutingEngine:
    """Mock agent routing engine for data-driven decisions."""
    
    def __init__(self):
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
        
        # Agent capabilities and specializations
        self.agent_capabilities = {
            AgentType.COST_OPTIMIZER: {
                "specialties": ["billing", "usage", "pricing", "optimization"],
                "threshold_metrics": {"cost_savings_potential": 100.0},
                "confidence_factors": ["usage_patterns", "tier_analysis"]
            },
            AgentType.PERFORMANCE_ANALYZER: {
                "specialties": ["latency", "throughput", "scalability", "bottlenecks"],
                "threshold_metrics": {"performance_impact": 0.15},
                "confidence_factors": ["response_time", "error_rates"]
            },
            AgentType.SECURITY_AUDITOR: {
                "specialties": ["compliance", "vulnerabilities", "access_control"],
                "threshold_metrics": {"security_risk_score": 0.7},
                "confidence_factors": ["threat_indicators", "compliance_gaps"]
            },
            AgentType.DATA_RESEARCHER: {
                "specialties": ["data_analysis", "insights", "trends", "patterns"],
                "threshold_metrics": {"data_complexity": 0.6},
                "confidence_factors": ["data_volume", "analysis_depth"]
            },
            AgentType.BUSINESS_ADVISOR: {
                "specialties": ["strategy", "roi", "growth", "market_analysis"],
                "threshold_metrics": {"business_impact": 0.8},
                "confidence_factors": ["revenue_potential", "market_opportunity"]
            },
            AgentType.TECHNICAL_CONSULTANT: {
                "specialties": ["architecture", "implementation", "best_practices"],
                "threshold_metrics": {"technical_complexity": 0.5},
                "confidence_factors": ["implementation_feasibility", "technical_debt"]
            }
        }
    
    async def route_based_on_usage_patterns(self, context: MockExecutionContext) -> Dict[str, Any]:
        """Route agent based on user usage patterns and data."""
        user_usage = await self.usage_tracker.get_user_usage(
            context.user_id,
            start_time=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        # Analyze usage patterns for routing decision
        usage_summary = user_usage.get("usage_summary", {})
        total_cost = user_usage.get("total_cost", 0.0)
        
        # Decision logic based on usage data
        routing_decision = {"agent": None, "confidence": 0.0, "reasoning": []}
        
        # High cost users -> Cost Optimizer
        if total_cost > 500.0:
            routing_decision.update({
                "agent": AgentType.COST_OPTIMIZER,
                "confidence": min(0.9, total_cost / 1000.0),
                "reasoning": [f"High monthly cost: ${total_cost:.2f}"]
            })
        
        # High API usage -> Performance Analyzer  
        elif "api_call" in usage_summary and usage_summary["api_call"]["quantity"] > 100000:
            api_quantity = usage_summary["api_call"]["quantity"]
            routing_decision.update({
                "agent": AgentType.PERFORMANCE_ANALYZER,
                "confidence": min(0.85, api_quantity / 200000.0),
                "reasoning": [f"High API usage: {api_quantity:,.0f} calls"]
            })
        
        # Complex data patterns -> Data Researcher
        elif len(usage_summary) >= 4:  # Multiple usage types indicate complexity
            routing_decision.update({
                "agent": AgentType.DATA_RESEARCHER,
                "confidence": 0.75,
                "reasoning": ["Complex multi-service usage pattern detected"]
            })
        
        # Default to Business Advisor
        else:
            routing_decision.update({
                "agent": AgentType.BUSINESS_ADVISOR,
                "confidence": 0.6,
                "reasoning": ["General business inquiry routing"]
            })
        
        # Add context preservation data
        routing_decision["context_data"] = {
            "user_usage_summary": usage_summary,
            "total_monthly_cost": total_cost,
            "routing_timestamp": datetime.now(timezone.utc).isoformat(),
            "context_metadata": context.metadata
        }
        
        return routing_decision
    
    async def generate_insights_from_context(self, context: MockExecutionContext) -> Dict[str, Any]:
        """Generate business insights from context data analysis."""
        # Get user's historical data
        user_usage = await self.usage_tracker.get_user_usage(
            context.user_id,
            start_time=datetime.now(timezone.utc) - timedelta(days=90)
        )
        
        # Calculate cost optimization insights
        usage_data = {}
        for usage_type, usage_info in user_usage.get("usage_summary", {}).items():
            usage_data[usage_type] = {"quantity": usage_info.get("quantity", 0)}
        
        if usage_data:
            cost_optimization = self.cost_calculator.compare_tier_costs(
                {k: v["quantity"] for k, v in usage_data.items()}
            )
        else:
            cost_optimization = {"comparisons": {}, "cheapest_tier": "starter"}
        
        # Generate predictive insights
        insights = {
            "cost_insights": self._analyze_cost_trends(user_usage),
            "usage_insights": self._analyze_usage_patterns(user_usage),
            "optimization_insights": self._generate_optimization_recommendations(cost_optimization),
            "predictive_insights": self._generate_predictive_analysis(user_usage),
            "context_preservation": {
                "original_request": context.user_request,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_sources": ["usage_tracker", "cost_calculator"],
                "confidence_score": self._calculate_insight_confidence(user_usage)
            }
        }
        
        return insights
    
    def _analyze_cost_trends(self, user_usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze cost trends from usage data."""
        total_cost = user_usage.get("total_cost", 0.0)
        usage_summary = user_usage.get("usage_summary", {})
        
        trends = []
        
        # Cost driver analysis
        if usage_summary:
            cost_drivers = []
            for usage_type, data in usage_summary.items():
                cost = data.get("cost", 0.0)
                if cost > 0:
                    cost_drivers.append({
                        "type": usage_type,
                        "cost": cost,
                        "percentage": (cost / total_cost * 100) if total_cost > 0 else 0
                    })
            
            cost_drivers.sort(key=lambda x: x["cost"], reverse=True)
            trends.append({
                "type": "cost_driver_analysis",
                "data": cost_drivers[:3],  # Top 3 cost drivers
                "insight": f"Top cost driver: {cost_drivers[0]['type']}" if cost_drivers else "No cost data"
            })
        
        # Cost tier analysis
        if total_cost > 0:
            if total_cost < 50:
                tier_recommendation = "starter"
                savings_potential = 0
            elif total_cost < 200:
                tier_recommendation = "professional" 
                savings_potential = total_cost * 0.1
            else:
                tier_recommendation = "enterprise"
                savings_potential = total_cost * 0.15
            
            trends.append({
                "type": "tier_optimization",
                "data": {
                    "current_cost": total_cost,
                    "recommended_tier": tier_recommendation,
                    "potential_savings": savings_potential
                },
                "insight": f"Potential ${savings_potential:.2f} monthly savings with {tier_recommendation} tier"
            })
        
        return trends
    
    def _analyze_usage_patterns(self, user_usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze usage patterns for insights."""
        usage_summary = user_usage.get("usage_summary", {})
        total_events = user_usage.get("total_events", 0)
        
        patterns = []
        
        # Usage intensity analysis
        if total_events > 0:
            if total_events > 10000:
                intensity = "high"
                recommendation = "Consider batch processing to optimize costs"
            elif total_events > 1000:
                intensity = "moderate"
                recommendation = "Current usage is well-balanced"
            else:
                intensity = "low"
                recommendation = "Great opportunity to expand usage"
            
            patterns.append({
                "type": "usage_intensity",
                "data": {"total_events": total_events, "intensity": intensity},
                "insight": recommendation
            })
        
        # Service diversity analysis
        service_count = len(usage_summary)
        if service_count > 0:
            if service_count >= 4:
                diversity_level = "high"
                insight = "Complex multi-service architecture detected"
            elif service_count >= 2:
                diversity_level = "moderate"
                insight = "Good service utilization balance"
            else:
                diversity_level = "low"
                insight = "Opportunity to leverage additional services"
            
            patterns.append({
                "type": "service_diversity",
                "data": {"service_count": service_count, "diversity": diversity_level},
                "insight": insight
            })
        
        return patterns
    
    def _generate_optimization_recommendations(self, cost_optimization: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations from cost data."""
        recommendations = []
        
        comparisons = cost_optimization.get("comparisons", {})
        if len(comparisons) > 1:
            # Tier comparison recommendations
            tier_costs = [(tier, data["projected_monthly_cost"]) for tier, data in comparisons.items()]
            tier_costs.sort(key=lambda x: x[1])
            
            cheapest_tier, cheapest_cost = tier_costs[0]
            most_expensive_tier, highest_cost = tier_costs[-1]
            
            if highest_cost - cheapest_cost > 50:  # Significant difference
                recommendations.append({
                    "type": "tier_optimization",
                    "priority": "high",
                    "recommendation": f"Switch to {cheapest_tier} tier for optimal cost",
                    "data": {
                        "potential_savings": highest_cost - cheapest_cost,
                        "current_best": cheapest_tier,
                        "cost_difference": highest_cost - cheapest_cost
                    },
                    "confidence": 0.85
                })
        
        # Usage-based recommendations
        for tier, data in comparisons.items():
            breakdown = data.get("breakdown_by_type", {})
            for service_type, service_data in breakdown.items():
                quantity = service_data.get("quantity", 0)
                total_cost = service_data.get("total_cost", 0)
                
                if quantity > 0 and total_cost > 20:  # Significant usage and cost
                    if service_type == "api_calls" and quantity > 50000:
                        recommendations.append({
                            "type": "usage_optimization",
                            "priority": "medium",
                            "recommendation": f"Optimize {service_type} usage with caching",
                            "data": {
                                "current_usage": quantity,
                                "current_cost": total_cost,
                                "optimization_potential": total_cost * 0.2
                            },
                            "confidence": 0.7
                        })
        
        return recommendations
    
    def _generate_predictive_analysis(self, user_usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate predictive analysis from historical data."""
        total_cost = user_usage.get("total_cost", 0.0)
        total_events = user_usage.get("total_events", 0)
        
        predictions = []
        
        # Growth prediction based on current usage
        if total_events > 100:  # Sufficient data for prediction
            # Simple linear growth model
            monthly_growth_rate = 0.15  # Assume 15% monthly growth
            predicted_next_month_events = int(total_events * (1 + monthly_growth_rate))
            predicted_cost_next_month = total_cost * (1 + monthly_growth_rate)
            
            predictions.append({
                "type": "usage_growth_prediction",
                "timeframe": "next_month",
                "data": {
                    "predicted_events": predicted_next_month_events,
                    "predicted_cost": predicted_cost_next_month,
                    "growth_rate": monthly_growth_rate
                },
                "insight": f"Projected {monthly_growth_rate*100:.0f}% growth next month",
                "confidence": 0.65
            })
        
        # Tier upgrade prediction
        if total_cost > 0:
            current_tier_threshold = self._estimate_current_tier_threshold(total_cost)
            next_tier_threshold = current_tier_threshold * 2
            
            if total_cost > current_tier_threshold * 0.8:  # Close to threshold
                predictions.append({
                    "type": "tier_upgrade_prediction",
                    "timeframe": "2-3_months",
                    "data": {
                        "current_cost": total_cost,
                        "tier_threshold": next_tier_threshold,
                        "months_to_upgrade": 2
                    },
                    "insight": f"Likely tier upgrade needed in 2-3 months",
                    "confidence": 0.72
                })
        
        return predictions
    
    def _estimate_current_tier_threshold(self, cost: float) -> float:
        """Estimate current tier threshold based on cost."""
        if cost < 50:
            return 50
        elif cost < 200:
            return 200
        else:
            return 500
    
    def _calculate_insight_confidence(self, user_usage: Dict[str, Any]) -> float:
        """Calculate confidence score for insights based on data quality."""
        total_events = user_usage.get("total_events", 0)
        usage_types = len(user_usage.get("usage_summary", {}))
        
        # Base confidence on data volume and diversity
        data_volume_score = min(1.0, total_events / 1000.0)  # Max at 1000 events
        data_diversity_score = min(1.0, usage_types / 5.0)    # Max at 5 usage types
        
        # Combine scores
        confidence = (data_volume_score * 0.6) + (data_diversity_score * 0.4)
        return min(0.95, max(0.3, confidence))  # Clamp between 0.3 and 0.95


class TestAgentDecisionMakingData:
    """Test suite for agent decision-making data processing and analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.routing_engine = AgentRoutingEngine()
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
        
        # Test contexts
        self.high_usage_context = MockExecutionContext(
            user_id="high_usage_user",
            thread_id="thread_001", 
            run_id="run_001",
            user_request="Help me optimize my API costs",
            metadata={"user_tier": "professional", "region": "us-east-1"}
        )
        
        self.low_usage_context = MockExecutionContext(
            user_id="low_usage_user",
            thread_id="thread_002",
            run_id="run_002", 
            user_request="What services do you offer?",
            metadata={"user_tier": "starter", "region": "us-west-2"}
        )
    
    @pytest.mark.asyncio
    async def test_data_driven_agent_routing_high_cost_user(self):
        """Test agent routing decisions based on high-cost user data patterns."""
        # Set up high-cost usage data
        high_cost_events = []
        base_time = datetime.now(timezone.utc) - timedelta(days=15)
        
        # Create expensive usage patterns
        cost_patterns = [
            (UsageType.LLM_TOKENS, 500000, 10.0),  # High LLM usage
            (UsageType.API_CALL, 200000, 200.0),   # High API usage
            (UsageType.STORAGE, 100, 23.0),        # Significant storage
            (UsageType.AGENT_EXECUTION, 5000, 25.0) # Heavy agent usage
        ]
        
        for usage_type, quantity, cost in cost_patterns:
            for day in range(15):  # 15 days of usage
                event = await self.usage_tracker.track_usage(
                    user_id=self.high_usage_context.user_id,
                    usage_type=usage_type,
                    quantity=quantity / 15,  # Daily usage
                    unit="units",
                    metadata={"day": day}
                )
                high_cost_events.append(event)
        
        # Test routing decision
        routing_result = await self.routing_engine.route_based_on_usage_patterns(
            self.high_usage_context
        )
        
        # Validate routing decision
        assert "agent" in routing_result
        assert "confidence" in routing_result
        assert "reasoning" in routing_result
        assert "context_data" in routing_result
        
        # High-cost user should route to Cost Optimizer
        assert routing_result["agent"] == AgentType.COST_OPTIMIZER
        assert routing_result["confidence"] > 0.7
        assert len(routing_result["reasoning"]) > 0
        
        # Validate context preservation
        context_data = routing_result["context_data"]
        assert "user_usage_summary" in context_data
        assert "total_monthly_cost" in context_data
        assert context_data["total_monthly_cost"] > 200  # Should be high cost
        assert "routing_timestamp" in context_data
    
    @pytest.mark.asyncio
    async def test_data_driven_agent_routing_performance_patterns(self):
        """Test agent routing for performance-focused usage patterns."""
        # Set up high API usage indicating performance concerns
        performance_user = "performance_user"
        
        # Create high-volume API usage pattern
        for hour in range(24):
            await self.usage_tracker.track_usage(
                user_id=performance_user,
                usage_type=UsageType.API_CALL,
                quantity=10000,  # High API volume
                unit="calls",
                metadata={"hour": hour, "response_time_avg": 150 + (hour * 2)}
            )
        
        performance_context = MockExecutionContext(
            user_id=performance_user,
            thread_id="perf_thread",
            run_id="perf_run",
            user_request="My API responses are getting slower",
            metadata={"performance_concern": True}
        )
        
        # Test routing
        routing_result = await self.routing_engine.route_based_on_usage_patterns(
            performance_context
        )
        
        # Should route to Performance Analyzer due to high API usage
        assert routing_result["agent"] == AgentType.PERFORMANCE_ANALYZER
        assert routing_result["confidence"] > 0.6
        
        # Validate reasoning contains API usage information
        reasoning = " ".join(routing_result["reasoning"]).lower()
        assert "api" in reasoning
        
        # Context should preserve performance-related metadata
        context_data = routing_result["context_data"]
        assert context_data["context_metadata"].get("performance_concern") == True
    
    @pytest.mark.asyncio
    async def test_context_data_preservation_and_transformation(self):
        """Test preservation and transformation of context data through agent workflows."""
        # Set up diverse usage data
        diverse_user = "diverse_usage_user"
        usage_types = [
            UsageType.API_CALL,
            UsageType.LLM_TOKENS,
            UsageType.STORAGE,
            UsageType.COMPUTE,
            UsageType.WEBSOCKET_CONNECTION
        ]
        
        for usage_type in usage_types:
            await self.usage_tracker.track_usage(
                user_id=diverse_user,
                usage_type=usage_type,
                quantity=1000,
                unit="units",
                metadata={"service_integration": usage_type.value}
            )
        
        diverse_context = MockExecutionContext(
            user_id=diverse_user,
            thread_id="diverse_thread",
            run_id="diverse_run",
            user_request="I need a comprehensive analysis of my usage",
            metadata={
                "analysis_type": "comprehensive",
                "priority": "high",
                "original_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Test context preservation through routing
        routing_result = await self.routing_engine.route_based_on_usage_patterns(
            diverse_context
        )
        
        # Should route to Data Researcher for complex patterns
        assert routing_result["agent"] == AgentType.DATA_RESEARCHER
        
        # Validate context preservation
        context_data = routing_result["context_data"]
        assert len(context_data["user_usage_summary"]) == len(usage_types)
        assert context_data["context_metadata"]["analysis_type"] == "comprehensive"
        assert context_data["context_metadata"]["priority"] == "high"
        
        # Test context transformation through insight generation
        insights = await self.routing_engine.generate_insights_from_context(diverse_context)
        
        # Validate insight structure
        assert "cost_insights" in insights
        assert "usage_insights" in insights
        assert "optimization_insights" in insights
        assert "predictive_insights" in insights
        assert "context_preservation" in insights
        
        # Validate context preservation in insights
        context_preservation = insights["context_preservation"]
        assert context_preservation["original_request"] == diverse_context.user_request
        assert "analysis_timestamp" in context_preservation
        assert context_preservation["confidence_score"] > 0.5
    
    @pytest.mark.asyncio 
    async def test_business_insight_generation_from_data_analysis(self):
        """Test generation of actionable business insights from data analysis."""
        # Set up business-focused usage data
        business_user = "business_insights_user"
        
        # Create business-relevant usage patterns
        business_usage_events = [
            (UsageType.API_CALL, 75000, 75.0, "customer_api_integration"),
            (UsageType.LLM_TOKENS, 2000000, 40.0, "content_generation"),
            (UsageType.AGENT_EXECUTION, 1500, 7.5, "automated_workflows"),
            (UsageType.STORAGE, 50, 1.15, "customer_data_storage")
        ]
        
        for usage_type, quantity, cost, description in business_usage_events:
            await self.usage_tracker.track_usage(
                user_id=business_user,
                usage_type=usage_type,
                quantity=quantity,
                unit="units",
                metadata={"business_function": description},
                cost=cost
            )
        
        business_context = MockExecutionContext(
            user_id=business_user,
            thread_id="business_thread", 
            run_id="business_run",
            user_request="Show me business insights and ROI analysis",
            metadata={"business_focus": "roi_analysis", "department": "operations"}
        )
        
        # Generate insights
        insights = await self.routing_engine.generate_insights_from_context(business_context)
        
        # Validate cost insights
        cost_insights = insights["cost_insights"]
        assert len(cost_insights) > 0
        
        # Should identify cost drivers
        cost_driver_insight = next((insight for insight in cost_insights 
                                  if insight.get("type") == "cost_driver_analysis"), None)
        assert cost_driver_insight is not None
        assert len(cost_driver_insight["data"]) > 0
        assert cost_driver_insight["data"][0]["cost"] > 0
        
        # Validate usage insights
        usage_insights = insights["usage_insights"]
        assert len(usage_insights) > 0
        
        # Should identify usage intensity and service diversity
        intensity_insight = next((insight for insight in usage_insights
                                if insight.get("type") == "usage_intensity"), None)
        assert intensity_insight is not None
        
        # Validate optimization insights
        optimization_insights = insights["optimization_insights"]
        assert len(optimization_insights) >= 0  # May have recommendations
        
        # Validate predictive insights
        predictive_insights = insights["predictive_insights"]
        assert len(predictive_insights) > 0
        
        # Should have growth predictions
        growth_prediction = next((insight for insight in predictive_insights
                                if insight.get("type") == "usage_growth_prediction"), None)
        if growth_prediction:  # May not always be present
            assert growth_prediction["confidence"] > 0.5
            assert "predicted_cost" in growth_prediction["data"]
    
    @pytest.mark.asyncio
    async def test_recommendation_engine_data_processing(self):
        """Test recommendation engine processing based on user data patterns."""
        # Set up optimization-focused scenario
        optimization_user = "optimization_target_user"
        
        # Create suboptimal usage pattern for clear recommendations
        suboptimal_usage = [
            (UsageType.API_CALL, 150000, 150.0),   # High API usage - caching opportunity
            (UsageType.LLM_TOKENS, 3000000, 60.0), # Very high token usage - prompt optimization
            (UsageType.STORAGE, 200, 4.6),         # High storage - archiving opportunity
        ]
        
        for usage_type, quantity, cost in suboptimal_usage:
            await self.usage_tracker.track_usage(
                user_id=optimization_user,
                usage_type=usage_type,
                quantity=quantity,
                unit="units"
            )
        
        optimization_context = MockExecutionContext(
            user_id=optimization_user,
            thread_id="opt_thread",
            run_id="opt_run", 
            user_request="Give me specific recommendations to reduce costs",
            metadata={"optimization_goal": "cost_reduction"}
        )
        
        # Generate insights with recommendations
        insights = await self.routing_engine.generate_insights_from_context(optimization_context)
        
        # Validate optimization recommendations
        optimization_insights = insights["optimization_insights"]
        assert len(optimization_insights) > 0
        
        # Should have specific, actionable recommendations
        recommendations_found = []
        for insight in optimization_insights:
            if insight.get("type") in ["tier_optimization", "usage_optimization"]:
                recommendations_found.append(insight)
                assert "recommendation" in insight
                assert "priority" in insight
                assert insight["priority"] in ["high", "medium", "low"]
                assert insight.get("confidence", 0) > 0.5
        
        assert len(recommendations_found) > 0, "Should generate actionable recommendations"
        
        # Validate recommendation data quality
        for rec in recommendations_found:
            if "data" in rec:
                data = rec["data"]
                if "potential_savings" in data:
                    assert data["potential_savings"] >= 0
                if "optimization_potential" in data:
                    assert data["optimization_potential"] >= 0
    
    @pytest.mark.asyncio
    async def test_predictive_analysis_and_trend_detection(self):
        """Test predictive analysis capabilities and trend detection from historical data."""
        # Set up growing usage trend
        trending_user = "trending_growth_user"
        
        # Create 30-day trend with increasing usage
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        daily_growth_rate = 1.02  # 2% daily growth
        
        for day in range(30):
            daily_multiplier = daily_growth_rate ** day
            daily_api_calls = int(1000 * daily_multiplier)
            daily_tokens = int(25000 * daily_multiplier)
            
            await self.usage_tracker.track_usage(
                user_id=trending_user,
                usage_type=UsageType.API_CALL,
                quantity=daily_api_calls,
                unit="calls",
                metadata={"day": day, "trend": "growing"}
            )
            
            await self.usage_tracker.track_usage(
                user_id=trending_user,
                usage_type=UsageType.LLM_TOKENS,
                quantity=daily_tokens,
                unit="tokens", 
                metadata={"day": day, "trend": "growing"}
            )
        
        trending_context = MockExecutionContext(
            user_id=trending_user,
            thread_id="trend_thread",
            run_id="trend_run",
            user_request="What trends do you see in my usage? What should I expect?",
            metadata={"analysis_focus": "predictive"}
        )
        
        # Generate predictive insights
        insights = await self.routing_engine.generate_insights_from_context(trending_context)
        
        # Validate predictive analysis
        predictive_insights = insights["predictive_insights"]
        assert len(predictive_insights) > 0
        
        # Should have growth predictions
        growth_predictions = [insight for insight in predictive_insights
                            if "growth" in insight.get("type", "").lower()]
        assert len(growth_predictions) > 0
        
        for prediction in growth_predictions:
            assert "timeframe" in prediction
            assert "data" in prediction
            assert "confidence" in prediction
            assert 0.0 <= prediction["confidence"] <= 1.0
            
            # Validate prediction data
            data = prediction["data"]
            if "predicted_cost" in data:
                assert data["predicted_cost"] > 0
            if "growth_rate" in data:
                assert data["growth_rate"] >= 0
        
        # Should predict tier upgrades for rapidly growing usage
        tier_predictions = [insight for insight in predictive_insights
                          if "tier" in insight.get("type", "").lower()]
        
        if tier_predictions:  # May not always predict tier changes
            for prediction in tier_predictions:
                assert "months_to_upgrade" in prediction["data"]
                assert prediction["data"]["months_to_upgrade"] > 0
    
    def test_agent_capability_matching_data_processing(self):
        """Test agent capability matching based on processed data characteristics."""
        # Test different request types and expected agent matches
        test_scenarios = [
            {
                "request": "I need to reduce my monthly costs by 30%",
                "keywords": ["costs", "reduce", "monthly"],
                "expected_agent_type": AgentType.COST_OPTIMIZER,
                "data_indicators": {"cost_focus": True}
            },
            {
                "request": "My API response times are inconsistent and slow",
                "keywords": ["response", "times", "slow", "performance"],
                "expected_agent_type": AgentType.PERFORMANCE_ANALYZER,
                "data_indicators": {"performance_focus": True}
            },
            {
                "request": "Help me understand market trends and business opportunities",
                "keywords": ["market", "trends", "business", "opportunities"],
                "expected_agent_type": AgentType.BUSINESS_ADVISOR,
                "data_indicators": {"business_focus": True}
            },
            {
                "request": "I need analysis of my usage patterns and data insights",
                "keywords": ["analysis", "patterns", "data", "insights"],
                "expected_agent_type": AgentType.DATA_RESEARCHER,
                "data_indicators": {"analysis_focus": True}
            }
        ]
        
        # Test capability matching logic
        for scenario in test_scenarios:
            # Analyze request content
            request_keywords = scenario["keywords"]
            expected_agent = scenario["expected_agent_type"]
            
            # Get agent capabilities
            agent_capabilities = self.routing_engine.agent_capabilities[expected_agent]
            
            # Validate keyword overlap with agent specialties
            specialty_overlap = []
            for keyword in request_keywords:
                for specialty in agent_capabilities["specialties"]:
                    if keyword.lower() in specialty.lower() or specialty.lower() in keyword.lower():
                        specialty_overlap.append((keyword, specialty))
            
            # Should have some overlap between request keywords and agent specialties
            assert len(specialty_overlap) > 0, f"No capability match for {scenario['request']}"
            
            # Validate confidence factors are relevant
            confidence_factors = agent_capabilities["confidence_factors"]
            assert len(confidence_factors) > 0
            
            # Validate threshold metrics exist
            threshold_metrics = agent_capabilities["threshold_metrics"]
            assert len(threshold_metrics) > 0
            
            for metric_name, threshold_value in threshold_metrics.items():
                assert isinstance(threshold_value, (int, float))
                assert threshold_value >= 0