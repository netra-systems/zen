"""
Metrics Exporter Module

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Observability & System Health  
- Value Impact: Provides metrics export to Prometheus and other monitoring systems
- Strategic Impact: Essential for SLA monitoring and operational excellence

Handles metric collection, aggregation, and export for monitoring systems.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics that can be exported."""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Container for metric data points."""
    name: str
    metric_type: MetricType
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: Optional[str] = None


@dataclass 
class MetricSample:
    """Individual metric sample with timestamp."""
    value: Union[int, float]
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricRegistry:
    """Registry for managing metrics before export."""
    
    def __init__(self, max_samples_per_metric: int = 1000):
        self.metrics: Dict[str, List[MetricSample]] = defaultdict(list)
        self.metric_metadata: Dict[str, MetricData] = {}
        self.max_samples = max_samples_per_metric
        self.total_samples = 0
        
    def register_metric(self, metric: MetricData) -> None:
        """Register a new metric."""
        self.metric_metadata[metric.name] = metric
        logger.debug(f"Registered metric: {metric.name} ({metric.metric_type})")
        
    def record_value(self, metric_name: str, value: Union[int, float], 
                    labels: Optional[Dict[str, str]] = None) -> None:
        """Record a value for a metric."""
        sample = MetricSample(
            value=value,
            timestamp=time.time(), 
            labels=labels or {}
        )
        
        # Add to samples list
        samples = self.metrics[metric_name]
        samples.append(sample)
        self.total_samples += 1
        
        # Keep only recent samples
        if len(samples) > self.max_samples:
            samples.pop(0)
            
        logger.debug(f"Recorded {metric_name}={value} with labels {labels}")
    
    def get_metric_samples(self, metric_name: str) -> List[MetricSample]:
        """Get all samples for a metric."""
        return self.metrics.get(metric_name, [])
    
    def get_latest_value(self, metric_name: str) -> Optional[Union[int, float]]:
        """Get the latest value for a metric."""
        samples = self.metrics.get(metric_name, [])
        return samples[-1].value if samples else None
    
    def get_all_metrics(self) -> Dict[str, List[MetricSample]]:
        """Get all metrics and their samples."""
        return dict(self.metrics)
    
    def clear_old_samples(self, retention_seconds: int = 3600) -> int:
        """Clear samples older than retention period."""
        cutoff_time = time.time() - retention_seconds
        removed_count = 0
        
        for metric_name, samples in self.metrics.items():
            original_count = len(samples)
            self.metrics[metric_name] = [
                s for s in samples if s.timestamp > cutoff_time
            ]
            removed_count += original_count - len(self.metrics[metric_name])
        
        self.total_samples -= removed_count
        logger.info(f"Removed {removed_count} old metric samples")
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_metrics": len(self.metric_metadata),
            "total_samples": self.total_samples,
            "active_metrics": len([m for m in self.metrics.keys() if self.metrics[m]]),
            "max_samples_per_metric": self.max_samples
        }


class PrometheusExporter:
    """Exports metrics in Prometheus format."""
    
    def __init__(self, registry: MetricRegistry):
        self.registry = registry
        
    def export_metrics(self) -> str:
        """Export all metrics in Prometheus text format."""
        output = []
        
        for metric_name, samples in self.registry.get_all_metrics().items():
            if not samples:
                continue
                
            # Get metadata
            metadata = self.registry.metric_metadata.get(metric_name)
            if metadata and metadata.help_text:
                output.append(f"# HELP {metric_name} {metadata.help_text}")
            if metadata:
                output.append(f"# TYPE {metric_name} {metadata.metric_type.value}")
            
            # Export latest sample for each label combination
            latest_by_labels = {}
            for sample in samples:
                label_key = json.dumps(sample.labels, sort_keys=True)
                latest_by_labels[label_key] = sample
            
            for sample in latest_by_labels.values():
                if sample.labels:
                    label_str = ','.join(f'{k}="{v}"' for k, v in sample.labels.items())
                    output.append(f"{metric_name}{{{label_str}}} {sample.value}")
                else:
                    output.append(f"{metric_name} {sample.value}")
        
        return '\n'.join(output)
    
    def export_metric(self, metric_name: str) -> str:
        """Export a specific metric in Prometheus format."""
        samples = self.registry.get_metric_samples(metric_name)
        if not samples:
            return ""
            
        output = []
        metadata = self.registry.metric_metadata.get(metric_name)
        
        if metadata and metadata.help_text:
            output.append(f"# HELP {metric_name} {metadata.help_text}")
        if metadata:
            output.append(f"# TYPE {metric_name} {metadata.metric_type.value}")
            
        # Use latest value
        latest_sample = samples[-1]
        if latest_sample.labels:
            label_str = ','.join(f'{k}="{v}"' for k, v in latest_sample.labels.items())
            output.append(f"{metric_name}{{{label_str}}} {latest_sample.value}")
        else:
            output.append(f"{metric_name} {latest_sample.value}")
            
        return '\n'.join(output)


class MetricsCollector:
    """Collects system metrics automatically."""
    
    def __init__(self, registry: MetricRegistry, collection_interval: float = 60.0):
        self.registry = registry
        self.collection_interval = collection_interval
        self.collection_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Register built-in metrics
        self._register_builtin_metrics()
    
    def _register_builtin_metrics(self) -> None:
        """Register built-in system metrics."""
        builtin_metrics = [
            MetricData("netra_http_requests_total", MetricType.COUNTER, 0, 
                      help_text="Total HTTP requests processed"),
            MetricData("netra_websocket_connections", MetricType.GAUGE, 0,
                      help_text="Current WebSocket connections"),
            MetricData("netra_agent_executions_total", MetricType.COUNTER, 0,
                      help_text="Total agent executions"),
            MetricData("netra_agent_execution_duration_seconds", MetricType.HISTOGRAM, 0,
                      help_text="Agent execution duration in seconds"),
            MetricData("netra_database_queries_total", MetricType.COUNTER, 0,
                      help_text="Total database queries executed"),
            MetricData("netra_cache_hits_total", MetricType.COUNTER, 0,
                      help_text="Total cache hits"),
            MetricData("netra_cache_misses_total", MetricType.COUNTER, 0,
                      help_text="Total cache misses"),
            MetricData("netra_errors_total", MetricType.COUNTER, 0,
                      help_text="Total errors encountered"),
        ]
        
        for metric in builtin_metrics:
            self.registry.register_metric(metric)
    
    async def start_collection(self) -> None:
        """Start automatic metric collection."""
        if self.is_running:
            return
            
        self.is_running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started metrics collection")
    
    async def stop_collection(self) -> None:
        """Stop automatic metric collection."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped metrics collection")
    
    async def _collection_loop(self) -> None:
        """Main collection loop."""
        try:
            while self.is_running:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in metrics collection loop: {e}")
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            # Memory usage (simplified)
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            self.registry.record_value("netra_memory_usage_mb", memory_usage)
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            self.registry.record_value("netra_cpu_usage_percent", cpu_percent)
            
            # Registry stats
            stats = self.registry.get_stats()
            for stat_name, stat_value in stats.items():
                self.registry.record_value(f"netra_registry_{stat_name}", stat_value)
                
        except ImportError:
            # psutil not available, skip system metrics
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class MetricsExporter:
    """Main metrics exporter class."""
    
    def __init__(self, collection_interval: float = 60.0):
        self.registry = MetricRegistry()
        self.prometheus_exporter = PrometheusExporter(self.registry)
        self.collector = MetricsCollector(self.registry, collection_interval)
        self.export_stats = {
            "total_exports": 0,
            "last_export_time": None,
            "export_errors": 0
        }
    
    async def start(self) -> None:
        """Start the metrics system."""
        await self.collector.start_collection()
        logger.info("Metrics exporter started")
    
    async def stop(self) -> None:
        """Stop the metrics system."""
        await self.collector.stop_collection()
        logger.info("Metrics exporter stopped")
    
    def record_counter(self, name: str, value: Union[int, float] = 1, 
                      labels: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        self.registry.record_value(name, value, labels)
    
    def record_gauge(self, name: str, value: Union[int, float], 
                    labels: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        self.registry.record_value(name, value, labels)
    
    def record_histogram(self, name: str, value: Union[int, float],
                        labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        self.registry.record_value(name, value, labels)
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        try:
            result = self.prometheus_exporter.export_metrics()
            self.export_stats["total_exports"] += 1
            self.export_stats["last_export_time"] = time.time()
            return result
        except Exception as e:
            self.export_stats["export_errors"] += 1
            logger.error(f"Error exporting Prometheus metrics: {e}")
            return f"# Error exporting metrics: {e}"
    
    def export_json(self) -> str:
        """Export metrics in JSON format."""
        try:
            metrics = {}
            for metric_name, samples in self.registry.get_all_metrics().items():
                if samples:
                    latest_sample = samples[-1]
                    metrics[metric_name] = {
                        "value": latest_sample.value,
                        "timestamp": latest_sample.timestamp,
                        "labels": latest_sample.labels
                    }
            
            result = json.dumps(metrics, indent=2)
            self.export_stats["total_exports"] += 1
            self.export_stats["last_export_time"] = time.time()
            return result
        except Exception as e:
            self.export_stats["export_errors"] += 1
            logger.error(f"Error exporting JSON metrics: {e}")
            return json.dumps({"error": str(e)})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get exporter statistics."""
        stats = {
            "exporter": self.export_stats.copy(),
            "registry": self.registry.get_stats(),
            "collector_running": self.collector.is_running
        }
        return stats
    
    async def cleanup_old_data(self, retention_seconds: int = 3600) -> None:
        """Clean up old metric data."""
        removed = self.registry.clear_old_samples(retention_seconds)
        logger.info(f"Cleaned up {removed} old metric samples")


# Global metrics exporter instance
_metrics_exporter: Optional[MetricsExporter] = None

def get_metrics_exporter() -> MetricsExporter:
    """Get global metrics exporter instance."""
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = MetricsExporter()
    return _metrics_exporter

def record_metric(name: str, value: Union[int, float], metric_type: str = "gauge", 
                 labels: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record a metric."""
    exporter = get_metrics_exporter()
    
    if metric_type == "counter":
        exporter.record_counter(name, value, labels)
    elif metric_type == "histogram":
        exporter.record_histogram(name, value, labels)
    else:
        exporter.record_gauge(name, value, labels)

async def start_metrics_system() -> None:
    """Start the global metrics system."""
    exporter = get_metrics_exporter()
    await exporter.start()

async def stop_metrics_system() -> None:
    """Stop the global metrics system."""
    exporter = get_metrics_exporter()
    await exporter.stop()