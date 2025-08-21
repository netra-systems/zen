"""Metrics Collector Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic metrics collection functionality for tests
- Value Impact: Ensures metrics collection tests can execute without import errors
- Strategic Impact: Enables observability functionality validation
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A metric value with timestamp."""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """A metric definition."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    values: List[MetricValue] = field(default_factory=list)


class MetricsCollector:
    """Collects application metrics for monitoring and observability."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: Dict[str, Metric] = {}
        self._lock = asyncio.Lock()
        self._collection_interval = 60  # seconds
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize the metrics collector."""
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
    
    async def shutdown(self) -> None:
        """Shutdown the metrics collector."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
    
    async def record_counter(self, name: str, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        await self._record_metric(name, MetricType.COUNTER, value, labels or {})
    
    async def record_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        await self._record_metric(name, MetricType.GAUGE, value, labels or {})
    
    async def record_histogram(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        await self._record_metric(name, MetricType.HISTOGRAM, value, labels or {})
    
    async def record_timing(self, name: str, start_time: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric."""
        duration = time.time() - start_time
        await self.record_histogram(f"{name}_duration_seconds", duration, labels)
    
    async def _record_metric(self, name: str, metric_type: MetricType, value: Union[int, float], labels: Dict[str, str]) -> None:
        """Record a metric value."""
        async with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(name=name, metric_type=metric_type)
            
            metric_value = MetricValue(value=value, labels=labels)
            self._metrics[name].values.append(metric_value)
            
            # Keep only recent values to prevent memory growth
            cutoff_time = datetime.now() - timedelta(hours=1)
            self._metrics[name].values = [
                v for v in self._metrics[name].values 
                if v.timestamp > cutoff_time
            ]
    
    async def get_metrics(self) -> Dict[str, Metric]:
        """Get all collected metrics."""
        async with self._lock:
            return dict(self._metrics)
    
    async def get_metric(self, name: str) -> Optional[Metric]:
        """Get a specific metric."""
        async with self._lock:
            return self._metrics.get(name)
    
    async def get_metric_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        async with self._lock:
            summary = {}
            for name, metric in self._metrics.items():
                if metric.values:
                    latest_value = metric.values[-1].value
                    total_samples = len(metric.values)
                    summary[name] = {
                        "type": metric.metric_type.value,
                        "latest_value": latest_value,
                        "total_samples": total_samples,
                        "description": metric.description
                    }
            return summary
    
    async def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        async with self._lock:
            self._metrics.clear()
    
    async def _collection_loop(self) -> None:
        """Background collection loop for system metrics."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue collection
                await asyncio.sleep(1)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent()
            await self.record_gauge("system_cpu_percent", cpu_percent)
            
            # Memory metrics  
            memory = psutil.virtual_memory()
            await self.record_gauge("system_memory_percent", memory.percent)
            await self.record_gauge("system_memory_used_bytes", memory.used)
            
            # Process metrics
            process = psutil.Process()
            await self.record_gauge("process_memory_rss_bytes", process.memory_info().rss)
            await self.record_gauge("process_cpu_percent", process.cpu_percent())
            
        except ImportError:
            # psutil not available, record basic metrics
            await self.record_gauge("system_timestamp", time.time())


# Global metrics collector instance
default_metrics_collector = MetricsCollector()