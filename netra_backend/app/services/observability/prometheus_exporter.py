"""Prometheus Exporter Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic Prometheus export functionality for tests
- Value Impact: Ensures Prometheus export tests can execute without import errors
- Strategic Impact: Enables Prometheus observability validation
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from netra_backend.app.metrics_collector import MetricsCollector, Metric, MetricType


@dataclass
class PrometheusConfig:
    """Prometheus exporter configuration."""
    port: int = 9090
    path: str = "/metrics"
    namespace: str = "netra"
    export_interval: int = 15  # seconds


class PrometheusExporter:
    """Exports metrics in Prometheus format."""
    
    def __init__(self, config: Optional[PrometheusConfig] = None):
        """Initialize Prometheus exporter."""
        self.config = config or PrometheusConfig()
        self._metrics_collector: Optional[MetricsCollector] = None
        self._export_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_export = datetime.now()
    
    async def initialize(self) -> None:
        """Initialize the Prometheus exporter."""
        self._metrics_collector = MetricsCollector()
        await self._metrics_collector.initialize()
        
        self._running = True
        self._export_task = asyncio.create_task(self._export_loop())
    
    async def shutdown(self) -> None:
        """Shutdown the Prometheus exporter."""
        self._running = False
        
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_collector:
            await self._metrics_collector.shutdown()
    
    async def export_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        if not self._metrics_collector:
            return ""
        
        metrics = await self._metrics_collector.get_metrics()
        prometheus_output = []
        
        for name, metric in metrics.items():
            prometheus_name = self._sanitize_metric_name(name)
            
            # Add metric help and type
            prometheus_output.append(f"# HELP {prometheus_name} {metric.description or 'No description'}")
            prometheus_output.append(f"# TYPE {prometheus_name} {self._get_prometheus_type(metric.metric_type)}")
            
            # Add metric values
            for value in metric.values[-1:]:  # Only export latest value
                labels_str = self._format_labels(value.labels)
                prometheus_output.append(f"{prometheus_name}{labels_str} {value.value}")
        
        self._last_export = datetime.now()
        return "\n".join(prometheus_output)
    
    async def get_export_status(self) -> Dict[str, Any]:
        """Get export status information."""
        metrics_count = 0
        if self._metrics_collector:
            metrics = await self._metrics_collector.get_metrics()
            metrics_count = len(metrics)
        
        return {
            "running": self._running,
            "last_export": self._last_export.isoformat(),
            "metrics_count": metrics_count,
            "export_interval": self.config.export_interval,
            "prometheus_endpoint": f":{self.config.port}{self.config.path}"
        }
    
    def _sanitize_metric_name(self, name: str) -> str:
        """Sanitize metric name for Prometheus."""
        # Replace invalid characters with underscores
        sanitized = ""
        for char in name:
            if char.isalnum() or char == "_":
                sanitized += char
            else:
                sanitized += "_"
        
        # Add namespace
        if self.config.namespace:
            return f"{self.config.namespace}_{sanitized}"
        return sanitized
    
    def _get_prometheus_type(self, metric_type: MetricType) -> str:
        """Convert metric type to Prometheus type."""
        type_mapping = {
            MetricType.COUNTER: "counter",
            MetricType.GAUGE: "gauge", 
            MetricType.HISTOGRAM: "histogram",
            MetricType.SUMMARY: "summary"
        }
        return type_mapping.get(metric_type, "gauge")
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        
        label_pairs = []
        for key, value in labels.items():
            # Escape quotes in label values
            escaped_value = value.replace('"', '\\"')
            label_pairs.append(f'{key}="{escaped_value}"')
        
        return "{" + ",".join(label_pairs) + "}"
    
    async def _export_loop(self) -> None:
        """Background export loop."""
        while self._running:
            try:
                # In a real implementation, this would serve HTTP requests
                # For testing, we just ensure the export functionality works
                await self.export_metrics()
                await asyncio.sleep(self.config.export_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue exporting
                await asyncio.sleep(1)


# Global Prometheus exporter instance
default_prometheus_exporter = PrometheusExporter()