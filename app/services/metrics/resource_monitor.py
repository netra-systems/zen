"""
Resource usage monitoring for corpus operations
Tracks CPU, memory, storage, and network usage during operations
"""

import asyncio
import psutil
import os
import shutil
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
import json

from app.logging_config import central_logger
from app.schemas.Metrics import (
    ResourceUsage, ResourceType, TimeSeriesPoint
)

logger = central_logger.get_logger(__name__)


class ResourceMonitor:
    """Monitors system resource usage during corpus operations"""
    
    def __init__(self, max_buffer_size: int = 1000, sampling_interval: float = 1.0):
        self.max_buffer_size = max_buffer_size
        self.sampling_interval = sampling_interval
        self._resource_history = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self._operation_snapshots = {}
        self._monitoring_active = False
        self._monitor_task = None
    
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
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped resource monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                await self._collect_resource_metrics()
                await asyncio.sleep(self.sampling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.sampling_interval)
    
    async def _collect_resource_metrics(self):
        """Collect current resource usage metrics"""
        timestamp = datetime.now(UTC)
        
        # CPU metrics
        cpu_usage = await self._get_cpu_usage()
        self._store_resource_metric(ResourceType.CPU, cpu_usage, "%", timestamp)
        
        # Memory metrics
        memory_usage = await self._get_memory_usage()
        self._store_resource_metric(ResourceType.MEMORY, memory_usage["percent"], "%", timestamp)
        
        # Storage metrics
        storage_usage = await self._get_storage_usage()
        self._store_resource_metric(ResourceType.STORAGE, storage_usage["percent"], "%", timestamp)
        
        # Network metrics (optional, basic implementation)
        network_stats = await self._get_network_stats()
        if network_stats:
            self._store_resource_metric(ResourceType.NETWORK, network_stats["bytes_sent"], "bytes", timestamp)
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }
    
    async def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage for corpus operations"""
        try:
            # Get usage for app directory
            app_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            usage = shutil.disk_usage(app_path)
            
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": (usage.used / usage.total) * 100
            }
        except Exception as e:
            logger.error(f"Error getting storage usage: {str(e)}")
            return {"total": 0, "used": 0, "free": 0, "percent": 0.0}
    
    async def _get_network_stats(self) -> Optional[Dict[str, Any]]:
        """Get basic network statistics"""
        try:
            stats = psutil.net_io_counters()
            return {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
        except Exception as e:
            logger.error(f"Error getting network stats: {str(e)}")
            return None
    
    def _store_resource_metric(
        self, 
        resource_type: ResourceType,
        value: float,
        unit: str,
        timestamp: datetime
    ):
        """Store resource metric in history"""
        metric = ResourceUsage(
            resource_type=resource_type,
            current_value=value,
            unit=unit,
            timestamp=timestamp
        )
        
        key = resource_type.value
        self._resource_history[key].append(metric)
    
    async def take_operation_snapshot(self, operation_id: str, corpus_id: str):
        """Take resource snapshot at start of operation"""
        snapshot = {
            "operation_id": operation_id,
            "corpus_id": corpus_id,
            "timestamp": datetime.now(UTC),
            "cpu": await self._get_cpu_usage(),
            "memory": await self._get_memory_usage(),
            "storage": await self._get_storage_usage(),
            "network": await self._get_network_stats()
        }
        
        self._operation_snapshots[operation_id] = snapshot
        logger.debug(f"Took resource snapshot for operation {operation_id}")
    
    async def calculate_operation_usage(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Calculate resource usage for completed operation"""
        if operation_id not in self._operation_snapshots:
            logger.warning(f"No start snapshot found for operation {operation_id}")
            return None
        
        start_snapshot = self._operation_snapshots.pop(operation_id)
        end_snapshot = {
            "cpu": await self._get_cpu_usage(),
            "memory": await self._get_memory_usage(),
            "storage": await self._get_storage_usage(),
            "network": await self._get_network_stats()
        }
        
        usage_delta = {
            "operation_id": operation_id,
            "corpus_id": start_snapshot["corpus_id"],
            "start_time": start_snapshot["timestamp"],
            "end_time": datetime.now(UTC),
            "resource_deltas": self._calculate_deltas(start_snapshot, end_snapshot),
            "peak_usage": await self._get_peak_usage_during_operation(
                start_snapshot["timestamp"], datetime.now(UTC)
            )
        }
        
        return usage_delta
    
    def _calculate_deltas(self, start: Dict, end: Dict) -> Dict[str, Any]:
        """Calculate resource usage deltas"""
        deltas = {}
        
        # Memory delta
        if start.get("memory") and end.get("memory"):
            deltas["memory_mb"] = (end["memory"]["used"] - start["memory"]["used"]) / (1024 * 1024)
        
        # Storage delta
        if start.get("storage") and end.get("storage"):
            deltas["storage_mb"] = (end["storage"]["used"] - start["storage"]["used"]) / (1024 * 1024)
        
        # Network delta
        if start.get("network") and end.get("network"):
            deltas["network_bytes_sent"] = end["network"]["bytes_sent"] - start["network"]["bytes_sent"]
            deltas["network_bytes_recv"] = end["network"]["bytes_recv"] - start["network"]["bytes_recv"]
        
        return deltas
    
    async def _get_peak_usage_during_operation(
        self, 
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """Get peak resource usage during operation timeframe"""
        peaks = {}
        
        for resource_type, history in self._resource_history.items():
            relevant_metrics = [
                metric for metric in history
                if start_time <= metric.timestamp <= end_time
            ]
            
            if relevant_metrics:
                peaks[f"peak_{resource_type}"] = max(m.current_value for m in relevant_metrics)
                peaks[f"avg_{resource_type}"] = sum(m.current_value for m in relevant_metrics) / len(relevant_metrics)
        
        return peaks
    
    def get_resource_time_series(
        self,
        resource_type: ResourceType,
        time_range_minutes: int = 60
    ) -> List[TimeSeriesPoint]:
        """Get time series data for resource usage"""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_range_minutes)
        key = resource_type.value
        
        points = []
        for metric in self._resource_history[key]:
            if metric.timestamp >= cutoff_time:
                points.append(TimeSeriesPoint(
                    timestamp=metric.timestamp,
                    value=metric.current_value,
                    tags={"resource": resource_type.value, "unit": metric.unit}
                ))
        
        return sorted(points, key=lambda x: x.timestamp)
    
    def get_resource_summary(self, time_range_hours: int = 1) -> Dict[str, Any]:
        """Get resource usage summary"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_range_hours)
        summary = {}
        
        for resource_type, history in self._resource_history.items():
            recent_metrics = [
                metric for metric in history
                if metric.timestamp >= cutoff_time
            ]
            
            if recent_metrics:
                values = [m.current_value for m in recent_metrics]
                summary[resource_type] = {
                    "current": recent_metrics[-1].current_value,
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "unit": recent_metrics[-1].unit,
                    "sample_count": len(values)
                }
        
        return summary
    
    def get_resource_alerts(self, thresholds: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Check for resource usage alerts"""
        if not thresholds:
            thresholds = {
                "cpu": 80.0,
                "memory": 85.0,
                "storage": 90.0
            }
        
        alerts = []
        current_time = datetime.now(UTC)
        
        for resource_type, history in self._resource_history.items():
            if not history:
                continue
            
            latest = list(history)[-1]
            threshold = thresholds.get(resource_type)
            
            if threshold and latest.current_value > threshold:
                alerts.append({
                    "resource": resource_type,
                    "current_value": latest.current_value,
                    "threshold": threshold,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp,
                    "severity": "high" if latest.current_value > threshold * 1.1 else "medium"
                })
        
        return alerts
    
    def get_monitor_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            "monitoring_active": self._monitoring_active,
            "sampling_interval": self.sampling_interval,
            "tracked_resources": list(self._resource_history.keys()),
            "total_samples": sum(len(history) for history in self._resource_history.values()),
            "active_operation_snapshots": len(self._operation_snapshots),
            "buffer_utilization": {
                resource: len(history) / self.max_buffer_size
                for resource, history in self._resource_history.items()
            }
        }