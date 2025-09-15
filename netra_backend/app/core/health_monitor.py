"""
Health Monitor Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a health monitoring implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_function: Callable
    interval: float = 30.0
    timeout: float = 10.0
    retries: int = 3
    critical: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    response_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Simple health monitor for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self):
        """Initialize health monitor."""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.running = False
        self.check_tasks: Dict[str, asyncio.Task] = {}

        logger.info("Health monitor initialized (test compatibility mode)")

    def register_health_check(self, health_check: HealthCheck):
        """Register a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Health check registered: {health_check.name}")

    def unregister_health_check(self, name: str):
        """Unregister a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
            if name in self.results:
                del self.results[name]
            if name in self.check_tasks:
                self.check_tasks[name].cancel()
                del self.check_tasks[name]
            logger.info(f"Health check unregistered: {name}")

    async def run_health_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.health_checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Health check not found",
                error="not_registered"
            )

        health_check = self.health_checks[name]
        start_time = time.time()

        try:
            # Run the health check function with timeout
            result = await asyncio.wait_for(
                self._execute_check_function(health_check.check_function),
                timeout=health_check.timeout
            )

            response_time = time.time() - start_time

            if isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "OK" if result else "Check failed"
            elif isinstance(result, dict):
                status = HealthStatus(result.get("status", "unknown"))
                message = result.get("message", "")
            else:
                status = HealthStatus.HEALTHY
                message = str(result)

            return HealthCheckResult(
                name=name,
                status=status,
                message=message,
                response_time=response_time,
                timestamp=time.time()
            )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {health_check.timeout}s",
                error="timeout",
                response_time=time.time() - start_time,
                timestamp=time.time()
            )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                error=str(e),
                response_time=time.time() - start_time,
                timestamp=time.time()
            )

    async def _execute_check_function(self, check_function: Callable) -> Any:
        """Execute a health check function."""
        if asyncio.iscoroutinefunction(check_function):
            return await check_function()
        else:
            return check_function()

    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        if not self.health_checks:
            return {}

        tasks = [
            self.run_health_check(name)
            for name in self.health_checks.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        result_dict = {}
        for result in results:
            if isinstance(result, HealthCheckResult):
                result_dict[result.name] = result
                self.results[result.name] = result
            else:
                logger.error(f"Health check returned unexpected result: {result}")

        return result_dict

    def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.running:
            return

        self.running = True

        # Start monitoring tasks for each health check
        for name, health_check in self.health_checks.items():
            task = asyncio.create_task(self._monitoring_loop(name, health_check))
            self.check_tasks[name] = task

        logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop health monitoring."""
        self.running = False

        # Cancel all monitoring tasks
        for task in self.check_tasks.values():
            task.cancel()

        self.check_tasks.clear()
        logger.info("Health monitoring stopped")

    async def _monitoring_loop(self, name: str, health_check: HealthCheck):
        """Monitoring loop for a specific health check."""
        while self.running:
            try:
                result = await self.run_health_check(name)
                self.results[name] = result

                if result.status == HealthStatus.UNHEALTHY and health_check.critical:
                    logger.error(f"Critical health check failed: {name} - {result.message}")

                await asyncio.sleep(health_check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for {name}: {e}")
                await asyncio.sleep(health_check.interval)

    def get_overall_health(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.results:
            return HealthStatus.UNKNOWN

        critical_checks = [
            name for name, check in self.health_checks.items()
            if check.critical
        ]

        # Check critical health checks first
        for name in critical_checks:
            if name in self.results:
                result = self.results[name]
                if result.status == HealthStatus.UNHEALTHY:
                    return HealthStatus.UNHEALTHY

        # Check for degraded status
        unhealthy_count = sum(
            1 for result in self.results.values()
            if result.status == HealthStatus.UNHEALTHY
        )

        total_count = len(self.results)
        unhealthy_ratio = unhealthy_count / total_count

        if unhealthy_ratio > 0.5:
            return HealthStatus.UNHEALTHY
        elif unhealthy_ratio > 0.2:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        overall_status = self.get_overall_health()

        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(
                1 for result in self.results.values()
                if result.status == status
            )

        return {
            "overall_status": overall_status.value,
            "total_checks": len(self.health_checks),
            "status_counts": status_counts,
            "monitoring_active": self.running,
            "last_check_time": max((r.timestamp for r in self.results.values()), default=0.0)
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report."""
        return {
            "summary": self.get_health_summary(),
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "timestamp": result.timestamp,
                    "response_time": result.response_time,
                    "error": result.error
                }
                for name, result in self.results.items()
            }
        }


# Global instance for compatibility
health_monitor = HealthMonitor()

__all__ = [
    "HealthMonitor",
    "HealthCheck",
    "HealthCheckResult",
    "HealthStatus",
    "health_monitor"
]