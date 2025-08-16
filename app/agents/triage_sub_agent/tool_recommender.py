"""Triage Tool Recommender

This module handles tool recommendations based on category and extracted entities.
"""

from typing import List
from .models import ToolRecommendation, ExtractedEntities


class ToolRecommender:
    """Recommends tools based on category and extracted entities"""
    
    def __init__(self):
        """Initialize the tool recommender"""
        self.tool_mapping = {
            "Workload Analysis": [
                "analyze_workload_events", 
                "get_workload_metrics", 
                "identify_patterns"
            ],
            "Cost Optimization": [
                "calculate_cost_savings", 
                "simulate_cost_optimization", 
                "analyze_cost_trends"
            ],
            "Performance Optimization": [
                "identify_latency_bottlenecks", 
                "optimize_throughput", 
                "analyze_performance"
            ],
            "Model Selection": [
                "compare_models", 
                "get_model_capabilities", 
                "recommend_model"
            ],
            "Supply Catalog Management": [
                "get_supply_catalog", 
                "update_model_config", 
                "add_new_model"
            ],
            "Monitoring & Reporting": [
                "generate_report", 
                "create_dashboard", 
                "get_metrics_summary"
            ]
        }
    
    def recommend_tools(
        self, 
        category: str, 
        entities: ExtractedEntities
    ) -> List[ToolRecommendation]:
        """Recommend tools based on category and extracted entities"""
        if category not in self.tool_mapping:
            return []
        recommendations = self._build_tool_recommendations(category, entities)
        return self._sort_and_limit_recommendations(recommendations)
    
    def _build_tool_recommendations(self, category: str, entities: ExtractedEntities) -> List[ToolRecommendation]:
        """Build recommendations for all tools in category."""
        recommendations = []
        for tool_name in self.tool_mapping[category]:
            relevance = self._calculate_relevance(tool_name, entities)
            recommendations.append(ToolRecommendation(
                tool_name=tool_name,
                relevance_score=min(1.0, relevance)
            ))
        return recommendations
    
    def _sort_and_limit_recommendations(self, recommendations: List[ToolRecommendation]) -> List[ToolRecommendation]:
        """Sort by relevance and return top 5."""
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:5]
    
    def _calculate_relevance(
        self, 
        tool_name: str, 
        entities: ExtractedEntities
    ) -> float:
        """Calculate relevance score for a tool"""
        relevance = 0.8  # Base relevance
        relevance += self._get_model_bonus(tool_name, entities)
        relevance += self._get_metrics_bonus(tool_name, entities)
        return relevance
    
    def _get_model_bonus(self, tool_name: str, entities: ExtractedEntities) -> float:
        """Get relevance bonus for model-related tools."""
        return 0.1 if entities.models_mentioned and "model" in tool_name else 0.0
    
    def _get_metrics_bonus(self, tool_name: str, entities: ExtractedEntities) -> float:
        """Get relevance bonus for metrics-related tools."""
        return 0.1 if entities.metrics_mentioned and self._has_metric_keywords(tool_name) else 0.0
    
    def _has_metric_keywords(self, tool_name: str) -> bool:
        """Check if tool name contains metric-related keywords"""
        metric_keywords = ["metric", "performance", "cost"]
        return any(keyword in tool_name for keyword in metric_keywords)