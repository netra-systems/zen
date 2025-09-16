from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
"""
Unified health check service managing all health checks.
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

from netra_backend.app.core.health_types import (
    CheckType,
    HealthCheckConfig,
    HealthCheckResult,
    HealthStatus,
    StandardHealthResponse
)
from netra_backend.app.core.unified_logging import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedHealthService:
    """Centralized health check service managing all health checks."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self._checks: Dict[str, HealthCheckConfig] = {}
        self._results_cache: Dict[str, HealthCheckResult] = {}
        self._cache_ttl = 30  # seconds
        self._last_check_time: Dict[str, float] = {}
        self._is_shutting_down = False
        self._shutdown_timestamp: Optional[float] = None
        
    async def register_check(self, config: HealthCheckConfig) -> None:
        """Register a new health check."""
        self._checks[config.name] = config
        logger.info(f"Registered health check: {config.name} ({config.check_type.value})")
    
    async def unregister_check(self, check_name: str) -> None:
        """Remove a health check."""
        self._checks.pop(check_name, None)
        self._results_cache.pop(check_name, None)
        self._last_check_time.pop(check_name, None)
    
    async def run_check(self, check_name: str, force_refresh: bool = False) -> HealthCheckResult:
        """Run a specific health check with caching."""
        if not force_refresh and self._is_result_cached(check_name):
            return self._results_cache[check_name]
        
        config = self._checks.get(check_name)
        if not config:
            return self._create_error_result(check_name, "Check not found")
        
        start_time = time.time()
        try:
            # Execute check with timeout
            if asyncio.iscoroutinefunction(config.check_function):
                result = await asyncio.wait_for(
                    config.check_function(),
                    timeout=config.timeout_seconds
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, config.check_function
                )
            
            # Convert result to standard format
            health_result = self._process_check_result(config, result, start_time)
            
        except asyncio.TimeoutError:
            health_result = self._create_timeout_result(config, start_time)
        except Exception as e:
            health_result = self._create_error_result(config.name, str(e), start_time)
        
        # Cache result
        self._results_cache[check_name] = health_result
        self._last_check_time[check_name] = time.time()
        
        return health_result
    
    async def get_liveness(self) -> StandardHealthResponse:
        """Get liveness status - is the service alive?"""
        liveness_checks = [name for name, config in self._checks.items() 
                          if config.check_type == CheckType.LIVENESS]
        
        if not liveness_checks:
            # If no liveness checks defined, use basic service liveness
            return self._create_basic_liveness_response()
        
        results = await self._run_checks_by_names(liveness_checks)
        return self._build_response(results, "liveness")
    
    async def get_readiness(self) -> StandardHealthResponse:
        """Get readiness status - is the service ready to serve traffic?"""
        # If shutting down, immediately return not ready
        if self._is_shutting_down:
            from datetime import datetime, UTC
            return StandardHealthResponse(
                status=HealthStatus.UNHEALTHY.value,
                service_name=self.service_name,
                version=self.version,
                timestamp=datetime.now(UTC).isoformat(),
                environment=self._get_environment(),
                summary={
                    "message": "Service is shutting down",
                    "shutdown_elapsed_seconds": time.time() - self._shutdown_timestamp if self._shutdown_timestamp else 0
                },
                details=self.get_shutdown_status()
            )
        
        readiness_checks = [name for name, config in self._checks.items() 
                           if config.check_type == CheckType.READINESS]
        
        results = await self._run_checks_by_names(readiness_checks)
        return self._build_response(results, "readiness")
    
    async def get_health(self, include_details: bool = True) -> StandardHealthResponse:
        """Get comprehensive health status."""
        all_results = await self.run_all_checks()
        return self._build_response(all_results, "health", include_details)
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks concurrently."""
        if not self._checks:
            return {}
        
        tasks = [self.run_check(name) for name in self._checks.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result_dict = {}
        for i, result in enumerate(results):
            check_name = list(self._checks.keys())[i]
            if isinstance(result, Exception):
                result_dict[check_name] = self._create_error_result(check_name, str(result))
            else:
                result_dict[check_name] = result
        
        return result_dict
    
    async def _run_checks_by_names(self, check_names: List[str]) -> Dict[str, HealthCheckResult]:
        """Run specific checks by name."""
        tasks = [self.run_check(name) for name in check_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result_dict = {}
        for i, result in enumerate(results):
            check_name = check_names[i]
            if isinstance(result, Exception):
                result_dict[check_name] = self._create_error_result(check_name, str(result))
            else:
                result_dict[check_name] = result
        
        return result_dict
    
    def _is_result_cached(self, check_name: str) -> bool:
        """Check if result is cached and still valid."""
        if check_name not in self._results_cache:
            return False
        
        last_check = self._last_check_time.get(check_name, 0)
        return (time.time() - last_check) < self._cache_ttl
    
    def _process_check_result(self, config: HealthCheckConfig, result: Any, 
                            start_time: float) -> HealthCheckResult:
        """Process check result into standard format."""
        response_time_ms = (time.time() - start_time) * 1000
        
        # Handle different result formats
        if isinstance(result, dict):
            status = result.get('status', HealthStatus.HEALTHY.value)
            message = result.get('message', config.description)
            details = result.get('details')
        elif isinstance(result, bool):
            status = HealthStatus.HEALTHY.value if result else HealthStatus.UNHEALTHY.value
            message = config.description
            details = None
        else:
            status = HealthStatus.HEALTHY.value
            message = str(result) if result else config.description
            details = None
        
        # Determine success and health score based on status
        success = status == HealthStatus.HEALTHY.value
        health_score = 1.0 if success else 0.0
        
        return HealthCheckResult(
            component_name=config.name,
            success=success,
            health_score=health_score,
            response_time_ms=response_time_ms,
            status=status,
            message=message,
            details=details or {},
            labels=config.labels
        )
    
    def _create_error_result(self, check_name: str, error: str, 
                           start_time: Optional[float] = None) -> HealthCheckResult:
        """Create error result for failed check."""
        response_time_ms = (time.time() - start_time) * 1000 if start_time else 0
        
        return HealthCheckResult(
            component_name=check_name,
            status=HealthStatus.UNHEALTHY.value,
            response_time_ms=response_time_ms,
            success=False,
            health_score=0.0,
            error_message=f"Check failed: {error}",
            details={"error": error}
        )
    
    def _create_timeout_result(self, config: HealthCheckConfig, 
                             start_time: float) -> HealthCheckResult:
        """Create timeout result for check that exceeded timeout."""
        response_time_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            component_name=config.name,
            status=HealthStatus.UNHEALTHY.value,
            response_time_ms=response_time_ms,
            message=f"Check timed out after {config.timeout_seconds}s",
            details={"timeout": config.timeout_seconds},
            labels=config.labels
        )
    
    def _build_response(self, results: Dict[str, HealthCheckResult], 
                       check_context: str, include_details: bool = True) -> StandardHealthResponse:
        """Build standardized health response."""
        from datetime import datetime, UTC
        
        overall_status = self._calculate_overall_status(results)
        checks_data = [self._format_check_result(name, result) for name, result in results.items()]
        
        response = StandardHealthResponse(
            status=overall_status,
            service_name=self.service_name,
            version=self.version,
            timestamp=datetime.now(UTC).isoformat(),
            environment=self._get_environment(),
            checks=checks_data,
            summary=self._build_summary(results)
        )
        
        if include_details:
            response.details = self._build_details(results, check_context)
        
        return response
    
    def _calculate_overall_status(self, results: Dict[str, HealthCheckResult]) -> str:
        """Calculate overall status based on priority-weighted results."""
        if not results:
            return HealthStatus.HEALTHY.value
        
        # Priority-based assessment
        critical_unhealthy = False
        has_degraded = False
        
        for name, result in results.items():
            config = self._checks.get(name)
            if not config:
                continue
                
            if result.status == HealthStatus.UNHEALTHY.value:
                if config.priority == 1:  # Critical
                    critical_unhealthy = True
                elif config.priority == 2:  # Important
                    has_degraded = True
            elif result.status == HealthStatus.DEGRADED.value:
                has_degraded = True
        
        if critical_unhealthy:
            return HealthStatus.UNHEALTHY.value
        elif has_degraded:
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.HEALTHY.value
    
    def _format_check_result(self, name: str, result: HealthCheckResult) -> Dict[str, Any]:
        """Format check result for response."""
        return {
            "name": result.component_name,
            "status": result.status,
            "response_time_ms": result.response_time_ms,
            "message": result.message,
            "labels": result.labels,
            "last_check": result.last_check,
            "details": result.details
        }
    
    def _build_summary(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Build summary statistics."""
        total_checks = len(results)
        healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY.value)
        degraded = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED.value)
        unhealthy = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY.value)
        
        # Calculate health score (0-1)
        if total_checks > 0:
            # Weight by priority
            weighted_score = 0
            total_weight = 0
            for name, result in results.items():
                config = self._checks.get(name)
                if config:
                    weight = 4 - config.priority  # Priority 1 = weight 3, Priority 3 = weight 1
                    if result.status == HealthStatus.HEALTHY.value:
                        weighted_score += weight
                    elif result.status == HealthStatus.DEGRADED.value:
                        weighted_score += weight * 0.5
                    total_weight += weight
            
            health_score = weighted_score / total_weight if total_weight > 0 else 0
        else:
            health_score = 1.0
        
        return {
            "total_checks": total_checks,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "overall_health_score": round(health_score, 2)
        }
    
    def _build_details(self, results: Dict[str, HealthCheckResult], 
                      check_context: str) -> Dict[str, Any]:
        """Build detailed information."""
        return {
            "check_context": check_context,
            "environment_info": {
                "environment": self._get_environment(),
                "service": self.service_name,
                "version": self.version
            },
            "configuration": {
                "cache_ttl_seconds": self._cache_ttl,
                "total_registered_checks": len(self._checks)
            }
        }
    
    def _create_basic_liveness_response(self) -> StandardHealthResponse:
        """Create basic liveness response when no checks defined."""
        from datetime import datetime, UTC
        
        return StandardHealthResponse(
            status=HealthStatus.HEALTHY.value,
            service_name=self.service_name,
            version=self.version,
            timestamp=datetime.now(UTC).isoformat(),
            environment=self._get_environment(),
            summary={"message": "Service is alive"}
        )
    
    def _get_environment(self) -> str:
        """Get current environment."""
        return get_env().get('ENVIRONMENT', 'development')
    
    async def mark_shutting_down(self) -> None:
        """Mark service as shutting down for graceful shutdown."""
        self._is_shutting_down = True
        self._shutdown_timestamp = time.time()
        logger.info("Health service marked as shutting down")
    
    def is_shutting_down(self) -> bool:
        """Check if service is in shutdown mode."""
        return self._is_shutting_down
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """Get shutdown status information."""
        if not self._is_shutting_down:
            return {"shutting_down": False}
        
        elapsed = time.time() - self._shutdown_timestamp if self._shutdown_timestamp else 0
        return {
            "shutting_down": True,
            "shutdown_elapsed_seconds": elapsed,
            "shutdown_timestamp": self._shutdown_timestamp
        }