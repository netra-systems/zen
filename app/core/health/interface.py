"""Unified Health Check Interface

Base interfaces for standardized health monitoring across all services.
Supports Enterprise SLA requirements with circuit breaker integration.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, UTC
from enum import Enum

from app.logging_config import central_logger
from ..health_types import HealthCheckResult, HealthStatus
from .telemetry import telemetry_manager

logger = central_logger.get_logger(__name__)


class HealthLevel(Enum):
    """Health check complexity levels."""
    BASIC = "basic"
    STANDARD = "standard" 
    COMPREHENSIVE = "comprehensive"


class BaseHealthChecker(ABC):
    """Base interface for all health checkers."""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
        self.circuit_breaker_enabled = True
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        pass
    
    async def check_with_timeout(self) -> HealthCheckResult:
        """Execute health check with timeout protection."""
        try:
            return await asyncio.wait_for(self.check_health(), timeout=self.timeout)
        except asyncio.TimeoutError:
            return self._create_timeout_result()
    
    def _create_timeout_result(self) -> HealthCheckResult:
        """Create timeout result for health check."""
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=self.timeout * 1000,
            error_message=f"Health check timeout after {self.timeout}s"
        )


class HealthInterface:
    """Unified health interface for all services."""
    
    def __init__(self, service_name: str, version: str = "1.0.0", sla_target: float = 99.9):
        self.service_name = service_name
        self.version = version
        self.sla_target = sla_target
        self._checkers: Dict[str, BaseHealthChecker] = {}
        self._start_time = datetime.now(UTC)
        
        # Register with telemetry system for Enterprise monitoring
        telemetry_manager.register_service(service_name, sla_target)
    
    def register_checker(self, checker: BaseHealthChecker) -> None:
        """Register a health checker component."""
        self._checkers[checker.name] = checker
        logger.debug(f"Registered health checker: {checker.name}")
    
    async def get_health_status(self, level: HealthLevel = HealthLevel.BASIC) -> Dict[str, Any]:
        """Get health status based on requested level."""
        if level == HealthLevel.BASIC:
            return await self._get_basic_health()
        elif level == HealthLevel.STANDARD:
            return await self._get_standard_health()
        else:
            return await self._get_comprehensive_health()
    
    async def _get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status - just service availability."""
        return {
            "status": "healthy",
            "service": self.service_name,
            "version": self.version,
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def _get_standard_health(self) -> Dict[str, Any]:
        """Get standard health with key component checks."""
        checks = await self._run_critical_checks()
        overall_status = self._determine_overall_status(checks)
        
        return {
            "status": overall_status.value,
            "service": self.service_name,
            "version": self.version,
            "uptime_seconds": self._get_uptime_seconds(),
            "checks": {name: result.success for name, result in checks.items()},
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def _get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health with detailed metrics."""
        checks = await self._run_all_checks()
        overall_status = self._determine_overall_status(checks)
        
        return {
            "status": overall_status.value,
            "service": self.service_name,
            "version": self.version,
            "uptime_seconds": self._get_uptime_seconds(),
            "checks": self._format_detailed_checks(checks),
            "metrics": await self._get_service_metrics(),
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def _run_critical_checks(self) -> Dict[str, HealthCheckResult]:
        """Run only critical health checks."""
        critical_components = ["postgres", "auth", "core"]
        results = {}
        
        for name, checker in self._checkers.items():
            if any(comp in name.lower() for comp in critical_components):
                results[name] = await checker.check_with_timeout()
        
        return results
    
    async def _run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks and record telemetry data."""
        tasks = {
            name: checker.check_with_timeout() 
            for name, checker in self._checkers.items()
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        health_results = {name: result for name, result in zip(tasks.keys(), results) 
                         if isinstance(result, HealthCheckResult)}
        
        # Record telemetry data for Enterprise monitoring
        telemetry_manager.record_health_data(self.service_name, health_results)
        
        return health_results
    
    def _determine_overall_status(self, checks: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system status from check results."""
        if not checks:
            return HealthStatus.HEALTHY
        
        failed_checks = [r for r in checks.values() if not r.success]
        failure_rate = len(failed_checks) / len(checks)
        
        if failure_rate == 0:
            return HealthStatus.HEALTHY
        elif failure_rate < 0.3:
            return HealthStatus.DEGRADED
        elif failure_rate < 0.7:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL
    
    def _format_detailed_checks(self, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Format detailed check results for comprehensive response."""
        return {
            name: {
                "success": result.success,
                "health_score": result.health_score,
                "response_time_ms": result.response_time_ms,
                "error": result.error_message if not result.success else None
            }
            for name, result in checks.items()
        }
    
    async def _get_service_metrics(self) -> Dict[str, Any]:
        """Get service-specific metrics including Enterprise telemetry."""
        base_metrics = {
            "total_checks": len(self._checkers),
            "uptime_seconds": self._get_uptime_seconds(),
            "circuit_breaker_enabled": True
        }
        
        # Add Enterprise telemetry metrics
        enterprise_metrics = telemetry_manager.get_service_metrics(self.service_name)
        if enterprise_metrics:
            base_metrics.update(enterprise_metrics)
        
        return base_metrics
    
    def _get_uptime_seconds(self) -> float:
        """Calculate service uptime in seconds."""
        return (datetime.now(UTC) - self._start_time).total_seconds()