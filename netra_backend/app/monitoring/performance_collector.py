"""Performance Collector for Issue #966

Provides response time tracking, throughput measurement, and resource monitoring
for the monitoring API endpoints. Integrates with existing performance monitoring
infrastructure while following SSOT patterns.

Business Value:
- Enables real-time performance monitoring through API endpoints
- Provides data for performance optimization decisions
- Supports SLO/SLI tracking for platform reliability
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

from shared.logging.unified_logging_ssot import get_logger
from dev_launcher.isolated_environment import IsolatedEnvironment

logger = get_logger(__name__)


@dataclass
class ResponseTimeMetrics:
    """Response time statistics."""
    mean_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    count: int = 0


@dataclass
class ThroughputMetrics:
    """Throughput measurement data."""
    requests_per_second: float = 0.0
    requests_per_minute: float = 0.0
    total_requests_1h: int = 0
    peak_rps: float = 0.0
    avg_rps_1h: float = 0.0


@dataclass
class ResourceMetrics:
    """System resource utilization."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    active_connections: int = 0
    thread_count: int = 0
    disk_usage_percent: float = 0.0


class PerformanceCollector:
    """
    Collects and aggregates performance metrics for API endpoints.
    
    Features:
    - Response time tracking with percentiles
    - Throughput measurement (RPS)
    - Resource utilization monitoring
    - Real-time health score calculation
    - Integration with existing performance infrastructure
    """
    
    def __init__(self, window_size: int = 1000, retention_hours: int = 24):
        """Initialize performance collector.
        
        Args:
            window_size: Maximum number of response time samples to keep
            retention_hours: Hours to retain performance data
        """
        self.window_size = window_size
        self.retention_hours = retention_hours
        
        # Response time tracking
        self.response_times = deque(maxlen=window_size)
        self.response_time_buckets = defaultdict(list)
        
        # Throughput tracking
        self.request_timestamps = deque(maxlen=window_size * 5)
        self.throughput_history = deque(maxlen=60)  # 1 hour of minute samples
        
        # Resource tracking
        self.resource_history = deque(maxlen=60)  # 1 hour of samples
        
        # Health tracking
        self.error_count = 0
        self.success_count = 0
        
        # Background collection
        self._collection_task: Optional[asyncio.Task] = None
        self._is_collecting = False
        
        logger.info("PerformanceCollector initialized")
    
    async def start_collection(self):
        """Start background metric collection."""
        if self._is_collecting:
            logger.warning("Performance collection already started")
            return
        
        self._is_collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started performance collection background task")
    
    async def stop_collection(self):
        """Stop background metric collection."""
        self._is_collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped performance collection")
    
    async def _collection_loop(self):
        """Background loop for periodic metric collection."""
        while self._is_collecting:
            try:
                # Collect resource metrics every 10 seconds
                await self._collect_resource_metrics()
                
                # Calculate throughput every minute
                if len(self.resource_history) % 6 == 0:  # Every 60 seconds
                    await self._calculate_throughput()
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance collection loop: {e}")
                await asyncio.sleep(5)
    
    async def record_request(self, endpoint: str, response_time_ms: float, 
                           status_code: int = 200):
        """Record a request's performance metrics.
        
        Args:
            endpoint: API endpoint name
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
        """
        timestamp = time.time()
        
        # Record response time
        self.response_times.append((timestamp, response_time_ms))
        self.response_time_buckets[endpoint].append(response_time_ms)
        
        # Record request timestamp for throughput calculation
        self.request_timestamps.append(timestamp)
        
        # Track success/error counts
        if 200 <= status_code < 400:
            self.success_count += 1
        else:
            self.error_count += 1
    
    async def _collect_resource_metrics(self):
        """Collect system resource utilization metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            memory_percent = memory.percent
            
            # Thread count
            try:
                process = psutil.Process()
                thread_count = process.num_threads()
            except:
                thread_count = 0
            
            # Disk usage
            try:
                disk = psutil.disk_usage('/')
                disk_usage_percent = disk.percent
            except:
                disk_usage_percent = 0.0
            
            # Database connections (try to get from existing monitoring)
            active_connections = await self._get_active_connections()
            
            resource_metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                active_connections=active_connections,
                thread_count=thread_count,
                disk_usage_percent=disk_usage_percent
            )
            
            self.resource_history.append((time.time(), resource_metrics))
            
        except Exception as e:
            logger.warning(f"Failed to collect resource metrics: {e}")
    
    async def _get_active_connections(self) -> int:
        """Get active database connections from existing monitoring."""
        try:
            from netra_backend.app.services.database.connection_monitor import connection_metrics
            pool_status = connection_metrics.get_pool_status()
            
            async_pool = pool_status.get("async_pool", {})
            sync_pool = pool_status.get("sync_pool", {})
            
            active_async = async_pool.get("checked_out", 0)
            active_sync = sync_pool.get("checked_out", 0)
            
            return active_async + active_sync
            
        except Exception:
            return 0
    
    async def _calculate_throughput(self):
        """Calculate throughput metrics."""
        current_time = time.time()
        
        # Count requests in last minute
        minute_ago = current_time - 60
        requests_last_minute = sum(
            1 for timestamp in self.request_timestamps 
            if timestamp > minute_ago
        )
        
        rps = requests_last_minute / 60.0
        self.throughput_history.append((current_time, rps))
    
    def _calculate_response_time_percentiles(self) -> ResponseTimeMetrics:
        """Calculate response time percentiles from recent samples."""
        if not self.response_times:
            return ResponseTimeMetrics()
        
        # Get recent response times (last 5 minutes)
        current_time = time.time()
        recent_cutoff = current_time - 300  # 5 minutes
        
        recent_times = [
            rt for timestamp, rt in self.response_times 
            if timestamp > recent_cutoff
        ]
        
        if not recent_times:
            return ResponseTimeMetrics()
        
        sorted_times = sorted(recent_times)
        count = len(sorted_times)
        
        return ResponseTimeMetrics(
            mean_ms=sum(sorted_times) / count,
            p50_ms=sorted_times[count // 2],
            p95_ms=sorted_times[int(count * 0.95)] if count > 20 else sorted_times[-1],
            p99_ms=sorted_times[int(count * 0.99)] if count > 100 else sorted_times[-1],
            min_ms=min(sorted_times),
            max_ms=max(sorted_times),
            count=count
        )
    
    def _calculate_throughput_summary(self) -> ThroughputMetrics:
        """Calculate throughput summary from recent data."""
        if not self.throughput_history:
            return ThroughputMetrics()
        
        current_time = time.time()
        
        # Get most recent RPS
        latest_rps = self.throughput_history[-1][1] if self.throughput_history else 0.0
        
        # Calculate peak RPS in last hour
        hour_ago = current_time - 3600
        recent_rps = [
            rps for timestamp, rps in self.throughput_history 
            if timestamp > hour_ago
        ]
        
        peak_rps = max(recent_rps) if recent_rps else 0.0
        avg_rps = sum(recent_rps) / len(recent_rps) if recent_rps else 0.0
        
        # Count total requests in last hour
        hour_requests = sum(
            1 for timestamp in self.request_timestamps 
            if timestamp > hour_ago
        )
        
        return ThroughputMetrics(
            requests_per_second=latest_rps,
            requests_per_minute=latest_rps * 60,
            total_requests_1h=hour_requests,
            peak_rps=peak_rps,
            avg_rps_1h=avg_rps
        )
    
    def _calculate_resource_summary(self) -> ResourceMetrics:
        """Calculate resource utilization summary."""
        if not self.resource_history:
            return ResourceMetrics()
        
        # Get most recent resource metrics
        latest_metrics = self.resource_history[-1][1]
        
        return latest_metrics
    
    def _calculate_health_score(self) -> float:
        """Calculate overall performance health score (0-100)."""
        score = 100.0
        
        # Response time health (40% of score)
        response_metrics = self._calculate_response_time_percentiles()
        if response_metrics.count > 0:
            # Penalize if p95 > 1000ms (1 second)
            if response_metrics.p95_ms > 1000:
                score -= 20
            elif response_metrics.p95_ms > 500:
                score -= 10
            
            # Penalize if p99 > 2000ms
            if response_metrics.p99_ms > 2000:
                score -= 20
        
        # Error rate health (30% of score)
        total_requests = self.success_count + self.error_count
        if total_requests > 0:
            error_rate = self.error_count / total_requests
            if error_rate > 0.05:  # 5% error rate
                score -= 30
            elif error_rate > 0.01:  # 1% error rate
                score -= 15
        
        # Resource health (30% of score)
        resource_metrics = self._calculate_resource_summary()
        if resource_metrics.cpu_percent > 90:
            score -= 15
        elif resource_metrics.cpu_percent > 80:
            score -= 10
        
        if resource_metrics.memory_percent > 90:
            score -= 15
        elif resource_metrics.memory_percent > 80:
            score -= 10
        
        return max(0.0, score)
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary for API endpoint.
        
        Returns:
            Dictionary containing all performance metrics
        """
        response_times = self._calculate_response_time_percentiles()
        throughput = self._calculate_throughput_summary()
        resources = self._calculate_resource_summary()
        health_score = self._calculate_health_score()
        
        return {
            "response_times": {
                "mean_ms": response_times.mean_ms,
                "p50_ms": response_times.p50_ms,
                "p95_ms": response_times.p95_ms,
                "p99_ms": response_times.p99_ms,
                "min_ms": response_times.min_ms,
                "max_ms": response_times.max_ms,
                "sample_count": response_times.count
            },
            "throughput": {
                "requests_per_second": throughput.requests_per_second,
                "requests_per_minute": throughput.requests_per_minute,
                "total_requests_1h": throughput.total_requests_1h,
                "peak_rps": throughput.peak_rps,
                "avg_rps_1h": throughput.avg_rps_1h
            },
            "resources": {
                "cpu_percent": resources.cpu_percent,
                "memory_mb": resources.memory_mb,
                "memory_percent": resources.memory_percent,
                "active_connections": resources.active_connections,
                "thread_count": resources.thread_count,
                "disk_usage_percent": resources.disk_usage_percent
            },
            "health_score": health_score,
            "error_rate": (
                self.error_count / (self.success_count + self.error_count)
                if (self.success_count + self.error_count) > 0 else 0.0
            ),
            "timestamp": datetime.now().isoformat()
        }
    
    async def reset_metrics(self):
        """Reset all collected metrics."""
        self.response_times.clear()
        self.response_time_buckets.clear()
        self.request_timestamps.clear()
        self.throughput_history.clear()
        self.resource_history.clear()
        self.error_count = 0
        self.success_count = 0
        logger.info("Performance metrics reset")


# Global performance collector instance
_performance_collector: Optional[PerformanceCollector] = None
_collector_lock = asyncio.Lock()


async def get_performance_collector() -> PerformanceCollector:
    """Get global performance collector instance."""
    global _performance_collector
    
    if _performance_collector is None:
        async with _collector_lock:
            if _performance_collector is None:
                _performance_collector = PerformanceCollector()
                await _performance_collector.start_collection()
    
    return _performance_collector


async def record_request_performance(endpoint: str, response_time_ms: float, 
                                   status_code: int = 200):
    """Convenience function to record request performance."""
    collector = await get_performance_collector()
    await collector.record_request(endpoint, response_time_ms, status_code)


# Integration with existing performance monitoring
try:
    from netra_backend.app.monitoring.performance_metrics import get_performance_monitor
    
    async def sync_with_existing_monitor():
        """Sync data with existing performance monitor."""
        try:
            existing_monitor = await get_performance_monitor()
            existing_summary = await existing_monitor.get_metrics_summary()
            
            # Use data from existing monitor if available
            logger.info("Synced with existing performance monitor")
            return existing_summary
            
        except Exception as e:
            logger.debug(f"Could not sync with existing monitor: {e}")
            return None
            
except ImportError:
    async def sync_with_existing_monitor():
        return None