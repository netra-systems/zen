"""
Quality metrics collection for corpus operations
Handles quality scores, validation metrics, and data integrity monitoring
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, deque
import statistics
import json

from app.logging_config import central_logger
from app.schemas.Metrics import (
    QualityMetrics, CorpusMetric, MetricType, TimeSeriesPoint
)

logger = central_logger.get_logger(__name__)


class QualityMetricsCollector:
    """Collects and analyzes quality metrics for corpus operations"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._quality_history = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self._validation_results = defaultdict(list)
        self._issue_tracker = defaultdict(lambda: defaultdict(int))
        self._quality_trends = defaultdict(list)
    
    async def record_quality_assessment(
        self,
        corpus_id: str,
        quality_metrics: QualityMetrics,
        operation_context: Optional[str] = None
    ):
        """Record quality assessment results"""
        entry = {
            "corpus_id": corpus_id,
            "timestamp": datetime.now(UTC),
            "metrics": quality_metrics,
            "context": operation_context or "general"
        }
        
        self._quality_history[corpus_id].append(entry)
        await self._track_quality_trends(corpus_id, quality_metrics)
        await self._analyze_issues(corpus_id, quality_metrics)
        
        logger.debug(f"Recorded quality assessment for corpus {corpus_id}: score={quality_metrics.overall_score:.3f}")
    
    async def _track_quality_trends(self, corpus_id: str, metrics: QualityMetrics):
        """Track quality trends over time"""
        trend_point = {
            "timestamp": datetime.now(UTC),
            "overall": metrics.overall_score,
            "validation": metrics.validation_score,
            "completeness": metrics.completeness_score,
            "consistency": metrics.consistency_score,
            "accuracy": metrics.accuracy_score or 0.0
        }
        
        self._quality_trends[corpus_id].append(trend_point)
        
        # Keep only recent trends
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        self._quality_trends[corpus_id] = [
            point for point in self._quality_trends[corpus_id]
            if point["timestamp"] >= cutoff
        ]
    
    async def _analyze_issues(self, corpus_id: str, metrics: QualityMetrics):
        """Analyze and track quality issues"""
        for issue in metrics.issues_detected:
            self._issue_tracker[corpus_id][issue] += 1
    
    def get_quality_score_distribution(self, corpus_id: str) -> Dict[str, float]:
        """Get distribution of quality scores"""
        history = list(self._quality_history[corpus_id])
        if not history:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
        
        scores = [entry["metrics"].overall_score for entry in history]
        
        return {
            "min": min(scores),
            "max": max(scores),
            "mean": statistics.mean(scores),
            "median": statistics.median(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0.0
        }
    
    def get_validation_summary(self, corpus_id: str) -> Dict[str, Any]:
        """Get validation metrics summary"""
        history = list(self._quality_history[corpus_id])
        if not history:
            return {"total_assessments": 0, "avg_scores": {}, "trend": "stable"}
        
        recent_metrics = [entry["metrics"] for entry in history[-10:]]
        
        avg_scores = {
            "validation": statistics.mean([m.validation_score for m in recent_metrics]),
            "completeness": statistics.mean([m.completeness_score for m in recent_metrics]),
            "consistency": statistics.mean([m.consistency_score for m in recent_metrics]),
            "accuracy": statistics.mean([m.accuracy_score or 0.0 for m in recent_metrics])
        }
        
        trend = self._calculate_trend(corpus_id)
        
        return {
            "total_assessments": len(history),
            "avg_scores": avg_scores,
            "trend": trend,
            "latest_assessment": history[-1]["timestamp"].isoformat() if history else None
        }
    
    def _calculate_trend(self, corpus_id: str) -> str:
        """Calculate quality trend direction"""
        trends = self._quality_trends.get(corpus_id, [])
        if len(trends) < 3:
            return "insufficient_data"
        
        recent_scores = [point["overall"] for point in trends[-5:]]
        early_scores = [point["overall"] for point in trends[-10:-5]] if len(trends) >= 10 else []
        
        if not early_scores:
            return "stable"
        
        recent_avg = statistics.mean(recent_scores)
        early_avg = statistics.mean(early_scores)
        
        if recent_avg > early_avg + 0.05:
            return "improving"
        elif recent_avg < early_avg - 0.05:
            return "declining"
        else:
            return "stable"
    
    def get_issue_analysis(self, corpus_id: str) -> Dict[str, Any]:
        """Get analysis of detected issues"""
        issues = self._issue_tracker.get(corpus_id, {})
        total_issues = sum(issues.values())
        
        if total_issues == 0:
            return {"total_issues": 0, "top_issues": [], "issue_categories": {}}
        
        sorted_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_issues": total_issues,
            "top_issues": sorted_issues[:5],
            "issue_categories": self._categorize_issues(issues),
            "unique_issue_types": len(issues)
        }
    
    def _categorize_issues(self, issues: Dict[str, int]) -> Dict[str, int]:
        """Categorize issues by type"""
        categories = {
            "data_quality": 0,
            "validation": 0,
            "completeness": 0,
            "consistency": 0,
            "other": 0
        }
        
        for issue_type, count in issues.items():
            category = self._classify_issue(issue_type)
            categories[category] += count
        
        return categories
    
    def _classify_issue(self, issue_type: str) -> str:
        """Classify issue into category"""
        issue_lower = issue_type.lower()
        
        if any(keyword in issue_lower for keyword in ["missing", "empty", "null", "incomplete"]):
            return "completeness"
        elif any(keyword in issue_lower for keyword in ["validation", "format", "type", "schema"]):
            return "validation"
        elif any(keyword in issue_lower for keyword in ["duplicate", "conflict", "mismatch"]):
            return "consistency"
        elif any(keyword in issue_lower for keyword in ["quality", "accuracy", "integrity"]):
            return "data_quality"
        else:
            return "other"
    
    def get_quality_time_series(
        self,
        corpus_id: str,
        metric_name: str = "overall",
        time_range_hours: int = 24
    ) -> List[TimeSeriesPoint]:
        """Get time series for quality metrics"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_range_hours)
        points = []
        
        for entry in self._quality_history[corpus_id]:
            if entry["timestamp"] < cutoff_time:
                continue
            
            value = self._extract_quality_value(entry["metrics"], metric_name)
            if value is not None:
                points.append(TimeSeriesPoint(
                    timestamp=entry["timestamp"],
                    value=value,
                    tags={"context": entry["context"], "metric": metric_name}
                ))
        
        return sorted(points, key=lambda x: x.timestamp)
    
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
    
    async def generate_quality_report(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        score_dist = self.get_quality_score_distribution(corpus_id)
        validation_summary = self.get_validation_summary(corpus_id)
        issue_analysis = self.get_issue_analysis(corpus_id)
        
        recommendations = await self._generate_recommendations(corpus_id, issue_analysis)
        
        return {
            "corpus_id": corpus_id,
            "report_timestamp": datetime.now(UTC).isoformat(),
            "quality_distribution": score_dist,
            "validation_summary": validation_summary,
            "issue_analysis": issue_analysis,
            "recommendations": recommendations,
            "overall_health": self._assess_overall_health(score_dist, issue_analysis)
        }
    
    async def _generate_recommendations(self, corpus_id: str, issue_analysis: Dict) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if issue_analysis["total_issues"] == 0:
            recommendations.append("Quality metrics look good - maintain current practices")
            return recommendations
        
        top_issues = issue_analysis.get("top_issues", [])
        categories = issue_analysis.get("issue_categories", {})
        
        if categories.get("completeness", 0) > 0:
            recommendations.append("Address data completeness issues - review missing fields")
        
        if categories.get("validation", 0) > 0:
            recommendations.append("Strengthen validation rules - check data formats and schemas")
        
        if categories.get("consistency", 0) > 0:
            recommendations.append("Improve data consistency - resolve duplicates and conflicts")
        
        if len(top_issues) > 0:
            most_common_issue = top_issues[0][0]
            recommendations.append(f"Priority: Address '{most_common_issue}' issue type")
        
        return recommendations
    
    def _assess_overall_health(
        self,
        score_dist: Dict[str, float],
        issue_analysis: Dict
    ) -> str:
        """Assess overall corpus health"""
        avg_score = score_dist.get("mean", 0.0)
        total_issues = issue_analysis.get("total_issues", 0)
        
        if avg_score >= 0.8 and total_issues < 5:
            return "excellent"
        elif avg_score >= 0.6 and total_issues < 15:
            return "good"
        elif avg_score >= 0.4 and total_issues < 30:
            return "fair"
        else:
            return "poor"
    
    def get_collector_status(self) -> Dict[str, Any]:
        """Get quality collector status"""
        total_assessments = sum(len(history) for history in self._quality_history.values())
        
        return {
            "tracked_corpora": len(self._quality_history),
            "total_assessments": total_assessments,
            "total_issues_tracked": sum(len(issues) for issues in self._issue_tracker.values()),
            "trend_points": sum(len(trends) for trends in self._quality_trends.values())
        }