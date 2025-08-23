"""
Prometheus Exporter: Monitoring metrics collection and export service.

This module provides prometheus metrics export functionality for monitoring
and observability across the Netra platform.

Business Value Justification (BVJ):
- Segment: Enterprise (observability requirements)
- Business Goal: Platform Stability - prevent downtime through monitoring
- Value Impact: Reduces incident response time from hours to minutes
- Revenue Impact: Prevents $10K+ MRR loss from platform instability
"""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MetricPoint(BaseModel):
    """Individual metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = {}
    timestamp: Optional[float] = None


class PrometheusExporter:
    """Prometheus metrics exporter service."""
    
    def __init__(self):
        """Initialize the prometheus exporter."""
        self._metrics: Dict[str, MetricPoint] = {}
        self._counters: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Record counter metric."""
        key = f"{name}_{hash(str(sorted((labels or {}).items())))}"
        self._counters[key] = self._counters.get(key, 0) + value
        
        self._metrics[key] = MetricPoint(
            name=name,
            value=self._counters[key], 
            labels=labels or {},
            timestamp=time.time()
        )
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record gauge metric."""
        key = f"{name}_{hash(str(sorted((labels or {}).items())))}"
        
        self._metrics[key] = MetricPoint(
            name=name,
            value=value,
            labels=labels or {},
            timestamp=time.time()
        )
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record histogram metric."""
        key = f"{name}_{hash(str(sorted((labels or {}).items())))}"
        
        if key not in self._histograms:
            self._histograms[key] = []
        
        self._histograms[key].append(value)
        
        # Store average as the metric value
        avg_value = sum(self._histograms[key]) / len(self._histograms[key])
        self._metrics[key] = MetricPoint(
            name=name,
            value=avg_value,
            labels=labels or {},
            timestamp=time.time()
        )
    
    def get_metrics(self) -> List[MetricPoint]:
        """Get all recorded metrics."""
        return list(self._metrics.values())
    
    def get_metric(self, name: str) -> Optional[MetricPoint]:
        """Get specific metric by name."""
        for metric in self._metrics.values():
            if metric.name == name:
                return metric
        return None
    
    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()
        self._counters.clear() 
        self._histograms.clear()
    
    def export_text_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        for metric in self._metrics.values():
            labels_str = ""
            if metric.labels:
                labels_list = [f'{k}="{v}"' for k, v in metric.labels.items()]
                labels_str = "{" + ",".join(labels_list) + "}"
            
            lines.append(f"{metric.name}{labels_str} {metric.value}")
        
        return "\n".join(lines)
    
    def record_request_duration(self, method: str, endpoint: str, duration: float) -> None:
        """Record HTTP request duration metric."""
        self.histogram(
            "http_request_duration_seconds",
            duration,
            {"method": method, "endpoint": endpoint}
        )
    
    def record_request_count(self, method: str, endpoint: str, status_code: int) -> None:
        """Record HTTP request count metric."""
        self.counter(
            "http_requests_total",
            1.0,
            {"method": method, "endpoint": endpoint, "status": str(status_code)}
        )
    
    def record_agent_execution(self, agent_type: str, duration: float, success: bool) -> None:
        """Record agent execution metrics."""
        self.histogram(
            "agent_execution_duration_seconds",
            duration,
            {"agent_type": agent_type, "success": str(success).lower()}
        )
        
        self.counter(
            "agent_executions_total",
            1.0,
            {"agent_type": agent_type, "success": str(success).lower()}
        )
    
    def record_database_operation(self, operation: str, table: str, duration: float) -> None:
        """Record database operation metrics."""
        self.histogram(
            "database_operation_duration_seconds",
            duration,
            {"operation": operation, "table": table}
        )
        
        self.counter(
            "database_operations_total",
            1.0,
            {"operation": operation, "table": table}
        )


# Global exporter instance for easy access
prometheus_exporter = PrometheusExporter()


def get_prometheus_exporter() -> PrometheusExporter:
    """Get the global prometheus exporter instance."""
    return prometheus_exporter