"""Factory Status Health Calculator.

Calculates overall factory health scores from collected metrics.
Provides weighted scoring across different metric categories.
"""

from typing import Any, Dict, List

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthScoreCalculator:
    """Calculates overall factory health scores."""
    
    def calculate(self, metrics_cache: Dict[str, Any]) -> float:
        """Calculate overall factory health score."""
        try:
            return self._compute_health_score(metrics_cache)
        except Exception as e:
            logger.warning(f"Health score calculation failed: {e}")
            return 0.0
    
    def _compute_health_score(self, metrics_cache: Dict[str, Any]) -> float:
        """Compute health score from cached metrics."""
        if not metrics_cache:
            return 0.0
        scores = self._collect_all_health_scores(metrics_cache)
        return sum(scores) if scores else 0.0
    
    def _collect_all_health_scores(self, metrics_cache: Dict[str, Any]) -> List[float]:
        """Collect all weighted health scores."""
        scores = []
        scores.extend(self._get_system_health_scores(metrics_cache))
        scores.extend(self._get_quality_health_scores(metrics_cache))
        scores.extend(self._get_performance_health_scores(metrics_cache))
        return scores
    
    def _get_system_health_scores(self, metrics_cache: Dict[str, Any]) -> List[float]:
        """Get system health scores with 25% weight."""
        system = metrics_cache.get("system", {})
        if not system:
            return []
        cpu_score = max(0, 100 - system.get("cpu_usage", 100))
        memory_score = max(0, 100 - system.get("memory_usage", 100))
        return [(cpu_score + memory_score) / 2 * 0.25]
    
    def _get_quality_health_scores(self, metrics_cache: Dict[str, Any]) -> List[float]:
        """Get code quality scores with 50% weight."""
        quality = metrics_cache.get("code_quality", {})
        if not quality:
            return []
        quality_score = self._calculate_quality_score(quality)
        return [quality_score * 0.5]
    
    def _calculate_quality_score(self, quality: Dict[str, float]) -> float:
        """Calculate combined code quality score."""
        syntax = quality.get("syntax_score", 0) * 100
        coverage = quality.get("test_coverage", 0)
        complexity = quality.get("complexity_score", 0) * 100
        return (syntax + coverage + complexity) / 3
    
    def _get_performance_health_scores(self, metrics_cache: Dict[str, Any]) -> List[float]:
        """Get performance scores with 25% weight."""
        performance = metrics_cache.get("performance", {})
        if not performance:
            return []
        throughput = performance.get("throughput_score", 0)
        availability = performance.get("availability", 0) * 100
        perf_score = (throughput + availability) / 2
        return [perf_score * 0.25]