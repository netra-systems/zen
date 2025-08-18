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
from ..shared_health_types import HealthStatus
from app.schemas.core_models import HealthCheckResult
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
            status="unhealthy",
            response_time=self.timeout,
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": f"Health check timeout after {self.timeout}s"
            }
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
            "checks": {name: result.details.get("success", True) for name, result in checks.items()},
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
        """Run only critical health checks, respecting development mode."""
        critical_components = ["postgres", "auth", "core"]
        results = {}
        
        for name, checker in self._checkers.items():
            if any(comp in name.lower() for comp in critical_components):
                results[name] = await checker.check_with_timeout()
            elif self._is_optional_in_development(name):
                results[name] = await self._run_optional_development_check(name, checker)
        
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
        """Determine overall system status, treating optional services gracefully."""
        if not checks:
            return HealthStatus.HEALTHY
        
        critical_failed = self._count_critical_failures(checks)
        total_critical = self._count_critical_checks(checks)
        
        if total_critical == 0:
            return HealthStatus.HEALTHY
        
        failure_rate = critical_failed / total_critical if total_critical > 0 else 0
        
        if failure_rate == 0:
            return HealthStatus.HEALTHY
        elif failure_rate < 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def _format_detailed_checks(self, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Format detailed check results for comprehensive response."""
        return {
            name: {
                "success": result.details.get("success", result.status == "healthy"),
                "health_score": result.details.get("health_score", 1.0 if result.status == "healthy" else 0.0),
                "response_time_ms": result.response_time * 1000,  # Convert seconds to ms
                "error": result.details.get("error_message") if result.status != "healthy" else None
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
    
    def _is_development_environment(self) -> bool:
        """Check if running in development environment."""
        import os
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        return environment == "development"
    
    def _is_optional_in_development(self, component_name: str) -> bool:
        """Check if component is optional in development mode."""
        if not self._is_development_environment():
            return False
        
        optional_services = ["redis", "clickhouse"]
        return any(service in component_name.lower() for service in optional_services)
    
    async def _run_optional_development_check(self, name: str, checker: BaseHealthChecker) -> HealthCheckResult:
        """Run optional development check with graceful failure."""
        try:
            return await checker.check_with_timeout()
        except Exception as e:
            # In development, treat optional service failures as warnings
            return self._create_development_warning_result(name, str(e))
    
    def _create_development_warning_result(self, component_name: str, error_msg: str) -> HealthCheckResult:
        """Create a warning result for optional development services."""
        from ..health_types import HealthCheckResult
        return HealthCheckResult(
            status="healthy",  # Mark as healthy in development
            response_time=0.0,
            details={
                "component_name": component_name,
                "success": True,
                "health_score": 0.8,  # Slightly degraded but acceptable
                "error_message": f"Development mode - {component_name} unavailable: {error_msg}",
                "status": "development_optional",
                "available": False
            }
        )
    
    def _count_critical_failures(self, checks: Dict[str, HealthCheckResult]) -> int:
        """Count failures in critical components only."""
        critical_components = ["postgres", "auth", "core"]
        critical_failed = 0
        
        for name, result in checks.items():
            if any(comp in name.lower() for comp in critical_components):
                success = result.details.get("success", result.status == "healthy")
                if not success:
                    critical_failed += 1
        
        return critical_failed
    
    def _count_critical_checks(self, checks: Dict[str, HealthCheckResult]) -> int:
        """Count total critical component checks."""
        critical_components = ["postgres", "auth", "core"]
        critical_count = 0
        
        for name in checks.keys():
            if any(comp in name.lower() for comp in critical_components):
                critical_count += 1
        
        return critical_count