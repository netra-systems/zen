"""Performance Insights Analysis Helper

Specialized performance insights analysis for InsightsGenerator.
Handles performance trends, outliers, error rates, and latency analysis.

Business Value: Performance optimization insights for customer reliability.
"""

from typing import Any, Dict, List


class PerformanceInsightsAnalyzer:
    """Specialized analyzer for performance-related insights."""
    
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
    
    async def analyze_performance_trends(self, performance_data: Dict[str, Any], 
                                       insights: Dict[str, Any]) -> None:
        """Analyze performance trends and add insights."""
        trends = performance_data.get("trends")
        if trends:
            await self._process_performance_trends(trends, insights)
    
    async def _process_performance_trends(self, trends: Dict[str, Any], 
                                        insights: Dict[str, Any]) -> None:
        """Process performance trends for insights."""
        await self._check_latency_trends(trends, insights)
        await self._check_cost_trends(trends, insights)
    
    async def _check_latency_trends(self, trends: Dict[str, Any], 
                                  insights: Dict[str, Any]) -> None:
        """Check latency trends and add insights."""
        if trends.get("latency", {}).get("direction") == "increasing":
            self._add_latency_degradation_insight(insights)
            self._add_performance_recommendation(insights)
    
    def _add_latency_degradation_insight(self, insights: Dict[str, Any]) -> None:
        """Add latency degradation insight."""
        insight = self._create_latency_degradation_insight()
        insights["performance_insights"].append(insight)

    def _create_latency_degradation_insight(self) -> Dict[str, Any]:
        """Create latency degradation insight dictionary."""
        return {
            "type": "performance_degradation", "message": "Latency is increasing over time",
            "severity": "medium", "metric": "latency"
        }
    
    def _add_performance_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add performance optimization recommendation."""
        recommendation = "Consider optimizing query performance or scaling resources"
        insights["recommendations"].append(recommendation)
    
    async def _check_cost_trends(self, trends: Dict[str, Any], 
                               insights: Dict[str, Any]) -> None:
        """Check cost trends and add insights."""
        if trends.get("cost", {}).get("direction") == "increasing":
            self._add_cost_increase_insight(insights)
            self._add_cost_optimization_recommendation(insights)
    
    def _add_cost_increase_insight(self, insights: Dict[str, Any]) -> None:
        """Add cost increase insight."""
        insights["cost_insights"].append({
            "type": "cost_increase", "message": "Costs are trending upward",
            "severity": "high", "metric": "cost"
        })
    
    def _add_cost_optimization_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add cost optimization recommendation."""
        recommendation = "Review resource allocation and consider cost optimization strategies"
        insights["recommendations"].append(recommendation)

    async def generate_performance_insights(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights specifically from performance data."""
        insights = []
        self._check_performance_outliers(performance_data, insights)
        self._check_error_rate_insights(performance_data, insights)
        self._check_latency_variability(performance_data, insights)
        return insights
    
    def _check_performance_outliers(self, performance_data: Dict[str, Any], 
                                  insights: List[Dict[str, Any]]) -> None:
        """Check for performance outliers and add insights."""
        outliers = performance_data.get("outliers", {})
        outlier_count = len(outliers.get("latency_outliers", []))
        if outlier_count > 0:
            self._add_outlier_insight(outlier_count, insights)
    
    def _add_outlier_insight(self, outlier_count: int, insights: List[Dict[str, Any]]) -> None:
        """Add performance outlier insight."""
        insights.append({
            "type": "performance_outliers", "severity": "medium",
            "message": f"Detected {outlier_count} performance outliers",
            "details": f"{outlier_count} data points with unusual latency values"
        })
    
    def _check_error_rate_insights(self, performance_data: Dict[str, Any], 
                                 insights: List[Dict[str, Any]]) -> None:
        """Check error rates and add insights."""
        error_stats = performance_data.get("error_rate")
        if error_stats and error_stats.get("mean", 0) > self.thresholds["error_rate"]:
            self._add_error_rate_insight(error_stats, insights)
    
    def _add_error_rate_insight(self, error_stats: Dict[str, Any], 
                              insights: List[Dict[str, Any]]) -> None:
        """Add high error rate insight."""
        insights.append({
            "type": "high_error_rate", "severity": "high", "metric": "error_rate",
            "message": f"Average error rate is {error_stats['mean']:.2%}"
        })
    
    def _check_latency_variability(self, performance_data: Dict[str, Any], 
                                 insights: List[Dict[str, Any]]) -> None:
        """Check latency variability and add insights."""
        latency_stats = performance_data.get("latency")
        if latency_stats and self._has_high_latency_variability(latency_stats):
            self._add_latency_variability_insight(latency_stats, insights)
    
    def _has_high_latency_variability(self, latency_stats: Dict[str, Any]) -> bool:
        """Check if latency has high variability."""
        p95, mean = latency_stats.get("p95", 0), latency_stats.get("mean", 0)
        return p95 > mean * 2
    
    def _add_latency_variability_insight(self, latency_stats: Dict[str, Any], 
                                       insights: List[Dict[str, Any]]) -> None:
        """Add latency variability insight."""
        p95, mean = latency_stats.get('p95', 0), latency_stats.get('mean', 0)
        insight = self._create_latency_variability_insight(p95, mean)
        insights.append(insight)

    def _create_latency_variability_insight(self, p95: float, mean: float) -> Dict[str, Any]:
        """Create latency variability insight dictionary."""
        return {
            "type": "latency_variability", "severity": "medium",
            "message": "High latency variability detected (P95 >> average)",
            "details": f"P95: {p95:.2f}ms, Mean: {mean:.2f}ms"
        }