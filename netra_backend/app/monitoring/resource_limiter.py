"""
Resource Limiter

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System stability & cost control
- Value Impact: Prevents resource exhaustion through proactive limiting
- Strategic Impact: Ensures system availability and prevents cascading failures

Implements resource limiting with load shedding and throttling mechanisms.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple
import psutil

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.resource_monitor import ResourceMonitor, ResourceType, ResourceStatus

logger = central_logger.get_logger(__name__)


class LimitingAction(Enum):
    """Actions that can be taken when limits are reached."""
    ALLOW = "allow"
    THROTTLE = "throttle" 
    REJECT = "reject"
    QUEUE = "queue"


class LimitingReason(Enum):
    """Reasons for limiting actions."""
    MEMORY_PRESSURE = "memory_pressure"
    CPU_OVERLOAD = "cpu_overload"
    IO_SATURATION = "io_saturation"
    FD_EXHAUSTION = "fd_exhaustion"
    RATE_LIMITED = "rate_limited"
    QUEUE_FULL = "queue_full"


@dataclass
class LimitingDecision:
    """Decision made by resource limiter."""
    action: LimitingAction
    reason: Optional[LimitingReason] = None
    delay_seconds: float = 0.0
    message: str = ""
    current_load: Dict[str, float] = None


@dataclass  
class ResourceLimits:
    """Resource usage limits."""
    memory_limit_percent: float = 85.0
    cpu_limit_percent: float = 90.0
    io_limit_percent: float = 80.0
    fd_limit_percent: float = 85.0
    concurrent_requests_limit: int = 1000
    queue_size_limit: int = 500
    
    # Throttling parameters
    throttle_delay_base_ms: int = 100
    throttle_delay_max_ms: int = 5000
    throttle_backoff_factor: float = 1.5


@dataclass
class LimiterConfig:
    """Configuration for resource limiter."""
    limits: ResourceLimits = None
    enable_load_shedding: bool = True
    enable_throttling: bool = True
    enable_request_queuing: bool = True
    monitoring_interval_seconds: int = 1
    shed_load_threshold: float = 95.0  # Percent
    recovery_threshold: float = 70.0   # Percent
    
    def __post_init__(self):
        if self.limits is None:
            self.limits = ResourceLimits()


class ResourceLimiter:
    """Implements resource limiting with load shedding and throttling."""
    
    def __init__(self, config: Optional[LimiterConfig] = None, resource_monitor: Optional[ResourceMonitor] = None):
        """Initialize resource limiter."""
        self.config = config or LimiterConfig()
        self.resource_monitor = resource_monitor
        
        # Current state
        self.is_load_shedding = False
        self.current_concurrent_requests = 0
        self.request_queue: deque = deque(maxlen=self.config.limits.queue_size_limit)
        
        # Throttling state
        self.throttling_active = False
        self.current_throttle_delay = self.config.limits.throttle_delay_base_ms
        
        # Request tracking
        self.recent_requests: deque = deque(maxlen=1000)  # Last 1000 requests
        self.rejected_requests = 0
        self.throttled_requests = 0
        self.queued_requests = 0
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self.stats = {
            'requests_processed': 0,
            'requests_rejected': 0,
            'requests_throttled': 0,
            'requests_queued': 0,
            'load_shedding_events': 0,
            'throttling_events': 0,
            'average_delay_ms': 0.0
        }
    
    async def start(self) -> None:
        """Start resource limiter monitoring."""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("Resource limiter started")
    
    async def stop(self) -> None:
        """Stop resource limiter."""
        self._shutdown = True
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Resource limiter stopped")
    
    async def check_request_limits(self, request_type: str = "default", priority: int = 1) -> LimitingDecision:
        """
        Check if request should be allowed based on current resource usage.
        
        Args:
            request_type: Type of request (for categorization)
            priority: Request priority (1=highest, 10=lowest)
            
        Returns:
            LimitingDecision with action to take
        """
        current_load = self._get_current_load()
        
        # Check if load shedding is active
        if self.is_load_shedding:
            # Only allow high priority requests during load shedding
            if priority > 3:
                self.stats['requests_rejected'] += 1
                return LimitingDecision(
                    action=LimitingAction.REJECT,
                    reason=LimitingReason.MEMORY_PRESSURE,
                    message="System under heavy load, rejecting low priority requests",
                    current_load=current_load
                )
        
        # Check memory pressure
        memory_usage = current_load.get('memory_percent', 0.0)
        if memory_usage > self.config.limits.memory_limit_percent:
            if memory_usage > self.config.shed_load_threshold:
                self.stats['requests_rejected'] += 1
                return LimitingDecision(
                    action=LimitingAction.REJECT,
                    reason=LimitingReason.MEMORY_PRESSURE,
                    message=f"Memory usage too high: {memory_usage:.1f}%",
                    current_load=current_load
                )
            else:
                # Throttle instead of reject
                delay = self._calculate_throttle_delay(memory_usage, self.config.limits.memory_limit_percent)
                self.stats['requests_throttled'] += 1
                return LimitingDecision(
                    action=LimitingAction.THROTTLE,
                    reason=LimitingReason.MEMORY_PRESSURE,
                    delay_seconds=delay / 1000.0,
                    message=f"Memory pressure, throttling request",
                    current_load=current_load
                )
        
        # Check CPU overload
        cpu_usage = current_load.get('cpu_percent', 0.0)
        if cpu_usage > self.config.limits.cpu_limit_percent:
            if cpu_usage > self.config.shed_load_threshold:
                self.stats['requests_rejected'] += 1
                return LimitingDecision(
                    action=LimitingAction.REJECT,
                    reason=LimitingReason.CPU_OVERLOAD,
                    message=f"CPU usage too high: {cpu_usage:.1f}%",
                    current_load=current_load
                )
            else:
                delay = self._calculate_throttle_delay(cpu_usage, self.config.limits.cpu_limit_percent)
                self.stats['requests_throttled'] += 1
                return LimitingDecision(
                    action=LimitingAction.THROTTLE,
                    reason=LimitingReason.CPU_OVERLOAD,
                    delay_seconds=delay / 1000.0,
                    message=f"CPU overload, throttling request",
                    current_load=current_load
                )
        
        # Check file descriptor usage
        fd_usage = current_load.get('fd_percent', 0.0)
        if fd_usage > self.config.limits.fd_limit_percent:
            self.stats['requests_rejected'] += 1
            return LimitingDecision(
                action=LimitingAction.REJECT,
                reason=LimitingReason.FD_EXHAUSTION,
                message=f"File descriptor usage too high: {fd_usage:.1f}%",
                current_load=current_load
            )
        
        # Check concurrent request limit
        if self.current_concurrent_requests >= self.config.limits.concurrent_requests_limit:
            # Try to queue if queuing is enabled
            if self.config.enable_request_queuing and len(self.request_queue) < self.config.limits.queue_size_limit:
                self.stats['requests_queued'] += 1
                return LimitingDecision(
                    action=LimitingAction.QUEUE,
                    reason=LimitingReason.RATE_LIMITED,
                    message="Request queued due to high concurrent load",
                    current_load=current_load
                )
            else:
                self.stats['requests_rejected'] += 1
                return LimitingDecision(
                    action=LimitingAction.REJECT,
                    reason=LimitingReason.QUEUE_FULL,
                    message="Too many concurrent requests and queue is full",
                    current_load=current_load
                )
        
        # Allow request
        self.stats['requests_processed'] += 1
        return LimitingDecision(
            action=LimitingAction.ALLOW,
            message="Request allowed",
            current_load=current_load
        )
    
    async def acquire_request_slot(self, request_id: str = None) -> bool:
        """
        Acquire a slot for processing a request.
        
        Args:
            request_id: Optional request identifier
            
        Returns:
            True if slot was acquired
        """
        if self.current_concurrent_requests >= self.config.limits.concurrent_requests_limit:
            return False
        
        self.current_concurrent_requests += 1
        self.recent_requests.append({
            'timestamp': time.time(),
            'request_id': request_id,
            'action': 'acquired'
        })
        
        return True
    
    async def release_request_slot(self, request_id: str = None) -> None:
        """
        Release a request processing slot.
        
        Args:
            request_id: Optional request identifier
        """
        if self.current_concurrent_requests > 0:
            self.current_concurrent_requests -= 1
            
        self.recent_requests.append({
            'timestamp': time.time(),
            'request_id': request_id,
            'action': 'released'
        })
    
    def _get_current_load(self) -> Dict[str, float]:
        """Get current resource load."""
        if self.resource_monitor:
            metrics = self.resource_monitor.get_current_metrics()
            return {
                'memory_percent': metrics.memory_percent,
                'cpu_percent': metrics.cpu_percent,
                'fd_percent': metrics.file_descriptors_percent,
                'io_percent': metrics.disk_io_percent,
                'concurrent_requests': self.current_concurrent_requests
            }
        else:
            # Fallback to basic psutil measurements
            try:
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent()
                
                return {
                    'memory_percent': memory.percent,
                    'cpu_percent': cpu,
                    'fd_percent': 0.0,  # Not available without monitor
                    'io_percent': 0.0,
                    'concurrent_requests': self.current_concurrent_requests
                }
            except Exception as e:
                logger.warning(f"Failed to get resource load: {e}")
                return {
                    'memory_percent': 0.0,
                    'cpu_percent': 0.0,
                    'fd_percent': 0.0,
                    'io_percent': 0.0,
                    'concurrent_requests': self.current_concurrent_requests
                }
    
    def _calculate_throttle_delay(self, current_usage: float, limit: float) -> float:
        """Calculate throttle delay based on usage."""
        if current_usage <= limit:
            return 0.0
        
        # Calculate how much we're over the limit
        overage_percent = (current_usage - limit) / limit
        
        # Exponential backoff based on overage
        delay = self.config.limits.throttle_delay_base_ms * (1 + overage_percent) ** self.config.limits.throttle_backoff_factor
        
        return min(delay, self.config.limits.throttle_delay_max_ms)
    
    async def _monitor_loop(self) -> None:
        """Monitor resource usage and adjust limiting behavior."""
        while not self._shutdown:
            try:
                await self._update_limiting_state()
                await asyncio.sleep(self.config.monitoring_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource limiter monitor loop: {e}")
    
    async def _update_limiting_state(self) -> None:
        """Update load shedding and throttling state based on current load."""
        current_load = self._get_current_load()
        
        # Check for load shedding conditions
        memory_percent = current_load.get('memory_percent', 0.0)
        cpu_percent = current_load.get('cpu_percent', 0.0)
        
        should_shed_load = (
            memory_percent > self.config.shed_load_threshold or
            cpu_percent > self.config.shed_load_threshold
        )
        
        should_recover = (
            memory_percent < self.config.recovery_threshold and
            cpu_percent < self.config.recovery_threshold
        )
        
        # Update load shedding state
        if should_shed_load and not self.is_load_shedding:
            self.is_load_shedding = True
            self.stats['load_shedding_events'] += 1
            logger.warning(f"Load shedding activated - Memory: {memory_percent:.1f}%, CPU: {cpu_percent:.1f}%")
            
        elif should_recover and self.is_load_shedding:
            self.is_load_shedding = False
            logger.info(f"Load shedding deactivated - Memory: {memory_percent:.1f}%, CPU: {cpu_percent:.1f}%")
        
        # Update throttling state
        should_throttle = (
            memory_percent > self.config.limits.memory_limit_percent or
            cpu_percent > self.config.limits.cpu_limit_percent
        )
        
        if should_throttle and not self.throttling_active:
            self.throttling_active = True
            self.stats['throttling_events'] += 1
            logger.info("Request throttling activated")
            
        elif not should_throttle and self.throttling_active:
            self.throttling_active = False
            self.current_throttle_delay = self.config.limits.throttle_delay_base_ms
            logger.info("Request throttling deactivated")
    
    def get_limiter_stats(self) -> Dict[str, Any]:
        """Get resource limiter statistics."""
        current_load = self._get_current_load()
        
        # Calculate average delay from recent requests
        recent_delays = []
        current_time = time.time()
        
        for request in list(self.recent_requests):
            if current_time - request['timestamp'] < 60:  # Last minute
                if 'delay' in request:
                    recent_delays.append(request['delay'])
        
        avg_delay = sum(recent_delays) / len(recent_delays) if recent_delays else 0.0
        
        return {
            'current_load': current_load,
            'is_load_shedding': self.is_load_shedding,
            'throttling_active': self.throttling_active,
            'concurrent_requests': self.current_concurrent_requests,
            'queue_size': len(self.request_queue),
            'recent_requests_count': len(self.recent_requests),
            'average_delay_ms': avg_delay,
            **self.stats
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the limiter."""
        current_load = self._get_current_load()
        
        status = "healthy"
        if self.is_load_shedding:
            status = "load_shedding"
        elif self.throttling_active:
            status = "throttling"
        elif current_load.get('memory_percent', 0) > 80 or current_load.get('cpu_percent', 0) > 80:
            status = "warning"
        
        return {
            'status': status,
            'load_shedding': self.is_load_shedding,
            'throttling': self.throttling_active,
            'resource_usage': current_load,
            'limits': {
                'memory_limit': self.config.limits.memory_limit_percent,
                'cpu_limit': self.config.limits.cpu_limit_percent,
                'concurrent_limit': self.config.limits.concurrent_requests_limit
            }
        }
    
    async def simulate_load_test(self, requests_per_second: int, duration_seconds: int) -> Dict[str, Any]:
        """
        Simulate load test to validate limiting behavior.
        
        Args:
            requests_per_second: Number of requests to simulate per second
            duration_seconds: Duration of the test
            
        Returns:
            Test results
        """
        logger.info(f"Starting load test: {requests_per_second} req/s for {duration_seconds}s")
        
        test_stats = {
            'allowed': 0,
            'throttled': 0,
            'rejected': 0,
            'queued': 0,
            'total_delay_ms': 0.0
        }
        
        start_time = time.time()
        request_interval = 1.0 / requests_per_second
        
        while time.time() - start_time < duration_seconds:
            # Simulate request
            decision = await self.check_request_limits("load_test", priority=5)
            
            test_stats[decision.action.value] += 1
            if decision.delay_seconds > 0:
                test_stats['total_delay_ms'] += decision.delay_seconds * 1000
                
            # Simulate processing time
            await asyncio.sleep(request_interval)
        
        test_duration = time.time() - start_time
        avg_delay = test_stats['total_delay_ms'] / max(test_stats['throttled'], 1)
        
        return {
            'duration_seconds': test_duration,
            'total_requests': sum(test_stats.values()) - test_stats['total_delay_ms'],
            'average_delay_ms': avg_delay,
            'breakdown': test_stats,
            'final_system_state': self.get_health_status()
        }


# Global resource limiter instance
_resource_limiter: Optional[ResourceLimiter] = None


def get_resource_limiter(config: Optional[LimiterConfig] = None, resource_monitor: Optional[ResourceMonitor] = None) -> ResourceLimiter:
    """Get global resource limiter instance."""
    global _resource_limiter
    if _resource_limiter is None:
        _resource_limiter = ResourceLimiter(config, resource_monitor)
    return _resource_limiter


async def check_request_allowed(request_type: str = "default", priority: int = 1) -> LimitingDecision:
    """Convenience function to check if request should be allowed."""
    limiter = get_resource_limiter()
    return await limiter.check_request_limits(request_type, priority)


async def acquire_processing_slot(request_id: str = None) -> bool:
    """Convenience function to acquire processing slot."""
    limiter = get_resource_limiter()
    return await limiter.acquire_request_slot(request_id)


async def release_processing_slot(request_id: str = None) -> None:
    """Convenience function to release processing slot."""
    limiter = get_resource_limiter()
    await limiter.release_request_slot(request_id)