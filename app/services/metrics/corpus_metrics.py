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
    ResourceUsage, OperationMetrics, TimeSeriesPoint,
    CorpusMetric, MetricType
)
from .core_collector import CoreMetricsCollector
from .quality_collector import QualityMetricsCollector
from .resource_monitor import ResourceMonitor
from .exporter import MetricsExporter
from .time_series import TimeSeriesStorage
from .corpus_metrics_helpers import CorpusMetricsHelpers

logger = central_logger.get_logger(__name__)


class CorpusMetricsCollector:
    """
    Main orchestrator for corpus operation metrics collection
    Integrates all metric collection components into a unified system
    """
    
    def __init__(self, redis_manager: Optional[RedisManager] = None, enable_resource_monitoring: bool = True, enable_real_time_updates: bool = True):
        """Initialize corpus metrics collector with all components"""
        self._init_collectors()
        self._init_config(redis_manager, enable_resource_monitoring, enable_real_time_updates)
        self.helpers = CorpusMetricsHelpers(self.time_series, self.quality_collector, self.resource_monitor)
        self._monitoring_active = False
        logger.info("Initialized corpus metrics collector")
    
    def _init_collectors(self) -> None:
        """Initialize all metric collection components"""
        self.core_collector = CoreMetricsCollector()
        self.quality_collector = QualityMetricsCollector()
        self.resource_monitor = ResourceMonitor()
        self.exporter = MetricsExporter()
    
    def _init_config(self, redis_manager: Optional[RedisManager], enable_resource_monitoring: bool, enable_real_time_updates: bool) -> None:
        """Initialize configuration settings"""
        self.redis_manager = redis_manager
        self.time_series = TimeSeriesStorage(redis_manager)
        self.enable_resource_monitoring = enable_resource_monitoring
        self.enable_real_time_updates = enable_real_time_updates
    
    async def start_monitoring(self) -> None:
        """Start all monitoring components"""
        if self._monitoring_active:
            logger.warning("Monitoring already active")
            return
        self._monitoring_active = True
        await self._start_resource_monitoring()
        logger.info("Started corpus metrics monitoring")
    
    async def _start_resource_monitoring(self) -> None:
        """Start resource monitoring if enabled"""
        if self.enable_resource_monitoring:
            await self.resource_monitor.start_monitoring()
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring components"""
        if not self._monitoring_active:
            return
        self._monitoring_active = False
        await self._stop_resource_monitoring()
        logger.info("Stopped corpus metrics monitoring")
    
    async def _stop_resource_monitoring(self) -> None:
        """Stop resource monitoring if enabled"""
        if self.enable_resource_monitoring:
            await self.resource_monitor.stop_monitoring()
    
    @asynccontextmanager
    async def track_operation(self, corpus_id: str, operation_type: str, context: Optional[Dict[str, Any]] = None):
        """Context manager for tracking corpus operations"""
        operation_id = await self.core_collector.start_operation(corpus_id, operation_type)
        await self._take_operation_snapshot(operation_id, corpus_id)
        try:
            yield operation_id
            await self._complete_operation_tracking(operation_id, True, context)
        except Exception as e:
            await self._complete_operation_tracking(operation_id, False, {"error": str(e)})
            raise
    
    async def _take_operation_snapshot(self, operation_id: str, corpus_id: str) -> None:
        """Take resource snapshot for operation if monitoring enabled"""
        if self.enable_resource_monitoring:
            await self.resource_monitor.take_operation_snapshot(operation_id, corpus_id)
    
    async def _complete_operation_tracking(self, operation_id: str, success: bool, context: Optional[Dict[str, Any]] = None) -> None:
        """Complete operation tracking with all collectors"""
        records_processed = context.get("records_processed") if context else None
        error_message = context.get("error") if context and not success else None
        operation_metrics = await self.core_collector.end_operation(operation_id, success, records_processed, error_message)
        await self._process_operation_completion(operation_id, operation_metrics)
    
    async def _process_operation_completion(self, operation_id: str, operation_metrics: Optional[OperationMetrics]) -> None:
        """Process completed operation metrics"""
        if not (self.enable_resource_monitoring and operation_metrics):
            return
        resource_usage = await self.resource_monitor.calculate_operation_usage(operation_id)
        if resource_usage and self.enable_real_time_updates:
            await self._store_time_series_data(operation_metrics.operation_type, operation_metrics, resource_usage)
    
    async def record_quality_assessment(self, corpus_id: str, quality_metrics: QualityMetrics, operation_context: Optional[str] = None) -> None:
        """Record quality assessment for corpus"""
        await self.quality_collector.record_quality_assessment(corpus_id, quality_metrics, operation_context)
        if self.enable_real_time_updates:
            await self.helpers.store_quality_time_series(corpus_id, quality_metrics, operation_context)
    
    async def track_generation_time(self, corpus_id: str, generation_time_ms: int, operation_context: Optional[str] = None) -> str:
        """Track generation time for corpus operations"""
        operation_id = f"{corpus_id}_{datetime.now(UTC).timestamp()}"
        metric = self.helpers.create_generation_metric(corpus_id, generation_time_ms, operation_id, operation_context)
        await self.helpers.store_metric(metric)
        if self.enable_real_time_updates:
            await self.helpers.store_generation_time_series(corpus_id, generation_time_ms, operation_context)
        logger.debug(f"Tracked generation time: {generation_time_ms}ms for corpus {corpus_id}")
        return operation_id
    
    async def measure_quality_score(self, corpus_id: str, quality_data: Dict[str, float], context: Optional[str] = None) -> QualityMetrics:
        """Measure and record quality score for corpus"""
        quality_metrics = self.helpers.build_quality_metrics(quality_data)
        await self.record_quality_assessment(corpus_id, quality_metrics, context)
        if self.enable_real_time_updates:
            await self.helpers.store_quality_time_series(corpus_id, quality_metrics, context)
        logger.info(f"Quality score {quality_metrics.overall_score:.3f} recorded for corpus {corpus_id}")
        return quality_metrics
    
    async def monitor_resource_usage(self, corpus_id: str, operation_id: Optional[str] = None) -> List[ResourceUsage]:
        """Monitor and record current resource usage"""
        if not self.enable_resource_monitoring:
            logger.warning("Resource monitoring disabled")
            return []
        current_usage = await self._get_current_resource_usage()
        await self._process_resource_monitoring(corpus_id, operation_id, current_usage)
        logger.debug(f"Resource usage monitored for corpus {corpus_id}")
        return current_usage
    
    async def _process_resource_monitoring(self, corpus_id: str, operation_id: Optional[str], current_usage: List[ResourceUsage]) -> None:
        """Process resource monitoring data"""
        if operation_id:
            await self.resource_monitor.associate_operation_usage(operation_id, current_usage)
        if self.enable_real_time_updates:
            await self.helpers.store_resource_time_series(corpus_id, current_usage)
    
    async def _get_current_resource_usage(self) -> List[ResourceUsage]:
        """Get current resource usage metrics"""
        if not self.enable_resource_monitoring:
            return []
        resource_summary = self.resource_monitor.get_resource_summary()
        usage_list = []
        await self.helpers.build_resource_usage_list(resource_summary, usage_list)
        return usage_list
    
    async def export_metrics(self, corpus_id: str, export_format: ExportFormat, time_range_hours: Optional[int] = None) -> str:
        """Export corpus metrics in specified format"""
        try:
            snapshot = await self.generate_metrics_snapshot(corpus_id)
            return await self.exporter.export_metrics(snapshot, export_format)
        except Exception as e:
            logger.error(f"Failed to export metrics for corpus {corpus_id}: {str(e)}")
            raise
    
    async def generate_metrics_snapshot(self, corpus_id: str) -> MetricsSnapshot:
        """Generate comprehensive metrics snapshot for corpus"""
        snapshot_time = datetime.now(UTC)
        operation_metrics = self._get_recent_operations(corpus_id)
        quality_metrics = await self._get_latest_quality_metrics(corpus_id)
        resource_usage = await self._get_current_resource_usage()
        health_status = await self._assess_corpus_health(corpus_id, quality_metrics)
        return self.helpers.build_metrics_snapshot(corpus_id, snapshot_time, operation_metrics, quality_metrics, resource_usage, health_status)
    
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
        return self.helpers.extract_quality_metrics_from_report(quality_report)
    
    async def _assess_corpus_health(self, corpus_id: str, quality_metrics: Optional[QualityMetrics]) -> str:
        """Assess overall corpus health status"""
        success_rate = self.core_collector.get_success_rate(corpus_id)
        quality_score = quality_metrics.overall_score if quality_metrics else 0.5
        resource_alerts = self.resource_monitor.get_resource_alerts()
        critical_alerts = [a for a in resource_alerts if a.get("severity") == "high"]
        health_score = (success_rate * 0.4) + (quality_score * 0.4) + (0.2 if not critical_alerts else 0.0)
        return self.helpers.categorize_health_score(health_score)
    
    async def _store_time_series_data(self, operation_type: str, operation_metrics: OperationMetrics, resource_usage: Optional[Dict[str, Any]] = None) -> None:
        """Store metrics as time-series data"""
        if not self.enable_real_time_updates:
            return
        timestamp = operation_metrics.end_time or datetime.now(UTC)
        await self.helpers.store_duration_series(operation_type, operation_metrics, timestamp)
        await self.helpers.store_throughput_series(operation_type, operation_metrics, timestamp)
    
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
    
    async def get_time_series_data(self, series_key: str, time_range_hours: int = 1) -> List[Dict[str, Any]]:
        """Retrieve time-series data for the specified series and time range"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range_hours)
        points = await self.time_series.get_series(series_key, start_time, end_time)
        return [{"timestamp": p.timestamp.isoformat(), "value": p.value, "tags": p.tags} for p in points]
    
    async def get_comprehensive_report(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive report for corpus including all metrics"""
        report_timestamp = datetime.now(UTC)
        metrics_snapshot = await self.generate_metrics_snapshot(corpus_id)
        quality_analysis = await self._get_latest_quality_metrics(corpus_id)
        collector_status = await self.get_collector_status()
        return {"corpus_id": corpus_id, "report_timestamp": report_timestamp.isoformat(), 
                "metrics_snapshot": metrics_snapshot, "quality_analysis": quality_analysis, 
                "collector_status": collector_status}

    async def cleanup_old_data(self, age_hours: int = 24) -> None:
        """Clean up old data from all collectors"""
        await self.core_collector.clear_old_data(age_hours)
        await self.time_series.cleanup_old_data()
        logger.info(f"Cleaned up metrics data older than {age_hours} hours")