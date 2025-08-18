"""Usage Insights Analysis Helper

Specialized usage pattern insights analysis for InsightsGenerator.
Handles usage patterns, cost efficiency, and scheduling optimization.

Business Value: Usage optimization insights for customer cost efficiency.
"""

from typing import Dict, List, Any


class UsageInsightsAnalyzer:
    """Specialized analyzer for usage-related insights."""
    
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
    
    async def analyze_usage_patterns(self, usage_data: Dict[str, Any], 
                                   insights: Dict[str, Any]) -> None:
        """Analyze usage patterns and add insights."""
        summary = usage_data.get("summary")
        if summary and "peak_usage_hour" in summary:
            await self._check_off_hours_usage(summary, insights)
    
    async def _check_off_hours_usage(self, summary: Dict[str, Any], 
                                   insights: Dict[str, Any]) -> None:
        """Check for off-hours usage patterns."""
        peak_hour = int(summary["peak_usage_hour"].split(":")[0])
        if self._is_off_hours(peak_hour):
            self._add_off_hours_insight(summary, insights)
            self._add_scheduling_recommendation(insights)
    
    def _is_off_hours(self, peak_hour: int) -> bool:
        """Check if peak hour is during off hours."""
        return (peak_hour < self.thresholds["off_hours_end"] or 
                peak_hour > self.thresholds["off_hours_start"])
    
    def _add_off_hours_insight(self, summary: Dict[str, Any], 
                             insights: Dict[str, Any]) -> None:
        """Add off-hours usage insight."""
        insights["usage_insights"].append({
            "type": "off_hours_usage", "severity": "low",
            "message": f"Peak usage occurs at {summary['peak_usage_hour']} (off hours)"
        })
    
    def _add_scheduling_recommendation(self, insights: Dict[str, Any]) -> None:
        """Add scheduling optimization recommendation."""
        recommendation = "Consider scheduled batch processing to optimize costs"
        insights["recommendations"].append(recommendation)

    async def generate_cost_insights(self, performance_data: Dict[str, Any], 
                                   usage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost-related insights."""
        insights = []
        return await self._process_cost_insights(performance_data, usage_data, insights)

    async def _process_cost_insights(self, performance_data: Dict[str, Any], 
                                   usage_data: Dict[str, Any], insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all cost insights and return list."""
        self._check_cost_efficiency(performance_data, insights)
        self._check_daily_cost_patterns(usage_data, insights)
        return insights
    
    def _check_cost_efficiency(self, performance_data: Dict[str, Any], 
                             insights: List[Dict[str, Any]]) -> None:
        """Check cost efficiency from performance data."""
        summary = performance_data.get("summary")
        if summary:
            self._analyze_cost_per_event(summary, insights)
    
    def _analyze_cost_per_event(self, summary: Dict[str, Any], 
                              insights: List[Dict[str, Any]]) -> None:
        """Analyze cost per event metrics."""
        total_cost, total_events = summary.get("total_cost", 0), summary.get("total_events", 0)
        if total_events > 0:
            self._check_cost_per_event_threshold(total_cost, total_events, insights)

    def _check_cost_per_event_threshold(self, total_cost: float, total_events: int, 
                                      insights: List[Dict[str, Any]]) -> None:
        """Check if cost per event exceeds threshold."""
        cost_per_event = total_cost / total_events
        if cost_per_event > self.thresholds["cost_per_event"]:
            self._add_cost_per_event_insight(cost_per_event, insights)
    
    def _add_cost_per_event_insight(self, cost_per_event: float, 
                                  insights: List[Dict[str, Any]]) -> None:
        """Add high cost per event insight."""
        insights.append({
            "type": "high_cost_per_event", "severity": "medium", "metric": "cost_efficiency",
            "message": f"Cost per event is ${cost_per_event:.4f}"
        })
    
    def _check_daily_cost_patterns(self, usage_data: Dict[str, Any], 
                                 insights: List[Dict[str, Any]]) -> None:
        """Check usage pattern cost implications."""
        usage_summary = usage_data.get("summary")
        if not usage_summary:
            return
        avg_daily_cost = usage_summary.get("average_daily_cost", 0)
        if avg_daily_cost > self.thresholds["daily_cost"]:
            self._add_daily_cost_insight(avg_daily_cost, insights)
    
    def _add_daily_cost_insight(self, avg_daily_cost: float, 
                              insights: List[Dict[str, Any]]) -> None:
        """Add high daily cost insight."""
        insights.append({
            "type": "high_daily_cost", "severity": "high", "metric": "daily_cost",
            "message": f"Average daily cost is ${avg_daily_cost:.2f}"
        })