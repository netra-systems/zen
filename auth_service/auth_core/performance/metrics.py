"""
Auth Service Performance Metrics - Real-time performance monitoring
Provides comprehensive metrics for authentication performance optimization
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class AuthMetric:
    """Individual authentication metric"""
    timestamp: float
    operation: str
    duration_ms: float
    success: bool
    user_id: Optional[str] = None
    error_type: Optional[str] = None
    cache_hit: bool = False

@dataclass
class PerformanceStats:
    """Aggregated performance statistics"""
    total_requests: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    requests_per_second: float = 0.0
    slow_requests_count: int = 0  # > 2000ms
    critical_errors: int = 0

class AuthPerformanceMonitor:
    """High-performance authentication metrics collection and analysis"""
    
    def __init__(self, max_metrics_history: int = 10000):
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.hourly_stats: Dict[int, PerformanceStats] = {}
        
        # Performance targets
        self.target_response_time_ms = 2000  # 2 seconds max
        self.target_success_rate = 0.95  # 95% success rate
        self.target_cache_hit_rate = 0.80  # 80% cache hit rate
        
        # Real-time monitoring
        self.current_window_start = time.time()
        self.window_duration = 300  # 5-minute windows
        self.current_window_metrics: List[AuthMetric] = []
        
        logger.info("Auth performance monitor initialized")
    
    def record_auth_operation(self, operation: str, duration_ms: float, 
                            success: bool = True, user_id: str = None, 
                            error_type: str = None, cache_hit: bool = False):
        """Record an authentication operation for performance analysis"""
        metric = AuthMetric(
            timestamp=time.time(),
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            user_id=user_id,
            error_type=error_type,
            cache_hit=cache_hit
        )
        
        # Add to history
        self.metrics_history.append(metric)
        self.current_window_metrics.append(metric)
        
        # Track operation-specific stats
        self.operation_stats[operation].append(duration_ms)
        if len(self.operation_stats[operation]) > 1000:
            # Keep only recent 1000 measurements per operation
            self.operation_stats[operation] = self.operation_stats[operation][-1000:]
        
        # Track errors
        if not success and error_type:
            self.error_counts[error_type] += 1
        
        # Log slow operations
        if duration_ms > self.target_response_time_ms:
            logger.warning(f"Slow auth operation: {operation} took {duration_ms:.0f}ms "
                          f"(target: {self.target_response_time_ms}ms)")
        
        # Rotate window if needed
        if time.time() - self.current_window_start > self.window_duration:
            self._rotate_window()
    
    def get_current_performance_stats(self) -> PerformanceStats:
        """Get current performance statistics"""
        if not self.current_window_metrics:
            return PerformanceStats()
        
        # Calculate stats for current window
        total_requests = len(self.current_window_metrics)
        successful_requests = sum(1 for m in self.current_window_metrics if m.success)
        cache_hits = sum(1 for m in self.current_window_metrics if m.cache_hit)
        
        # Response time statistics
        response_times = [m.duration_ms for m in self.current_window_metrics]
        response_times.sort()
        
        avg_response_time = sum(response_times) / len(response_times)
        p95_index = int(len(response_times) * 0.95)
        p99_index = int(len(response_times) * 0.99)
        
        p95_response_time = response_times[p95_index] if p95_index < len(response_times) else response_times[-1]
        p99_response_time = response_times[p99_index] if p99_index < len(response_times) else response_times[-1]
        
        # Rates and counts
        window_duration = min(time.time() - self.current_window_start, self.window_duration)
        requests_per_second = total_requests / window_duration if window_duration > 0 else 0
        
        slow_requests = sum(1 for rt in response_times if rt > self.target_response_time_ms)
        critical_errors = sum(1 for m in self.current_window_metrics 
                            if not m.success and m.error_type in ['jwt_validation_failed', 'database_error', 'redis_error'])
        
        return PerformanceStats(
            total_requests=total_requests,
            success_rate=successful_requests / total_requests if total_requests > 0 else 0,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            cache_hit_rate=cache_hits / total_requests if total_requests > 0 else 0,
            error_rate=(total_requests - successful_requests) / total_requests if total_requests > 0 else 0,
            requests_per_second=requests_per_second,
            slow_requests_count=slow_requests,
            critical_errors=critical_errors
        )
    
    def get_operation_performance(self, operation: str) -> Dict[str, Any]:
        """Get performance stats for a specific operation"""
        if operation not in self.operation_stats:
            return {"error": f"No data for operation: {operation}"}
        
        durations = self.operation_stats[operation]
        if not durations:
            return {"error": f"No duration data for operation: {operation}"}
        
        durations_sorted = sorted(durations)
        count = len(durations)
        
        return {
            "operation": operation,
            "total_calls": count,
            "avg_duration_ms": sum(durations) / count,
            "min_duration_ms": durations_sorted[0],
            "max_duration_ms": durations_sorted[-1],
            "p50_duration_ms": durations_sorted[count // 2],
            "p95_duration_ms": durations_sorted[int(count * 0.95)] if count > 0 else 0,
            "p99_duration_ms": durations_sorted[int(count * 0.99)] if count > 0 else 0,
            "slow_calls": sum(1 for d in durations if d > self.target_response_time_ms)
        }
    
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on targets"""
        alerts = []
        stats = self.get_current_performance_stats()
        
        # Response time alerts
        if stats.avg_response_time_ms > self.target_response_time_ms:
            alerts.append({
                "type": "slow_response_time",
                "severity": "warning",
                "message": f"Average response time {stats.avg_response_time_ms:.0f}ms exceeds target {self.target_response_time_ms}ms",
                "current_value": stats.avg_response_time_ms,
                "target_value": self.target_response_time_ms
            })
        
        if stats.p95_response_time_ms > self.target_response_time_ms * 1.5:
            alerts.append({
                "type": "very_slow_p95",
                "severity": "critical",
                "message": f"P95 response time {stats.p95_response_time_ms:.0f}ms is critically slow",
                "current_value": stats.p95_response_time_ms,
                "target_value": self.target_response_time_ms
            })
        
        # Success rate alerts
        if stats.success_rate < self.target_success_rate:
            alerts.append({
                "type": "low_success_rate",
                "severity": "critical",
                "message": f"Success rate {stats.success_rate:.1%} below target {self.target_success_rate:.1%}",
                "current_value": stats.success_rate,
                "target_value": self.target_success_rate
            })
        
        # Cache hit rate alerts
        if stats.cache_hit_rate < self.target_cache_hit_rate:
            alerts.append({
                "type": "low_cache_hit_rate",
                "severity": "warning",
                "message": f"Cache hit rate {stats.cache_hit_rate:.1%} below target {self.target_cache_hit_rate:.1%}",
                "current_value": stats.cache_hit_rate,
                "target_value": self.target_cache_hit_rate
            })
        
        # Critical errors
        if stats.critical_errors > 0:
            alerts.append({
                "type": "critical_errors",
                "severity": "critical",
                "message": f"{stats.critical_errors} critical errors in current window",
                "current_value": stats.critical_errors,
                "target_value": 0
            })
        
        return alerts
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_stats = self.get_current_performance_stats()
        alerts = self.get_performance_alerts()
        
        # Top operations by volume and latency
        operation_performance = {}
        for operation in self.operation_stats.keys():
            operation_performance[operation] = self.get_operation_performance(operation)
        
        # Error breakdown
        total_errors = sum(self.error_counts.values())
        error_breakdown = {error: count for error, count in self.error_counts.items()}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "window_duration_seconds": self.window_duration,
            "current_stats": {
                "total_requests": current_stats.total_requests,
                "success_rate": f"{current_stats.success_rate:.1%}",
                "avg_response_time_ms": f"{current_stats.avg_response_time_ms:.1f}",
                "p95_response_time_ms": f"{current_stats.p95_response_time_ms:.1f}",
                "p99_response_time_ms": f"{current_stats.p99_response_time_ms:.1f}",
                "cache_hit_rate": f"{current_stats.cache_hit_rate:.1%}",
                "requests_per_second": f"{current_stats.requests_per_second:.1f}",
                "slow_requests": current_stats.slow_requests_count
            },
            "targets": {
                "response_time_ms": self.target_response_time_ms,
                "success_rate": f"{self.target_success_rate:.1%}",
                "cache_hit_rate": f"{self.target_cache_hit_rate:.1%}"
            },
            "alerts": alerts,
            "operation_performance": operation_performance,
            "error_breakdown": error_breakdown,
            "total_errors": total_errors,
            "health_score": self._calculate_health_score(current_stats)
        }
    
    def _calculate_health_score(self, stats: PerformanceStats) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # Response time penalty
        if stats.avg_response_time_ms > self.target_response_time_ms:
            penalty = min(50, (stats.avg_response_time_ms - self.target_response_time_ms) / self.target_response_time_ms * 30)
            score -= penalty
        
        # Success rate penalty
        if stats.success_rate < self.target_success_rate:
            penalty = (self.target_success_rate - stats.success_rate) * 100
            score -= penalty
        
        # Cache hit rate penalty (smaller impact)
        if stats.cache_hit_rate < self.target_cache_hit_rate:
            penalty = (self.target_cache_hit_rate - stats.cache_hit_rate) * 20
            score -= penalty
        
        # Critical errors penalty
        if stats.critical_errors > 0:
            score -= min(30, stats.critical_errors * 10)
        
        return max(0, score)
    
    def _rotate_window(self):
        """Rotate the current monitoring window"""
        # Calculate stats for completed window
        window_stats = self.get_current_performance_stats()
        
        # Store hourly stats (simplified - could be more sophisticated)
        current_hour = int(time.time() // 3600)
        self.hourly_stats[current_hour] = window_stats
        
        # Keep only recent hourly stats (24 hours)
        if len(self.hourly_stats) > 24:
            oldest_hour = min(self.hourly_stats.keys())
            del self.hourly_stats[oldest_hour]
        
        # Reset current window
        self.current_window_start = time.time()
        self.current_window_metrics = []
        
        logger.debug(f"Rotated performance window - Previous window: {window_stats.total_requests} requests, "
                    f"{window_stats.avg_response_time_ms:.1f}ms avg, {window_stats.success_rate:.1%} success rate")
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._periodic_reporting())
        logger.info("Performance monitoring started")
    
    async def _periodic_reporting(self):
        """Periodic performance reporting"""
        while True:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                stats = self.get_current_performance_stats()
                alerts = self.get_performance_alerts()
                
                if alerts:
                    logger.warning(f"Performance alerts: {len(alerts)} issues detected")
                    for alert in alerts:
                        logger.warning(f"  {alert['type']}: {alert['message']}")
                
                # Log summary every 5 minutes
                if int(time.time()) % 300 == 0:
                    logger.info(f"Performance summary: {stats.total_requests} requests, "
                              f"{stats.avg_response_time_ms:.0f}ms avg, {stats.success_rate:.1%} success, "
                              f"{stats.cache_hit_rate:.1%} cache hit rate")
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)

# Global performance monitor instance
auth_performance_monitor = AuthPerformanceMonitor()

# Decorator for automatic performance monitoring
def monitor_auth_performance(operation: str):
    """Decorator to automatically monitor authentication operation performance"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_type = None
                cache_hit = kwargs.get('_cache_hit', False)  # Special param for cache hits
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_type = type(e).__name__.lower()
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    user_id = kwargs.get('user_id') or args[0] if args else None
                    auth_performance_monitor.record_auth_operation(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=success,
                        user_id=user_id,
                        error_type=error_type,
                        cache_hit=cache_hit
                    )
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_type = None
                cache_hit = kwargs.get('_cache_hit', False)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_type = type(e).__name__.lower()
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    user_id = kwargs.get('user_id') or args[0] if args else None
                    auth_performance_monitor.record_auth_operation(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=success,
                        user_id=user_id,
                        error_type=error_type,
                        cache_hit=cache_hit
                    )
            return sync_wrapper
    return decorator