"""WebSocket Telemetry Collection and Metrics Management.

Handles real-time telemetry collection, connection metrics, and job tracking
for unified WebSocket state management system.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionMetrics:
    """Connection-level metrics for telemetry."""
    connection_id: str
    user_id: str
    connected_at: float
    last_activity: float
    messages_sent: int
    messages_received: int
    errors: int
    bytes_sent: int
    bytes_received: int


@dataclass
class JobMetrics:
    """Job-level metrics for workflow tracking."""
    job_id: str
    created_at: float
    last_activity: float
    messages_queued: int
    messages_processed: int
    active_connections: int
    completion_status: str  # "active", "completed", "failed", "cancelled"


class TelemetryCollector:
    """Real-time telemetry collection and aggregation."""
    
    def __init__(self) -> None:
        """Initialize telemetry collector with metrics storage."""
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.job_metrics: Dict[str, JobMetrics] = {}
        self.system_metrics = self._initialize_system_metrics()
        self.performance_history: deque = deque(maxlen=1000)

    def _initialize_system_metrics(self) -> Dict[str, Any]:
        """Initialize system metrics dictionary."""
        return {
            "start_time": time.time(), "total_connections": 0, "peak_connections": 0,
            "total_messages": 0, "total_errors": 0, "uptime_seconds": 0.0
        }

    def track_connection(self, conn_info: ConnectionInfo) -> None:
        """Start tracking connection metrics."""
        metrics = self._create_connection_metrics(conn_info)
        self.connection_metrics[conn_info.connection_id] = metrics
        self.system_metrics["total_connections"] += 1
        self._update_peak_connections()

    def _create_connection_metrics(self, conn_info: ConnectionInfo) -> ConnectionMetrics:
        """Create new connection metrics instance."""
        current_time = time.time()
        return ConnectionMetrics(**self._get_connection_metric_args(conn_info, current_time))

    def _get_connection_metric_args(self, conn_info: ConnectionInfo, current_time: float) -> Dict[str, Any]:
        """Get connection metrics constructor arguments."""
        base_args = self._get_base_connection_args(conn_info, current_time)
        counter_args = self._get_connection_counter_args()
        return {**base_args, **counter_args}

    def _get_base_connection_args(self, conn_info: ConnectionInfo, current_time: float) -> Dict[str, Any]:
        """Get base connection arguments."""
        return {
            "connection_id": conn_info.connection_id, "user_id": conn_info.user_id,
            "connected_at": current_time, "last_activity": current_time
        }

    def _get_connection_counter_args(self) -> Dict[str, Any]:
        """Get connection counter arguments."""
        return {
            "messages_sent": 0, "messages_received": 0, "errors": 0,
            "bytes_sent": 0, "bytes_received": 0
        }

    def _update_peak_connections(self) -> None:
        """Update peak connections metric."""
        current_count = len(self.connection_metrics)
        if current_count > self.system_metrics["peak_connections"]:
            self.system_metrics["peak_connections"] = current_count

    def update_connection_activity(self, connection_id: str, message_type: str, byte_count: int = 0) -> None:
        """Update connection activity metrics."""
        if connection_id not in self.connection_metrics:
            return
        metrics = self.connection_metrics[connection_id]
        metrics.last_activity = time.time()
        self._update_activity_metrics(metrics, message_type, byte_count)

    def _update_activity_metrics(self, metrics: ConnectionMetrics, message_type: str, byte_count: int) -> None:
        """Update specific activity metrics based on message type."""
        if message_type == "sent":
            metrics.messages_sent += 1
            metrics.bytes_sent += byte_count
        elif message_type == "received":
            metrics.messages_received += 1
            metrics.bytes_received += byte_count
        elif message_type == "error":
            metrics.errors += 1

    def track_job(self, job_id: str) -> None:
        """Start tracking job metrics."""
        metrics = self._create_job_metrics(job_id)
        self.job_metrics[job_id] = metrics

    def _create_job_metrics(self, job_id: str) -> JobMetrics:
        """Create new job metrics instance."""
        current_time = time.time()
        return JobMetrics(**self._get_job_metric_args(job_id, current_time))

    def _get_job_metric_args(self, job_id: str, current_time: float) -> Dict[str, Any]:
        """Get job metrics constructor arguments."""
        base_args = self._get_base_job_args(job_id, current_time)
        counter_args = self._get_job_counter_args()
        return {**base_args, **counter_args}

    def _get_base_job_args(self, job_id: str, current_time: float) -> Dict[str, Any]:
        """Get base job arguments."""
        return {
            "job_id": job_id, "created_at": current_time,
            "last_activity": current_time, "completion_status": "active"
        }

    def _get_job_counter_args(self) -> Dict[str, Any]:
        """Get job counter arguments."""
        return {"messages_queued": 0, "messages_processed": 0, "active_connections": 0}

    def update_job_activity(self, job_id: str, activity_type: str, count: int = 1) -> None:
        """Update job activity metrics."""
        if job_id not in self.job_metrics:
            self.track_job(job_id)
        metrics = self.job_metrics[job_id]
        metrics.last_activity = time.time()
        self._update_job_metrics(metrics, activity_type, count)

    def _update_job_metrics(self, metrics: JobMetrics, activity_type: str, count: int) -> None:
        """Update specific job metrics based on activity type."""
        if activity_type == "queued":
            metrics.messages_queued += count
        elif activity_type == "processed":
            metrics.messages_processed += count
        elif activity_type == "connection_count":
            metrics.active_connections = count

    def record_performance_sample(self, sample_data: Dict[str, float]) -> None:
        """Record performance sample for trending analysis."""
        sample_with_timestamp = {**sample_data, "timestamp": time.time()}
        self.performance_history.append(sample_with_timestamp)

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Get current telemetry snapshot."""
        self._update_system_metrics()
        return {
            "system_metrics": self.system_metrics.copy(),
            "connection_summary": self._get_connection_summary(),
            "job_summary": self._get_job_summary(),
            "performance_trends": self._get_performance_trends()
        }

    def _update_system_metrics(self) -> None:
        """Update calculated system metrics."""
        self.system_metrics["uptime_seconds"] = time.time() - self.system_metrics["start_time"]
        self.system_metrics["active_connections"] = len(self.connection_metrics)

    def _get_connection_summary(self) -> Dict[str, Any]:
        """Get summarized connection metrics."""
        if not self.connection_metrics:
            return {"active": 0, "total_messages": 0, "total_errors": 0}
        return self._calculate_connection_totals()

    def _calculate_connection_totals(self) -> Dict[str, Any]:
        """Calculate total connection metrics."""
        message_totals = self._calculate_message_totals()
        return self._build_connection_summary(message_totals)
    
    def _calculate_message_totals(self) -> Dict[str, int]:
        """Calculate aggregate message totals from all connections."""
        metrics_values = self.connection_metrics.values()
        return {
            "sent": sum(m.messages_sent for m in metrics_values),
            "received": sum(m.messages_received for m in metrics_values),
            "errors": sum(m.errors for m in metrics_values)
        }
    
    def _build_connection_summary(self, message_totals: Dict[str, int]) -> Dict[str, Any]:
        """Build connection summary dictionary with totals."""
        return {
            "active": len(self.connection_metrics),
            "total_messages_sent": message_totals["sent"],
            "total_messages_received": message_totals["received"],
            "total_errors": message_totals["errors"]
        }

    def _get_job_summary(self) -> Dict[str, Any]:
        """Get summarized job metrics."""
        if not self.job_metrics:
            return {"active_jobs": 0, "completed_jobs": 0}
        active_jobs = sum(1 for m in self.job_metrics.values() if m.completion_status == "active")
        completed_jobs = sum(1 for m in self.job_metrics.values() if m.completion_status == "completed")
        return {"active_jobs": active_jobs, "completed_jobs": completed_jobs, "total_jobs": len(self.job_metrics)}

    def _get_performance_trends(self) -> List[Dict[str, Any]]:
        """Get recent performance trend data."""
        return list(self.performance_history)[-10:]  # Last 10 samples