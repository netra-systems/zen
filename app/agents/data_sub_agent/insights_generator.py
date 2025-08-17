"""Insights generation module for DataSubAgent - generates actionable insights from analysis data."""

from typing import Dict, List, Any

from app.logging_config import central_logger as logger


class InsightsGenerator:
    """Generates actionable insights from analysis data"""
    
    def __init__(self):
        """Initialize the InsightsGenerator with configuration."""
        self.logger = logger.get_logger(__name__)
        self.thresholds = {
            "error_rate": 0.05,  # 5% error rate threshold
            "cost_per_event": 0.01,  # 1 cent per event threshold
            "daily_cost": 100.0,  # $100/day threshold
            "off_hours_start": 22,  # 10 PM
            "off_hours_end": 6  # 6 AM
        }
    
    async def generate_insights(
        self, 
        performance_data: Dict[str, Any], 
        usage_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate actionable insights from analysis data"""
        insights = self._initialize_insights_structure()
        return await self._process_all_insights(performance_data, usage_data, insights)
    
    async def _process_all_insights(
        self, 
        performance_data: Dict[str, Any], 
        usage_data: Dict[str, Any], 
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process all insight types and return final insights"""
        await self._analyze_performance_trends(performance_data, insights)
        await self._analyze_usage_patterns(usage_data, insights)
        return insights
    
    def _initialize_insights_structure(self) -> Dict[str, Any]:
        """Initialize insights structure with empty collections"""
        return {
            "performance_insights": [],
            "usage_insights": [],
            "cost_insights": [],
            "recommendations": []
        }
    
    async def _analyze_performance_trends(
        self, performance_data: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Analyze performance trends and add insights"""
        trends = performance_data.get("trends")
        if not trends:
            return
        await self._process_performance_trends(trends, insights)
    
    async def _process_performance_trends(
        self, trends: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Process performance trends for insights"""
        await self._check_latency_trends(trends, insights)
        await self._check_cost_trends(trends, insights)
    
    async def _check_latency_trends(
        self, trends: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Check latency trends and add insights"""
        if trends.get("latency", {}).get("direction") != "increasing":
            return
        self._add_latency_degradation_insight(insights)
        self._add_performance_recommendation(insights)
    
    def _add_latency_degradation_insight(self, insights: Dict[str, Any]) -> None:
        """Add latency degradation insight"""
        insights["performance_insights"].append({
            "type": "performance_degradation",
            "message": "Latency is increasing over time",
            "severity": "medium",
            "metric": "latency"
        })
    
    def _add_performance_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add performance optimization recommendation"""
        recommendation = "Consider optimizing query performance or scaling resources"
        insights["recommendations"].append(recommendation)
    
    async def _check_cost_trends(
        self, trends: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Check cost trends and add insights"""
        if trends.get("cost", {}).get("direction") != "increasing":
            return
        self._add_cost_increase_insight(insights)
        self._add_cost_optimization_recommendation(insights)
    
    def _add_cost_increase_insight(self, insights: Dict[str, Any]) -> None:
        """Add cost increase insight"""
        insights["cost_insights"].append({
            "type": "cost_increase",
            "message": "Costs are trending upward",
            "severity": "high",
            "metric": "cost"
        })
    
    def _add_cost_optimization_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add cost optimization recommendation"""
        recommendation = "Review resource allocation and consider cost optimization strategies"
        insights["recommendations"].append(recommendation)
    
    async def _analyze_usage_patterns(
        self, usage_data: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Analyze usage patterns and add insights"""
        summary = usage_data.get("summary")
        if not summary or "peak_usage_hour" not in summary:
            return
        await self._check_off_hours_usage(summary, insights)
    
    async def _check_off_hours_usage(
        self, summary: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Check for off-hours usage patterns"""
        peak_hour = int(summary["peak_usage_hour"].split(":")[0])
        if not self._is_off_hours(peak_hour):
            return
        self._add_off_hours_insight(summary, insights)
        self._add_scheduling_recommendation(insights)
    
    def _is_off_hours(self, peak_hour: int) -> bool:
        """Check if peak hour is during off hours"""
        return (peak_hour < self.thresholds["off_hours_end"] or 
                peak_hour > self.thresholds["off_hours_start"])
    
    def _add_off_hours_insight(
        self, summary: Dict[str, Any], insights: Dict[str, Any]
    ) -> None:
        """Add off-hours usage insight"""
        insights["usage_insights"].append({
            "type": "off_hours_usage",
            "message": f"Peak usage occurs at {summary['peak_usage_hour']} (off hours)",
            "severity": "low"
        })
    
    def _add_scheduling_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add scheduling optimization recommendation"""
        recommendation = "Consider scheduled batch processing to optimize costs"
        insights["recommendations"].append(recommendation)
    
    async def generate_performance_insights(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights specifically from performance data"""
        insights = []
        self._check_performance_outliers(performance_data, insights)
        self._check_error_rate_insights(performance_data, insights)
        self._check_latency_variability(performance_data, insights)
        return insights
    
    def _check_performance_outliers(
        self, performance_data: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Check for performance outliers and add insights"""
        outliers = performance_data.get("outliers", {})
        outlier_count = len(outliers.get("latency_outliers", []))
        if outlier_count > 0:
            self._add_outlier_insight(outlier_count, insights)
    
    def _add_outlier_insight(self, outlier_count: int, insights: List[Dict[str, Any]]) -> None:
        """Add performance outlier insight"""
        insights.append({
            "type": "performance_outliers",
            "message": f"Detected {outlier_count} performance outliers",
            "severity": "medium",
            "details": f"{outlier_count} data points with unusual latency values"
        })
    
    def _check_error_rate_insights(
        self, performance_data: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Check error rates and add insights"""
        error_stats = performance_data.get("error_rate")
        if not error_stats:
            return
        if error_stats.get("mean", 0) > self.thresholds["error_rate"]:
            self._add_error_rate_insight(error_stats, insights)
    
    def _add_error_rate_insight(
        self, error_stats: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Add high error rate insight"""
        insights.append({
            "type": "high_error_rate",
            "message": f"Average error rate is {error_stats['mean']:.2%}",
            "severity": "high",
            "metric": "error_rate"
        })
    
    def _check_latency_variability(
        self, performance_data: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Check latency variability and add insights"""
        latency_stats = performance_data.get("latency")
        if not latency_stats:
            return
        if self._has_high_latency_variability(latency_stats):
            self._add_latency_variability_insight(latency_stats, insights)
    
    def _has_high_latency_variability(self, latency_stats: Dict[str, Any]) -> bool:
        """Check if latency has high variability"""
        p95 = latency_stats.get("p95", 0)
        mean = latency_stats.get("mean", 0)
        return p95 > mean * 2
    
    def _add_latency_variability_insight(
        self, latency_stats: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Add latency variability insight"""
        p95 = latency_stats.get('p95', 0)
        mean = latency_stats.get('mean', 0)
        insights.append({
            "type": "latency_variability",
            "message": "High latency variability detected (P95 >> average)",
            "severity": "medium",
            "details": f"P95: {p95:.2f}ms, Mean: {mean:.2f}ms"
        })
    
    async def generate_cost_insights(self, performance_data: Dict[str, Any], usage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost-related insights"""
        insights = []
        self._check_cost_efficiency(performance_data, insights)
        self._check_daily_cost_patterns(usage_data, insights)
        return insights
    
    def _check_cost_efficiency(
        self, performance_data: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Check cost efficiency from performance data"""
        summary = performance_data.get("summary")
        if not summary:
            return
        self._analyze_cost_per_event(summary, insights)
    
    def _analyze_cost_per_event(
        self, summary: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Analyze cost per event metrics"""
        total_cost = summary.get("total_cost", 0)
        total_events = summary.get("total_events", 0)
        if total_events <= 0:
            return
        cost_per_event = total_cost / total_events
        if cost_per_event > self.thresholds["cost_per_event"]:
            self._add_cost_per_event_insight(cost_per_event, insights)
    
    def _add_cost_per_event_insight(
        self, cost_per_event: float, insights: List[Dict[str, Any]]
    ) -> None:
        """Add high cost per event insight"""
        insights.append({
            "type": "high_cost_per_event",
            "message": f"Cost per event is ${cost_per_event:.4f}",
            "severity": "medium",
            "metric": "cost_efficiency"
        })
    
    def _check_daily_cost_patterns(
        self, usage_data: Dict[str, Any], insights: List[Dict[str, Any]]
    ) -> None:
        """Check usage pattern cost implications"""
        usage_summary = usage_data.get("summary")
        if not usage_summary:
            return
        avg_daily_cost = usage_summary.get("average_daily_cost", 0)
        if avg_daily_cost > self.thresholds["daily_cost"]:
            self._add_daily_cost_insight(avg_daily_cost, insights)
    
    def _add_daily_cost_insight(
        self, avg_daily_cost: float, insights: List[Dict[str, Any]]
    ) -> None:
        """Add high daily cost insight"""
        insights.append({
            "type": "high_daily_cost",
            "message": f"Average daily cost is ${avg_daily_cost:.2f}",
            "severity": "high",
            "metric": "daily_cost"
        })
    
    async def generate_recommendations(self, all_insights: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations based on insights"""
        insight_types = self._group_insights_by_type(all_insights)
        recommendations = []
        self._add_all_recommendation_types(insight_types, recommendations)
        return recommendations
    
    def _add_all_recommendation_types(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add all types of recommendations to the list"""
        self._add_performance_recommendations(insight_types, recommendations)
        self._add_error_recommendations(insight_types, recommendations)
        self._add_cost_recommendations(insight_types, recommendations)
        self._add_scheduling_recommendations(insight_types, recommendations)
    
    def _group_insights_by_type(self, all_insights: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group insights by type for pattern analysis"""
        insight_types = {}
        for insight in all_insights:
            self._add_insight_to_group(insight, insight_types)
        return insight_types
    
    def _add_insight_to_group(
        self, insight: Dict[str, Any], insight_types: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Add a single insight to its type group"""
        insight_type = insight.get("type", "unknown")
        if insight_type not in insight_types:
            insight_types[insight_type] = []
        insight_types[insight_type].append(insight)
    
    def _add_performance_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add performance-related recommendations"""
        self._add_degradation_recommendations(insight_types, recommendations)
        self._add_latency_recommendations(insight_types, recommendations)
    
    def _add_degradation_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add recommendations for performance degradation"""
        if "performance_degradation" not in insight_types:
            return
        recommendations.append("Implement performance monitoring alerts to catch degradation early")
        recommendations.append("Consider horizontal scaling or resource optimization")
    
    def _add_latency_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add recommendations for latency variability"""
        if "latency_variability" not in insight_types:
            return
        recommendations.append("Investigate causes of latency spikes and implement caching strategies")
        recommendations.append("Consider load balancing improvements")
    
    def _add_error_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add error-related recommendations"""
        if "high_error_rate" in insight_types:
            recommendations.append("Investigate error patterns and implement retry mechanisms")
            recommendations.append("Review error handling and logging for root cause analysis")
    
    def _add_cost_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add cost-related recommendations"""
        has_cost_issues = ("high_cost_per_event" in insight_types or 
                          "high_daily_cost" in insight_types)
        if has_cost_issues:
            recommendations.append("Conduct cost optimization analysis focusing on resource utilization")
            recommendations.append("Consider implementing cost budgets and alerts")
    
    def _add_scheduling_recommendations(
        self, insight_types: Dict[str, List[Dict[str, Any]]], recommendations: List[str]
    ) -> None:
        """Add scheduling-related recommendations"""
        if "off_hours_usage" in insight_types:
            recommendations.append("Optimize scheduling to reduce off-hours usage costs")
            recommendations.append("Consider reserved capacity for predictable workloads")