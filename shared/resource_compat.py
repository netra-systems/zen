"""
Cross-Platform Resource Module Compatibility Layer

This module provides cross-platform compatibility for Unix-specific resource
monitoring functionality, enabling memory leak detection and resource monitoring
tests to run on Windows, Linux, and macOS.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Enable comprehensive testing on all developer platforms
- Value Impact: Prevent platform-specific test failures blocking Golden Path validation
- Strategic Impact: Ensure system reliability across all deployment environments

Key Features:
- Windows resource monitoring using psutil
- Unix resource module fallback compatibility
- Memory usage tracking and limits
- CPU time monitoring
- Cross-platform resource usage reporting
"""

import os
import platform
import time
import threading
from typing import Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Try to import Unix resource module
try:
    import resource as unix_resource
    UNIX_RESOURCE_AVAILABLE = True
except ImportError:
    UNIX_RESOURCE_AVAILABLE = False
    unix_resource = None

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceUsage:
    """Cross-platform resource usage information"""
    max_rss: int = 0           # Maximum resident set size (bytes)
    user_time: float = 0.0     # User CPU time (seconds)
    system_time: float = 0.0   # System CPU time (seconds)
    peak_memory: int = 0       # Peak memory usage (bytes)
    current_memory: int = 0    # Current memory usage (bytes)
    page_faults: int = 0       # Page faults
    platform: str = "unknown"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class ResourceLimitExceeded(Exception):
    """Exception raised when resource limits are exceeded"""
    pass


class CrossPlatformResourceMonitor:
    """Cross-platform resource monitoring and limits"""

    # Resource limit constants (compatible with Unix resource module)
    RLIMIT_AS = 'RLIMIT_AS'           # Virtual memory limit
    RLIMIT_RSS = 'RLIMIT_RSS'         # Resident set size limit
    RLIMIT_CPU = 'RLIMIT_CPU'         # CPU time limit
    RLIMIT_FSIZE = 'RLIMIT_FSIZE'     # File size limit
    RLIMIT_NOFILE = 'RLIMIT_NOFILE'   # Number of open files limit

    # Resource usage constants
    RUSAGE_SELF = 0
    RUSAGE_CHILDREN = 1
    RUSAGE_BOTH = 2

    def __init__(self):
        self.platform = platform.system().lower()
        self._limits: Dict[str, Tuple[int, int]] = {}
        self._start_time = time.time()
        self._baseline_memory = self._get_current_memory()

        logger.info(f"CrossPlatformResourceMonitor initialized on {self.platform}")

    def getrlimit(self, resource_type: str) -> Tuple[int, int]:
        """
        Get resource limits (soft limit, hard limit).

        Compatible with Unix resource.getrlimit() function.

        Args:
            resource_type: Resource type constant (RLIMIT_AS, etc.)

        Returns:
            Tuple of (soft_limit, hard_limit)
        """
        if UNIX_RESOURCE_AVAILABLE and self.platform in ['linux', 'darwin']:
            # Use Unix resource module on supported platforms
            resource_map = {
                self.RLIMIT_AS: unix_resource.RLIMIT_AS,
                self.RLIMIT_RSS: getattr(unix_resource, 'RLIMIT_RSS', None),
                self.RLIMIT_CPU: unix_resource.RLIMIT_CPU,
                self.RLIMIT_FSIZE: unix_resource.RLIMIT_FSIZE,
                self.RLIMIT_NOFILE: unix_resource.RLIMIT_NOFILE
            }

            unix_constant = resource_map.get(resource_type)
            if unix_constant is not None:
                return unix_resource.getrlimit(unix_constant)

        # Fallback to stored limits or defaults
        return self._limits.get(resource_type, (-1, -1))  # -1 = unlimited

    def setrlimit(self, resource_type: str, limits: Tuple[int, int]) -> None:
        """
        Set resource limits.

        Compatible with Unix resource.setrlimit() function.

        Args:
            resource_type: Resource type constant
            limits: Tuple of (soft_limit, hard_limit)
        """
        if UNIX_RESOURCE_AVAILABLE and self.platform in ['linux', 'darwin']:
            # Use Unix resource module on supported platforms
            resource_map = {
                self.RLIMIT_AS: unix_resource.RLIMIT_AS,
                self.RLIMIT_RSS: getattr(unix_resource, 'RLIMIT_RSS', None),
                self.RLIMIT_CPU: unix_resource.RLIMIT_CPU,
                self.RLIMIT_FSIZE: unix_resource.RLIMIT_FSIZE,
                self.RLIMIT_NOFILE: unix_resource.RLIMIT_NOFILE
            }

            unix_constant = resource_map.get(resource_type)
            if unix_constant is not None:
                try:
                    unix_resource.setrlimit(unix_constant, limits)
                    logger.debug(f"Set {resource_type} limits to {limits}")
                except (ValueError, OSError) as e:
                    logger.warning(f"Failed to set {resource_type} limits: {e}")

        # Always store limits for cross-platform consistency
        self._limits[resource_type] = limits
        logger.debug(f"Stored {resource_type} limits: {limits}")

    def getrusage(self, who: int = None) -> ResourceUsage:
        """
        Get resource usage information.

        Compatible with Unix resource.getrusage() function.

        Args:
            who: RUSAGE_SELF, RUSAGE_CHILDREN, or RUSAGE_BOTH

        Returns:
            ResourceUsage object with cross-platform usage information
        """
        if who is None:
            who = self.RUSAGE_SELF

        usage = ResourceUsage(platform=self.platform)

        try:
            if PSUTIL_AVAILABLE:
                # Use psutil for cross-platform resource information
                process = psutil.Process()

                # Memory information
                memory_info = process.memory_info()
                usage.current_memory = memory_info.rss
                usage.max_rss = memory_info.rss  # Current RSS as max for now

                # CPU time information
                cpu_times = process.cpu_times()
                usage.user_time = cpu_times.user
                usage.system_time = cpu_times.system

                # Additional memory info if available
                try:
                    memory_full = process.memory_full_info()
                    usage.peak_memory = getattr(memory_full, 'peak_wset', memory_info.rss)
                except (AttributeError, psutil.AccessDenied):
                    usage.peak_memory = memory_info.rss

                # Page faults if available
                try:
                    io_counters = process.io_counters()
                    # Page faults aren't directly available in psutil, use read_count as proxy
                    usage.page_faults = getattr(io_counters, 'read_count', 0)
                except (AttributeError, psutil.AccessDenied):
                    usage.page_faults = 0

            elif UNIX_RESOURCE_AVAILABLE and self.platform in ['linux', 'darwin']:
                # Use Unix resource module
                rusage = unix_resource.getrusage(who)

                usage.max_rss = rusage.ru_maxrss
                usage.user_time = rusage.ru_utime
                usage.system_time = rusage.ru_stime
                usage.page_faults = rusage.ru_majflt + rusage.ru_minflt
                usage.current_memory = rusage.ru_maxrss
                usage.peak_memory = rusage.ru_maxrss

            else:
                # Minimal fallback for systems without psutil or resource
                logger.warning("No resource monitoring available - using minimal fallback")
                usage.current_memory = self._get_basic_memory_estimate()
                usage.max_rss = usage.current_memory
                usage.peak_memory = usage.current_memory

        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            # Return minimal usage information
            usage.current_memory = self._get_basic_memory_estimate()

        return usage

    def _get_current_memory(self) -> int:
        """Get current memory usage in bytes"""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.Process().memory_info().rss
            except Exception:
                pass

        return self._get_basic_memory_estimate()

    def _get_basic_memory_estimate(self) -> int:
        """Basic memory estimate fallback"""
        try:
            # Very basic estimate - not accurate but prevents crashes
            import sys
            import gc

            # Count objects as rough memory estimate
            object_count = len(gc.get_objects())
            estimated_memory = object_count * 64  # Rough estimate: 64 bytes per object

            return max(estimated_memory, 50 * 1024 * 1024)  # Minimum 50MB estimate

        except Exception:
            return 50 * 1024 * 1024  # Default 50MB

    def check_memory_limit(self, limit_mb: int) -> bool:
        """
        Check if current memory usage exceeds limit.

        Args:
            limit_mb: Memory limit in megabytes

        Returns:
            True if under limit, False if over limit
        """
        current_memory = self._get_current_memory()
        limit_bytes = limit_mb * 1024 * 1024

        if current_memory > limit_bytes:
            logger.warning(f"Memory limit exceeded: {current_memory / 1024 / 1024:.1f}MB > {limit_mb}MB")
            return False

        return True

    def enforce_memory_limit(self, limit_mb: int) -> None:
        """
        Enforce memory limit, raising exception if exceeded.

        Args:
            limit_mb: Memory limit in megabytes

        Raises:
            ResourceLimitExceeded: If memory limit is exceeded
        """
        if not self.check_memory_limit(limit_mb):
            current_memory = self._get_current_memory()
            raise ResourceLimitExceeded(
                f"Memory limit of {limit_mb}MB exceeded (current: {current_memory / 1024 / 1024:.1f}MB)"
            )

    def get_memory_growth(self) -> int:
        """Get memory growth since monitor initialization"""
        current_memory = self._get_current_memory()
        return current_memory - self._baseline_memory

    def reset_baseline(self) -> None:
        """Reset baseline memory measurement"""
        self._baseline_memory = self._get_current_memory()
        self._start_time = time.time()
        logger.debug("Resource monitor baseline reset")


# Global resource monitor instance
_resource_monitor = None
_monitor_lock = threading.Lock()


def get_resource_monitor() -> CrossPlatformResourceMonitor:
    """Get global cross-platform resource monitor instance"""
    global _resource_monitor

    with _monitor_lock:
        if _resource_monitor is None:
            _resource_monitor = CrossPlatformResourceMonitor()

        return _resource_monitor


# Compatibility layer - provides Unix resource module interface
def getrlimit(resource_type):
    """Unix resource.getrlimit() compatibility function"""
    monitor = get_resource_monitor()
    return monitor.getrlimit(resource_type)


def setrlimit(resource_type, limits):
    """Unix resource.setrlimit() compatibility function"""
    monitor = get_resource_monitor()
    return monitor.setrlimit(resource_type, limits)


def getrusage(who=0):
    """Unix resource.getrusage() compatibility function"""
    monitor = get_resource_monitor()
    usage = monitor.getrusage(who)

    # Create object with Unix resource module compatible attributes
    class CompatUsage:
        def __init__(self, usage_data):
            self.ru_maxrss = usage_data.max_rss
            self.ru_utime = usage_data.user_time
            self.ru_stime = usage_data.system_time
            self.ru_majflt = usage_data.page_faults // 2  # Approximate major faults
            self.ru_minflt = usage_data.page_faults // 2  # Approximate minor faults
            # Add other fields that might be expected
            self.ru_ixrss = 0
            self.ru_idrss = 0
            self.ru_isrss = 0
            self.ru_nswap = 0
            self.ru_inblock = 0
            self.ru_oublock = 0
            self.ru_msgsnd = 0
            self.ru_msgrcv = 0
            self.ru_nsignals = 0
            self.ru_nvcsw = 0
            self.ru_nivcsw = 0

    return CompatUsage(usage)


# Export Unix resource module constants for compatibility
RLIMIT_AS = CrossPlatformResourceMonitor.RLIMIT_AS
RLIMIT_RSS = CrossPlatformResourceMonitor.RLIMIT_RSS
RLIMIT_CPU = CrossPlatformResourceMonitor.RLIMIT_CPU
RLIMIT_FSIZE = CrossPlatformResourceMonitor.RLIMIT_FSIZE
RLIMIT_NOFILE = CrossPlatformResourceMonitor.RLIMIT_NOFILE
RUSAGE_SELF = CrossPlatformResourceMonitor.RUSAGE_SELF
RUSAGE_CHILDREN = CrossPlatformResourceMonitor.RUSAGE_CHILDREN


# Module-level convenience functions
def check_memory_limit(limit_mb: int) -> bool:
    """Check if current memory usage is under limit"""
    monitor = get_resource_monitor()
    return monitor.check_memory_limit(limit_mb)


def enforce_memory_limit(limit_mb: int) -> None:
    """Enforce memory limit, raise exception if exceeded"""
    monitor = get_resource_monitor()
    return monitor.enforce_memory_limit(limit_mb)


def get_current_memory_mb() -> float:
    """Get current memory usage in megabytes"""
    monitor = get_resource_monitor()
    return monitor._get_current_memory() / 1024 / 1024


def get_memory_growth_mb() -> float:
    """Get memory growth since baseline in megabytes"""
    monitor = get_resource_monitor()
    return monitor.get_memory_growth() / 1024 / 1024


# Export public interface
__all__ = [
    # Cross-platform monitor
    'CrossPlatformResourceMonitor',
    'ResourceUsage',
    'ResourceLimitExceeded',
    'get_resource_monitor',

    # Unix resource compatibility
    'getrlimit',
    'setrlimit',
    'getrusage',

    # Constants
    'RLIMIT_AS',
    'RLIMIT_RSS',
    'RLIMIT_CPU',
    'RLIMIT_FSIZE',
    'RLIMIT_NOFILE',
    'RUSAGE_SELF',
    'RUSAGE_CHILDREN',

    # Convenience functions
    'check_memory_limit',
    'enforce_memory_limit',
    'get_current_memory_mb',
    'get_memory_growth_mb'
]