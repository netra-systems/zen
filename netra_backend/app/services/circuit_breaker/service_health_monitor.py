"""Service Health Monitor Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic service health monitoring functionality for tests
- Value Impact: Ensures service health monitoring tests can execute without import errors
- Strategic Impact: Enables service health monitoring validation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ServiceHealthStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Health metrics for a service."""
    response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    success_rate_percent: float = 100.0
    last_check_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class ServiceHealthInfo:
    """Health information for a service."""
    name: str
    status: ServiceHealthStatus = ServiceHealthStatus.UNKNOWN
    metrics: HealthMetrics = field(default_factory=HealthMetrics)
    endpoint: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class ServiceHealthMonitor:
    """Monitors health of services and tracks their status."""
    
    def __init__(self):
        """Initialize service health monitor."""
        self._services: Dict[str, ServiceHealthInfo] = {}
        self._health_checks: Dict[str, Callable] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._check_interval = 30  # seconds
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[str, ServiceHealthInfo], None]] = []
    
    async def start(self) -> None:
        """Start the health monitoring."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self) -> None:
        """Stop the health monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def register_service(
        self, 
        service_name: str, 
        health_check_function: Callable,
        endpoint: Optional[str] = None
    ) -> None:
        """Register a service for health monitoring."""
        async with self._lock:
            self._services[service_name] = ServiceHealthInfo(
                name=service_name,
                endpoint=endpoint
            )
            self._health_checks[service_name] = health_check_function
    
    async def unregister_service(self, service_name: str) -> None:
        """Unregister a service from health monitoring."""
        async with self._lock:
            self._services.pop(service_name, None)
            self._health_checks.pop(service_name, None)
    
    async def check_service_health(self, service_name: str) -> Optional[ServiceHealthInfo]:
        """Check health of a specific service."""
        async with self._lock:
            health_check = self._health_checks.get(service_name)
            service_info = self._services.get(service_name)
            
            if not health_check or not service_info:
                return None
        
        start_time = time.time()
        
        try:
            # Run health check
            if asyncio.iscoroutinefunction(health_check):
                result = await asyncio.wait_for(health_check(), timeout=30)
            else:
                result = health_check()
            
            response_time = (time.time() - start_time) * 1000
            
            # Update service info based on result
            async with self._lock:
                service_info = self._services[service_name]
                service_info.metrics.response_time_ms = response_time
                service_info.metrics.last_check_time = datetime.now()
                service_info.last_updated = datetime.now()
                
                if result is True or (isinstance(result, dict) and result.get("status") == "healthy"):
                    service_info.status = ServiceHealthStatus.HEALTHY
                    service_info.metrics.consecutive_successes += 1
                    service_info.metrics.consecutive_failures = 0
                    service_info.message = "Service is healthy"
                    
                    if isinstance(result, dict):
                        service_info.details = result.get("details", {})
                        service_info.message = result.get("message", "Service is healthy")
                
                elif result is False or (isinstance(result, dict) and result.get("status") == "unhealthy"):
                    service_info.status = ServiceHealthStatus.UNHEALTHY
                    service_info.metrics.consecutive_failures += 1
                    service_info.metrics.consecutive_successes = 0
                    service_info.message = "Service is unhealthy"
                    
                    if isinstance(result, dict):
                        service_info.details = result.get("details", {})
                        service_info.message = result.get("message", "Service is unhealthy")
                
                else:
                    service_info.status = ServiceHealthStatus.DEGRADED
                    service_info.message = "Service status unclear"
                
                # Update success/error rates
                total_checks = service_info.metrics.consecutive_successes + service_info.metrics.consecutive_failures
                if total_checks > 0:
                    service_info.metrics.success_rate_percent = (service_info.metrics.consecutive_successes / total_checks) * 100
                    service_info.metrics.error_rate_percent = 100 - service_info.metrics.success_rate_percent
        
        except asyncio.TimeoutError:
            async with self._lock:
                service_info = self._services[service_name]
                service_info.status = ServiceHealthStatus.UNHEALTHY
                service_info.metrics.consecutive_failures += 1
                service_info.metrics.consecutive_successes = 0
                service_info.message = "Health check timed out"
                service_info.last_updated = datetime.now()
        
        except Exception as e:
            async with self._lock:
                service_info = self._services[service_name]
                service_info.status = ServiceHealthStatus.UNHEALTHY
                service_info.metrics.consecutive_failures += 1
                service_info.metrics.consecutive_successes = 0
                service_info.message = f"Health check failed: {str(e)}"
                service_info.last_updated = datetime.now()
        
        # Notify listeners
        await self._notify_listeners(service_name, service_info)
        
        return service_info
    
    async def get_service_health(self, service_name: str) -> Optional[ServiceHealthInfo]:
        """Get current health information for a service."""
        async with self._lock:
            return self._services.get(service_name)
    
    async def get_all_service_health(self) -> Dict[str, ServiceHealthInfo]:
        """Get health information for all services."""
        async with self._lock:
            return dict(self._services)
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        async with self._lock:
            services = list(self._services.values())
        
        if not services:
            return {
                "total_services": 0,
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "unknown": 0,
                "overall_status": "unknown"
            }
        
        summary = {
            "total_services": len(services),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0
        }
        
        for service in services:
            summary[service.status.value] += 1
        
        # Determine overall status
        if summary["unhealthy"] > 0:
            overall_status = "unhealthy"
        elif summary["degraded"] > 0:
            overall_status = "degraded"
        elif summary["healthy"] == summary["total_services"]:
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        summary["overall_status"] = overall_status
        
        return summary
    
    def add_health_listener(self, listener: Callable[[str, ServiceHealthInfo], None]) -> None:
        """Add a listener for health status changes."""
        self._listeners.append(listener)
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                async with self._lock:
                    service_names = list(self._services.keys())
                
                # Check all services
                for service_name in service_names:
                    await self.check_service_health(service_name)
                
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue monitoring
                await asyncio.sleep(5)
    
    async def _notify_listeners(self, service_name: str, service_info: ServiceHealthInfo) -> None:
        """Notify listeners about health status changes."""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(service_name, service_info)
                else:
                    listener(service_name, service_info)
            except Exception as e:
                # Log error but continue with other listeners
                pass


# Common health check functions
async def http_health_check(url: str) -> Dict[str, Any]:
    """Basic HTTP health check."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": f"HTTP {response.status_code}",
                    "details": {"status_code": response.status_code}
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                    "details": {"status_code": response.status_code}
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"HTTP check failed: {str(e)}"
        }


# Global service health monitor instance
default_service_health_monitor = ServiceHealthMonitor()