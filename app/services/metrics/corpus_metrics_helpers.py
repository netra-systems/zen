"""
Helper functions for corpus metrics collection operations
Supports the main CorpusMetricsCollector with utility methods
"""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

from app.logging_config import central_logger
from app.schemas.Metrics import (
    QualityMetrics, ResourceUsage, OperationMetrics,
    TimeSeriesPoint, CorpusMetric, MetricType, MetricsSnapshot
)

logger = central_logger.get_logger(__name__)


class CorpusMetricsHelpers:
    """Helper methods for corpus metrics operations"""
    
    def __init__(self, time_series_storage, quality_collector, resource_monitor):
        """Initialize helpers with required components"""
        self.time_series = time_series_storage
        self.quality_collector = quality_collector
        self.resource_monitor = resource_monitor
    
    async def store_generation_time_series(self, corpus_id: str, generation_time_ms: int, context: Optional[str]) -> None:
        """Store generation time as time series data"""
        series_key = f"generation_time_{corpus_id}"
        point = TimeSeriesPoint(
            timestamp=datetime.now(UTC),
            value=generation_time_ms,
            tags={"metric": "generation_time", "context": context or "general"}
        )
        await self.time_series.store_point(series_key, point)
    
    async def store_quality_time_series(self, corpus_id: str, quality_metrics: QualityMetrics, operation_context: Optional[str]) -> None:
        """Store quality metrics as time series data"""
        series_key = f"quality_{corpus_id}"
        point = TimeSeriesPoint(
            timestamp=quality_metrics.timestamp,
            value=quality_metrics.overall_score,
            tags={"metric": "quality_score", "context": operation_context or "general"}
        )
        await self.time_series.store_point(series_key, point)
    
    async def store_resource_time_series(self, corpus_id: str, resource_usage: List[ResourceUsage]) -> None:
        """Store resource usage as time series data"""
        for usage in resource_usage:
            series_key = f"resource_{usage.resource_type}_{corpus_id}"
            point = TimeSeriesPoint(
                timestamp=usage.timestamp,
                value=usage.current_value,
                tags={"resource": usage.resource_type.value, "unit": usage.unit}
            )
            await self.time_series.store_point(series_key, point)
    
    async def store_duration_series(self, operation_type: str, operation_metrics: OperationMetrics, timestamp: datetime) -> None:
        """Store operation duration as time series"""
        if not operation_metrics.duration_ms:
            return
        series_key = f"duration_{operation_type}"
        point = TimeSeriesPoint(
            timestamp=timestamp,
            value=operation_metrics.duration_ms,
            tags={"operation": operation_type, "success": str(operation_metrics.success)}
        )
        await self.time_series.store_point(series_key, point)
    
    async def store_throughput_series(self, operation_type: str, operation_metrics: OperationMetrics, timestamp: datetime) -> None:
        """Store throughput as time series"""
        if not operation_metrics.throughput_per_second:
            return
        series_key = f"throughput_{operation_type}"
        point = TimeSeriesPoint(
            timestamp=timestamp,
            value=operation_metrics.throughput_per_second,
            tags={"operation": operation_type}
        )
        await self.time_series.store_point(series_key, point)
    
    def create_generation_metric(self, corpus_id: str, generation_time_ms: int, operation_id: str, context: Optional[str]) -> CorpusMetric:
        """Create generation time metric object"""
        return CorpusMetric(
            metric_id=operation_id,
            corpus_id=corpus_id,
            metric_type=MetricType.GENERATION_TIME,
            value=generation_time_ms,
            unit="ms",
            timestamp=datetime.now(UTC),
            tags={"context": context or "general"}
        )
    
    def build_quality_metrics(self, quality_data: Dict[str, float]) -> QualityMetrics:
        """Build quality metrics from raw data"""
        return QualityMetrics(
            overall_score=quality_data.get("overall", 0.0),
            validation_score=quality_data.get("validation", 0.0),
            completeness_score=quality_data.get("completeness", 0.0),
            consistency_score=quality_data.get("consistency", 0.0),
            accuracy_score=quality_data.get("accuracy"),
            timestamp=datetime.now(UTC),
            issues_detected=quality_data.get("issues", [])
        )
    
    async def build_resource_usage_list(self, resource_summary: Dict[str, Any], usage_list: List[ResourceUsage]) -> None:
        """Build resource usage list from summary data"""
        for resource_type, data in resource_summary.items():
            if isinstance(data, dict) and "current" in data:
                usage_list.append(ResourceUsage(
                    resource_type=resource_type,
                    current_value=data["current"],
                    max_value=data.get("max"),
                    average_value=data.get("avg"),
                    unit=data.get("unit", ""),
                    timestamp=datetime.now(UTC)
                ))
    
    def build_metrics_snapshot(self, corpus_id: str, snapshot_time: datetime, operation_metrics: List[OperationMetrics], 
                              quality_metrics: Optional[QualityMetrics], resource_usage: List[ResourceUsage], health_status: str) -> MetricsSnapshot:
        """Build comprehensive metrics snapshot"""
        return MetricsSnapshot(
            corpus_id=corpus_id,
            snapshot_time=snapshot_time,
            operation_metrics=operation_metrics,
            quality_metrics=quality_metrics,
            resource_usage=resource_usage,
            custom_metrics=[],
            total_records=0,  # Would be populated from actual corpus data
            health_status=health_status
        )
    
    def extract_quality_metrics_from_report(self, quality_report: Dict[str, Any]) -> QualityMetrics:
        """Extract quality metrics from quality report"""
        dist = quality_report["quality_distribution"]
        issues = quality_report.get("issue_analysis", {}).get("top_issues", [])
        return QualityMetrics(
            overall_score=dist.get("mean", 0.0),
            validation_score=0.8,  # Placeholder - would come from actual validation
            completeness_score=0.9,  # Placeholder
            consistency_score=0.85,  # Placeholder
            timestamp=datetime.now(UTC),
            issues_detected=[issue[0] for issue in issues[:5]]
        )
    
    def categorize_health_score(self, health_score: float) -> str:
        """Categorize health score into status levels"""
        if health_score >= 0.8:
            return "excellent"
        elif health_score >= 0.6:
            return "good"
        elif health_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    async def store_metric(self, metric: CorpusMetric) -> None:
        """Store metric to time series storage"""
        if not self.time_series:
            return
        point = TimeSeriesPoint(timestamp=metric.timestamp, value=float(metric.value), tags=metric.tags)
        await self.time_series.store_point(f"{metric.metric_type}_{metric.corpus_id}", point)
        logger.debug(f"Stored metric {metric.metric_type} for corpus {metric.corpus_id}")