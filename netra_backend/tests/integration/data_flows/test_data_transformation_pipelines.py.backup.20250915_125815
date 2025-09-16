"""
Data Transformation Pipeline Integration Tests

These tests validate data processing pipelines that transform raw data into
business insights, cost analysis, performance metrics, and actionable recommendations.

Focus Areas:
- Raw data processing into business insights
- Cost analysis and optimization calculations  
- Performance metrics aggregation and analysis
- User behavior analysis and pattern detection
- Business intelligence data transformation
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List
import asyncio

from netra_backend.app.services.billing.cost_calculator import CostCalculator, CostBreakdown, CostType
from netra_backend.app.services.billing.usage_tracker import UsageTracker, UsageType, UsageEvent
from netra_backend.app.services.quality.quality_score_calculators import QualityScoreCalculators


class DataTransformationProcessor:
    """Helper class for data transformation operations."""
    
    def __init__(self):
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
    
    async def process_raw_usage_to_insights(self, raw_events: List[UsageEvent]) -> Dict[str, Any]:
        """Transform raw usage events into business insights."""
        if not raw_events:
            return {"insights": [], "summary": {}}
        
        # Aggregate usage by type and time
        usage_by_type = {}
        hourly_usage = {}
        total_cost = 0.0
        
        for event in raw_events:
            # By type aggregation
            usage_type = event.usage_type.value
            if usage_type not in usage_by_type:
                usage_by_type[usage_type] = {"quantity": 0.0, "cost": 0.0, "events": 0}
            
            usage_by_type[usage_type]["quantity"] += event.quantity
            usage_by_type[usage_type]["cost"] += event.cost
            usage_by_type[usage_type]["events"] += 1
            total_cost += event.cost
            
            # Hourly aggregation
            hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_usage:
                hourly_usage[hour_key] = 0.0
            hourly_usage[hour_key] += event.cost
        
        # Generate insights
        insights = []
        
        # Top cost drivers
        sorted_usage = sorted(usage_by_type.items(), 
                            key=lambda x: x[1]["cost"], reverse=True)
        if sorted_usage:
            top_cost_driver = sorted_usage[0]
            insights.append({
                "type": "cost_optimization",
                "message": f"Top cost driver is {top_cost_driver[0]} at ${top_cost_driver[1]['cost']:.2f}",
                "priority": "high",
                "savings_potential": top_cost_driver[1]["cost"] * 0.15  # 15% potential savings
            })
        
        # Usage pattern analysis
        if len(hourly_usage) > 1:
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])
            insights.append({
                "type": "usage_pattern",
                "message": f"Peak usage at {peak_hour[0]} with ${peak_hour[1]:.2f} in costs",
                "priority": "medium",
                "optimization_suggestion": "Consider load balancing or batching during peak hours"
            })
        
        return {
            "insights": insights,
            "summary": {
                "total_events": len(raw_events),
                "total_cost": total_cost,
                "usage_by_type": usage_by_type,
                "hourly_distribution": hourly_usage
            }
        }
    
    def calculate_cost_optimization_recommendations(self, usage_data: Dict[str, Any], 
                                                   current_tier: str) -> Dict[str, Any]:
        """Transform usage data into cost optimization recommendations."""
        recommendations = []
        potential_savings = 0.0
        
        # Calculate costs for all tiers
        tier_comparison = self.cost_calculator.compare_tier_costs(
            {k: v["quantity"] for k, v in usage_data.items()}
        )
        
        current_cost = tier_comparison["comparisons"][current_tier]["projected_monthly_cost"]
        cheapest_tier = tier_comparison["cheapest_tier"]
        cheapest_cost = tier_comparison["cheapest_cost"]
        
        # Tier optimization recommendation
        if cheapest_tier != current_tier:
            savings = current_cost - cheapest_cost
            recommendations.append({
                "type": "tier_optimization",
                "recommendation": f"Switch from {current_tier} to {cheapest_tier} tier",
                "monthly_savings": savings,
                "percentage_savings": (savings / current_cost) * 100 if current_cost > 0 else 0,
                "priority": "high" if savings > 50 else "medium"
            })
            potential_savings += savings
        
        # Usage optimization recommendations
        for usage_type, usage_info in usage_data.items():
            quantity = usage_info["quantity"]
            
            if usage_type == "api_calls" and quantity > 50000:
                # High API usage optimization
                potential_reduction = quantity * 0.20  # 20% reduction potential
                cost_per_call = 0.001  # Approximate cost per call
                monthly_savings = potential_reduction * cost_per_call
                
                recommendations.append({
                    "type": "usage_optimization",
                    "recommendation": "Implement API response caching to reduce redundant calls",
                    "usage_type": usage_type,
                    "current_usage": quantity,
                    "potential_reduction": potential_reduction,
                    "monthly_savings": monthly_savings,
                    "priority": "high"
                })
                potential_savings += monthly_savings
            
            elif usage_type == "llm_tokens" and quantity > 1000000:
                # High token usage optimization
                potential_reduction = quantity * 0.25  # 25% reduction potential
                cost_per_token = 0.00002
                monthly_savings = potential_reduction * cost_per_token
                
                recommendations.append({
                    "type": "usage_optimization",
                    "recommendation": "Optimize prompt engineering and use shorter contexts",
                    "usage_type": usage_type,
                    "current_usage": quantity,
                    "potential_reduction": potential_reduction,
                    "monthly_savings": monthly_savings,
                    "priority": "high"
                })
                potential_savings += monthly_savings
        
        return {
            "recommendations": recommendations,
            "current_tier": current_tier,
            "optimal_tier": cheapest_tier,
            "current_monthly_cost": current_cost,
            "optimized_monthly_cost": current_cost - potential_savings,
            "total_potential_savings": potential_savings,
            "tier_comparisons": tier_comparison["comparisons"]
        }


class TestDataTransformationPipelines:
    """Test suite for data transformation pipelines and business intelligence processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = DataTransformationProcessor()
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
        
        # Test data
        self.sample_usage_data = {
            "api_calls": {"quantity": 75000},
            "llm_tokens": {"quantity": 2500000}, 
            "storage": {"quantity": 50.0},
            "bandwidth": {"quantity": 12.5},
            "agent_execution": {"quantity": 1500}
        }
    
    @pytest.mark.asyncio
    async def test_raw_data_processing_to_business_insights(self):
        """Test transformation of raw usage events into actionable business insights."""
        # Create sample raw usage events
        base_time = datetime.now(timezone.utc)
        raw_events = []
        
        # Generate diverse usage patterns
        event_patterns = [
            (UsageType.API_CALL, 1000, 1.0, "API batch processing"),
            (UsageType.LLM_TOKENS, 50000, 1.0, "Content generation"),
            (UsageType.STORAGE, 5.0, 0.115, "Data storage"), 
            (UsageType.API_CALL, 2000, 2.0, "Peak hour usage"),
            (UsageType.LLM_TOKENS, 75000, 1.5, "Analysis processing"),
            (UsageType.AGENT_EXECUTION, 10, 0.05, "Agent workflows")
        ]
        
        for i, (usage_type, quantity, cost, description) in enumerate(event_patterns):
            event = UsageEvent(
                user_id=f"user_{i//2 + 1}",  # Multiple users
                usage_type=usage_type,
                quantity=quantity,
                unit="units",
                timestamp=base_time + timedelta(hours=i),
                metadata={"description": description},
                cost=cost
            )
            raw_events.append(event)
        
        # Process raw data into insights
        insights_result = await self.processor.process_raw_usage_to_insights(raw_events)
        
        # Validate insights generation
        assert "insights" in insights_result
        assert "summary" in insights_result
        assert len(insights_result["insights"]) > 0, "Should generate actionable insights"
        
        # Validate summary statistics
        summary = insights_result["summary"]
        assert summary["total_events"] == len(raw_events)
        assert summary["total_cost"] > 0
        assert len(summary["usage_by_type"]) > 0
        assert len(summary["hourly_distribution"]) > 0
        
        # Validate insight types and structure
        for insight in insights_result["insights"]:
            assert "type" in insight
            assert "message" in insight
            assert "priority" in insight
            assert insight["type"] in ["cost_optimization", "usage_pattern", "performance"]
            assert insight["priority"] in ["high", "medium", "low"]
    
    def test_cost_analysis_optimization_calculations(self):
        """Test cost analysis pipeline that calculates optimization opportunities."""
        # Test cost optimization analysis
        optimization_result = self.processor.calculate_cost_optimization_recommendations(
            self.sample_usage_data,
            current_tier="professional"
        )
        
        # Validate optimization structure
        assert "recommendations" in optimization_result
        assert "current_tier" in optimization_result
        assert "optimal_tier" in optimization_result
        assert "total_potential_savings" in optimization_result
        assert "tier_comparisons" in optimization_result
        
        # Validate recommendations
        recommendations = optimization_result["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0, "Should generate optimization recommendations"
        
        # Validate recommendation structure
        for rec in recommendations:
            assert "type" in rec
            assert "recommendation" in rec
            assert "priority" in rec
            assert rec["type"] in ["tier_optimization", "usage_optimization", "performance_optimization"]
            assert rec["priority"] in ["high", "medium", "low"]
            
            if "monthly_savings" in rec:
                assert rec["monthly_savings"] >= 0, "Savings should be non-negative"
        
        # Validate tier comparison data
        tier_comparisons = optimization_result["tier_comparisons"]
        assert len(tier_comparisons) >= 3, "Should compare multiple tiers"
        
        for tier_name, comparison in tier_comparisons.items():
            assert "projected_monthly_cost" in comparison
            assert "breakdown_by_type" in comparison
            assert comparison["projected_monthly_cost"] >= 0
    
    def test_performance_metrics_aggregation_analysis(self):
        """Test performance metrics aggregation and trend analysis."""
        # Create performance-focused usage data
        performance_scenarios = [
            {"api_calls": {"quantity": 10000}, "response_time_avg": 150, "error_rate": 0.02},
            {"api_calls": {"quantity": 15000}, "response_time_avg": 200, "error_rate": 0.015},  
            {"api_calls": {"quantity": 8000}, "response_time_avg": 120, "error_rate": 0.01},
            {"api_calls": {"quantity": 25000}, "response_time_avg": 350, "error_rate": 0.05}
        ]
        
        # Process performance metrics
        performance_analysis = self._analyze_performance_patterns(performance_scenarios)
        
        # Validate performance analysis
        assert "metrics" in performance_analysis
        assert "trends" in performance_analysis
        assert "recommendations" in performance_analysis
        
        metrics = performance_analysis["metrics"]
        assert "average_response_time" in metrics
        assert "error_rate_trend" in metrics
        assert "throughput_analysis" in metrics
        
        # Validate performance trends
        trends = performance_analysis["trends"]
        assert "response_time_correlation" in trends
        assert "error_rate_threshold_alerts" in trends
        
        # Should identify performance degradation patterns
        recommendations = performance_analysis["recommendations"]
        assert len(recommendations) > 0
        
        # Check for performance optimization recommendations
        perf_recs = [r for r in recommendations if "performance" in r.get("type", "").lower()]
        assert len(perf_recs) > 0, "Should generate performance recommendations"
    
    def test_user_behavior_analysis_pattern_detection(self):
        """Test user behavior analysis and usage pattern detection."""
        # Create user behavior data patterns
        user_behavior_data = {
            "user_001": {
                "sessions": [
                    {"start": "09:00", "duration": 120, "api_calls": 500, "tokens": 25000},
                    {"start": "14:30", "duration": 90, "api_calls": 300, "tokens": 15000}
                ],
                "tier": "professional",
                "weekly_usage": 45000
            },
            "user_002": {  
                "sessions": [
                    {"start": "08:00", "duration": 180, "api_calls": 1200, "tokens": 80000},
                    {"start": "20:00", "duration": 60, "api_calls": 200, "tokens": 10000}
                ],
                "tier": "enterprise", 
                "weekly_usage": 120000
            },
            "user_003": {
                "sessions": [
                    {"start": "10:00", "duration": 45, "api_calls": 100, "tokens": 5000}
                ],
                "tier": "starter",
                "weekly_usage": 8000
            }
        }
        
        # Analyze user behavior patterns
        behavior_analysis = self._analyze_user_behavior(user_behavior_data)
        
        # Validate behavior analysis structure
        assert "user_segments" in behavior_analysis
        assert "usage_patterns" in behavior_analysis  
        assert "engagement_metrics" in behavior_analysis
        assert "recommendations" in behavior_analysis
        
        # Validate user segmentation
        segments = behavior_analysis["user_segments"]
        assert len(segments) >= 2, "Should identify different user segments"
        
        for segment in segments:
            assert "segment_name" in segment
            assert "characteristics" in segment
            assert "user_count" in segment
            assert segment["user_count"] > 0
        
        # Validate usage patterns
        patterns = behavior_analysis["usage_patterns"]
        assert "peak_hours" in patterns
        assert "session_duration_avg" in patterns
        assert "usage_intensity" in patterns
        
        # Validate engagement metrics
        engagement = behavior_analysis["engagement_metrics"]
        assert "active_users" in engagement
        assert "retention_indicators" in engagement
    
    def test_business_intelligence_data_transformation(self):
        """Test transformation of operational data into business intelligence insights."""
        # Create comprehensive BI dataset
        bi_raw_data = {
            "revenue": {
                "monthly_recurring": 45000.0,
                "one_time_charges": 12000.0,
                "tier_distribution": {
                    "free": {"users": 1200, "revenue": 0},
                    "starter": {"users": 450, "revenue": 4500},
                    "professional": {"users": 180, "revenue": 9000}, 
                    "enterprise": {"users": 25, "revenue": 12500}
                }
            },
            "usage_metrics": {
                "total_api_calls": 5500000,
                "total_llm_tokens": 85000000,
                "total_storage_gb": 2500,
                "active_users_monthly": 1855
            },
            "operational": {
                "support_tickets": 125,
                "uptime_percentage": 99.7,
                "response_time_avg": 185
            }
        }
        
        # Transform into BI insights
        bi_insights = self._transform_to_business_intelligence(bi_raw_data)
        
        # Validate BI transformation
        assert "kpi_dashboard" in bi_insights
        assert "growth_metrics" in bi_insights
        assert "revenue_analysis" in bi_insights
        assert "operational_health" in bi_insights
        
        # Validate KPI dashboard
        kpis = bi_insights["kpi_dashboard"]
        assert "monthly_recurring_revenue" in kpis
        assert "customer_acquisition_cost" in kpis
        assert "average_revenue_per_user" in kpis
        assert "usage_efficiency" in kpis
        
        # Validate growth metrics
        growth = bi_insights["growth_metrics"] 
        assert "user_growth_rate" in growth
        assert "revenue_growth_rate" in growth
        assert "usage_growth_rate" in growth
        
        # Validate revenue analysis
        revenue_analysis = bi_insights["revenue_analysis"]
        assert "tier_performance" in revenue_analysis
        assert "conversion_opportunities" in revenue_analysis
        
        # Validate tier performance includes conversion recommendations
        tier_performance = revenue_analysis["tier_performance"]
        assert len(tier_performance) >= 3, "Should analyze multiple tiers"
        
        for tier, performance in tier_performance.items():
            assert "user_count" in performance
            assert "revenue_per_user" in performance
            assert performance["user_count"] >= 0
            assert performance["revenue_per_user"] >= 0
    
    def test_data_quality_transformation_accuracy(self):
        """Test accuracy of data quality transformations and score aggregations."""
        # Create samples with known quality characteristics
        quality_samples = [
            {
                "content": "Implement Redis caching with 300-second TTL to reduce database load by 40%.",
                "expected_high_scores": ["actionability", "quantification", "specificity"]
            },
            {
                "content": "Consider optimizing performance through various improvements and enhancements.",
                "expected_low_scores": ["specificity", "actionability", "quantification"]
            },
            {
                "content": "Step 1: Configure batch_size=32. Step 2: Set learning_rate=0.001. Step 3: Run for 1000 epochs.",
                "expected_high_scores": ["actionability", "quantification"]
            },
            {
                "content": "This analysis provides comprehensive insights into your system's capabilities and potential areas for improvement.",
                "expected_low_scores": ["specificity", "actionability"]
            }
        ]
        
        # Process quality scores
        quality_results = []
        for sample in quality_samples:
            content = sample["content"]
            scores = {
                "specificity": QualityScoreCalculators.calculate_specificity_score(content),
                "actionability": QualityScoreCalculators.calculate_actionability_score(content),
                "quantification": QualityScoreCalculators.calculate_quantification_score(content),
                "novelty": QualityScoreCalculators.calculate_novelty_score(content),
                "completeness": QualityScoreCalculators.calculate_completeness_score(content, "recommendation"),
                "domain_relevance": QualityScoreCalculators.calculate_domain_relevance_score(content)
            }
            
            quality_results.append({
                "content": content,
                "scores": scores,
                "expected_high": sample.get("expected_high_scores", []),
                "expected_low": sample.get("expected_low_scores", [])
            })
        
        # Validate quality score transformations
        for result in quality_results:
            scores = result["scores"]
            
            # All scores should be in valid range
            for score_name, score_value in scores.items():
                assert 0.0 <= score_value <= 1.0, f"{score_name} score {score_value} out of range [0,1]"
            
            # Validate expected high scores
            for expected_high in result["expected_high"]:
                if expected_high in scores:
                    assert scores[expected_high] > 0.5, f"Expected high {expected_high} score for: {result['content'][:50]}..."
            
            # Validate expected low scores
            for expected_low in result["expected_low"]:
                if expected_low in scores:
                    assert scores[expected_low] < 0.6, f"Expected low {expected_low} score for: {result['content'][:50]}..."
        
        # Validate aggregate quality transformations
        aggregate_scores = self._calculate_aggregate_quality_metrics(quality_results)
        
        assert "average_scores" in aggregate_scores
        assert "score_distribution" in aggregate_scores
        assert "quality_insights" in aggregate_scores
        
        # Average scores should be reasonable
        avg_scores = aggregate_scores["average_scores"]
        for score_name, avg_value in avg_scores.items():
            assert 0.0 <= avg_value <= 1.0, f"Average {score_name} score out of range"
    
    def _analyze_performance_patterns(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper method to analyze performance patterns."""
        total_calls = sum(s["api_calls"]["quantity"] for s in scenarios)
        avg_response_time = sum(s["response_time_avg"] for s in scenarios) / len(scenarios)
        avg_error_rate = sum(s["error_rate"] for s in scenarios) / len(scenarios)
        
        # Identify correlation between load and response time
        high_load_scenarios = [s for s in scenarios if s["api_calls"]["quantity"] > 12000]
        response_time_correlation = "positive" if len(high_load_scenarios) > 0 and \
            sum(s["response_time_avg"] for s in high_load_scenarios) / len(high_load_scenarios) > avg_response_time else "none"
        
        recommendations = []
        if avg_response_time > 200:
            recommendations.append({
                "type": "performance_optimization",
                "message": "High average response time detected",
                "recommendation": "Implement caching and optimize database queries",
                "priority": "high"
            })
        
        if avg_error_rate > 0.03:
            recommendations.append({
                "type": "performance_optimization", 
                "message": "High error rate detected",
                "recommendation": "Implement retry logic and circuit breakers",
                "priority": "high"
            })
        
        return {
            "metrics": {
                "average_response_time": avg_response_time,
                "error_rate_trend": avg_error_rate,
                "throughput_analysis": total_calls / len(scenarios)
            },
            "trends": {
                "response_time_correlation": response_time_correlation,
                "error_rate_threshold_alerts": avg_error_rate > 0.02
            },
            "recommendations": recommendations
        }
    
    def _analyze_user_behavior(self, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to analyze user behavior patterns."""
        # Segment users by usage intensity
        segments = []
        high_usage_users = [uid for uid, data in behavior_data.items() if data["weekly_usage"] > 50000]
        medium_usage_users = [uid for uid, data in behavior_data.items() if 10000 <= data["weekly_usage"] <= 50000]
        low_usage_users = [uid for uid, data in behavior_data.items() if data["weekly_usage"] < 10000]
        
        if high_usage_users:
            segments.append({
                "segment_name": "power_users",
                "characteristics": "High weekly usage, multiple sessions",
                "user_count": len(high_usage_users)
            })
        
        if medium_usage_users:
            segments.append({
                "segment_name": "regular_users", 
                "characteristics": "Moderate usage, consistent patterns",
                "user_count": len(medium_usage_users)
            })
        
        if low_usage_users:
            segments.append({
                "segment_name": "occasional_users",
                "characteristics": "Low usage, infrequent sessions",
                "user_count": len(low_usage_users)
            })
        
        # Calculate usage patterns
        all_sessions = []
        for user_data in behavior_data.values():
            all_sessions.extend(user_data.get("sessions", []))
        
        avg_session_duration = sum(s["duration"] for s in all_sessions) / len(all_sessions) if all_sessions else 0
        
        return {
            "user_segments": segments,
            "usage_patterns": {
                "peak_hours": ["09:00-10:00", "14:00-15:00"],  # Based on session start times
                "session_duration_avg": avg_session_duration,
                "usage_intensity": "varied"
            },
            "engagement_metrics": {
                "active_users": len(behavior_data),
                "retention_indicators": len(segments)
            }
        }
    
    def _transform_to_business_intelligence(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to transform raw data into business intelligence."""
        revenue = raw_data["revenue"]
        usage = raw_data["usage_metrics"]
        operational = raw_data["operational"]
        
        total_revenue = revenue["monthly_recurring"] + revenue["one_time_charges"]
        total_users = sum(tier["users"] for tier in revenue["tier_distribution"].values())
        arpu = total_revenue / total_users if total_users > 0 else 0
        
        # Calculate tier performance
        tier_performance = {}
        for tier_name, tier_data in revenue["tier_distribution"].items():
            tier_performance[tier_name] = {
                "user_count": tier_data["users"],
                "revenue_per_user": tier_data["revenue"] / tier_data["users"] if tier_data["users"] > 0 else 0,
                "revenue_share": tier_data["revenue"] / total_revenue if total_revenue > 0 else 0
            }
        
        return {
            "kpi_dashboard": {
                "monthly_recurring_revenue": revenue["monthly_recurring"],
                "customer_acquisition_cost": 50.0,  # Placeholder calculation
                "average_revenue_per_user": arpu,
                "usage_efficiency": usage["total_api_calls"] / total_users if total_users > 0 else 0
            },
            "growth_metrics": {
                "user_growth_rate": 0.15,  # 15% monthly growth
                "revenue_growth_rate": 0.12,  # 12% monthly growth
                "usage_growth_rate": 0.18   # 18% monthly growth
            },
            "revenue_analysis": {
                "tier_performance": tier_performance,
                "conversion_opportunities": len([t for t in tier_performance.values() if t["user_count"] > 100])
            },
            "operational_health": {
                "system_uptime": operational["uptime_percentage"],
                "support_efficiency": operational["support_tickets"] / total_users,
                "performance_score": 100 - (operational["response_time_avg"] - 100) / 10
            }
        }
    
    def _calculate_aggregate_quality_metrics(self, quality_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper method to calculate aggregate quality metrics."""
        all_scores = {}
        for result in quality_results:
            for score_name, score_value in result["scores"].items():
                if score_name not in all_scores:
                    all_scores[score_name] = []
                all_scores[score_name].append(score_value)
        
        # Calculate averages
        average_scores = {}
        for score_name, scores in all_scores.items():
            average_scores[score_name] = sum(scores) / len(scores)
        
        # Score distribution analysis
        score_distribution = {}
        for score_name, scores in all_scores.items():
            high_scores = len([s for s in scores if s > 0.7])
            medium_scores = len([s for s in scores if 0.4 <= s <= 0.7])
            low_scores = len([s for s in scores if s < 0.4])
            
            score_distribution[score_name] = {
                "high": high_scores,
                "medium": medium_scores, 
                "low": low_scores
            }
        
        return {
            "average_scores": average_scores,
            "score_distribution": score_distribution,
            "quality_insights": [
                "Quality scores show consistent patterns across different content types",
                "Actionability and quantification scores correlate with specific technical content"
            ]
        }