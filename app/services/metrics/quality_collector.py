"""
Quality metrics collection for corpus operations
Handles quality scores, validation metrics, and data integrity monitoring
"""

import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from app.logging_config import central_logger
from app.schemas.Metrics import (
    QualityMetrics, CorpusMetric, MetricType, TimeSeriesPoint
)
from .quality_trend_analyzer import QualityTrendAnalyzer
from .quality_statistics_calculator import QualityStatisticsCalculator
from .quality_issue_analyzer import QualityIssueAnalyzer
from .quality_report_generator import QualityReportGenerator

logger = central_logger.get_logger(__name__)


class QualityMetricsCollector:
    """Collects and analyzes quality metrics for corpus operations"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._quality_history = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self._validation_results = defaultdict(list)
        
        # Initialize specialized analyzers
        self._trend_analyzer = QualityTrendAnalyzer(max_buffer_size)
        self._statistics_calculator = QualityStatisticsCalculator()
        self._issue_analyzer = QualityIssueAnalyzer()
        self._report_generator = QualityReportGenerator()
    
    async def record_quality_assessment(
        self,
        corpus_id: str,
        quality_metrics: QualityMetrics,
        operation_context: Optional[str] = None
    ):
        """Record quality assessment results"""
        entry = self._create_assessment_entry(corpus_id, quality_metrics, operation_context)
        self._quality_history[corpus_id].append(entry)
        await self._process_quality_metrics(corpus_id, quality_metrics)
        logger.debug(f"Recorded quality assessment for corpus {corpus_id}: score={quality_metrics.overall_score:.3f}")
    
    def _create_assessment_entry(self, corpus_id: str, quality_metrics: QualityMetrics, operation_context: Optional[str]) -> Dict[str, Any]:
        """Create quality assessment entry."""
        return {
            "corpus_id": corpus_id,
            "timestamp": datetime.now(UTC),
            "metrics": quality_metrics,
            "context": operation_context or "general"
        }
    
    async def _process_quality_metrics(self, corpus_id: str, quality_metrics: QualityMetrics) -> None:
        """Process quality metrics for tracking and analysis."""
        await self._trend_analyzer.track_quality_trends(corpus_id, quality_metrics)
        await self._issue_analyzer.analyze_issues(corpus_id, quality_metrics)
    
    def get_quality_score_distribution(self, corpus_id: str) -> Dict[str, float]:
        """Get distribution of quality scores"""
        return self._statistics_calculator.get_quality_score_distribution(
            self._quality_history[corpus_id]
        )
    
    def get_validation_summary(self, corpus_id: str) -> Dict[str, Any]:
        """Get validation metrics summary"""
        return self._statistics_calculator.get_validation_summary(
            self._quality_history[corpus_id],
            self._trend_analyzer
        )
    
    def get_issue_analysis(self, corpus_id: str) -> Dict[str, Any]:
        """Get analysis of detected issues"""
        return self._issue_analyzer.get_issue_analysis(corpus_id)
    
    def get_quality_time_series(
        self,
        corpus_id: str,
        metric_name: str = "overall",
        time_range_hours: int = 24
    ) -> List[TimeSeriesPoint]:
        """Get time series for quality metrics"""
        return self._statistics_calculator.get_quality_time_series(
            self._quality_history[corpus_id],
            metric_name,
            time_range_hours
        )
    
    async def generate_quality_report(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        score_dist = self.get_quality_score_distribution(corpus_id)
        validation_summary = self.get_validation_summary(corpus_id)
        issue_analysis = self.get_issue_analysis(corpus_id)
        
        return await self._report_generator.generate_quality_report(
            corpus_id,
            score_dist,
            validation_summary,
            issue_analysis
        )
    
    def get_collector_status(self) -> Dict[str, Any]:
        """Get quality collector status"""
        total_assessments = sum(len(history) for history in self._quality_history.values())
        
        return {
            "tracked_corpora": len(self._quality_history),
            "total_assessments": total_assessments,
            "total_issues_tracked": self._issue_analyzer.get_total_issues_tracked(),
            "trend_points": self._trend_analyzer.get_total_trend_points()
        }