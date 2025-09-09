"""
Health Checker - SSOT Service Initialization Implementation

This module provides health checking functionality for the Netra platform.
Following SSOT principles, this is the canonical implementation for service health monitoring.

Business Value: Platform/Internal - System Reliability & Monitoring
Ensures all platform services are healthy and operational across all environments.

CRITICAL: This is a minimal SSOT-compliant stub to resolve import errors.
Full implementation should follow CLAUDE.md SSOT patterns.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: HealthStatus
    service_name: str
    check_name: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class ServiceHealth:
    """Overall health status of a service."""
    service_name: str
    overall_status: HealthStatus
    last_check: datetime
    checks: List[HealthCheckResult] = field(default_factory=list)
    uptime_percentage: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    SSOT Health Checker.
    
    This is the canonical implementation for all health checking across the platform.
    Provides comprehensive health monitoring for services, dependencies, and resources.
    """
    
    def __init__(self):
        """Initialize health checker with SSOT environment."""
        self._env = get_env()
        self._checks: Dict[str, Callable] = {}
        self._service_health: Dict[str, ServiceHealth] = {}
        self._check_interval = int(self._env.get("HEALTH_CHECK_INTERVAL", "30"))
        self._enabled = self._env.get("HEALTH_CHECKER_ENABLED", "true").lower() == "true"
        self._is_running = False
    
    def register_check(self, 
                      service_name: str,
                      check_name: str,
                      check_func: Callable,
                      timeout: float = 5.0) -> None:
        """
        Register a health check for a service.
        
        Args:
            service_name: Name of the service
            check_name: Name of the health check
            check_func: Function that performs the health check
            timeout: Timeout for the health check in seconds
        """
        check_key = f"{service_name}:{check_name}"
        self._checks[check_key] = {
            "service_name": service_name,
            "check_name": check_name,
            "func": check_func,
            "timeout": timeout
        }
        
        # Initialize service health if not exists
        if service_name not in self._service_health:
            self._service_health[service_name] = ServiceHealth(
                service_name=service_name,
                overall_status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow()
            )
        
        logger.info(f"Registered health check '{check_name}' for service '{service_name}'")
    
    async def run_check(self, service_name: str, check_name: str) -> HealthCheckResult:
        """
        Run a specific health check.
        
        Args:
            service_name: Name of the service
            check_name: Name of the health check
            
        Returns:
            Health check result
        """
        check_key = f"{service_name}:{check_name}"
        
        if check_key not in self._checks:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                service_name=service_name,
                check_name=check_name,
                timestamp=datetime.utcnow(),
                response_time_ms=0.0,
                error_message=f"Check '{check_name}' not registered for service '{service_name}'"
            )
        
        check_config = self._checks[check_key]
        start_time = time.time()
        
        try:
            # Run the health check with timeout
            if asyncio.iscoroutinefunction(check_config["func"]):
                result = await asyncio.wait_for(
                    check_config["func"](),
                    timeout=check_config["timeout"]
                )
            else:
                result = check_config["func"]()
            
            response_time = (time.time() - start_time) * 1000
            
            # Interpret result
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "healthy"))
                details = result.get("details", {})
                error_message = result.get("error")
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                details = {}
                error_message = None
            else:
                status = HealthStatus.HEALTHY
                details = {"result": str(result)}
                error_message = None
            
            return HealthCheckResult(
                status=status,
                service_name=service_name,
                check_name=check_name,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details=details,
                error_message=error_message
            )
            
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                service_name=service_name,
                check_name=check_name,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                error_message=f"Health check timed out after {check_config['timeout']} seconds"
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.exception(f"Health check failed for {service_name}:{check_name}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                service_name=service_name,
                check_name=check_name,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """
        Check health of all registered checks for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service health status
        """
        if service_name not in self._service_health:
            return ServiceHealth(
                service_name=service_name,
                overall_status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                metadata={"error": "Service not registered"}
            )
        
        # Find all checks for this service
        service_checks = [
            key for key in self._checks.keys() 
            if key.startswith(f"{service_name}:")
        ]
        
        if not service_checks:
            # No checks registered, assume healthy
            self._service_health[service_name].overall_status = HealthStatus.HEALTHY
            self._service_health[service_name].last_check = datetime.utcnow()
            return self._service_health[service_name]
        
        # Run all checks for the service
        check_results = []
        for check_key in service_checks:
            _, check_name = check_key.split(":", 1)
            result = await self.run_check(service_name, check_name)
            check_results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(check_results)
        
        # Update service health
        service_health = self._service_health[service_name]
        service_health.overall_status = overall_status
        service_health.last_check = datetime.utcnow()
        service_health.checks = check_results
        
        return service_health
    
    def _determine_overall_status(self, check_results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall status from individual check results."""
        if not check_results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in check_results]
        
        # If any check is unhealthy, service is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any check is degraded, service is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        # If all checks are healthy, service is healthy
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        
        # If we have unknown statuses, service is unknown
        return HealthStatus.UNKNOWN
    
    async def get_system_health(self) -> Dict[str, ServiceHealth]:
        """
        Get health status of all registered services.
        
        Returns:
            Dictionary mapping service names to their health status
        """
        if not self._enabled:
            return {}
        
        system_health = {}
        
        for service_name in self._service_health.keys():
            try:
                health = await self.check_service_health(service_name)
                system_health[service_name] = health
            except Exception as e:
                logger.exception(f"Failed to check health for service {service_name}")
                system_health[service_name] = ServiceHealth(
                    service_name=service_name,
                    overall_status=HealthStatus.UNHEALTHY,
                    last_check=datetime.utcnow(),
                    metadata={"error": str(e)}
                )
        
        return system_health
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of system health.
        
        Returns:
            Health summary dictionary
        """
        if not self._service_health:
            return {
                "overall_status": "unknown",
                "total_services": 0,
                "healthy_services": 0,
                "unhealthy_services": 0,
                "services": []
            }
        
        services = list(self._service_health.values())
        healthy_count = sum(1 for s in services if s.overall_status == HealthStatus.HEALTHY)
        unhealthy_count = sum(1 for s in services if s.overall_status == HealthStatus.UNHEALTHY)
        
        # Determine overall system status
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif healthy_count == len(services):
            overall_status = "healthy"
        else:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "total_services": len(services),
            "healthy_services": healthy_count,
            "unhealthy_services": unhealthy_count,
            "services": [
                {
                    "name": s.service_name,
                    "status": s.overall_status.value,
                    "last_check": s.last_check.isoformat()
                }
                for s in services
            ]
        }


# Common health check functions
async def database_health_check() -> Dict[str, Any]:
    """Basic database health check."""
    try:
        # This would typically check database connectivity
        # For now, return a stub
        return {
            "status": "healthy",
            "details": {"connection": "ok"}
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def redis_health_check() -> Dict[str, Any]:
    """Basic Redis health check."""
    try:
        # This would typically check Redis connectivity
        # For now, return a stub
        return {
            "status": "healthy",
            "details": {"connection": "ok"}
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# SSOT Factory Function
def create_health_checker() -> HealthChecker:
    """
    SSOT factory function for creating health checker instances.
    
    Returns:
        Configured health checker
    """
    return HealthChecker()


# Export SSOT interface
__all__ = [
    "HealthChecker",
    "HealthCheckResult",
    "ServiceHealth",
    "HealthStatus",
    "database_health_check",
    "redis_health_check",
    "create_health_checker"
]