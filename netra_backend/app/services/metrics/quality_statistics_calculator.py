"""
Quality statistics calculation for corpus operations
Handles score distributions, averages, and statistical analysis
"""

import statistics
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.schemas.metrics import QualityMetrics, TimeSeriesPoint


class QualityStatisticsCalculator:
    """Calculates quality statistics and distributions"""
    
    def get_quality_score_distribution(self, quality_history: deque) -> Dict[str, float]:
        """Get distribution of quality scores"""
        history = list(quality_history)
        if not history:
            return self._get_empty_distribution()
        
        scores = [entry["metrics"].overall_score for entry in history]
        return self._calculate_score_statistics(scores)
    
    def _get_empty_distribution(self) -> Dict[str, float]:
        """Get empty score distribution."""
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
    
    def _calculate_score_statistics(self, scores: List[float]) -> Dict[str, float]:
        """Calculate statistical distribution of scores."""
        return {
            "min": min(scores),
            "max": max(scores),
            "mean": statistics.mean(scores),
            "median": statistics.median(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0.0
        }
    
    def get_validation_summary(self, quality_history: deque, trend_calculator) -> Dict[str, Any]:
        """Get validation metrics summary"""
        history = list(quality_history)
        if not history:
            return self._get_empty_validation_summary()
        
        recent_metrics = [entry["metrics"] for entry in history[-10:]]
        avg_scores = self._calculate_average_scores(recent_metrics)
        trend = trend_calculator.calculate_trend(quality_history[0]["corpus_id"]) if history else "stable"
        return self._build_validation_summary(history, avg_scores, trend)
    
    def _get_empty_validation_summary(self) -> Dict[str, Any]:
        """Get empty validation summary."""
        return {"total_assessments": 0, "avg_scores": {}, "trend": "stable"}
    
    def _calculate_average_scores(self, recent_metrics: List[QualityMetrics]) -> Dict[str, float]:
        """Calculate average scores from recent metrics."""
        return {
            "validation": statistics.mean([m.validation_score for m in recent_metrics]),
            "completeness": statistics.mean([m.completeness_score for m in recent_metrics]),
            "consistency": statistics.mean([m.consistency_score for m in recent_metrics]),
            "accuracy": statistics.mean([m.accuracy_score or 0.0 for m in recent_metrics])
        }
    
    def _build_validation_summary(self, history: List[Dict], avg_scores: Dict[str, float], trend: str) -> Dict[str, Any]:
        """Build validation summary from components."""
        return {
            "total_assessments": len(history),
            "avg_scores": avg_scores,
            "trend": trend,
            "latest_assessment": history[-1]["timestamp"].isoformat() if history else None
        }
    
    def get_quality_time_series(
        self,
        quality_history: deque,
        metric_name: str = "overall",
        time_range_hours: int = 24
    ) -> List[TimeSeriesPoint]:
        """Get time series for quality metrics"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_range_hours)
        points = self._collect_time_series_points(quality_history, cutoff_time, metric_name)
        return sorted(points, key=lambda x: x.timestamp)
    
    def _collect_time_series_points(self, quality_history: deque, cutoff_time: datetime, metric_name: str) -> List[TimeSeriesPoint]:
        """Collect time series points from quality history."""
        points = []
        
        for entry in quality_history:
            if entry["timestamp"] < cutoff_time:
                continue
            
            point = self._create_time_series_point(entry, metric_name)
            if point:
                points.append(point)
        
        return points
    
    def _create_time_series_point(self, entry: Dict, metric_name: str) -> Optional[TimeSeriesPoint]:
        """Create time series point from entry."""
        value = self._extract_quality_value(entry["metrics"], metric_name)
        if value is not None:
            return TimeSeriesPoint(
                timestamp=entry["timestamp"],
                value=value,
                tags={"context": entry["context"], "metric": metric_name}
            )
        return None
    
    def _extract_quality_value(self, metrics: QualityMetrics, metric_name: str) -> Optional[float]:
        """Extract specific quality metric value"""
        mapping = {
            "overall": metrics.overall_score,
            "validation": metrics.validation_score,
            "completeness": metrics.completeness_score,
            "consistency": metrics.consistency_score,
            "accuracy": metrics.accuracy_score
        }
        return mapping.get(metric_name)