"""Metrics Service for collecting and managing application metrics

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Observability and performance optimization
- Value Impact: Enables data-driven optimization and proactive issue detection
- Strategic Impact: Supports 99.9% uptime SLA and reduces operational costs
"""

import asyncio
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric:
    """Metric data model"""
    
    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.name = name
        self.metric_type = metric_type
        self.value = value
        self.labels = labels or {}
        self.timestamp = timestamp or datetime.now(UTC)


class MetricsCollector:
    """Collects and stores metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = {}
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        key = self._get_metric_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
        self._store_metric(Metric(name, MetricType.COUNTER, self.counters[key], labels))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric"""
        key = self._get_metric_key(name, labels)
        self.gauges[key] = value
        self._store_metric(Metric(name, MetricType.GAUGE, value, labels))
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric"""
        self._store_metric(Metric(name, MetricType.HISTOGRAM, value, labels))
    
    def record_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a summary metric"""
        self._store_metric(Metric(name, MetricType.SUMMARY, value, labels))
    
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Generate metric key from name and labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}({label_str})"
    
    def _store_metric(self, metric: Metric) -> None:
        """Store metric in collection"""
        if metric.name not in self.metrics:
            self.metrics[metric.name] = []
        self.metrics[metric.name].append(metric)
        
        # Keep only last 1000 metrics per name to prevent memory issues
        if len(self.metrics[metric.name]) > 1000:
            self.metrics[metric.name] = self.metrics[metric.name][-1000:]


class MetricsService:
    """Service for managing application metrics"""
    
    def __init__(self):
        self.collector = MetricsCollector()
        self.exporters: List[Any] = []
        self.is_running = False
        self.export_interval = 60  # seconds
        self._export_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the metrics service"""
        self.is_running = True
        self._export_task = asyncio.create_task(self._export_loop())
        logger.info("Metrics service started")
    
    async def stop(self) -> None:
        """Stop the metrics service"""
        self.is_running = False
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics service stopped")
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        self.collector.increment_counter(name, value, labels)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric"""
        self.collector.set_gauge(name, value, labels)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric"""
        self.collector.record_histogram(name, value, labels)
    
    def record_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a summary metric"""
        self.collector.record_summary(name, value, labels)
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, List[Metric]]:
        """Get collected metrics"""
        if name:
            return {name: self.collector.metrics.get(name, [])}
        return self.collector.metrics.copy()
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names"""
        return list(self.collector.metrics.keys())
    
    def get_latest_metric_values(self) -> Dict[str, float]:
        """Get latest values for all metrics"""
        latest_values = {}
        
        # Add counters
        latest_values.update(self.collector.counters)
        
        # Add gauges
        latest_values.update(self.collector.gauges)
        
        # Add latest histogram/summary values
        for name, metric_list in self.collector.metrics.items():
            if metric_list and metric_list[-1].metric_type in [MetricType.HISTOGRAM, MetricType.SUMMARY]:
                latest_values[name] = metric_list[-1].value
        
        return latest_values
    
    def clear_metrics(self, name: Optional[str] = None) -> None:
        """Clear metrics"""
        if name:
            if name in self.collector.metrics:
                del self.collector.metrics[name]
            if name in self.collector.counters:
                del self.collector.counters[name]
            if name in self.collector.gauges:
                del self.collector.gauges[name]
        else:
            self.collector.metrics.clear()
            self.collector.counters.clear()
            self.collector.gauges.clear()
    
    def add_exporter(self, exporter) -> None:
        """Add metrics exporter"""
        self.exporters.append(exporter)
    
    def remove_exporter(self, exporter) -> None:
        """Remove metrics exporter"""
        if exporter in self.exporters:
            self.exporters.remove(exporter)
    
    async def export_metrics(self) -> None:
        """Export metrics to all exporters"""
        metrics = self.get_metrics()
        for exporter in self.exporters:
            try:
                await exporter.export(metrics)
            except Exception as e:
                logger.error(f"Error exporting metrics: {e}")
    
    async def _export_loop(self) -> None:
        """Periodic metrics export loop"""
        while self.is_running:
            try:
                await self.export_metrics()
                await asyncio.sleep(self.export_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics export loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get metrics service status"""
        return {
            "is_running": self.is_running,
            "total_metrics": len(self.collector.metrics),
            "exporters_count": len(self.exporters),
            "export_interval": self.export_interval,
            "counters_count": len(self.collector.counters),
            "gauges_count": len(self.collector.gauges)
        }


# Common application metrics
def record_request_duration(duration_ms: float, method: str, endpoint: str, status_code: int) -> None:
    """Record HTTP request duration"""
    global _metrics_service
    if _metrics_service:
        _metrics_service.record_histogram(
            "http_request_duration_ms",
            duration_ms,
            {"method": method, "endpoint": endpoint, "status_code": str(status_code)}
        )


def increment_request_count(method: str, endpoint: str, status_code: int) -> None:
    """Increment HTTP request count"""
    global _metrics_service
    if _metrics_service:
        _metrics_service.increment_counter(
            "http_requests_total",
            1.0,
            {"method": method, "endpoint": endpoint, "status_code": str(status_code)}
        )


def set_active_connections(count: int) -> None:
    """Set active connections gauge"""
    global _metrics_service
    if _metrics_service:
        _metrics_service.set_gauge("active_connections", float(count))


def record_llm_request_duration(duration_ms: float, provider: str, model: str) -> None:
    """Record LLM request duration"""
    global _metrics_service
    if _metrics_service:
        _metrics_service.record_histogram(
            "llm_request_duration_ms",
            duration_ms,
            {"provider": provider, "model": model}
        )


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get global metrics service instance"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def set_metrics_service(service: MetricsService) -> None:
    """Set global metrics service instance"""
    global _metrics_service
    _metrics_service = service