"""Unified Health Check Interface

Base interfaces for standardized health monitoring across all services.
Supports Enterprise SLA requirements with circuit breaker integration.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.core.health.telemetry import telemetry_manager
from netra_backend.app.core.shared_health_types import HealthStatus
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env
from netra_backend.app.schemas.core_models import HealthCheckResult

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
        self.timeout = self._resolve_timeout(timeout)
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
        timeout_details = self._build_timeout_details()
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=self.timeout * 1000,
            status="unhealthy",
            response_time=self.timeout,
            details=timeout_details
        )
    
    def _build_timeout_details(self) -> Dict[str, Any]:
        """Build timeout result details."""
        return {"component_name": self.name, "success": False, "health_score": 0.0,
                "error_message": f"Health check timeout after {self.timeout}s"}
        
    def _resolve_timeout(self, default_timeout: float) -> float:
        """Resolve timeout from environment or use default."""
        env = get_env()
        env_timeout = env.get("HEALTH_CHECK_TIMEOUT")
        logger.debug(f"_resolve_timeout: env_timeout={env_timeout}, default_timeout={default_timeout}")
        if env_timeout is not None:
            try:
                resolved_timeout = float(env_timeout)
                logger.debug(f"_resolve_timeout: resolved timeout from env: {resolved_timeout}")
                return resolved_timeout
            except (ValueError, TypeError):
                logger.warning(f"Invalid HEALTH_CHECK_TIMEOUT value: {env_timeout}, using default: {default_timeout}")
        logger.debug(f"_resolve_timeout: using default timeout: {default_timeout}")
        return default_timeout


class HealthInterface:
    """Unified health interface for all services."""
    
    def __init__(self, service_name: str, version: str = "1.0.0", sla_target: float = 99.9):
        self._initialize_service_properties(service_name, version, sla_target)
        self._setup_telemetry_registration(service_name, sla_target)
    
    def _initialize_service_properties(self, service_name: str, version: str, sla_target: float) -> None:
        """Initialize core service properties."""
        self.service_name, self.version, self.sla_target = service_name, version, sla_target
        self._checkers: Dict[str, BaseHealthChecker] = {}
        self._start_time = datetime.now(UTC)
    
    def _setup_telemetry_registration(self, service_name: str, sla_target: float) -> None:
        """Register with telemetry system for Enterprise monitoring."""
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
            "timestamp": time.time()
        }
    
    async def _get_standard_health(self) -> Dict[str, Any]:
        """Get standard health with key component checks."""
        checks = await self._run_critical_checks()
        overall_status = self._determine_overall_status(checks)
        return self._build_standard_health_response(overall_status, checks)
    
    def _build_standard_health_response(self, status: HealthStatus, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Build standard health response."""
        return {"status": status.value, "service": self.service_name, "version": self.version,
                "uptime_seconds": self._get_uptime_seconds(), "timestamp": time.time(),
                "checks": {name: result.details.get("success", True) for name, result in checks.items()}}
    
    async def _get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health with detailed metrics."""
        checks = await self._run_all_checks()
        overall_status = self._determine_overall_status(checks)
        return await self._build_comprehensive_health_response(overall_status, checks)
    
    async def _build_comprehensive_health_response(self, status: HealthStatus, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Build comprehensive health response."""
        return {"status": status.value, "service": self.service_name, "version": self.version,
                "uptime_seconds": self._get_uptime_seconds(), "timestamp": time.time(),
                "checks": self._format_detailed_checks(checks), "metrics": await self._get_service_metrics()}
    
    async def _run_critical_checks(self) -> Dict[str, HealthCheckResult]:
        """Run only critical health checks, respecting development mode."""
        results = {}
        for name, checker in self._checkers.items():
            result = await self._execute_checker_by_criticality(name, checker)
            if result is not None:
                results[name] = result
        return results
    
    async def _execute_checker_by_criticality(self, name: str, checker: BaseHealthChecker) -> Optional[HealthCheckResult]:
        """Execute checker based on component criticality."""
        critical_components = ["postgres", "auth", "core"]
        if any(comp in name.lower() for comp in critical_components):
            return await checker.check_with_timeout()
        elif self._is_optional_service(name):
            return await self._run_optional_service_check(name, checker)
        return None
    
    async def _run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks and record telemetry data."""
        tasks = self._create_health_check_tasks()
        health_results = await self._execute_and_filter_results(tasks)
        self._record_telemetry_data(health_results)
        return health_results
    
    def _create_health_check_tasks(self) -> Dict[str, Any]:
        """Create health check tasks for all registered checkers."""
        return {name: checker.check_with_timeout() for name, checker in self._checkers.items()}
    
    async def _execute_and_filter_results(self, tasks: Dict[str, Any]) -> Dict[str, HealthCheckResult]:
        """Execute tasks and filter valid health results."""
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {name: result for name, result in zip(tasks.keys(), results) if isinstance(result, HealthCheckResult)}
    
    def _record_telemetry_data(self, health_results: Dict[str, HealthCheckResult]) -> None:
        """Record telemetry data for Enterprise monitoring."""
        telemetry_manager.record_health_data(self.service_name, health_results)
    
    def _determine_overall_status(self, checks: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system status, treating optional services gracefully."""
        if not checks:
            return HealthStatus.HEALTHY
        return self._calculate_status_from_failure_rate(checks)
    
    def _calculate_status_from_failure_rate(self, checks: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Calculate status based on critical component failure rate."""
        critical_failed = self._count_critical_failures(checks)
        total_critical = self._count_critical_checks(checks)
        return self._map_failure_rate_to_status(critical_failed, total_critical)
    
    def _map_failure_rate_to_status(self, critical_failed: int, total_critical: int) -> HealthStatus:
        """Map failure rate to health status."""
        if total_critical == 0:
            return HealthStatus.HEALTHY
        failure_rate = critical_failed / total_critical
        if failure_rate == 0:
            return HealthStatus.HEALTHY
        elif failure_rate < 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def _format_detailed_checks(self, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Format detailed check results for comprehensive response."""
        return {
            name: self._format_single_check_result(result)
            for name, result in checks.items()
        }
    
    def _format_single_check_result(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Format single health check result."""
        return {"success": result.details.get("success", result.status == "healthy"),
                "health_score": result.details.get("health_score", 1.0 if result.status == "healthy" else 0.0),
                "response_time_ms": result.response_time * 1000,
                "error": result.details.get("error_message") if result.status != "healthy" else None}
    
    async def _get_service_metrics(self) -> Dict[str, Any]:
        """Get service-specific metrics including Enterprise telemetry."""
        base_metrics = self._create_base_metrics()
        return self._enhance_with_enterprise_metrics(base_metrics)
    
    def _create_base_metrics(self) -> Dict[str, Any]:
        """Create base service metrics."""
        return {"total_checks": len(self._checkers), "uptime_seconds": self._get_uptime_seconds(), "circuit_breaker_enabled": True}
    
    def _enhance_with_enterprise_metrics(self, base_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance base metrics with Enterprise telemetry."""
        enterprise_metrics = telemetry_manager.get_service_metrics(self.service_name)
        if enterprise_metrics:
            base_metrics.update(enterprise_metrics)
        return base_metrics
    
    def _get_uptime_seconds(self) -> float:
        """Calculate service uptime in seconds."""
        return (datetime.now(UTC) - self._start_time).total_seconds()
    
    def _is_development_environment(self) -> bool:
        """Check if running in development environment."""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        return config.environment.lower() == "development"
    
    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment."""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        return config.environment.lower() == "staging"
    
    def _is_optional_service(self, component_name: str) -> bool:
        """Check if component is optional in development or staging mode."""
        # CRITICAL FIX: Allow graceful degradation for optional services in staging
        # when they are misconfigured (e.g., missing passwords from Secret Manager)
        if not (self._is_development_environment() or self._is_staging_environment()):
            return False
        
        optional_services = ["redis", "clickhouse"]
        return any(service in component_name.lower() for service in optional_services)
    
    async def _run_optional_service_check(self, name: str, checker: BaseHealthChecker) -> HealthCheckResult:
        """Run optional service check with graceful failure for staging/development."""
        try:
            return await checker.check_with_timeout()
        except Exception as e:
            # In development/staging, treat optional service failures as warnings
            return self._create_optional_service_warning_result(name, str(e))
    
    def _create_optional_service_warning_result(self, component_name: str, error_msg: str) -> HealthCheckResult:
        """Create a warning result for optional services in staging/development."""
        from netra_backend.app.core.health_types import HealthCheckResult
        details = self._build_optional_service_warning_details(component_name, error_msg)
        return HealthCheckResult(
            status="healthy",
            response_time=0.0,
            details=details
        )
    
    def _build_optional_service_warning_details(self, component_name: str, error_msg: str) -> Dict[str, Any]:
        """Build optional service warning result details."""
        env_name = "staging" if self._is_staging_environment() else "development"
        return {"component_name": component_name, "success": True, "health_score": 0.8,
                "error_message": f"{env_name} mode - {component_name} unavailable: {error_msg}",
                "status": f"{env_name}_optional", "available": False}
    
    def _count_critical_failures(self, checks: Dict[str, HealthCheckResult]) -> int:
        """Count failures in critical components only."""
        critical_components = ["postgres", "auth", "core"]
        return sum(1 for name, result in checks.items() 
                  if self._is_critical_component_failed(name, result, critical_components))
    
    def _is_critical_component_failed(self, name: str, result: HealthCheckResult, critical_components: List[str]) -> bool:
        """Check if critical component has failed."""
        if not any(comp in name.lower() for comp in critical_components):
            return False
        success = result.details.get("success", result.status == "healthy")
        return not success
    
    def _count_critical_checks(self, checks: Dict[str, HealthCheckResult]) -> int:
        """Count total critical component checks."""
        critical_components = ["postgres", "auth", "core"]
        return sum(1 for name in checks.keys() 
                  if self._is_critical_component(name, critical_components))
    
    def _is_critical_component(self, name: str, critical_components: List[str]) -> bool:
        """Check if component is critical."""
        return any(comp in name.lower() for comp in critical_components)