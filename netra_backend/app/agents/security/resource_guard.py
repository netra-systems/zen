"""ResourceGuard - Comprehensive resource protection for agent execution.

This module provides memory monitoring, CPU limits, concurrent execution control,
and rate limiting to prevent resource exhaustion and DoS attacks.

Business Value: Ensures system stability under load and prevents resource-based attacks
that could cause service degradation or outages.
"""

import asyncio
import os
import psutil
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class ResourceViolationType(Enum):
    """Types of resource violations."""
    MEMORY_EXCEEDED = "memory_exceeded"
    CPU_EXCEEDED = "cpu_exceeded"
    CONCURRENT_LIMIT = "concurrent_limit"
    RATE_LIMIT = "rate_limit"
    DISK_SPACE = "disk_space"


@dataclass
class ResourceLimits:
    """Resource limit configuration."""
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    max_concurrent_per_user: int = 10
    max_concurrent_global: int = 100
    rate_limit_per_minute: int = 100
    min_disk_space_mb: int = 1024
    check_interval_seconds: float = 5.0


class ResourceUsage(BaseModel):
    """Current resource usage statistics."""
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    disk_space_mb: float
    concurrent_executions: int
    active_users: int
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserResourceTracker:
    """Tracks resource usage per user."""
    
    def __init__(self):
        self.concurrent_executions: Dict[str, int] = {}
        self.request_timestamps: Dict[str, List[float]] = {}
        self.total_memory_per_user: Dict[str, float] = {}
        
    def increment_concurrent(self, user_id: str) -> int:
        """Increment concurrent execution count for user."""
        self.concurrent_executions[user_id] = self.concurrent_executions.get(user_id, 0) + 1
        return self.concurrent_executions[user_id]
    
    def decrement_concurrent(self, user_id: str) -> int:
        """Decrement concurrent execution count for user."""
        if user_id in self.concurrent_executions:
            self.concurrent_executions[user_id] = max(0, self.concurrent_executions[user_id] - 1)
            if self.concurrent_executions[user_id] == 0:
                del self.concurrent_executions[user_id]
        return self.concurrent_executions.get(user_id, 0)
    
    def add_request_timestamp(self, user_id: str, timestamp: float):
        """Add request timestamp for rate limiting."""
        if user_id not in self.request_timestamps:
            self.request_timestamps[user_id] = []
        self.request_timestamps[user_id].append(timestamp)
    
    def cleanup_old_timestamps(self, cutoff_time: float):
        """Remove timestamps older than cutoff."""
        for user_id in list(self.request_timestamps.keys()):
            timestamps = [ts for ts in self.request_timestamps[user_id] if ts > cutoff_time]
            if timestamps:
                self.request_timestamps[user_id] = timestamps
            else:
                del self.request_timestamps[user_id]
    
    def get_recent_request_count(self, user_id: str, cutoff_time: float) -> int:
        """Get number of recent requests for user."""
        if user_id not in self.request_timestamps:
            return 0
        return len([ts for ts in self.request_timestamps[user_id] if ts > cutoff_time])


class ResourceGuard:
    """Comprehensive resource protection system.
    
    This class provides:
    - Memory usage monitoring and enforcement
    - CPU usage limits
    - Concurrent execution limits (per user and global)
    - Rate limiting (requests per minute)
    - Disk space monitoring
    - Automatic cleanup and recovery
    """
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """Initialize ResourceGuard with configuration."""
        self.env = IsolatedEnvironment()
        
        # Load configuration from environment or use defaults
        self.limits = limits or ResourceLimits(
            max_memory_mb=int(self.env.get('RESOURCE_GUARD_MAX_MEMORY_MB', '512')),
            max_cpu_percent=float(self.env.get('RESOURCE_GUARD_MAX_CPU_PERCENT', '80.0')),
            max_concurrent_per_user=int(self.env.get('RESOURCE_GUARD_MAX_CONCURRENT_PER_USER', '10')),
            max_concurrent_global=int(self.env.get('RESOURCE_GUARD_MAX_CONCURRENT_GLOBAL', '100')),
            rate_limit_per_minute=int(self.env.get('RESOURCE_GUARD_RATE_LIMIT_PER_MINUTE', '100')),
            min_disk_space_mb=int(self.env.get('RESOURCE_GUARD_MIN_DISK_SPACE_MB', '1024')),
            check_interval_seconds=float(self.env.get('RESOURCE_GUARD_CHECK_INTERVAL', '5.0'))
        )
        
        # Resource tracking
        self.user_tracker = UserResourceTracker()
        self._process = psutil.Process(os.getpid())
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # Violation tracking
        self._violation_counts: Dict[ResourceViolationType, int] = {
            violation_type: 0 for violation_type in ResourceViolationType
        }
        self._last_violation_times: Dict[ResourceViolationType, datetime] = {}
        
        # Current usage cache
        self._current_usage: Optional[ResourceUsage] = None
        self._last_usage_update = 0
        
        logger.info(f"[U+1F6E1][U+FE0F] ResourceGuard initialized with limits: {self.limits}")
    
    async def validate_resource_request(self, user_id: str, estimated_memory_mb: float = 0) -> Optional[str]:
        """Validate if a new resource request can be granted.
        
        Args:
            user_id: User making the request
            estimated_memory_mb: Estimated memory usage for the request
            
        Returns:
            None if request is allowed, error message if denied
        """
        now = time.time()
        
        # Update usage statistics
        await self._update_current_usage()
        
        # Check global concurrent limit
        total_concurrent = sum(self.user_tracker.concurrent_executions.values())
        if total_concurrent >= self.limits.max_concurrent_global:
            self._record_violation(ResourceViolationType.CONCURRENT_LIMIT)
            return f"Global concurrent execution limit exceeded ({total_concurrent}/{self.limits.max_concurrent_global}). System is at capacity."
        
        # Check per-user concurrent limit
        user_concurrent = self.user_tracker.concurrent_executions.get(user_id, 0)
        if user_concurrent >= self.limits.max_concurrent_per_user:
            self._record_violation(ResourceViolationType.CONCURRENT_LIMIT)
            return f"User concurrent execution limit exceeded ({user_concurrent}/{self.limits.max_concurrent_per_user}). Please wait for existing tasks to complete."
        
        # Check rate limiting
        cutoff_time = now - 60  # 60 seconds ago
        self.user_tracker.cleanup_old_timestamps(cutoff_time)
        recent_requests = self.user_tracker.get_recent_request_count(user_id, cutoff_time)
        
        if recent_requests >= self.limits.rate_limit_per_minute:
            self._record_violation(ResourceViolationType.RATE_LIMIT)
            return f"Rate limit exceeded ({recent_requests}/{self.limits.rate_limit_per_minute} requests per minute). Please slow down."
        
        # Check memory constraints
        if self._current_usage:
            projected_memory = self._current_usage.memory_mb + estimated_memory_mb
            if projected_memory > self.limits.max_memory_mb:
                self._record_violation(ResourceViolationType.MEMORY_EXCEEDED)
                return f"Insufficient memory available ({projected_memory:.1f}MB would exceed {self.limits.max_memory_mb}MB limit)."
        
        # Check CPU constraints (if currently high)
        if self._current_usage and self._current_usage.cpu_percent > self.limits.max_cpu_percent:
            self._record_violation(ResourceViolationType.CPU_EXCEEDED)
            return f"CPU usage too high ({self._current_usage.cpu_percent:.1f}% > {self.limits.max_cpu_percent}%). Please try again later."
        
        # Check disk space
        if self._current_usage and self._current_usage.disk_space_mb < self.limits.min_disk_space_mb:
            self._record_violation(ResourceViolationType.DISK_SPACE)
            return f"Insufficient disk space ({self._current_usage.disk_space_mb:.1f}MB < {self.limits.min_disk_space_mb}MB required)."
        
        # Request is valid - record it
        self.user_tracker.add_request_timestamp(user_id, now)
        
        return None
    
    async def acquire_resources(self, user_id: str, estimated_memory_mb: float = 0) -> bool:
        """Acquire resources for execution.
        
        Args:
            user_id: User acquiring resources
            estimated_memory_mb: Estimated memory usage
            
        Returns:
            True if resources acquired, False if denied
        """
        validation_error = await self.validate_resource_request(user_id, estimated_memory_mb)
        if validation_error:
            logger.warning(f"[U+1F6AB] Resource request denied for {user_id}: {validation_error}")
            return False
        
        # Acquire resources
        concurrent_count = self.user_tracker.increment_concurrent(user_id)
        logger.debug(f"[U+1F4C8] Resources acquired for {user_id}: concurrent={concurrent_count}")
        
        # Start monitoring if not already running
        if not self._is_monitoring:
            await self.start_monitoring()
        
        return True
    
    async def release_resources(self, user_id: str) -> None:
        """Release resources after execution completion."""
        concurrent_count = self.user_tracker.decrement_concurrent(user_id)
        logger.debug(f"[U+1F4C9] Resources released for {user_id}: concurrent={concurrent_count}")
    
    async def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage statistics."""
        await self._update_current_usage()
        return self._current_usage
    
    async def _update_current_usage(self) -> None:
        """Update current usage statistics."""
        now = time.time()
        
        # Cache usage updates to avoid excessive system calls
        if now - self._last_usage_update < 1.0 and self._current_usage:
            return
        
        try:
            # Get memory information
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Get system memory info for percentage
            system_memory = psutil.virtual_memory()
            memory_percent = (memory_mb / (system_memory.total / 1024 / 1024)) * 100
            
            # Get CPU usage
            cpu_percent = self._process.cpu_percent()
            
            # Get disk space
            disk_usage = psutil.disk_usage('/')
            disk_space_mb = disk_usage.free / 1024 / 1024
            
            # Get concurrent execution count
            concurrent_executions = sum(self.user_tracker.concurrent_executions.values())
            active_users = len(self.user_tracker.concurrent_executions)
            
            self._current_usage = ResourceUsage(
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                disk_space_mb=disk_space_mb,
                concurrent_executions=concurrent_executions,
                active_users=active_users,
                timestamp=datetime.now(UTC)
            )
            
            self._last_usage_update = now
            
        except Exception as e:
            logger.warning(f"Failed to update resource usage: {e}")
    
    def _record_violation(self, violation_type: ResourceViolationType) -> None:
        """Record a resource violation."""
        self._violation_counts[violation_type] += 1
        self._last_violation_times[violation_type] = datetime.now(UTC)
        
        logger.warning(f" ALERT:  Resource violation: {violation_type.value} (count: {self._violation_counts[violation_type]})")
    
    async def start_monitoring(self) -> None:
        """Start background resource monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("[U+1F441][U+FE0F] Started resource monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background resource monitoring."""
        self._is_monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[U+23F9][U+FE0F] Stopped resource monitoring")
    
    async def _monitor_loop(self) -> None:
        """Main resource monitoring loop."""
        while self._is_monitoring:
            try:
                await asyncio.sleep(self.limits.check_interval_seconds)
                await self._update_current_usage()
                
                if self._current_usage:
                    # Check for resource violations
                    if self._current_usage.memory_mb > self.limits.max_memory_mb:
                        self._record_violation(ResourceViolationType.MEMORY_EXCEEDED)
                        logger.error(f" ALERT:  Memory limit exceeded: {self._current_usage.memory_mb:.1f}MB > {self.limits.max_memory_mb}MB")
                    
                    if self._current_usage.cpu_percent > self.limits.max_cpu_percent:
                        self._record_violation(ResourceViolationType.CPU_EXCEEDED)
                        logger.warning(f" WARNING: [U+FE0F] CPU usage high: {self._current_usage.cpu_percent:.1f}% > {self.limits.max_cpu_percent}%")
                    
                    if self._current_usage.disk_space_mb < self.limits.min_disk_space_mb:
                        self._record_violation(ResourceViolationType.DISK_SPACE)
                        logger.error(f" ALERT:  Low disk space: {self._current_usage.disk_space_mb:.1f}MB < {self.limits.min_disk_space_mb}MB")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """Get comprehensive resource status."""
        await self._update_current_usage()
        
        status = "healthy"
        issues = []
        
        if self._current_usage:
            # Determine status based on current usage
            if self._current_usage.memory_mb > self.limits.max_memory_mb * 0.9:
                status = "warning"
                issues.append(f"High memory usage: {self._current_usage.memory_mb:.1f}MB")
            
            if self._current_usage.memory_mb > self.limits.max_memory_mb:
                status = "critical"
                issues.append(f"Memory limit exceeded: {self._current_usage.memory_mb:.1f}MB")
            
            if self._current_usage.cpu_percent > self.limits.max_cpu_percent * 0.8:
                status = "warning"
                issues.append(f"High CPU usage: {self._current_usage.cpu_percent:.1f}%")
            
            if self._current_usage.cpu_percent > self.limits.max_cpu_percent:
                status = "critical"
                issues.append(f"CPU limit exceeded: {self._current_usage.cpu_percent:.1f}%")
            
            if self._current_usage.concurrent_executions > self.limits.max_concurrent_global * 0.8:
                status = "warning"
                issues.append(f"High concurrent load: {self._current_usage.concurrent_executions}")
        
        return {
            "status": status,
            "issues": issues,
            "current_usage": self._current_usage.dict() if self._current_usage else None,
            "limits": {
                "max_memory_mb": self.limits.max_memory_mb,
                "max_cpu_percent": self.limits.max_cpu_percent,
                "max_concurrent_per_user": self.limits.max_concurrent_per_user,
                "max_concurrent_global": self.limits.max_concurrent_global,
                "rate_limit_per_minute": self.limits.rate_limit_per_minute,
                "min_disk_space_mb": self.limits.min_disk_space_mb
            },
            "violations": {
                violation_type.value: {
                    "count": self._violation_counts[violation_type],
                    "last_occurrence": self._last_violation_times.get(violation_type, {}).isoformat() 
                        if violation_type in self._last_violation_times else None
                }
                for violation_type in ResourceViolationType
            },
            "user_stats": {
                "active_users": len(self.user_tracker.concurrent_executions),
                "concurrent_executions_by_user": self.user_tracker.concurrent_executions.copy(),
                "total_concurrent": sum(self.user_tracker.concurrent_executions.values())
            }
        }
    
    async def emergency_cleanup(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Emergency cleanup of resources.
        
        Args:
            user_id: If specified, clean up only this user's resources
            
        Returns:
            Cleanup statistics
        """
        if user_id:
            logger.critical(f"[U+1F9F9] Emergency cleanup for user: {user_id}")
            old_count = self.user_tracker.concurrent_executions.get(user_id, 0)
            
            if user_id in self.user_tracker.concurrent_executions:
                del self.user_tracker.concurrent_executions[user_id]
            if user_id in self.user_tracker.request_timestamps:
                del self.user_tracker.request_timestamps[user_id]
            
            return {
                "user_id": user_id,
                "cleaned_executions": old_count,
                "timestamp": datetime.now(UTC).isoformat()
            }
        else:
            logger.critical("[U+1F9F9] Emergency cleanup of ALL resources")
            total_executions = sum(self.user_tracker.concurrent_executions.values())
            affected_users = len(self.user_tracker.concurrent_executions)
            
            self.user_tracker.concurrent_executions.clear()
            self.user_tracker.request_timestamps.clear()
            
            return {
                "cleaned_executions": total_executions,
                "affected_users": affected_users,
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    async def update_limits(self, new_limits: ResourceLimits) -> None:
        """Update resource limits dynamically."""
        old_limits = self.limits
        self.limits = new_limits
        
        logger.info(f"[U+1F527] Resource limits updated from {old_limits} to {new_limits}")
    
    async def get_user_resource_summary(self, user_id: str) -> Dict[str, Any]:
        """Get resource usage summary for a specific user."""
        concurrent = self.user_tracker.concurrent_executions.get(user_id, 0)
        
        # Get recent request count
        now = time.time()
        cutoff_time = now - 60
        recent_requests = self.user_tracker.get_recent_request_count(user_id, cutoff_time)
        
        return {
            "user_id": user_id,
            "concurrent_executions": concurrent,
            "recent_requests": recent_requests,
            "limits": {
                "max_concurrent": self.limits.max_concurrent_per_user,
                "max_requests_per_minute": self.limits.rate_limit_per_minute
            },
            "utilization": {
                "concurrent_percent": (concurrent / self.limits.max_concurrent_per_user) * 100,
                "rate_limit_percent": (recent_requests / self.limits.rate_limit_per_minute) * 100
            }
        }