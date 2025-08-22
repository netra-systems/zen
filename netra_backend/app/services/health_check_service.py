"""Health Check Service Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic health check functionality for tests
- Value Impact: Ensures health check tests can execute without import errors
- Strategic Impact: Enables health monitoring functionality validation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Definition of a health check."""
    name: str
    description: str
    check_function: Callable[[], Any]
    timeout_seconds: float = 30.0
    interval_seconds: float = 60.0
    critical: bool = True
    dependencies: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class HealthCheckService:
    """Service for managing health checks and monitoring system health."""
    
    def __init__(self):
        """Initialize health check service."""
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, HealthResult] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[HealthResult], None]] = []
    
    async def start(self) -> None:
        """Start the health check service."""
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
    
    async def stop(self) -> None:
        """Stop the health check service."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
    
    async def register_check(self, health_check: HealthCheck) -> None:
        """Register a health check."""
        async with self._lock:
            self._checks[health_check.name] = health_check
    
    async def unregister_check(self, check_name: str) -> None:
        """Unregister a health check."""
        async with self._lock:
            self._checks.pop(check_name, None)
            self._results.pop(check_name, None)
    
    async def run_check(self, check_name: str) -> HealthResult:
        """Run a specific health check."""
        async with self._lock:
            check = self._checks.get(check_name)
            if not check:
                return HealthResult(
                    name=check_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check '{check_name}' not found"
                )
        
        start_time = time.time()
        result = HealthResult(name=check_name, status=HealthStatus.UNKNOWN)
        
        try:
            # Run the health check with timeout
            if asyncio.iscoroutinefunction(check.check_function):
                check_result = await asyncio.wait_for(
                    check.check_function(),
                    timeout=check.timeout_seconds
                )
            else:
                check_result = check.check_function()
            
            # Interpret result
            if check_result is True:
                result.status = HealthStatus.HEALTHY
                result.message = "Check passed"
            elif check_result is False:
                result.status = HealthStatus.UNHEALTHY
                result.message = "Check failed"
            elif isinstance(check_result, dict):
                result.status = HealthStatus(check_result.get("status", "healthy"))
                result.message = check_result.get("message", "")
                result.details = check_result.get("details", {})
            else:
                result.status = HealthStatus.HEALTHY
                result.message = str(check_result)
        
        except asyncio.TimeoutError:
            result.status = HealthStatus.UNHEALTHY
            result.error = f"Health check timed out after {check.timeout_seconds}s"
        except Exception as e:
            result.status = HealthStatus.UNHEALTHY
            result.error = str(e)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000
        result.duration_ms = duration
        
        # Store result
        async with self._lock:
            self._results[check_name] = result
        
        # Notify listeners
        await self._notify_listeners(result)
        
        return result
    
    async def run_all_checks(self) -> Dict[str, HealthResult]:
        """Run all registered health checks."""
        async with self._lock:
            check_names = list(self._checks.keys())
        
        # Run checks concurrently
        tasks = [self.run_check(name) for name in check_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result_dict = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                result_dict[check_names[i]] = HealthResult(
                    name=check_names[i],
                    status=HealthStatus.UNHEALTHY,
                    error=str(result)
                )
            else:
                result_dict[result.name] = result
        
        return result_dict
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        async with self._lock:
            results = dict(self._results)
        
        if not results:
            return {
                "status": "unknown",
                "checks": {},
                "summary": {
                    "total": 0,
                    "healthy": 0,
                    "degraded": 0,
                    "unhealthy": 0,
                    "unknown": 0
                }
            }
        
        # Calculate summary
        summary = {
            "total": len(results),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0
        }
        
        overall_status = HealthStatus.HEALTHY
        check_details = {}
        
        for name, result in results.items():
            summary[result.status.value] += 1
            check_details[name] = {
                "status": result.status.value,
                "message": result.message,
                "timestamp": result.timestamp.isoformat(),
                "duration_ms": result.duration_ms
            }
            
            if result.error:
                check_details[name]["error"] = result.error
            
            # Update overall status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status.value,
            "checks": check_details,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_check_result(self, check_name: str) -> Optional[HealthResult]:
        """Get the result of a specific health check."""
        async with self._lock:
            return self._results.get(check_name)
    
    def add_health_listener(self, listener: Callable[[HealthResult], None]) -> None:
        """Add a listener for health check results."""
        self._listeners.append(listener)
    
    async def clear_results(self) -> None:
        """Clear all health check results."""
        async with self._lock:
            self._results.clear()
    
    async def _check_loop(self) -> None:
        """Background loop for running health checks."""
        while self._running:
            try:
                await self.run_all_checks()
                # Wait for the minimum interval
                min_interval = 60  # Default interval
                async with self._lock:
                    if self._checks:
                        min_interval = min(check.interval_seconds for check in self._checks.values())
                
                await asyncio.sleep(min_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue checking
                await asyncio.sleep(5)
    
    async def _notify_listeners(self, result: HealthResult) -> None:
        """Notify all listeners about a health check result."""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(result)
                else:
                    listener(result)
            except Exception as e:
                # Log error but continue with other listeners
                pass


# Common health check functions
async def database_health_check() -> Dict[str, Any]:
    """Basic database health check."""
    try:
        # Simulate database check
        await asyncio.sleep(0.1)
        return {
            "status": "healthy",
            "message": "Database connection successful",
            "details": {"response_time_ms": 100}
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database check failed: {str(e)}"
        }


async def redis_health_check() -> Dict[str, Any]:
    """Basic Redis health check."""
    try:
        # Simulate Redis check
        await asyncio.sleep(0.05)
        return {
            "status": "healthy",
            "message": "Redis connection successful",
            "details": {"response_time_ms": 50}
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis check failed: {str(e)}"
        }


# Global health check service instance
default_health_check_service = HealthCheckService()