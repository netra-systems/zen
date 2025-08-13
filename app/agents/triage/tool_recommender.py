# Triage Tool Recommender Module - Tool recommendation logic
from typing import List
from app.agents.triage.models import ToolRecommendation, ExtractedEntities

class ToolRecommender:
    """Recommends tools based on category and entities."""
    
    TOOL_MAPPING = {
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
    
    @staticmethod
    def recommend(category: str, entities: ExtractedEntities) -> List[ToolRecommendation]:
        """Recommend tools based on category and extracted entities."""
        recommendations = []
        
        if category in ToolRecommender.TOOL_MAPPING:
            tools = ToolRecommender.TOOL_MAPPING[category]
            for tool_name in tools:
                relevance = ToolRecommender._calculate_relevance(
                    tool_name, entities
                )
                recommendations.append(ToolRecommendation(
                    tool_name=tool_name,
                    relevance_score=relevance
                ))
        
        # Sort by relevance and return top 5
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:5]
    
    @staticmethod
    def _calculate_relevance(tool_name: str, entities: ExtractedEntities) -> float:
        """Calculate tool relevance based on entities."""
        relevance = 0.8  # Base relevance
        
        # Boost relevance based on entity matches
        if entities.models_mentioned and "model" in tool_name:
            relevance += 0.1
        
        metrics_in_tool = ["metric", "performance", "cost"]
        if entities.metrics_mentioned:
            if any(m in tool_name for m in metrics_in_tool):
                relevance += 0.1
        
        return min(1.0, relevance)