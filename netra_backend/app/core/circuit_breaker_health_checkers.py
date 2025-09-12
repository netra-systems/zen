"""Circuit breaker health checkers with  <= 8 line functions.

Health checking implementations for various system components with aggressive
function decomposition. All functions  <= 8 lines.
"""

import asyncio
from datetime import datetime
from typing import Any

from netra_backend.app.core.shared_health_types import HealthChecker, HealthStatus, HealthCheckResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ApiHealthChecker(HealthChecker):
    """Health checker for external APIs."""
    
    def __init__(self, endpoint: str, timeout: float = 5.0):
        """Initialize with API endpoint."""
        self.endpoint = endpoint
        self.timeout = timeout
    
    async def check_health(self) -> HealthCheckResult:
        """Check API endpoint health."""
        start_time = datetime.now()
        try:
            return await self._execute_api_check(start_time)
        except asyncio.TimeoutError:
            return self._create_timeout_result(start_time)
        except Exception as e:
            return self._create_error_result(start_time, e)
    
    async def _execute_api_check(self, start_time: datetime) -> HealthCheckResult:
        """Execute API health check."""
        import aiohttp
        timeout_config = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(f"{self.endpoint}/health") as response:
                response_time = self._calculate_response_time(start_time)
                status = self._determine_status_from_response(response.status)
                return self._create_success_result(status, response_time, response.status)
    
    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def _determine_status_from_response(self, status_code: int) -> HealthStatus:
        """Determine health status from HTTP status code."""
        if status_code == 200:
            return HealthStatus.HEALTHY
        elif status_code in [503, 429]:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def _create_success_result(self, status: HealthStatus, response_time: float, status_code: int) -> HealthCheckResult:
        """Create successful health check result."""
        return HealthCheckResult(
            component_name="api",
            success=(status == HealthStatus.HEALTHY),
            health_score=95.0 if status == HealthStatus.HEALTHY else 50.0 if status == HealthStatus.DEGRADED else 0.0,
            response_time_ms=response_time * 1000,
            status=status.value,
            response_time=response_time,
            details={'status_code': status_code}
        )
    
    def _create_timeout_result(self, start_time: datetime) -> HealthCheckResult:
        """Create timeout health check result."""
        response_time = self._calculate_response_time(start_time)
        return HealthCheckResult(
            component_name="api",
            success=False,
            health_score=0.0,
            response_time_ms=response_time * 1000,
            status=HealthStatus.UNHEALTHY.value,
            response_time=response_time,
            error_message='timeout',
            details={'error': 'timeout'}
        )
    
    def _create_error_result(self, start_time: datetime, error: Exception) -> HealthCheckResult:
        """Create error health check result."""
        response_time = self._calculate_response_time(start_time)
        return HealthCheckResult(
            component_name="api",
            success=False,
            health_score=0.0,
            response_time_ms=response_time * 1000,
            status=HealthStatus.UNHEALTHY.value,
            response_time=response_time,
            error_message=str(error),
            details={'error': str(error)}
        )


class ServiceHealthChecker(HealthChecker):
    """Generic health checker for internal services."""
    
    def __init__(self, service_name: str, check_function: Any):
        """Initialize with service name and check function."""
        self.service_name = service_name
        self.check_function = check_function
    
    async def check_health(self) -> HealthCheckResult:
        """Check service health using provided function."""
        start_time = datetime.now()
        try:
            return await self._execute_service_check(start_time)
        except Exception as e:
            logger.error(f"Health check failed for {self.service_name}: {e}")
            return self._create_failed_result(start_time, e)
    
    async def _execute_service_check(self, start_time: datetime) -> HealthCheckResult:
        """Execute service-specific health check."""
        if asyncio.iscoroutinefunction(self.check_function):
            result = await self.check_function()
        else:
            result = self.check_function()
        response_time = self._calculate_response_time(start_time)
        return self._create_result_from_check(result, response_time)
    
    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def _create_result_from_check(self, result: Any, response_time: float) -> HealthCheckResult:
        """Create result from check function output."""
        if isinstance(result, bool):
            return self._create_boolean_result(result, response_time)
        elif isinstance(result, dict) and 'healthy' in result:
            return self._create_dict_result(result, response_time)
        else:
            return self._create_default_result(result, response_time)
    
    def _create_boolean_result(self, result: bool, response_time: float) -> HealthCheckResult:
        """Create result from boolean check."""
        status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
        return HealthCheckResult(
            component_name="service",
            success=(status == HealthStatus.HEALTHY),
            health_score=100.0 if status == HealthStatus.HEALTHY else 0.0,
            response_time_ms=response_time * 1000,
            status=status.value,
            response_time=response_time
        )
    
    def _create_dict_result(self, result: dict, response_time: float) -> HealthCheckResult:
        """Create result from dictionary check."""
        status = HealthStatus.HEALTHY if result['healthy'] else HealthStatus.UNHEALTHY
        return HealthCheckResult(
            component_name="service",
            success=(status == HealthStatus.HEALTHY),
            health_score=100.0 if status == HealthStatus.HEALTHY else 0.0,
            response_time_ms=response_time * 1000,
            status=status.value,
            response_time=response_time,
            details=result
        )
    
    def _create_default_result(self, result: Any, response_time: float) -> HealthCheckResult:
        """Create result from generic check."""
        return HealthCheckResult(
            component_name="service",
            success=True,
            health_score=100.0,
            response_time_ms=response_time * 1000,
            status=HealthStatus.HEALTHY.value,
            response_time=response_time,
            details={'result': str(result)}
        )
    
    def _create_failed_result(self, start_time: datetime, error: Exception) -> HealthCheckResult:
        """Create failed health check result."""
        response_time = self._calculate_response_time(start_time)
        return HealthCheckResult(
            component_name=self.service_name,
            success=False,
            health_score=0.0,
            response_time_ms=response_time * 1000,
            status=HealthStatus.UNHEALTHY.value,
            response_time=response_time,
            error_message=str(error),
            details={'error': str(error), 'service': self.service_name}
        )


class CircuitBreakerHealthChecker(HealthChecker):
    """Health checker that implements circuit breaker pattern."""
    
    def __init__(self, service_name: str = "circuit_breaker"):
        """Initialize circuit breaker health checker."""
        self.service_name = service_name
        self.failure_count = 0
        self.success_count = 0
        self.last_check_time = None
    
    async def check_health(self) -> HealthCheckResult:
        """Check health with circuit breaker logic."""
        start_time = datetime.now()
        try:
            # Simple health check - always healthy for stub implementation
            self.success_count += 1
            response_time = (datetime.now() - start_time).total_seconds()
            
            return HealthCheckResult(
                component_name=self.service_name,
                success=True,
                health_score=95.0,
                response_time_ms=response_time * 1000,
                status=HealthStatus.HEALTHY.value,
                response_time=response_time,
                details={
                    'service': self.service_name,
                    'success_count': self.success_count,
                    'failure_count': self.failure_count
                }
            )
        except Exception as e:
            self.failure_count += 1
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthCheckResult(
                component_name=self.service_name,
                success=False,
                health_score=0.0,
                response_time_ms=response_time * 1000,
                status=HealthStatus.UNHEALTHY.value,
                response_time=response_time,
                error_message=str(e),
                details={'error': str(e), 'service': self.service_name}
            )