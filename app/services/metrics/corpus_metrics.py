"""
Main corpus metrics collector orchestrating all metric collection components
Provides unified interface for comprehensive corpus operation monitoring
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

from app.logging_config import central_logger
from app.redis_manager import RedisManager
from app.schemas.Metrics import (
    MetricsSnapshot, ExportFormat, QualityMetrics,
    ResourceUsage, OperationMetrics, TimeSeriesPoint
)
from .core_collector import CoreMetricsCollector
from .quality_collector import QualityMetricsCollector
from .resource_monitor import ResourceMonitor
from .exporter import MetricsExporter
from .time_series import TimeSeriesStorage

logger = central_logger.get_logger(__name__)


class CorpusMetricsCollector:
    """
    Main orchestrator for corpus operation metrics collection
    Integrates all metric collection components into a unified system
    """
    
    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        enable_resource_monitoring: bool = True,
        enable_real_time_updates: bool = True
    ):
        # Initialize all collectors
        self.core_collector = CoreMetricsCollector()
        self.quality_collector = QualityMetricsCollector()
        self.resource_monitor = ResourceMonitor()
        self.exporter = MetricsExporter()
        self.time_series = TimeSeriesStorage(redis_manager)
        
        # Configuration
        self.redis_manager = redis_manager
        self.enable_resource_monitoring = enable_resource_monitoring
        self.enable_real_time_updates = enable_real_time_updates
        self._monitoring_active = False
        
        logger.info("Initialized corpus metrics collector")
    
    async def start_monitoring(self):
        """Start all monitoring components"""
        if self._monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self._monitoring_active = True
        
        if self.enable_resource_monitoring:
            await self.resource_monitor.start_monitoring()
        
        logger.info("Started corpus metrics monitoring")
    
    async def stop_monitoring(self):
        """Stop all monitoring components"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self.enable_resource_monitoring:
            await self.resource_monitor.stop_monitoring()
        
        logger.info("Stopped corpus metrics monitoring")
    
    @asynccontextmanager
    async def track_operation(
        self,
        corpus_id: str,
        operation_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracking corpus operations"""
        operation_id = await self.core_collector.start_operation(corpus_id, operation_type)
        
        if self.enable_resource_monitoring:
            await self.resource_monitor.take_operation_snapshot(operation_id, corpus_id)
        
        try:
            yield operation_id
            # Operation succeeded
            await self._complete_operation_tracking(operation_id, True, context)
        except Exception as e:
            # Operation failed
            await self._complete_operation_tracking(operation_id, False, {"error": str(e)})
            raise
    
    async def _complete_operation_tracking(
        self,
        operation_id: str,
        success: bool,
        context: Optional[Dict[str, Any]] = None
    ):
        """Complete operation tracking with all collectors"""
        # Core metrics
        records_processed = context.get("records_processed") if context else None
        error_message = context.get("error") if context and not success else None
        
        operation_metrics = await self.core_collector.end_operation(
            operation_id, success, records_processed, error_message
        )
        
        # Resource usage
        if self.enable_resource_monitoring and operation_metrics:
            resource_usage = await self.resource_monitor.calculate_operation_usage(operation_id)
            if resource_usage and self.enable_real_time_updates:
                await self._store_time_series_data(
                    operation_metrics.operation_type,
                    operation_metrics,
                    resource_usage
                )
    
    async def record_quality_assessment(
        self,
        corpus_id: str,
        quality_metrics: QualityMetrics,
        operation_context: Optional[str] = None
    ):
        """Record quality assessment for corpus"""
        await self.quality_collector.record_quality_assessment(
            corpus_id, quality_metrics, operation_context
        )
        
        if self.enable_real_time_updates:
            series_key = f"quality_{corpus_id}"
            point = TimeSeriesPoint(
                timestamp=quality_metrics.timestamp,
                value=quality_metrics.overall_score,
                tags={"metric": "quality_score", "context": operation_context or "general"}
            )
            await self.time_series.store_point(series_key, point)
    
    async def _store_time_series_data(
        self,
        operation_type: str,
        operation_metrics: OperationMetrics,
        resource_usage: Optional[Dict[str, Any]] = None
    ):
        """Store metrics as time-series data"""
        if not self.enable_real_time_updates:
            return
        
        timestamp = operation_metrics.end_time or datetime.now(UTC)
        
        # Store operation duration
        if operation_metrics.duration_ms:
            series_key = f"duration_{operation_type}"
            point = TimeSeriesPoint(
                timestamp=timestamp,
                value=operation_metrics.duration_ms,
                tags={"operation": operation_type, "success": str(operation_metrics.success)}
            )
            await self.time_series.store_point(series_key, point)
        
        # Store throughput
        if operation_metrics.throughput_per_second:
            series_key = f"throughput_{operation_type}"
            point = TimeSeriesPoint(
                timestamp=timestamp,
                value=operation_metrics.throughput_per_second,
                tags={"operation": operation_type}
            )
            await self.time_series.store_point(series_key, point)
    
    async def generate_metrics_snapshot(self, corpus_id: str) -> MetricsSnapshot:
        """Generate comprehensive metrics snapshot for corpus"""
        snapshot_time = datetime.now(UTC)
        
        # Get recent operation metrics
        operation_metrics = self._get_recent_operations(corpus_id)
        
        # Get quality metrics
        quality_metrics = await self._get_latest_quality_metrics(corpus_id)
        
        # Get resource usage
        resource_usage = await self._get_current_resource_usage()
        
        # Get custom metrics
        custom_metrics = []  # Can be extended with specific corpus metrics
        
        # Determine health status
        health_status = await self._assess_corpus_health(corpus_id, quality_metrics)
        
        return MetricsSnapshot(
            corpus_id=corpus_id,
            snapshot_time=snapshot_time,
            operation_metrics=operation_metrics,
            quality_metrics=quality_metrics,
            resource_usage=resource_usage,
            custom_metrics=custom_metrics,
            total_records=await self._get_corpus_record_count(corpus_id),
            health_status=health_status
        )
    
    def _get_recent_operations(self, corpus_id: str, limit: int = 10) -> List[OperationMetrics]:
        """Get recent operation metrics for corpus"""
        # This would typically query from a database or cache
        # For now, return empty list - can be extended with actual data retrieval
        return []
    
    async def _get_latest_quality_metrics(self, corpus_id: str) -> Optional[QualityMetrics]:
        """Get latest quality metrics for corpus"""
        quality_report = await self.quality_collector.generate_quality_report(corpus_id)
        
        if not quality_report or quality_report.get("quality_distribution", {}).get("count", 0) == 0:
            return None
        
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
    
    async def _get_current_resource_usage(self) -> List[ResourceUsage]:
        """Get current resource usage metrics"""
        if not self.enable_resource_monitoring:
            return []
        
        resource_summary = self.resource_monitor.get_resource_summary()
        usage_list = []
        
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
        
        return usage_list
    
    async def _assess_corpus_health(
        self,
        corpus_id: str,
        quality_metrics: Optional[QualityMetrics]
    ) -> str:
        """Assess overall corpus health status"""
        # Success rate check
        success_rate = self.core_collector.get_success_rate(corpus_id)
        
        # Quality score check
        quality_score = quality_metrics.overall_score if quality_metrics else 0.5
        
        # Resource alerts check
        resource_alerts = self.resource_monitor.get_resource_alerts()
        critical_alerts = [a for a in resource_alerts if a.get("severity") == "high"]
        
        # Calculate health score
        health_score = (success_rate * 0.4) + (quality_score * 0.4) + (0.2 if not critical_alerts else 0.0)
        
        if health_score >= 0.8:
            return "excellent"
        elif health_score >= 0.6:
            return "good"
        elif health_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    async def _get_corpus_record_count(self, corpus_id: str) -> int:
        """Get total record count for corpus"""
        # Placeholder - would query actual corpus data
        return 0
    
    async def export_metrics(
        self,
        corpus_id: str,
        export_format: ExportFormat,
        time_range_hours: Optional[int] = None
    ) -> str:
        """Export corpus metrics in specified format"""
        snapshot = await self.generate_metrics_snapshot(corpus_id)
        return await self.exporter.export_metrics(snapshot, export_format)
    
    async def get_time_series_data(
        self,
        series_key: str,
        time_range_hours: int = 1,
        aggregation: Optional[str] = None
    ) -> List[TimeSeriesPoint]:
        """Get time-series data for visualization"""
        if aggregation:
            return await self.time_series.aggregate_series(
                series_key, aggregation, interval_minutes=5, time_range_hours=time_range_hours
            )
        else:
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(hours=time_range_hours)
            return await self.time_series.get_series(series_key, start_time, end_time)
    
    async def get_comprehensive_report(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        snapshot = await self.generate_metrics_snapshot(corpus_id)
        quality_report = await self.quality_collector.generate_quality_report(corpus_id)
        
        return {
            "corpus_id": corpus_id,
            "report_timestamp": datetime.now(UTC).isoformat(),
            "metrics_snapshot": snapshot,
            "quality_analysis": quality_report,
            "success_rate": self.core_collector.get_success_rate(corpus_id),
            "average_generation_time": self.core_collector.get_average_generation_time(corpus_id),
            "resource_summary": self.resource_monitor.get_resource_summary(),
            "resource_alerts": self.resource_monitor.get_resource_alerts(),
            "collector_status": await self.get_collector_status()
        }
    
    async def get_collector_status(self) -> Dict[str, Any]:
        """Get status of all collectors"""
        return {
            "monitoring_active": self._monitoring_active,
            "core_collector": self.core_collector.get_buffer_status(),
            "quality_collector": self.quality_collector.get_collector_status(),
            "resource_monitor": self.resource_monitor.get_monitor_status(),
            "time_series": self.time_series.get_storage_status(),
            "redis_available": self.redis_manager is not None,
            "real_time_updates": self.enable_real_time_updates,
            "resource_monitoring": self.enable_resource_monitoring
        }
    
    async def cleanup_old_data(self, age_hours: int = 24):
        """Clean up old data from all collectors"""
        await self.core_collector.clear_old_data(age_hours)
        await self.time_series.cleanup_old_data()
        logger.info(f"Cleaned up metrics data older than {age_hours} hours")