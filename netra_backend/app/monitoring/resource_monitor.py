"""
Resource Monitor

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System stability & cost optimization
- Value Impact: Prevents resource exhaustion and improves system reliability
- Strategic Impact: Enables proactive resource management and cost control

Implements comprehensive resource monitoring with limit detection and alerting.
"""

import asyncio
import gc
import os
import platform
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import threading
try:
    import resource
except ImportError:
    # resource module not available on Windows
    resource = None

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ResourceStatus(Enum):
    """Resource status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class ResourceType(Enum):
    """Types of resources to monitor."""
    MEMORY = "memory"
    CPU = "cpu"
    DISK_IO = "disk_io"
    NETWORK = "network"
    FILE_DESCRIPTORS = "file_descriptors"
    THREADS = "threads"


@dataclass
class ResourceThresholds:
    """Resource usage thresholds."""
    warning_threshold: float = 75.0  # Percentage
    critical_threshold: float = 90.0  # Percentage
    exhaustion_threshold: float = 98.0  # Percentage


@dataclass
class ResourceAlert:
    """Resource alert information."""
    resource_type: ResourceType
    status: ResourceStatus
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""


@dataclass
class ResourceMetrics:
    """Current resource usage metrics."""
    # Memory metrics
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    
    # CPU metrics
    cpu_percent: float = 0.0
    cpu_count: int = 0
    load_average: List[float] = field(default_factory=list)
    
    # Disk I/O metrics
    disk_read_mb_per_sec: float = 0.0
    disk_write_mb_per_sec: float = 0.0
    disk_io_percent: float = 0.0
    
    # Network metrics
    network_bytes_sent_per_sec: float = 0.0
    network_bytes_recv_per_sec: float = 0.0
    network_connections: int = 0
    
    # System limits
    file_descriptors_used: int = 0
    file_descriptors_limit: int = 0
    file_descriptors_percent: float = 0.0
    
    # Process metrics
    threads_count: int = 0
    process_memory_mb: float = 0.0
    process_cpu_percent: float = 0.0
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MonitorConfig:
    """Configuration for resource monitor."""
    collection_interval_seconds: int = 5
    alert_cooldown_seconds: int = 60
    enable_gc_monitoring: bool = True
    enable_io_monitoring: bool = True
    enable_network_monitoring: bool = True
    thresholds: Dict[ResourceType, ResourceThresholds] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default thresholds if not provided."""
        if not self.thresholds:
            self.thresholds = {
                ResourceType.MEMORY: ResourceThresholds(75.0, 90.0, 98.0),
                ResourceType.CPU: ResourceThresholds(80.0, 95.0, 99.0),
                ResourceType.DISK_IO: ResourceThresholds(70.0, 85.0, 95.0),
                ResourceType.NETWORK: ResourceThresholds(75.0, 90.0, 98.0),
                ResourceType.FILE_DESCRIPTORS: ResourceThresholds(80.0, 95.0, 99.0),
                ResourceType.THREADS: ResourceThresholds(75.0, 90.0, 98.0)
            }


class ResourceMonitor:
    """Monitors system resource usage with alerting."""
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        """Initialize resource monitor."""
        self.config = config or MonitorConfig()
        
        # Current metrics
        self.current_metrics = ResourceMetrics()
        self.previous_metrics: Optional[ResourceMetrics] = None
        
        # Alert management
        self.active_alerts: Dict[ResourceType, ResourceAlert] = {}
        self.alert_callbacks: List[Callable[[ResourceAlert], None]] = []
        self.last_alert_times: Dict[ResourceType, float] = {}
        
        # Monitoring tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self.stats = {
            'measurements_taken': 0,
            'alerts_triggered': 0,
            'gc_collections': 0,
            'peak_memory_mb': 0.0,
            'peak_cpu_percent': 0.0,
            'peak_file_descriptors': 0
        }
        
        # Initialize system information
        self._init_system_info()
    
    def _init_system_info(self) -> None:
        """Initialize system information."""
        try:
            self.current_metrics.cpu_count = psutil.cpu_count()
            
            # Get system limits
            try:
                if resource:
                    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
                    self.current_metrics.file_descriptors_limit = soft_limit
                else:
                    # Default for Windows
                    self.current_metrics.file_descriptors_limit = 2048
            except Exception as e:
                logger.warning(f"Could not get file descriptor limit: {e}")
                self.current_metrics.file_descriptors_limit = 1024  # Reasonable default
            
            logger.info(f"System info - CPUs: {self.current_metrics.cpu_count}, FD limit: {self.current_metrics.file_descriptors_limit}")
            
        except Exception as e:
            logger.error(f"Failed to initialize system info: {e}")
    
    async def start(self) -> None:
        """Start resource monitoring."""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Take initial measurement
        await self._collect_metrics()
        
        logger.info("Resource monitor started")
    
    async def stop(self) -> None:
        """Stop resource monitoring."""
        self._shutdown = True
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Resource monitor stopped")
    
    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Add callback for resource alerts."""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Remove alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown:
            try:
                await self._collect_metrics()
                await self._check_thresholds()
                await asyncio.sleep(self.config.collection_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _collect_metrics(self) -> None:
        """Collect current resource metrics."""
        try:
            # Store previous metrics for rate calculations
            self.previous_metrics = self.current_metrics
            new_metrics = ResourceMetrics()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            new_metrics.memory_percent = memory.percent
            new_metrics.memory_used_mb = memory.used / (1024 * 1024)
            new_metrics.memory_available_mb = memory.available / (1024 * 1024)
            
            # CPU metrics
            new_metrics.cpu_percent = psutil.cpu_percent(interval=None)
            new_metrics.cpu_count = self.current_metrics.cpu_count
            
            try:
                new_metrics.load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                # getloadavg not available on Windows
                new_metrics.load_average = []
            
            # Process-specific metrics
            process = psutil.Process()
            new_metrics.process_memory_mb = process.memory_info().rss / (1024 * 1024)
            new_metrics.process_cpu_percent = process.cpu_percent()
            new_metrics.threads_count = process.num_threads()
            
            # File descriptors
            try:
                new_metrics.file_descriptors_used = process.num_fds()
                new_metrics.file_descriptors_limit = self.current_metrics.file_descriptors_limit
                if new_metrics.file_descriptors_limit > 0:
                    new_metrics.file_descriptors_percent = (
                        new_metrics.file_descriptors_used / new_metrics.file_descriptors_limit * 100
                    )
            except Exception:
                # num_fds not available on Windows
                new_metrics.file_descriptors_used = 0
                new_metrics.file_descriptors_percent = 0.0
            
            # I/O metrics
            if self.config.enable_io_monitoring:
                await self._collect_io_metrics(new_metrics)
            
            # Network metrics
            if self.config.enable_network_monitoring:
                await self._collect_network_metrics(new_metrics)
            
            self.current_metrics = new_metrics
            self.stats['measurements_taken'] += 1
            
            # Update peak values
            self._update_peak_stats()
            
            # Garbage collection monitoring
            if self.config.enable_gc_monitoring:
                self._check_garbage_collection()
            
        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")
    
    async def _collect_io_metrics(self, metrics: ResourceMetrics) -> None:
        """Collect I/O metrics."""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io and self.previous_metrics:
                time_diff = (metrics.timestamp - self.previous_metrics.timestamp).total_seconds()
                if time_diff > 0:
                    # Calculate rates
                    prev_disk = psutil.disk_io_counters()  # This is a cumulative counter
                    
                    # For now, just store raw values
                    # In a real implementation, you'd calculate rates from previous values
                    metrics.disk_read_mb_per_sec = 0.0
                    metrics.disk_write_mb_per_sec = 0.0
                    
                    # Estimate I/O percentage (simplified)
                    # This would need proper implementation based on system capabilities
                    metrics.disk_io_percent = min(95.0, (metrics.disk_read_mb_per_sec + metrics.disk_write_mb_per_sec) / 10)
                    
        except Exception as e:
            logger.debug(f"Could not collect I/O metrics: {e}")
    
    async def _collect_network_metrics(self, metrics: ResourceMetrics) -> None:
        """Collect network metrics."""
        try:
            net_io = psutil.net_io_counters()
            if net_io and self.previous_metrics:
                time_diff = (metrics.timestamp - self.previous_metrics.timestamp).total_seconds()
                if time_diff > 0:
                    # For now, just store raw values
                    # In a real implementation, you'd calculate rates from previous values
                    metrics.network_bytes_sent_per_sec = 0.0
                    metrics.network_bytes_recv_per_sec = 0.0
            
            # Count active network connections
            try:
                connections = psutil.net_connections()
                metrics.network_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            except (psutil.AccessDenied, OSError):
                metrics.network_connections = 0
                
        except Exception as e:
            logger.debug(f"Could not collect network metrics: {e}")
    
    def _update_peak_stats(self) -> None:
        """Update peak statistics."""
        self.stats['peak_memory_mb'] = max(
            self.stats['peak_memory_mb'],
            self.current_metrics.memory_used_mb
        )
        
        self.stats['peak_cpu_percent'] = max(
            self.stats['peak_cpu_percent'],
            self.current_metrics.cpu_percent
        )
        
        self.stats['peak_file_descriptors'] = max(
            self.stats['peak_file_descriptors'],
            self.current_metrics.file_descriptors_used
        )
    
    def _check_garbage_collection(self) -> None:
        """Check and possibly trigger garbage collection."""
        gc_counts = gc.get_count()
        
        # Trigger GC if generation 0 has too many objects
        if gc_counts[0] > 1000:
            collected = gc.collect()
            self.stats['gc_collections'] += 1
            
            if collected > 0:
                logger.debug(f"Garbage collected {collected} objects")
    
    async def _check_thresholds(self) -> None:
        """Check resource usage against thresholds."""
        current_time = time.time()
        
        # Memory check
        await self._check_resource_threshold(
            ResourceType.MEMORY,
            self.current_metrics.memory_percent,
            current_time,
            f"Memory usage: {self.current_metrics.memory_percent:.1f}%"
        )
        
        # CPU check
        await self._check_resource_threshold(
            ResourceType.CPU,
            self.current_metrics.cpu_percent,
            current_time,
            f"CPU usage: {self.current_metrics.cpu_percent:.1f}%"
        )
        
        # File descriptors check
        await self._check_resource_threshold(
            ResourceType.FILE_DESCRIPTORS,
            self.current_metrics.file_descriptors_percent,
            current_time,
            f"File descriptors: {self.current_metrics.file_descriptors_used}/{self.current_metrics.file_descriptors_limit} ({self.current_metrics.file_descriptors_percent:.1f}%)"
        )
        
        # Disk I/O check
        if self.config.enable_io_monitoring:
            await self._check_resource_threshold(
                ResourceType.DISK_IO,
                self.current_metrics.disk_io_percent,
                current_time,
                f"Disk I/O: {self.current_metrics.disk_io_percent:.1f}%"
            )
    
    async def _check_resource_threshold(
        self,
        resource_type: ResourceType,
        current_value: float,
        current_time: float,
        message: str
    ) -> None:
        """Check specific resource against thresholds."""
        thresholds = self.config.thresholds.get(resource_type)
        if not thresholds:
            return
        
        # Determine status
        status = ResourceStatus.NORMAL
        threshold_value = 0.0
        
        if current_value >= thresholds.exhaustion_threshold:
            status = ResourceStatus.EXHAUSTED
            threshold_value = thresholds.exhaustion_threshold
        elif current_value >= thresholds.critical_threshold:
            status = ResourceStatus.CRITICAL
            threshold_value = thresholds.critical_threshold
        elif current_value >= thresholds.warning_threshold:
            status = ResourceStatus.WARNING
            threshold_value = thresholds.warning_threshold
        
        # Check if we should alert
        existing_alert = self.active_alerts.get(resource_type)
        last_alert_time = self.last_alert_times.get(resource_type, 0)
        
        if status != ResourceStatus.NORMAL:
            # Should we alert?
            should_alert = (
                existing_alert is None or  # No existing alert
                existing_alert.status != status or  # Status changed
                (current_time - last_alert_time) > self.config.alert_cooldown_seconds  # Cooldown expired
            )
            
            if should_alert:
                alert = ResourceAlert(
                    resource_type=resource_type,
                    status=status,
                    current_value=current_value,
                    threshold=threshold_value,
                    message=message
                )
                
                self.active_alerts[resource_type] = alert
                self.last_alert_times[resource_type] = current_time
                self.stats['alerts_triggered'] += 1
                
                # Send alert
                await self._send_alert(alert)
                
        else:
            # Resource returned to normal
            if existing_alert:
                del self.active_alerts[resource_type]
                logger.info(f"Resource {resource_type.value} returned to normal: {message}")
    
    async def _send_alert(self, alert: ResourceAlert) -> None:
        """Send resource alert to callbacks."""
        log_message = f"Resource {alert.resource_type.value} {alert.status.value}: {alert.message}"
        
        if alert.status == ResourceStatus.EXHAUSTED:
            logger.error(log_message)
        elif alert.status == ResourceStatus.CRITICAL:
            logger.error(log_message)
        elif alert.status == ResourceStatus.WARNING:
            logger.warning(log_message)
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics."""
        return self.current_metrics
    
    def get_active_alerts(self) -> Dict[ResourceType, ResourceAlert]:
        """Get currently active alerts."""
        return self.active_alerts.copy()
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            'measurements_taken': self.stats['measurements_taken'],
            'alerts_triggered': self.stats['alerts_triggered'],
            'active_alerts': len(self.active_alerts),
            'gc_collections': self.stats['gc_collections'],
            'peaks': {
                'memory_mb': self.stats['peak_memory_mb'],
                'cpu_percent': self.stats['peak_cpu_percent'],
                'file_descriptors': self.stats['peak_file_descriptors']
            },
            'current_metrics': {
                'memory_percent': self.current_metrics.memory_percent,
                'cpu_percent': self.current_metrics.cpu_percent,
                'file_descriptors_percent': self.current_metrics.file_descriptors_percent,
                'threads_count': self.current_metrics.threads_count
            }
        }
    
    def is_resource_healthy(self, resource_type: ResourceType) -> bool:
        """Check if specific resource is healthy."""
        return resource_type not in self.active_alerts
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        total_resources = len(ResourceType)
        healthy_resources = sum(1 for rt in ResourceType if self.is_resource_healthy(rt))
        
        health_percentage = (healthy_resources / total_resources) * 100
        
        overall_status = ResourceStatus.NORMAL
        if len(self.active_alerts) > 0:
            # Get worst status
            statuses = [alert.status for alert in self.active_alerts.values()]
            if ResourceStatus.EXHAUSTED in statuses:
                overall_status = ResourceStatus.EXHAUSTED
            elif ResourceStatus.CRITICAL in statuses:
                overall_status = ResourceStatus.CRITICAL
            elif ResourceStatus.WARNING in statuses:
                overall_status = ResourceStatus.WARNING
        
        return {
            'overall_status': overall_status.value,
            'health_percentage': health_percentage,
            'healthy_resources': healthy_resources,
            'total_resources': total_resources,
            'active_alerts': len(self.active_alerts),
            'system_info': {
                'cpu_count': self.current_metrics.cpu_count,
                'memory_total_mb': self.current_metrics.memory_used_mb + self.current_metrics.memory_available_mb,
                'fd_limit': self.current_metrics.file_descriptors_limit
            }
        }


# Global resource monitor instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor(config: Optional[MonitorConfig] = None) -> ResourceMonitor:
    """Get global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor(config)
    return _resource_monitor


async def check_system_resources() -> Dict[str, Any]:
    """Convenience function to check system resource status."""
    monitor = get_resource_monitor()
    return monitor.get_system_health_summary()


def add_resource_alert_callback(callback: Callable[[ResourceAlert], None]) -> None:
    """Convenience function to add resource alert callback."""
    monitor = get_resource_monitor()
    monitor.add_alert_callback(callback)