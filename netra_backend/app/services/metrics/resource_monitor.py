"""
Resource usage monitoring for corpus operations
Tracks CPU, memory, storage, and network usage during operations
"""

import asyncio
import json
import os
import shutil
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.metrics import (
    ResourceType,
    ResourceUsage,
    TimeSeriesPoint,
)

logger = central_logger.get_logger(__name__)


class ResourceMonitor:
    """Monitors system resource usage during corpus operations"""
    
    def __init__(self, max_buffer_size: int = 1000, sampling_interval: float = 1.0):
        self.max_buffer_size = max_buffer_size
        self.sampling_interval = sampling_interval
        self._resource_history = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self._initialize_monitoring_state()
    
    async def start_monitoring(self):
        """Start continuous resource monitoring"""
        if self._monitoring_active:
            logger.warning("Resource monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started resource monitoring")
    
    async def stop_monitoring(self):
        """Stop continuous resource monitoring"""
        self._monitoring_active = False
        if self._monitor_task:
            await self._cancel_monitoring_task()
        logger.info("Stopped resource monitoring")

    async def _cancel_monitoring_task(self):
        """Cancel and wait for monitoring task"""
        self._monitor_task.cancel()
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                await self._execute_monitoring_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e)
    
    async def _execute_monitoring_cycle(self):
        """Execute single monitoring cycle."""
        await self._collect_resource_metrics()
        await asyncio.sleep(self.sampling_interval)
    
    async def _collect_resource_metrics(self):
        """Collect current resource usage metrics"""
        timestamp = datetime.now(UTC)
        await self._collect_all_metrics(timestamp)

    async def _handle_monitoring_error(self, error: Exception):
        """Handle monitoring loop error"""
        logger.error(f"Error in monitoring loop: {str(error)}")
        await asyncio.sleep(self.sampling_interval)

    async def _collect_cpu_metrics(self, timestamp: datetime):
        """Collect CPU usage metrics"""
        cpu_usage = await self._get_cpu_usage()
        self._store_resource_metric(ResourceType.CPU, cpu_usage, "%", timestamp)

    async def _collect_memory_metrics(self, timestamp: datetime):
        """Collect memory usage metrics"""
        memory_usage = await self._get_memory_usage()
        self._store_resource_metric(ResourceType.MEMORY, memory_usage["percent"], "%", timestamp)

    async def _collect_storage_metrics(self, timestamp: datetime):
        """Collect storage usage metrics"""
        storage_usage = await self._get_storage_usage()
        self._store_resource_metric(ResourceType.STORAGE, storage_usage["percent"], "%", timestamp)

    async def _collect_network_metrics(self, timestamp: datetime):
        """Collect network usage metrics"""
        network_stats = await self._get_network_stats()
        if network_stats:
            self._store_resource_metric(ResourceType.NETWORK, network_stats["bytes_sent"], "bytes", timestamp)
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        return self._build_memory_dict(memory)
    
    async def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage for corpus operations"""
        try:
            app_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            usage = shutil.disk_usage(app_path)
            return self._calculate_storage_metrics(usage)
        except Exception as e:
            logger.error(f"Error getting storage usage: {str(e)}")
            return self._get_default_storage_metrics()

    def _calculate_storage_metrics(self, usage) -> Dict[str, Any]:
        """Calculate storage metrics from usage data"""
        return self._build_storage_dict(usage)

    def _get_default_storage_metrics(self) -> Dict[str, Any]:
        """Get default storage metrics for error case"""
        return {"total": 0, "used": 0, "free": 0, "percent": 0.0}
    
    async def _get_network_stats(self) -> Optional[Dict[str, Any]]:
        """Get basic network statistics"""
        try:
            stats = psutil.net_io_counters()
            return self._build_network_stats(stats)
        except Exception as e:
            logger.error(f"Error getting network stats: {str(e)}")
            return None

    def _build_network_stats(self, stats) -> Dict[str, Any]:
        """Build network statistics dictionary"""
        return self._create_network_dict(stats)
    
    def _store_resource_metric(
        self, 
        resource_type: ResourceType,
        value: float,
        unit: str,
        timestamp: datetime
    ):
        """Store resource metric in history"""
        metric = self._create_resource_usage(resource_type, value, unit, timestamp)
        self._append_metric_to_history(metric, resource_type)

    def _create_resource_usage(
        self,
        resource_type: ResourceType,
        value: float,
        unit: str,
        timestamp: datetime
    ) -> ResourceUsage:
        """Create ResourceUsage object"""
        kwargs = self._build_resource_usage_kwargs(resource_type, value, unit, timestamp)
        return ResourceUsage(**kwargs)

    def _build_resource_usage_kwargs(
        self,
        resource_type: ResourceType,
        value: float,
        unit: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Build ResourceUsage constructor kwargs"""
        base_kwargs = {"resource_type": resource_type, "current_value": value}
        time_kwargs = {"unit": unit, "timestamp": timestamp}
        return {**base_kwargs, **time_kwargs}
    
    async def take_operation_snapshot(self, operation_id: str, corpus_id: str):
        """Take resource snapshot at start of operation"""
        snapshot = await self._create_snapshot(operation_id, corpus_id)
        self._operation_snapshots[operation_id] = snapshot
        logger.debug(f"Took resource snapshot for operation {operation_id}")

    async def _create_snapshot(self, operation_id: str, corpus_id: str) -> Dict[str, Any]:
        """Create resource usage snapshot"""
        base_data = self._build_snapshot_base(operation_id, corpus_id)
        resource_data = await self._collect_snapshot_resources()
        return {**base_data, **resource_data}

    def _build_snapshot_base(self, operation_id: str, corpus_id: str) -> Dict[str, Any]:
        """Build base snapshot data"""
        return {
            "operation_id": operation_id,
            "corpus_id": corpus_id,
            "timestamp": datetime.now(UTC)
        }

    async def _collect_snapshot_resources(self) -> Dict[str, Any]:
        """Collect resource data for snapshot"""
        return {
            "cpu": await self._get_cpu_usage(),
            "memory": await self._get_memory_usage(),
            "storage": await self._get_storage_usage(),
            "network": await self._get_network_stats()
        }
    
    async def calculate_operation_usage(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Calculate resource usage for completed operation"""
        if operation_id not in self._operation_snapshots:
            logger.warning(f"No start snapshot found for operation {operation_id}")
            return None
        start_snapshot = self._operation_snapshots.pop(operation_id)
        end_snapshot = await self._get_current_usage_snapshot()
        return await self._build_usage_delta(operation_id, start_snapshot, end_snapshot)

    async def _get_current_usage_snapshot(self) -> Dict[str, Any]:
        """Get current resource usage snapshot"""
        return await self._collect_snapshot_resources()

    async def _build_usage_delta(self, operation_id: str, start_snapshot: Dict, end_snapshot: Dict) -> Dict[str, Any]:
        """Build usage delta from snapshots"""
        end_time = datetime.now(UTC)
        base_delta = self._build_delta_base(operation_id, start_snapshot, end_time)
        resource_data = await self._build_delta_resources(start_snapshot, end_snapshot, end_time)
        return {**base_delta, **resource_data}

    def _build_delta_base(self, operation_id: str, start_snapshot: Dict, end_time: datetime) -> Dict[str, Any]:
        """Build base delta information"""
        return self._create_delta_base_dict(operation_id, start_snapshot, end_time)

    async def _build_delta_resources(self, start_snapshot: Dict, end_snapshot: Dict, end_time: datetime) -> Dict[str, Any]:
        """Build resource delta information"""
        deltas = self._calculate_deltas(start_snapshot, end_snapshot)
        peak_usage = await self._get_peak_usage_during_operation(start_snapshot["timestamp"], end_time)
        return {"resource_deltas": deltas, "peak_usage": peak_usage}
    
    def _calculate_deltas(self, start: Dict, end: Dict) -> Dict[str, Any]:
        """Calculate resource usage deltas"""
        deltas = {}
        self._add_all_deltas(deltas, start, end)
        return deltas

    def _add_memory_delta(self, deltas: Dict, start: Dict, end: Dict):
        """Add memory usage delta"""
        if start.get("memory") and end.get("memory"):
            deltas["memory_mb"] = (end["memory"]["used"] - start["memory"]["used"]) / (1024 * 1024)

    def _add_storage_delta(self, deltas: Dict, start: Dict, end: Dict):
        """Add storage usage delta"""
        if start.get("storage") and end.get("storage"):
            deltas["storage_mb"] = (end["storage"]["used"] - start["storage"]["used"]) / (1024 * 1024)

    def _add_network_delta(self, deltas: Dict, start: Dict, end: Dict):
        """Add network usage delta"""
        if start.get("network") and end.get("network"):
            self._add_network_sent_delta(deltas, start, end)
            self._add_network_recv_delta(deltas, start, end)
    
    async def _get_peak_usage_during_operation(
        self, 
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """Get peak resource usage during operation timeframe"""
        peaks = {}
        self._process_all_resource_peaks(peaks, start_time, end_time)
        return peaks

    def _calculate_resource_peaks(self, peaks: Dict, resource_type: str, history, start_time: datetime, end_time: datetime):
        """Calculate peak and average for resource type"""
        relevant_metrics = self._filter_metrics_by_time(history, start_time, end_time)
        if relevant_metrics:
            self._add_peak_metrics(peaks, resource_type, relevant_metrics)
    
    def get_resource_time_series(
        self,
        resource_type: ResourceType,
        time_range_minutes: int = 60
    ) -> List[TimeSeriesPoint]:
        """Get time series data for resource usage"""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_range_minutes)
        key = resource_type.value
        points = self._build_time_series_points(resource_type, key, cutoff_time)
        return sorted(points, key=lambda x: x.timestamp)

    def _build_time_series_points(
        self,
        resource_type: ResourceType,
        key: str,
        cutoff_time: datetime
    ) -> List[TimeSeriesPoint]:
        """Build time series points from history"""
        points = []
        self._process_metrics_for_time_series(points, resource_type, key, cutoff_time)
        return points

    def _process_metrics_for_time_series(
        self,
        points: List[TimeSeriesPoint],
        resource_type: ResourceType,
        key: str,
        cutoff_time: datetime
    ) -> None:
        """Process metrics and add valid points to list"""
        for metric in self._resource_history[key]:
            self._add_metric_if_valid(points, resource_type, metric, cutoff_time)

    def _add_metric_if_valid(
        self,
        points: List[TimeSeriesPoint],
        resource_type: ResourceType,
        metric,
        cutoff_time: datetime
    ) -> None:
        """Add metric to points if it meets time criteria"""
        if metric.timestamp >= cutoff_time:
            point = self._create_time_series_point(resource_type, metric)
            points.append(point)

    def _create_time_series_point(self, resource_type: ResourceType, metric) -> TimeSeriesPoint:
        """Create TimeSeriesPoint from metric"""
        tags = {"resource": resource_type.value, "unit": metric.unit}
        return TimeSeriesPoint(timestamp=metric.timestamp, value=metric.current_value, tags=tags)
    
    def get_resource_summary(self, time_range_hours: int = 1) -> Dict[str, Any]:
        """Get resource usage summary"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_range_hours)
        summary = {}
        self._build_all_resource_summaries(summary, cutoff_time)
        return summary

    def _add_resource_summary(self, summary: Dict, resource_type: str, history, cutoff_time: datetime):
        """Add resource summary for specific type"""
        recent_metrics = self._filter_recent_metrics(history, cutoff_time)
        if recent_metrics:
            values = [m.current_value for m in recent_metrics]
            summary[resource_type] = self._build_metrics_summary(recent_metrics, values)

    def _filter_recent_metrics(self, history, cutoff_time: datetime) -> List:
        """Filter metrics within time range"""
        return [metric for metric in history if metric.timestamp >= cutoff_time]

    def _build_metrics_summary(self, recent_metrics: List, values: List) -> Dict[str, Any]:
        """Build metrics summary dictionary"""
        return self._create_summary_dict(recent_metrics, values)
    
    def get_resource_alerts(self, thresholds: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Check for resource usage alerts"""
        if not thresholds:
            thresholds = self._get_default_thresholds()
        alerts = []
        self._check_all_resource_alerts(alerts, thresholds)
        return alerts

    def _get_default_thresholds(self) -> Dict[str, float]:
        """Get default resource thresholds"""
        return {"cpu": 80.0, "memory": 85.0, "storage": 90.0}

    def _check_resource_alert(self, alerts: List, resource_type: str, history, thresholds: Dict):
        """Check and add resource alert if threshold exceeded"""
        if not history:
            return
        latest = list(history)[-1]
        self._add_alert_if_threshold_exceeded(alerts, resource_type, latest, thresholds)

    def _should_create_alert(self, threshold: Optional[float], latest) -> bool:
        """Check if alert should be created"""
        return threshold is not None and latest.current_value > threshold

    def _create_alert(self, resource_type: str, latest, threshold: float) -> Dict[str, Any]:
        """Create alert dictionary"""
        severity = self._calculate_alert_severity(latest.current_value, threshold)
        return self._build_alert_dict(resource_type, latest, threshold, severity)

    def _calculate_alert_severity(self, current_value: float, threshold: float) -> str:
        """Calculate alert severity level"""
        return "high" if current_value > threshold * 1.1 else "medium"

    def _build_alert_dict(
        self,
        resource_type: str,
        latest,
        threshold: float,
        severity: str
    ) -> Dict[str, Any]:
        """Build alert dictionary"""
        alert_components = self._get_alert_components(resource_type, latest, threshold, severity)
        return {**alert_components['base'], **alert_components['meta'], **alert_components['time']}
    
    def _get_alert_components(self, resource_type: str, latest, threshold: float, severity: str) -> Dict[str, Dict[str, Any]]:
        """Get alert dictionary components."""
        base = {"resource": resource_type, "current_value": latest.current_value}
        meta = {"threshold": threshold, "unit": latest.unit}
        time = {"timestamp": latest.timestamp, "severity": severity}
        return {'base': base, 'meta': meta, 'time': time}
    
    def get_monitor_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        basic_status = self._get_basic_status()
        resource_status = self._get_resource_status()
        return {**basic_status, **resource_status}

    def _get_basic_status(self) -> Dict[str, Any]:
        """Get basic monitoring status"""
        return self._build_basic_status_dict()

    def _get_resource_status(self) -> Dict[str, Any]:
        """Get resource monitoring status"""
        return self._build_resource_status_dict()

    def _calculate_total_samples(self) -> int:
        """Calculate total samples across all resources"""
        return sum(len(history) for history in self._resource_history.values())

    def _calculate_buffer_utilization(self) -> Dict[str, float]:
        """Calculate buffer utilization for each resource"""
        return self._build_buffer_utilization_dict()
    
    def _initialize_monitoring_state(self) -> None:
        """Initialize monitoring state variables"""
        self._operation_snapshots = {}
        self._monitoring_active = False
        self._monitor_task = None
    
    async def _collect_all_metrics(self, timestamp: datetime) -> None:
        """Collect all metric types with timestamp"""
        await self._collect_cpu_metrics(timestamp)
        await self._collect_memory_metrics(timestamp)
        await self._collect_storage_metrics(timestamp)
        await self._collect_network_metrics(timestamp)
    
    def _build_memory_dict(self, memory) -> Dict[str, Any]:
        """Build memory usage dictionary"""
        return {"total": memory.total, "available": memory.available, "used": memory.used, "percent": memory.percent}
    
    def _build_storage_dict(self, usage) -> Dict[str, Any]:
        """Build storage usage dictionary"""
        return {"total": usage.total, "used": usage.used, "free": usage.free, "percent": (usage.used / usage.total) * 100}
    
    def _create_network_dict(self, stats) -> Dict[str, Any]:
        """Create network statistics dictionary"""
        return {"bytes_sent": stats.bytes_sent, "bytes_recv": stats.bytes_recv, "packets_sent": stats.packets_sent, "packets_recv": stats.packets_recv}
    
    def _append_metric_to_history(self, metric, resource_type: ResourceType) -> None:
        """Append metric to resource history"""
        key = resource_type.value
        self._resource_history[key].append(metric)
    
    def _create_delta_base_dict(self, operation_id: str, start_snapshot: Dict, end_time: datetime) -> Dict[str, Any]:
        """Create base delta information dictionary"""
        return {"operation_id": operation_id, "corpus_id": start_snapshot["corpus_id"], "start_time": start_snapshot["timestamp"], "end_time": end_time}
    
    def _add_all_deltas(self, deltas: Dict, start: Dict, end: Dict) -> None:
        """Add all delta calculations"""
        self._add_memory_delta(deltas, start, end)
        self._add_storage_delta(deltas, start, end)
        self._add_network_delta(deltas, start, end)
    
    def _add_network_sent_delta(self, deltas: Dict, start: Dict, end: Dict) -> None:
        """Add network sent delta"""
        deltas["network_bytes_sent"] = end["network"]["bytes_sent"] - start["network"]["bytes_sent"]
    
    def _add_network_recv_delta(self, deltas: Dict, start: Dict, end: Dict) -> None:
        """Add network received delta"""
        deltas["network_bytes_recv"] = end["network"]["bytes_recv"] - start["network"]["bytes_recv"]
    
    def _process_all_resource_peaks(self, peaks: Dict, start_time: datetime, end_time: datetime) -> None:
        """Process peaks for all resource types"""
        for resource_type, history in self._resource_history.items():
            self._calculate_resource_peaks(peaks, resource_type, history, start_time, end_time)
    
    def _filter_metrics_by_time(self, history, start_time: datetime, end_time: datetime) -> List:
        """Filter metrics by time range"""
        return [metric for metric in history if start_time <= metric.timestamp <= end_time]
    
    def _add_peak_metrics(self, peaks: Dict, resource_type: str, relevant_metrics: List) -> None:
        """Add peak and average metrics"""
        peaks[f"peak_{resource_type}"] = max(m.current_value for m in relevant_metrics)
        peaks[f"avg_{resource_type}"] = sum(m.current_value for m in relevant_metrics) / len(relevant_metrics)
    
    def _build_all_resource_summaries(self, summary: Dict, cutoff_time: datetime) -> None:
        """Build summaries for all resource types"""
        for resource_type, history in self._resource_history.items():
            self._add_resource_summary(summary, resource_type, history, cutoff_time)
    
    def _create_summary_dict(self, recent_metrics: List, values: List) -> Dict[str, Any]:
        """Create metrics summary dictionary"""
        return {"current": recent_metrics[-1].current_value, "min": min(values), "max": max(values), "avg": sum(values) / len(values), "unit": recent_metrics[-1].unit, "sample_count": len(values)}
    
    def _check_all_resource_alerts(self, alerts: List, thresholds: Dict) -> None:
        """Check alerts for all resource types"""
        for resource_type, history in self._resource_history.items():
            self._check_resource_alert(alerts, resource_type, history, thresholds)
    
    def _add_alert_if_threshold_exceeded(self, alerts: List, resource_type: str, latest, thresholds: Dict) -> None:
        """Add alert if threshold is exceeded"""
        threshold = thresholds.get(resource_type)
        if self._should_create_alert(threshold, latest):
            alerts.append(self._create_alert(resource_type, latest, threshold))
    
    def _build_basic_status_dict(self) -> Dict[str, Any]:
        """Build basic status dictionary"""
        return {"monitoring_active": self._monitoring_active, "sampling_interval": self.sampling_interval, "tracked_resources": list(self._resource_history.keys())}
    
    def _build_resource_status_dict(self) -> Dict[str, Any]:
        """Build resource status dictionary"""
        return {"total_samples": self._calculate_total_samples(), "active_operation_snapshots": len(self._operation_snapshots), "buffer_utilization": self._calculate_buffer_utilization()}
    
    def _build_buffer_utilization_dict(self) -> Dict[str, float]:
        """Build buffer utilization dictionary"""
        return {resource: len(history) / self.max_buffer_size for resource, history in self._resource_history.items()}