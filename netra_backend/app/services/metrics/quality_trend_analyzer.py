"""
Quality trend analysis for corpus operations
Handles trend tracking and directional analysis
"""

import statistics
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from netra_backend.app.schemas.Metrics import QualityMetrics


class QualityTrendAnalyzer:
    """Analyzes quality trends over time"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._quality_trends = defaultdict(list)
    
    async def track_quality_trends(self, corpus_id: str, metrics: QualityMetrics):
        """Track quality trends over time"""
        trend_point = self._create_trend_point(metrics)
        self._quality_trends[corpus_id].append(trend_point)
        self._cleanup_old_trends(corpus_id)
    
    def _create_trend_point(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Create trend point from metrics."""
        return {
            "timestamp": datetime.now(UTC),
            "overall": metrics.overall_score,
            "validation": metrics.validation_score,
            "completeness": metrics.completeness_score,
            "consistency": metrics.consistency_score,
            "accuracy": metrics.accuracy_score or 0.0
        }
    
    def _cleanup_old_trends(self, corpus_id: str) -> None:
        """Remove old trend points beyond 24 hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        self._quality_trends[corpus_id] = [
            point for point in self._quality_trends[corpus_id]
            if point["timestamp"] >= cutoff
        ]
    
    def calculate_trend(self, corpus_id: str) -> str:
        """Calculate quality trend direction"""
        trends = self._quality_trends.get(corpus_id, [])
        if len(trends) < 3:
            return "insufficient_data"
        
        recent_scores, early_scores = self._extract_trend_scores(trends)
        if not early_scores:
            return "stable"
        return self._determine_trend_direction(recent_scores, early_scores)
    
    def _extract_trend_scores(self, trends: List[Dict]) -> tuple[List[float], List[float]]:
        """Extract recent and early scores from trends."""
        recent_scores = [point["overall"] for point in trends[-5:]]
        early_scores = [point["overall"] for point in trends[-10:-5]] if len(trends) >= 10 else []
        return recent_scores, early_scores
    
    def _determine_trend_direction(self, recent_scores: List[float], early_scores: List[float]) -> str:
        """Determine trend direction from score averages."""
        recent_avg = statistics.mean(recent_scores)
        early_avg = statistics.mean(early_scores)
        
        if recent_avg > early_avg + 0.05:
            return "improving"
        elif recent_avg < early_avg - 0.05:
            return "declining"
        else:
            return "stable"
    
    def get_trend_points_count(self, corpus_id: str) -> int:
        """Get count of trend points for corpus."""
        return len(self._quality_trends.get(corpus_id, []))
    
    def get_total_trend_points(self) -> int:
        """Get total trend points across all corpora."""
        return sum(len(trends) for trends in self._quality_trends.values())