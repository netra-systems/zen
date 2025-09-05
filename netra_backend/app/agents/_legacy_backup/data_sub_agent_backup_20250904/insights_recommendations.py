"""Insights Recommendations Generator

Specialized recommendations generator for InsightsGenerator.
Generates specific recommendations based on grouped insights analysis.

Business Value: Actionable recommendations for customer optimization strategies.
"""

from typing import Any, Dict, List


class InsightsRecommendationsGenerator:
    """Specialized generator for insight-based recommendations."""
    
    async def generate_recommendations(self, all_insights: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations based on insights."""
        insight_types = self._group_insights_by_type(all_insights)
        recommendations = []
        self._add_all_recommendation_types(insight_types, recommendations)
        return recommendations
    
    def _add_all_recommendation_types(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                    recommendations: List[str]) -> None:
        """Add all types of recommendations to the list."""
        self._add_performance_recommendations(insight_types, recommendations)
        self._add_error_recommendations(insight_types, recommendations)
        self._add_cost_recommendations(insight_types, recommendations)
        self._add_scheduling_recommendations(insight_types, recommendations)
    
    def _group_insights_by_type(self, all_insights: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group insights by type for pattern analysis."""
        insight_types = {}
        for insight in all_insights:
            self._add_insight_to_group(insight, insight_types)
        return insight_types
    
    def _add_insight_to_group(self, insight: Dict[str, Any], 
                            insight_types: Dict[str, List[Dict[str, Any]]]) -> None:
        """Add a single insight to its type group."""
        insight_type = insight.get("type", "unknown")
        if insight_type not in insight_types:
            insight_types[insight_type] = []
        insight_types[insight_type].append(insight)
    
    def _add_performance_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                       recommendations: List[str]) -> None:
        """Add performance-related recommendations."""
        self._add_degradation_recommendations(insight_types, recommendations)
        self._add_latency_recommendations(insight_types, recommendations)
    
    def _add_degradation_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                       recommendations: List[str]) -> None:
        """Add recommendations for performance degradation."""
        if "performance_degradation" in insight_types:
            recommendations.append("Implement performance monitoring alerts to catch degradation early")
            recommendations.append("Consider horizontal scaling or resource optimization")
    
    def _add_latency_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                   recommendations: List[str]) -> None:
        """Add recommendations for latency variability."""
        if "latency_variability" in insight_types:
            recommendations.append("Investigate causes of latency spikes and implement caching strategies")
            recommendations.append("Consider load balancing improvements")
    
    def _add_error_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                 recommendations: List[str]) -> None:
        """Add error-related recommendations."""
        if "high_error_rate" in insight_types:
            recommendations.append("Investigate error patterns and implement retry mechanisms")
            recommendations.append("Review error handling and logging for root cause analysis")
    
    def _add_cost_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                recommendations: List[str]) -> None:
        """Add cost-related recommendations."""
        has_cost_issues = ("high_cost_per_event" in insight_types or 
                          "high_daily_cost" in insight_types)
        if has_cost_issues:
            recommendations.append("Conduct cost optimization analysis focusing on resource utilization")
            recommendations.append("Consider implementing cost budgets and alerts")
    
    def _add_scheduling_recommendations(self, insight_types: Dict[str, List[Dict[str, Any]]], 
                                      recommendations: List[str]) -> None:
        """Add scheduling-related recommendations."""
        if "off_hours_usage" in insight_types:
            recommendations.append("Optimize scheduling to reduce off-hours usage costs")
            recommendations.append("Consider reserved capacity for predictable workloads")