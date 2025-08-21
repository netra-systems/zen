"""Recommendation Generator Module.

Generates recommendations based on AI operations analysis.
Handles complexity, model, security, and tool recommendations.
"""

from typing import Dict, List, Any

from netra_backend.app.logging_config import central_logger as logger


class RecommendationGenerator:
    """Generates recommendations based on AI analysis results."""
    
    def generate_recommendations(self, ai_map: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        metrics = ai_map.get("metrics", {})
        security = ai_map.get("security", {})
        
        self._add_complexity_recommendations(recommendations, metrics)
        self._add_model_recommendations(recommendations, metrics)
        self._add_security_recommendations(recommendations, security)
        self._add_tool_recommendations(recommendations, metrics)
        return recommendations
    
    def _add_complexity_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add complexity-based recommendations."""
        if metrics.get("estimated_complexity") == "high":
            recommendations.append(
                "Consider modularizing AI operations for better maintainability"
            )
    
    def _add_model_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add model diversity recommendations."""
        if metrics.get("unique_models", 0) > 3:
            recommendations.append(
                "Standardize on fewer models to reduce complexity"
            )
    
    def _add_security_recommendations(
        self, 
        recommendations: List[str], 
        security: Dict[str, Any]
    ) -> None:
        """Add security recommendations."""
        if security.get("warnings"):
            recommendations.append(
                "Review and secure exposed API credentials"
            )
    
    def _add_tool_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add tool-related recommendations."""
        if metrics.get("tool_count", 0) > 10:
            recommendations.append(
                "Consider consolidating tools to reduce overhead"
            )