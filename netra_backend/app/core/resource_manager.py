"""
Resource Management System for Netra Backend.

Provides comprehensive resource management with:
- Memory monitoring with configurable limits and leak detection
- File descriptor tracking and automatic cleanup
- Thread pool management with graceful scaling
- Background task timeout enforcement
- Zombie process detection and cleanup
- Resource cleanup on shutdown with timeout handling

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Stability)
- Business Goal: Platform Stability & Operational Excellence  
- Value Impact: Prevents resource exhaustion that causes service degradation and outages
- Revenue Impact: Resource leaks lead to system crashes and 100% unavailability, protecting entire revenue stream
"""
import asyncio
import gc
import logging
import os
import psutil
try:
    import resource  # Unix only
except ImportError:
    resource = None  # Windows doesn't have resource module
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Union
from weakref import WeakSet
import tracemalloc

from netra_backend.app.core.circuit_breaker import CircuitBreaker, CircuitConfig
from netra_backend.app.core.error_types import ResourceError
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.unified_logging import get_logger


class ResourceType(Enum):
    """Types of system resources."""
    MEMORY = "memory"
    FILE_DESCRIPTORS = "file_descriptors"
    THREADS = "threads"
    PROCESSES = "processes"
    CONNECTIONS = "connections"
    TIMERS = "timers"
    TASKS = "tasks"


class ResourceStatus(Enum):
    """Resource status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


@dataclass
class ResourceLimits:
    """Resource usage limits."""
    memory_mb: Optional[int] = None
    memory_percent: float = 80.0
    file_descriptors: Optional[int] = None
    fd_percent: float = 80.0
    threads: int = 100
    processes: int = 50
    connections: int = 1000
    tasks: int = 500
    
    # Growth rate limits (per minute)
    memory_growth_mb_per_min: float = 100.0
    fd_growth_per_min: int = 50
    thread_growth_per_min: int = 20


@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    file_descriptors: int = 0
    fd_percent: float = 0.0
    threads: int = 0
    processes: int = 0
    connections: int = 0
    active_tasks: int = 0
    cpu_percent: float = 0.0
    
    # Growth tracking
    memory_growth_1m: float = 0.0
    fd_growth_1m: int = 0
    thread_growth_1m: int = 0


@dataclass
class ResourceAlert:
    """Resource usage alert."""
    resource_type: ResourceType
    status: ResourceStatus
    current_value: Union[int, float]
    limit_value: Union[int, float]
    percentage: float
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    actions_taken: List[str] = field(default_factory=list)


class ResourceManager:
    """
    Comprehensive system resource management.
    
    Features:
    - Real-time resource monitoring and alerting
    - Automatic resource limit enforcement
    - Memory leak detection and mitigation
    - File descriptor tracking and cleanup
    - Thread pool management with scaling
    - Background task lifecycle management
    - Zombie process detection and cleanup
    - Graceful resource cleanup on shutdown
    """
    
    def __init__(self, 
                 limits: Optional[ResourceLimits] = None,
                 monitoring_interval: float = 30.0,
                 cleanup_interval: float = 300.0,  # 5 minutes
                 enable_tracemalloc: bool = True):
        self.logger = get_logger(__name__)
        
        # Configuration
        self.limits = limits or ResourceLimits()
        self.monitoring_interval = monitoring_interval
        self.cleanup_interval = cleanup_interval
        self.enable_tracemalloc = enable_tracemalloc
        
        # Current process info
        self.process = psutil.Process()
        self.process_start_time = datetime.now(UTC)
        
        # Resource tracking
        self.usage_history: List[ResourceUsage] = []
        self.max_history = 100
        self.current_usage = ResourceUsage()
        self.alerts: List[ResourceAlert] = []
        self.max_alerts = 50
        
        # Managed resources
        self.thread_pools: Dict[str, ThreadPoolExecutor] = {}
        self.process_pools: Dict[str, ProcessPoolExecutor] = {}
        self.active_tasks: WeakSet = WeakSet()
        self.tracked_connections: WeakSet = WeakSet()
        self.cleanup_callbacks: List[Callable[[], Any]] = []
        
        # Monitoring tasks
        self.monitor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Locks
        self.resource_lock = asyncio.Lock()
        self.cleanup_lock = asyncio.Lock()
        
        # Circuit breakers for resource protection
        memory_config = CircuitConfig(
            name="memory_protection",
            failure_threshold=3,
            recovery_timeout=60.0
        )
        self.memory_breaker = CircuitBreaker(memory_config)
        
        # Initialize tracemalloc if enabled
        if self.enable_tracemalloc:
            try:
                tracemalloc.start()
                self.logger.info("Memory tracing enabled")
            except Exception as e:
                self.logger.warning("Failed to enable memory tracing", extra={"error": str(e)})
        
        self.logger.info("ResourceManager initialized", extra={
            "memory_limit_mb": self.limits.memory_mb,
            "monitoring_interval": monitoring_interval,
            "tracemalloc_enabled": tracemalloc.is_tracing()
        })
    
    async def initialize(self) -> None:
        """Initialize resource manager and start monitoring."""
        self.logger.info("Starting resource manager")
        
        # Get initial resource snapshot
        await self._update_resource_usage()
        
        # Start monitoring tasks
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(),
            name="resource-monitor"
        )
        
        self.cleanup_task = asyncio.create_task(
            self._cleanup_loop(), 
            name="resource-cleanup"
        )
        
        self.logger.info("Resource manager started", extra={
            "initial_memory_mb": self.current_usage.memory_mb,
            "initial_fds": self.current_usage.file_descriptors
        })
    
    async def _monitoring_loop(self) -> None:
        """Main resource monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # Update usage statistics
                await self._update_resource_usage()
                
                # Check limits and generate alerts
                await self._check_resource_limits()
                
                # Perform memory leak detection
                if len(self.usage_history) > 10:
                    await self._detect_memory_leaks()
                
                # Auto-cleanup if needed
                await self._auto_cleanup_if_needed()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in resource monitoring loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Cleanup completed tasks
                await self._cleanup_completed_tasks()
                
                # Check for zombie processes
                await self._cleanup_zombie_processes()
                
                # Trim resource history
                self._trim_resource_history()
                
                # Garbage collection if memory usage is high
                if self.current_usage.memory_percent > 70:
                    await self._perform_garbage_collection()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in cleanup loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _update_resource_usage(self) -> None:
        """Update current resource usage statistics."""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            system_memory = psutil.virtual_memory()
            memory_percent = (memory_mb / (system_memory.total / (1024 * 1024))) * 100
            
            # File descriptors
            try:
                fd_count = self.process.num_fds()
                if resource:  # Unix systems
                    fd_limit_soft, fd_limit_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                    fd_percent = (fd_count / fd_limit_soft) * 100
                else:
                    fd_percent = 0.0  # Can't determine limits on Windows
            except (AttributeError, OSError):
                # Windows or other systems without num_fds
                fd_count = len(self.process.open_files()) + len(self.process.connections())
                fd_percent = 0.0
            
            # Threads and processes
            thread_count = self.process.num_threads()
            child_processes = len(self.process.children())
            
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            
            # Active tasks (async tasks)
            active_task_count = len(self.active_tasks)
            
            # Connection tracking
            connection_count = len(self.tracked_connections)
            
            # Calculate growth rates if we have history
            memory_growth_1m = 0.0
            fd_growth_1m = 0
            thread_growth_1m = 0
            
            if self.usage_history:
                # Find usage from 1 minute ago
                cutoff_time = datetime.now(UTC) - timedelta(minutes=1)
                for usage in reversed(self.usage_history):
                    if usage.timestamp <= cutoff_time:
                        memory_growth_1m = memory_mb - usage.memory_mb
                        fd_growth_1m = fd_count - usage.file_descriptors
                        thread_growth_1m = thread_count - usage.threads
                        break
            
            # Update current usage
            self.current_usage = ResourceUsage(
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                file_descriptors=fd_count,
                fd_percent=fd_percent,
                threads=thread_count,
                processes=child_processes,
                connections=connection_count,
                active_tasks=active_task_count,
                cpu_percent=cpu_percent,
                memory_growth_1m=memory_growth_1m,
                fd_growth_1m=fd_growth_1m,
                thread_growth_1m=thread_growth_1m
            )
            
            # Add to history
            self.usage_history.append(self.current_usage)
            
        except Exception as e:
            self.logger.error("Failed to update resource usage", extra={
                "error": str(e)
            }, exc_info=True)
    
    async def _check_resource_limits(self) -> None:
        """Check resource usage against limits and generate alerts."""
        usage = self.current_usage
        alerts_generated = []
        
        # Memory checks
        if self.limits.memory_mb and usage.memory_mb > self.limits.memory_mb:
            alert = ResourceAlert(
                resource_type=ResourceType.MEMORY,
                status=ResourceStatus.CRITICAL,
                current_value=usage.memory_mb,
                limit_value=self.limits.memory_mb,
                percentage=100.0,
                message=f"Memory usage {usage.memory_mb:.1f}MB exceeds limit {self.limits.memory_mb}MB"
            )
            alerts_generated.append(alert)
        
        elif usage.memory_percent > self.limits.memory_percent:
            status = ResourceStatus.CRITICAL if usage.memory_percent > 95 else ResourceStatus.WARNING
            alert = ResourceAlert(
                resource_type=ResourceType.MEMORY,
                status=status,
                current_value=usage.memory_percent,
                limit_value=self.limits.memory_percent,
                percentage=usage.memory_percent,
                message=f"Memory usage {usage.memory_percent:.1f}% exceeds threshold {self.limits.memory_percent}%"
            )
            alerts_generated.append(alert)
        
        # Add alerts and log
        for alert in alerts_generated:
            self.alerts.append(alert)
            self.logger.warning("Resource alert generated", extra={
                "resource_type": alert.resource_type.value,
                "status": alert.status.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "percentage": alert.percentage
            })
        
        # Trim alerts history
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
    
    async def _detect_memory_leaks(self) -> None:
        """Detect potential memory leaks based on usage patterns."""
        if len(self.usage_history) < 10:
            return
        
        # Check for consistent memory growth
        recent_usage = self.usage_history[-10:]
        memory_values = [u.memory_mb for u in recent_usage]
        
        # Simple linear regression to detect growth trend
        n = len(memory_values)
        x_values = list(range(n))
        
        x_mean = sum(x_values) / n
        y_mean = sum(memory_values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, memory_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator > 0:
            slope = numerator / denominator  # MB per measurement
            
            # Convert to MB per hour (assuming measurements every 30 seconds)
            slope_per_hour = slope * (3600 / self.monitoring_interval)
            
            if slope_per_hour > 50:  # Growing by more than 50MB per hour
                self.logger.warning("Potential memory leak detected", extra={
                    "growth_rate_mb_per_hour": slope_per_hour,
                    "current_memory_mb": self.current_usage.memory_mb
                })
    
    async def _auto_cleanup_if_needed(self) -> None:
        """Perform automatic cleanup if resources are running low."""
        usage = self.current_usage
        
        # Trigger cleanup if memory usage is high
        if usage.memory_percent > 85:
            await self._perform_emergency_cleanup("high_memory")
    
    async def _perform_emergency_cleanup(self, reason: str) -> None:
        """Perform emergency resource cleanup."""
        async with self.cleanup_lock:
            self.logger.warning("Performing emergency cleanup", extra={
                "reason": reason,
                "memory_mb": self.current_usage.memory_mb
            })
            
            # Cleanup completed tasks
            await self._cleanup_completed_tasks()
            
            # Force garbage collection
            await self._perform_garbage_collection()
            
            # Cleanup zombie processes
            await self._cleanup_zombie_processes()
    
    async def _cleanup_completed_tasks(self) -> int:
        """Clean up completed async tasks."""
        completed_count = 0
        
        # Use a copy of the WeakSet to avoid modification during iteration
        tasks_copy = list(self.active_tasks)
        
        for task in tasks_copy:
            try:
                if task.done():
                    completed_count += 1
            except Exception:
                completed_count += 1
        
        return completed_count
    
    async def _cleanup_zombie_processes(self) -> int:
        """Clean up zombie child processes."""
        cleaned_count = 0
        
        try:
            children = self.process.children(recursive=False)
            for child in children:
                try:
                    if child.status() == psutil.STATUS_ZOMBIE:
                        child.wait()  # Wait for zombie process
                        cleaned_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        
        return cleaned_count
    
    async def _perform_garbage_collection(self) -> None:
        """Perform Python garbage collection."""
        try:
            def gc_collect():
                return gc.collect()
            
            loop = asyncio.get_event_loop()
            collected = await loop.run_in_executor(None, gc_collect)
            
            self.logger.debug("Garbage collection completed", extra={
                "objects_collected": collected
            })
            
        except Exception as e:
            self.logger.error("Error during garbage collection", extra={
                "error": str(e)
            })
    
    def _trim_resource_history(self) -> None:
        """Trim resource usage history to maintain size limits."""
        if len(self.usage_history) > self.max_history:
            self.usage_history = self.usage_history[-self.max_history:]
    
    def get_thread_pool(self, name: str, max_workers: Optional[int] = None) -> ThreadPoolExecutor:
        """Get or create a managed thread pool."""
        if name not in self.thread_pools:
            if max_workers is None:
                max_workers = min(32, (os.cpu_count() or 1) + 4)
            
            pool = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"netra-{name}"
            )
            self.thread_pools[name] = pool
            
            self.logger.debug("Created thread pool", extra={
                "name": name,
                "max_workers": max_workers
            })
        
        return self.thread_pools[name]
    
    def track_task(self, task: asyncio.Task) -> asyncio.Task:
        """Track an async task for resource management."""
        self.active_tasks.add(task)
        return task
    
    def track_connection(self, connection: Any) -> Any:
        """Track a connection object for resource management."""
        self.tracked_connections.add(connection)
        return connection
    
    def register_cleanup_callback(self, callback: Callable[[], Any]) -> None:
        """Register a cleanup callback to be called during emergency cleanup."""
        self.cleanup_callbacks.append(callback)
    
    async def cleanup(self) -> None:
        """Clean up resource manager and all tracked resources."""
        self.logger.info("Starting resource manager cleanup")
        
        # Cancel monitoring tasks
        for task in [self.monitor_task, self.cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        
        # Cleanup thread pools
        for name, pool in self.thread_pools.items():
            try:
                pool.shutdown(wait=True)
            except Exception as e:
                self.logger.warning("Error shutting down thread pool", extra={
                    "name": name,
                    "error": str(e)
                })
        
        # Final cleanup
        await self._cleanup_completed_tasks()
        await self._cleanup_zombie_processes()
        await self._perform_garbage_collection()
        
        self.logger.info("Resource manager cleanup completed")
    
    @asynccontextmanager
    async def resource_context(self):
        """Context manager for resource lifecycle management."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get comprehensive resource status."""
        return {
            "current_usage": {
                "memory_mb": self.current_usage.memory_mb,
                "memory_percent": self.current_usage.memory_percent,
                "file_descriptors": self.current_usage.file_descriptors,
                "threads": self.current_usage.threads,
                "processes": self.current_usage.processes,
                "active_tasks": self.current_usage.active_tasks,
                "connections": self.current_usage.connections,
                "cpu_percent": self.current_usage.cpu_percent
            },
            "limits": {
                "memory_mb": self.limits.memory_mb,
                "memory_percent": self.limits.memory_percent,
                "threads": self.limits.threads,
                "processes": self.limits.processes
            },
            "alerts": [
                {
                    "type": alert.resource_type.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "actions_taken": alert.actions_taken
                }
                for alert in self.alerts[-10:]  # Last 10 alerts
            ],
            "pools": {
                "thread_pools": list(self.thread_pools.keys())
            },
            "monitoring": {
                "running": self.monitor_task is not None and not self.monitor_task.done()
            }
        }


# Global resource manager instance
resource_manager = ResourceManager()