# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Tool recommendations (25-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 7
# Review: Pending | Score: 95
# ================================
"""Tool recommendation utilities - compliant with 25-line limit."""

from typing import List, Dict
from netra_backend.app.agents.triage_sub_agent.models import ToolRecommendation, ExtractedEntities


def get_tool_mapping() -> Dict[str, List[str]]:
    """Get mapping of categories to tools."""
    return {
        "Workload Analysis": ["analyze_workload_events", "get_workload_metrics", "identify_patterns"],
        "Cost Optimization": ["calculate_cost_savings", "simulate_cost_optimization", "analyze_cost_trends"],
        "Performance Optimization": ["identify_latency_bottlenecks", "optimize_throughput", "analyze_performance"],
        "Model Selection": ["compare_models", "get_model_capabilities", "recommend_model"],
        "Supply Catalog Management": ["get_supply_catalog", "update_model_config", "add_new_model"],
        "Monitoring & Reporting": ["generate_report", "create_dashboard", "get_metrics_summary"],
        "Quality Optimization": ["analyze_quality_metrics", "optimize_quality_gates", "quality_analysis"]
    }


def calculate_relevance(tool_name: str, entities: ExtractedEntities) -> float:
    """Calculate tool relevance based on entities."""
    relevance = 0.8  # Base relevance
    if entities.models_mentioned and "model" in tool_name:
        relevance += 0.1
    if entities.metrics_mentioned:
        if any(m in tool_name for m in ["metric", "performance", "cost"]):
            relevance += 0.1
    return min(1.0, relevance)


def create_recommendation(tool_name: str, relevance: float) -> ToolRecommendation:
    """Create a tool recommendation."""
    return ToolRecommendation(
        tool_name=tool_name,
        relevance_score=relevance,
        parameters={}
    )


def recommend_tools(category: str, entities: ExtractedEntities) -> List[ToolRecommendation]:
    """Recommend tools based on category and entities."""
    tool_mapping = get_tool_mapping()
    if category not in tool_mapping:
        return []
    recommendations = _build_recommendations(tool_mapping[category], entities)
    return _sort_and_limit_recommendations(recommendations)


def _build_recommendations(tool_names: List[str], entities: ExtractedEntities) -> List[ToolRecommendation]:
    """Build recommendations for tool names."""
    recommendations = []
    for tool_name in tool_names:
        relevance = calculate_relevance(tool_name, entities)
        recommendations.append(create_recommendation(tool_name, relevance))
    return recommendations


def _sort_and_limit_recommendations(recommendations: List[ToolRecommendation]) -> List[ToolRecommendation]:
    """Sort by relevance and limit to top 5."""
    recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
    return recommendations[:5]