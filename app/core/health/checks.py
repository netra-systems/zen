"""Unified Health Check Implementations

Standardized health checkers for databases, services, and dependencies.
Integrates with existing health infrastructure and circuit breakers.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from app.logging_config import central_logger
from ..health_types import HealthCheckResult
from ..health_checkers import (
    check_postgres_health, check_clickhouse_health, 
    check_redis_health, check_websocket_health
)
from .interface import BaseHealthChecker

logger = central_logger.get_logger(__name__)


# Import DatabaseHealthChecker from canonical location - CONSOLIDATED
from app.db.health_checks import DatabaseHealthChecker as CoreDatabaseHealthChecker

class UnifiedDatabaseHealthChecker(BaseHealthChecker):
    """Unified database health checker supporting PostgreSQL and ClickHouse."""
    
    def __init__(self, db_type: str = "postgres", timeout: float = 5.0):
        super().__init__(f"database_{db_type}", timeout)
        self.db_type = db_type
        self._check_function = self._get_check_function()
    
    async def check_health(self) -> HealthCheckResult:
        """Perform database health check."""
        try:
            return await self._check_function()
        except Exception as e:
            return self._create_error_result(str(e))
    
    def _get_check_function(self):
        """Get appropriate check function for database type."""
        check_functions = {
            "postgres": check_postgres_health,
            "clickhouse": check_clickhouse_health,
            "redis": check_redis_health
        }
        return check_functions.get(self.db_type, check_postgres_health)
    
    def _create_error_result(self, error_msg: str) -> HealthCheckResult:
        """Create error result for health check."""
        return HealthCheckResult(
            status="unhealthy",
            response_time=0.0,
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": error_msg
            }
        )


class ServiceHealthChecker(BaseHealthChecker):
    """Health checker for internal service dependencies."""
    
    def __init__(self, service_name: str, endpoint_url: Optional[str] = None):
        super().__init__(f"service_{service_name}")
        self.service_name = service_name
        self.endpoint_url = endpoint_url or f"http://localhost:8080/health"
    
    async def check_health(self) -> HealthCheckResult:
        """Check service health via HTTP endpoint."""
        start_time = time.time()
        
        try:
            result = await self._check_service_endpoint()
            response_time = (time.time() - start_time) * 1000
            return self._create_service_result(result, response_time)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return self._create_service_error(str(e), response_time)
    
    async def _check_service_endpoint(self) -> Dict[str, Any]:
        """Check service endpoint with HTTP client."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.endpoint_url)
            response.raise_for_status()
            return response.json()
    
    def _create_service_result(self, result: Dict[str, Any], response_time: float) -> HealthCheckResult:
        """Create service health result from endpoint response."""
        success = result.get("status") in ["healthy", "ok", "running"]
        health_score = 1.0 if success else 0.0
        
        return HealthCheckResult(
            status="healthy" if success else "unhealthy",
            response_time=response_time / 1000,  # Convert ms to seconds
            details={
                "component_name": self.name,
                "success": success,
                "health_score": health_score,
                "metadata": result
            }
        )
    
    def _create_service_error(self, error_msg: str, response_time: float) -> HealthCheckResult:
        """Create error result for service check."""
        return HealthCheckResult(
            status="unhealthy",
            response_time=response_time / 1000,  # Convert ms to seconds
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": error_msg
            }
        )


class DependencyHealthChecker(BaseHealthChecker):
    """Health checker for external dependencies and integrations."""
    
    def __init__(self, dependency_name: str, check_type: str = "connectivity"):
        super().__init__(f"dependency_{dependency_name}")
        self.dependency_name = dependency_name
        self.check_type = check_type
    
    async def check_health(self) -> HealthCheckResult:
        """Check dependency health based on type."""
        start_time = time.time()
        
        try:
            result = await self._perform_dependency_check()
            response_time = (time.time() - start_time) * 1000
            return self._create_dependency_result(result, response_time)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return self._create_dependency_error(str(e), response_time)
    
    async def _perform_dependency_check(self) -> bool:
        """Perform dependency-specific health check."""
        if self.dependency_name == "websocket":
            result = await check_websocket_health()
            return result.details.get("success", result.status == "healthy")
        elif self.dependency_name == "llm":
            return await self._check_llm_connectivity()
        else:
            return await self._check_generic_dependency()
    
    async def _check_llm_connectivity(self) -> bool:
        """Check LLM service connectivity."""
        try:
            from app.llm.llm_manager import llm_manager
            return llm_manager.is_healthy()
        except Exception:
            return False
    
    async def _check_generic_dependency(self) -> bool:
        """Check generic dependency availability."""
        # Placeholder for generic dependency checks
        await asyncio.sleep(0.01)  # Simulate check
        return True
    
    def _create_dependency_result(self, success: bool, response_time: float) -> HealthCheckResult:
        """Create dependency health result."""
        return HealthCheckResult(
            status="healthy" if success else "unhealthy",
            response_time=response_time / 1000,  # Convert ms to seconds
            details={
                "component_name": self.name,
                "success": success,
                "health_score": 1.0 if success else 0.0
            }
        )
    
    def _create_dependency_error(self, error_msg: str, response_time: float) -> HealthCheckResult:
        """Create error result for dependency check."""
        return HealthCheckResult(
            status="unhealthy",
            response_time=response_time / 1000,  # Convert ms to seconds
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": error_msg
            }
        )


class CircuitBreakerHealthChecker(BaseHealthChecker):
    """Health checker with circuit breaker integration."""
    
    def __init__(self, name: str, wrapped_checker: BaseHealthChecker):
        super().__init__(f"cb_{name}")
        self.wrapped_checker = wrapped_checker
        self.failure_count = 0
        self.failure_threshold = 5
        self.recovery_timeout = 30
        self.last_failure_time: Optional[datetime] = None
        self.circuit_open = False
    
    async def check_health(self) -> HealthCheckResult:
        """Perform health check with circuit breaker protection."""
        if self._should_skip_check():
            return self._create_circuit_open_result()
        
        try:
            result = await self.wrapped_checker.check_health()
            await self._handle_check_result(result)
            return result
        except Exception as e:
            await self._handle_check_failure()
            return self._create_circuit_error_result(str(e))
    
    def _should_skip_check(self) -> bool:
        """Check if circuit breaker should skip the health check."""
        if not self.circuit_open:
            return False
        
        if self.last_failure_time is None:
            return False
        
        time_since_failure = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        return time_since_failure < self.recovery_timeout
    
    async def _handle_check_result(self, result: HealthCheckResult) -> None:
        """Handle successful or failed check result."""
        success = result.details.get("success", result.status == "healthy")
        if success:
            self.failure_count = 0
            self.circuit_open = False
        else:
            await self._handle_check_failure()
    
    async def _handle_check_failure(self) -> None:
        """Handle health check failure and update circuit state."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(f"Circuit breaker opened for {self.name}")
    
    def _create_circuit_open_result(self) -> HealthCheckResult:
        """Create result when circuit breaker is open."""
        return HealthCheckResult(
            status="unhealthy",
            response_time=0.0,
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": "Circuit breaker open - service unavailable"
            }
        )
    
    def _create_circuit_error_result(self, error_msg: str) -> HealthCheckResult:
        """Create error result for circuit breaker failure."""
        return HealthCheckResult(
            status="unhealthy",
            response_time=0.0,
            details={
                "component_name": self.name,
                "success": False,
                "health_score": 0.0,
                "error_message": f"Circuit breaker error: {error_msg}"
            }
        )


# Alias for unified health system compatibility
DatabaseHealthChecker = UnifiedDatabaseHealthChecker