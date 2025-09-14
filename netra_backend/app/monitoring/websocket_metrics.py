"""
WebSocket Metrics Module

This module provides comprehensive metrics collection for WebSocket events
and notifications, focusing on per-user isolation and factory-based tracking.

BUSINESS VALUE:
- Track event delivery success rates per user
- Monitor connection pool health per user context
- Measure queue sizes and processing times
- Identify bottlenecks in event delivery
- Support SLA monitoring and alerting

CRITICAL METRICS:
1. Event Delivery Metrics (per user)
   - Events sent/received/failed
   - Delivery latency percentiles
   - Success rates by event type
   
2. Connection Pool Metrics (per factory instance)
   - Active connections per user
   - Connection lifetime and reuse
   - Connection errors and recoveries
   
3. Queue Metrics (per user context)
   - Queue sizes and depths
   - Processing rates
   - Backpressure indicators
   
4. Factory Performance Metrics
   - Factory creation rate
   - Resource utilization per factory
   - Isolation boundary violations (should be 0)
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from enum import Enum
import threading

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class EventMetrics:
    """Metrics for WebSocket event delivery."""
    events_sent: int = 0
    events_received: int = 0
    events_failed: int = 0
    events_retried: int = 0
    
    # Latency tracking (in milliseconds)
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # Event type breakdown
    events_by_type: Dict[str, int] = field(default_factory=dict)
    failures_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Timestamps
    first_event_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    
    def record_event(self, event_type: str, latency_ms: float, success: bool = True):
        """Record an event delivery attempt."""
        now = datetime.now(timezone.utc)
        
        if not self.first_event_time:
            self.first_event_time = now
        self.last_event_time = now
        
        if success:
            self.events_sent += 1
            self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
            self.latencies.append(latency_ms)
        else:
            self.events_failed += 1
            self.failures_by_type[event_type] = self.failures_by_type.get(event_type, 0) + 1
            self.last_failure_time = now
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Calculate latency percentiles."""
        if not self.latencies:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.5)],
            "p90": sorted_latencies[int(n * 0.9)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)]
        }
    
    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self.events_sent + self.events_failed
        if total == 0:
            return 100.0
        return (self.events_sent / total) * 100


@dataclass
class ConnectionPoolMetrics:
    """Metrics for WebSocket connection pools."""
    active_connections: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    connection_errors: int = 0
    
    # Connection lifetime tracking
    connection_lifetimes: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Resource tracking
    max_connections_seen: int = 0
    connection_reuse_count: int = 0
    
    # Health indicators
    last_error_time: Optional[datetime] = None
    consecutive_errors: int = 0
    
    def record_connection_created(self):
        """Record a new connection creation."""
        self.active_connections += 1
        self.total_connections_created += 1
        if self.active_connections > self.max_connections_seen:
            self.max_connections_seen = self.active_connections
        self.consecutive_errors = 0  # Reset on success
    
    def record_connection_closed(self, lifetime_seconds: float):
        """Record a connection closure."""
        self.active_connections = max(0, self.active_connections - 1)
        self.total_connections_closed += 1
        self.connection_lifetimes.append(lifetime_seconds)
    
    def record_connection_error(self):
        """Record a connection error."""
        self.connection_errors += 1
        self.consecutive_errors += 1
        self.last_error_time = datetime.now(timezone.utc)
    
    def get_health_status(self) -> str:
        """Determine connection pool health."""
        if self.consecutive_errors >= 5:
            return "critical"
        elif self.consecutive_errors >= 3:
            return "degraded"
        elif self.active_connections == 0 and self.total_connections_created > 0:
            return "warning"
        return "healthy"


@dataclass
class QueueMetrics:
    """Metrics for event queues."""
    current_size: int = 0
    max_size_seen: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    
    # Processing time tracking
    processing_times: deque = field(default_factory=lambda: deque(maxlen=500))
    
    # Backpressure indicators
    backpressure_events: int = 0
    last_backpressure_time: Optional[datetime] = None
    
    def record_enqueue(self, queue_size: int):
        """Record an enqueue operation."""
        self.current_size = queue_size
        self.total_enqueued += 1
        if queue_size > self.max_size_seen:
            self.max_size_seen = queue_size
    
    def record_dequeue(self, processing_time_ms: float):
        """Record a dequeue operation."""
        self.current_size = max(0, self.current_size - 1)
        self.total_dequeued += 1
        self.processing_times.append(processing_time_ms)
    
    def record_backpressure(self):
        """Record a backpressure event."""
        self.backpressure_events += 1
        self.last_backpressure_time = datetime.now(timezone.utc)
    
    def get_processing_rate(self, window_seconds: int = 60) -> float:
        """Calculate processing rate (events/second)."""
        # Simplified rate calculation
        if window_seconds <= 0:
            return 0.0
        return self.total_dequeued / window_seconds


@dataclass
class ManagerMetrics:
    """Metrics for individual WebSocket manager instances."""
    connections_managed: int = 0
    messages_sent_total: int = 0
    messages_failed_total: int = 0
    last_activity: Optional[datetime] = None
    manager_age_seconds: float = 0.0
    cleanup_scheduled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "connections_managed": self.connections_managed,
            "messages_sent_total": self.messages_sent_total,
            "messages_failed_total": self.messages_failed_total,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "manager_age_seconds": self.manager_age_seconds,
            "cleanup_scheduled": self.cleanup_scheduled
        }


@dataclass
class FactoryMetrics:
    """Metrics for WebSocket factory instances."""
    factories_created: int = 0
    factories_destroyed: int = 0
    active_factories: int = 0
    
    # Resource tracking
    total_memory_mb: float = 0.0
    total_cpu_percent: float = 0.0
    
    # Isolation tracking (should always be 0)
    isolation_violations: int = 0
    cross_user_events: int = 0
    
    # Creation rate tracking
    creation_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "factories_created": self.factories_created,
            "factories_destroyed": self.factories_destroyed,
            "active_factories": self.active_factories,
            "total_memory_mb": self.total_memory_mb,
            "total_cpu_percent": self.total_cpu_percent,
            "isolation_violations": self.isolation_violations,
            "cross_user_events": self.cross_user_events
        }
    
    def record_factory_created(self):
        """Record factory creation."""
        self.factories_created += 1
        self.active_factories += 1
        self.creation_times.append(datetime.now(timezone.utc))
    
    def record_factory_destroyed(self):
        """Record factory destruction."""
        self.factories_destroyed += 1
        self.active_factories = max(0, self.active_factories - 1)
    
    def record_isolation_violation(self):
        """Record an isolation boundary violation (critical issue)."""
        self.isolation_violations += 1
        logger.error("CRITICAL: WebSocket factory isolation violation detected!")
    
    def get_creation_rate(self, window_minutes: int = 5) -> float:
        """Calculate factory creation rate."""
        if not self.creation_times:
            return 0.0
        
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        recent_creations = sum(1 for t in self.creation_times if t > cutoff)
        return recent_creations / window_minutes


class WebSocketMetricsCollector:
    """
    Central metrics collector for WebSocket monitoring.
    
    Provides per-user metric isolation and factory-based tracking.
    Thread-safe for concurrent access from multiple factories.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Per-user metrics
        self._user_event_metrics: Dict[str, EventMetrics] = {}
        self._user_connection_metrics: Dict[str, ConnectionPoolMetrics] = {}
        self._user_queue_metrics: Dict[str, QueueMetrics] = {}
        
        # Global factory metrics
        self._factory_metrics = FactoryMetrics()
        
        # System-wide metrics
        self._system_start_time = datetime.now(timezone.utc)
        self._total_users_seen: Set[str] = set()
        
        logger.info("WebSocketMetricsCollector initialized")
    
    def get_or_create_user_metrics(self, user_id: str) -> tuple:
        """Get or create metrics for a user."""
        with self._lock:
            if user_id not in self._user_event_metrics:
                self._user_event_metrics[user_id] = EventMetrics()
                self._user_connection_metrics[user_id] = ConnectionPoolMetrics()
                self._user_queue_metrics[user_id] = QueueMetrics()
                self._total_users_seen.add(user_id)
                logger.debug(f"Created metrics for user: {user_id}")
            
            return (
                self._user_event_metrics[user_id],
                self._user_connection_metrics[user_id],
                self._user_queue_metrics[user_id]
            )
    
    def record_event_sent(self, user_id: str, event_type: str, latency_ms: float, success: bool = True):
        """Record an event being sent to a user."""
        event_metrics, _, _ = self.get_or_create_user_metrics(user_id)
        with self._lock:
            event_metrics.record_event(event_type, latency_ms, success)
    
    def record_connection_created(self, user_id: str):
        """Record a new connection for a user."""
        _, conn_metrics, _ = self.get_or_create_user_metrics(user_id)
        with self._lock:
            conn_metrics.record_connection_created()
    
    def record_connection_closed(self, user_id: str, lifetime_seconds: float):
        """Record a connection closure."""
        _, conn_metrics, _ = self.get_or_create_user_metrics(user_id)
        with self._lock:
            conn_metrics.record_connection_closed(lifetime_seconds)
    
    def record_connection_error(self, user_id: str):
        """Record a connection error."""
        _, conn_metrics, _ = self.get_or_create_user_metrics(user_id)
        with self._lock:
            conn_metrics.record_connection_error()
    
    def record_queue_operation(self, user_id: str, operation: str, **kwargs):
        """Record a queue operation."""
        _, _, queue_metrics = self.get_or_create_user_metrics(user_id)
        with self._lock:
            if operation == "enqueue":
                queue_metrics.record_enqueue(kwargs.get("queue_size", 0))
            elif operation == "dequeue":
                queue_metrics.record_dequeue(kwargs.get("processing_time_ms", 0))
            elif operation == "backpressure":
                queue_metrics.record_backpressure()
    
    def record_factory_created(self):
        """Record factory creation."""
        with self._lock:
            self._factory_metrics.record_factory_created()
    
    def record_factory_destroyed(self):
        """Record factory destruction."""
        with self._lock:
            self._factory_metrics.record_factory_destroyed()
    
    def record_isolation_violation(self):
        """Record an isolation violation (critical)."""
        with self._lock:
            self._factory_metrics.record_isolation_violation()
    
    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get all metrics for a specific user."""
        event_metrics, conn_metrics, queue_metrics = self.get_or_create_user_metrics(user_id)
        
        with self._lock:
            return {
                "user_id": user_id,
                "events": {
                    "sent": event_metrics.events_sent,
                    "failed": event_metrics.events_failed,
                    "success_rate": event_metrics.get_success_rate(),
                    "latency_percentiles": event_metrics.get_latency_percentiles(),
                    "by_type": dict(event_metrics.events_by_type),
                    "failures_by_type": dict(event_metrics.failures_by_type),
                    "last_event_time": event_metrics.last_event_time.isoformat() if event_metrics.last_event_time else None
                },
                "connections": {
                    "active": conn_metrics.active_connections,
                    "total_created": conn_metrics.total_connections_created,
                    "total_closed": conn_metrics.total_connections_closed,
                    "errors": conn_metrics.connection_errors,
                    "health": conn_metrics.get_health_status(),
                    "max_seen": conn_metrics.max_connections_seen
                },
                "queues": {
                    "current_size": queue_metrics.current_size,
                    "max_size": queue_metrics.max_size_seen,
                    "total_processed": queue_metrics.total_dequeued,
                    "backpressure_events": queue_metrics.backpressure_events,
                    "processing_rate": queue_metrics.get_processing_rate()
                }
            }
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get factory-level metrics."""
        with self._lock:
            return {
                "factories": {
                    "created": self._factory_metrics.factories_created,
                    "destroyed": self._factory_metrics.factories_destroyed,
                    "active": self._factory_metrics.active_factories,
                    "creation_rate_per_min": self._factory_metrics.get_creation_rate()
                },
                "isolation": {
                    "violations": self._factory_metrics.isolation_violations,
                    "cross_user_events": self._factory_metrics.cross_user_events
                },
                "resources": {
                    "memory_mb": self._factory_metrics.total_memory_mb,
                    "cpu_percent": self._factory_metrics.total_cpu_percent
                }
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        with self._lock:
            total_events = sum(m.events_sent + m.events_failed for m in self._user_event_metrics.values())
            total_connections = sum(m.active_connections for m in self._user_connection_metrics.values())
            
            # Calculate system-wide success rate
            total_sent = sum(m.events_sent for m in self._user_event_metrics.values())
            total_failed = sum(m.events_failed for m in self._user_event_metrics.values())
            system_success_rate = (total_sent / (total_sent + total_failed) * 100) if (total_sent + total_failed) > 0 else 100.0
            
            return {
                "uptime_hours": (datetime.now(timezone.utc) - self._system_start_time).total_seconds() / 3600,
                "total_users": len(self._total_users_seen),
                "active_users": len([m for m in self._user_event_metrics.values() if m.events_sent > 0]),
                "total_events": total_events,
                "total_connections": total_connections,
                "system_success_rate": system_success_rate,
                "factory_metrics": self.get_factory_metrics()
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics snapshot."""
        with self._lock:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": self.get_system_metrics(),
                "users": {
                    user_id: self.get_user_metrics(user_id)
                    for user_id in list(self._user_event_metrics.keys())[:100]  # Limit for API response
                }
            }
    
    def clear_user_metrics(self, user_id: str):
        """Clear metrics for a specific user (for cleanup)."""
        with self._lock:
            self._user_event_metrics.pop(user_id, None)
            self._user_connection_metrics.pop(user_id, None)
            self._user_queue_metrics.pop(user_id, None)
            logger.debug(f"Cleared metrics for user: {user_id}")
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            # System metrics
            system = self.get_system_metrics()
            lines.append(f'# HELP websocket_uptime_hours WebSocket system uptime in hours')
            lines.append(f'# TYPE websocket_uptime_hours gauge')
            lines.append(f'websocket_uptime_hours {system["uptime_hours"]:.2f}')
            
            lines.append(f'# HELP websocket_total_users Total unique users seen')
            lines.append(f'# TYPE websocket_total_users counter')
            lines.append(f'websocket_total_users {system["total_users"]}')
            
            lines.append(f'# HELP websocket_active_users Currently active users')
            lines.append(f'# TYPE websocket_active_users gauge')
            lines.append(f'websocket_active_users {system["active_users"]}')
            
            lines.append(f'# HELP websocket_total_events Total events processed')
            lines.append(f'# TYPE websocket_total_events counter')
            lines.append(f'websocket_total_events {system["total_events"]}')
            
            lines.append(f'# HELP websocket_success_rate System-wide success rate')
            lines.append(f'# TYPE websocket_success_rate gauge')
            lines.append(f'websocket_success_rate {system["system_success_rate"]:.2f}')
            
            # Factory metrics
            factory = self._factory_metrics
            lines.append(f'# HELP websocket_factories_active Active factory instances')
            lines.append(f'# TYPE websocket_factories_active gauge')
            lines.append(f'websocket_factories_active {factory.active_factories}')
            
            lines.append(f'# HELP websocket_isolation_violations Factory isolation violations')
            lines.append(f'# TYPE websocket_isolation_violations counter')
            lines.append(f'websocket_isolation_violations {factory.isolation_violations}')
            
            # Per-user metrics (aggregated)
            for user_id, event_metrics in list(self._user_event_metrics.items())[:10]:  # Limit for export
                safe_user_id = user_id.replace("-", "_")
                lines.append(f'websocket_user_events_sent{{user="{safe_user_id}"}} {event_metrics.events_sent}')
                lines.append(f'websocket_user_events_failed{{user="{safe_user_id}"}} {event_metrics.events_failed}')
                lines.append(f'websocket_user_success_rate{{user="{safe_user_id}"}} {event_metrics.get_success_rate():.2f}')
        
        return "\n".join(lines)


# Global metrics collector instance
_metrics_collector: Optional[WebSocketMetricsCollector] = None
_metrics_lock = threading.Lock()


def get_websocket_metrics_collector() -> WebSocketMetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = WebSocketMetricsCollector()
                logger.info("Created global WebSocketMetricsCollector")
    
    return _metrics_collector


def reset_metrics_collector():
    """Reset the metrics collector (for testing)."""
    global _metrics_collector
    with _metrics_lock:
        _metrics_collector = None
        logger.info("Reset WebSocketMetricsCollector")


# Convenience functions for metric recording

def record_websocket_event(user_id: str, event_type: str, latency_ms: float, success: bool = True):
    """Record a WebSocket event."""
    collector = get_websocket_metrics_collector()
    collector.record_event_sent(user_id, event_type, latency_ms, success)


def record_websocket_connection(user_id: str, event: str, **kwargs):
    """Record WebSocket connection events."""
    collector = get_websocket_metrics_collector()
    
    if event == "created":
        collector.record_connection_created(user_id)
    elif event == "closed":
        collector.record_connection_closed(user_id, kwargs.get("lifetime_seconds", 0))
    elif event == "error":
        collector.record_connection_error(user_id)


def record_websocket_queue(user_id: str, operation: str, **kwargs):
    """Record WebSocket queue operations."""
    collector = get_websocket_metrics_collector()
    collector.record_queue_operation(user_id, operation, **kwargs)


def record_factory_event(event: str):
    """Record factory lifecycle events."""
    collector = get_websocket_metrics_collector()
    
    if event == "created":
        collector.record_factory_created()
    elif event == "destroyed":
        collector.record_factory_destroyed()
    elif event == "isolation_violation":
        collector.record_isolation_violation()


def get_user_websocket_metrics(user_id: str) -> Dict[str, Any]:
    """Get metrics for a specific user."""
    collector = get_websocket_metrics_collector()
    return collector.get_user_metrics(user_id)


def get_all_websocket_metrics() -> Dict[str, Any]:
    """Get all WebSocket metrics."""
    collector = get_websocket_metrics_collector()
    return collector.get_all_metrics()


def export_metrics_prometheus() -> str:
    """Export metrics in Prometheus format."""
    collector = get_websocket_metrics_collector()
    return collector.export_prometheus_metrics()