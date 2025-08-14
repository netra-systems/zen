"""Insights generation module for DataSubAgent - generates actionable insights from analysis data."""

from typing import Dict, List, Any

from app.logging_config import central_logger as logger


class InsightsGenerator:
    """Generates actionable insights from analysis data"""
    
    def __init__(self):
        pass
    
    async def generate_insights(
        self, 
        performance_data: Dict[str, Any], 
        usage_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate actionable insights from analysis data"""
        
        insights = {
            "performance_insights": [],
            "usage_insights": [],
            "cost_insights": [],
            "recommendations": []
        }
        
        # Analyze performance trends
        if "trends" in performance_data:
            trends = performance_data["trends"]
            
            if trends.get("latency", {}).get("direction") == "increasing":
                insights["performance_insights"].append({
                    "type": "performance_degradation",
                    "message": "Latency is increasing over time",
                    "severity": "medium",
                    "metric": "latency"
                })
                insights["recommendations"].append("Consider optimizing query performance or scaling resources")
            
            if trends.get("cost", {}).get("direction") == "increasing":
                insights["cost_insights"].append({
                    "type": "cost_increase",
                    "message": "Costs are trending upward",
                    "severity": "high",
                    "metric": "cost"
                })
                insights["recommendations"].append("Review resource allocation and consider cost optimization strategies")
        
        # Analyze usage patterns
        if usage_data.get("summary"):
            summary = usage_data["summary"]
            
            # Check for unusual usage patterns
            if "peak_usage_hour" in summary:
                peak_hour = int(summary["peak_usage_hour"].split(":")[0])
                if peak_hour < 6 or peak_hour > 22:  # Off hours
                    insights["usage_insights"].append({
                        "type": "off_hours_usage",
                        "message": f"Peak usage occurs at {summary['peak_usage_hour']} (off hours)",
                        "severity": "low"
                    })
                    insights["recommendations"].append("Consider scheduled batch processing to optimize costs")
        
        return insights
    
    async def generate_performance_insights(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights specifically from performance data"""
        
        insights = []
        
        # Check for anomalies in performance metrics
        if "outliers" in performance_data:
            outlier_count = len(performance_data["outliers"].get("latency_outliers", []))
            if outlier_count > 0:
                insights.append({
                    "type": "performance_outliers",
                    "message": f"Detected {outlier_count} performance outliers",
                    "severity": "medium",
                    "details": f"{outlier_count} data points with unusual latency values"
                })
        
        # Check error rates
        if "error_rate" in performance_data:
            error_stats = performance_data["error_rate"]
            if error_stats.get("mean", 0) > 0.05:  # 5% error rate threshold
                insights.append({
                    "type": "high_error_rate",
                    "message": f"Average error rate is {error_stats['mean']:.2%}",
                    "severity": "high",
                    "metric": "error_rate"
                })
        
        # Check latency distribution
        if "latency" in performance_data:
            latency_stats = performance_data["latency"]
            if latency_stats.get("p95", 0) > latency_stats.get("mean", 0) * 2:
                insights.append({
                    "type": "latency_variability",
                    "message": "High latency variability detected (P95 >> average)",
                    "severity": "medium",
                    "details": f"P95: {latency_stats.get('p95', 0):.2f}ms, Mean: {latency_stats.get('mean', 0):.2f}ms"
                })
        
        return insights
    
    async def generate_cost_insights(self, performance_data: Dict[str, Any], usage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost-related insights"""
        
        insights = []
        
        # Check cost efficiency from performance data
        if "summary" in performance_data:
            total_cost = performance_data["summary"].get("total_cost", 0)
            total_events = performance_data["summary"].get("total_events", 0)
            
            if total_events > 0:
                cost_per_event = total_cost / total_events
                if cost_per_event > 0.01:  # 1 cent per event threshold
                    insights.append({
                        "type": "high_cost_per_event",
                        "message": f"Cost per event is ${cost_per_event:.4f}",
                        "severity": "medium",
                        "metric": "cost_efficiency"
                    })
        
        # Check usage pattern cost implications
        if usage_data.get("summary"):
            usage_summary = usage_data["summary"]
            avg_daily_cost = usage_summary.get("average_daily_cost", 0)
            
            if avg_daily_cost > 100:  # $100/day threshold
                insights.append({
                    "type": "high_daily_cost",
                    "message": f"Average daily cost is ${avg_daily_cost:.2f}",
                    "severity": "high",
                    "metric": "daily_cost"
                })
        
        return insights
    
    async def generate_recommendations(self, all_insights: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations based on insights"""
        
        recommendations = []
        
        # Group insights by type
        insight_types = {}
        for insight in all_insights:
            insight_type = insight.get("type", "unknown")
            if insight_type not in insight_types:
                insight_types[insight_type] = []
            insight_types[insight_type].append(insight)
        
        # Generate recommendations based on insight patterns
        if "performance_degradation" in insight_types:
            recommendations.append("Implement performance monitoring alerts to catch degradation early")
            recommendations.append("Consider horizontal scaling or resource optimization")
        
        if "high_error_rate" in insight_types:
            recommendations.append("Investigate error patterns and implement retry mechanisms")
            recommendations.append("Review error handling and logging for root cause analysis")
        
        if "high_cost_per_event" in insight_types or "high_daily_cost" in insight_types:
            recommendations.append("Conduct cost optimization analysis focusing on resource utilization")
            recommendations.append("Consider implementing cost budgets and alerts")
        
        if "off_hours_usage" in insight_types:
            recommendations.append("Optimize scheduling to reduce off-hours usage costs")
            recommendations.append("Consider reserved capacity for predictable workloads")
        
        if "latency_variability" in insight_types:
            recommendations.append("Investigate causes of latency spikes and implement caching strategies")
            recommendations.append("Consider load balancing improvements")
        
        return recommendations