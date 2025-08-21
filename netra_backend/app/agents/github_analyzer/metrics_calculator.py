"""Metrics Calculator Module.

Calculates analysis metrics for AI operations maps.
Handles metric computation and tool counting.
"""

from typing import Dict, List, Any

from netra_backend.app.logging_config import central_logger as logger


class GitHubAnalyzerMetricsCalculator:
    """Calculates metrics for AI operations analysis."""
    
    def calculate_metrics(self, ai_map: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate analysis metrics."""
        infra = ai_map["ai_infrastructure"]
        code_locations = ai_map["code_locations"]
        return {
            "total_llm_calls": len(infra.get("llm_endpoints", [])),
            "unique_models": len(infra.get("models", {}).get("used_models", [])),
            "agent_count": len(infra.get("agents", [])),
            "tool_count": self._calculate_tool_count(infra),
            "config_files": len(code_locations.get("config_files", [])),
            "ai_files": len(code_locations.get("ai_files", [])),
            "estimated_complexity": infra.get("patterns", {}).get("complexity", "unknown")
        }
    
    def _calculate_tool_count(self, infra: Dict[str, Any]) -> int:
        """Calculate total tool count."""
        tools = len(infra.get("tools", []))
        functions = len(infra.get("functions", []))
        return tools + functions