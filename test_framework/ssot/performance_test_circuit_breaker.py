"""
Performance Test Circuit Breaker System

This module provides pre-flight infrastructure health checks with timeouts to prevent
E2E tests from hanging indefinitely when Redis/PostgreSQL are degraded or unavailable.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Prevents test suite hangs that block development workflows and waste developer time.

CRITICAL: Tests should fail fast with clear error categorization instead of hanging
for minutes when infrastructure is degraded.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
import psycopg2
import redis.asyncio as redis
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class InfrastructureStatus(Enum):
    """Infrastructure component status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ComponentHealthCheck:
    """Individual infrastructure component health check result."""
    component: str
    status: InfrastructureStatus
    response_time_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_healthy(self) -> bool:
        """Check if component is healthy enough for testing."""
        return self.status in [InfrastructureStatus.HEALTHY, InfrastructureStatus.DEGRADED]


@dataclass
class CircuitBreakerConfig:
    """Configuration for performance test circuit breaker."""
    # Component timeout limits (ms)
    redis_timeout_ms: int = 5000
    postgres_timeout_ms: int = 5000 
    http_timeout_ms: int = 10000
    websocket_timeout_ms: int = 15000
    
    # Circuit breaker thresholds
    max_consecutive_failures: int = 3
    failure_rate_threshold: float = 0.5  # 50%
    circuit_open_duration_seconds: int = 60
    
    # Health check intervals
    health_check_interval_ms: int = 30000
    
    @classmethod
    def for_environment(cls, environment: str = "test") -> "CircuitBreakerConfig":
        """Create config optimized for specific environment."""
        if environment == "staging":
            # More lenient timeouts for GCP staging
            return cls(
                redis_timeout_ms=10000,
                postgres_timeout_ms=10000,
                http_timeout_ms=15000,
                websocket_timeout_ms=30000,
            )
        elif environment == "production":
            # Stricter timeouts for production
            return cls(
                redis_timeout_ms=3000,
                postgres_timeout_ms=3000,
                http_timeout_ms=5000,
                websocket_timeout_ms=10000,
            )
        else:
            # Default test environment timeouts
            return cls()


class PerformanceTestCircuitBreaker:
    """
    Circuit breaker for performance tests to prevent hanging on degraded infrastructure.
    
    Performs pre-flight health checks with timeouts and fails fast when infrastructure
    is unavailable, preventing test suite hangs and providing clear error categorization.
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, environment: str = "test"):
        """Initialize circuit breaker with configuration."""
        self.config = config or CircuitBreakerConfig.for_environment(environment)
        self.environment = environment
        self.env = get_env()
        
        # Circuit breaker state
        self.component_failures: Dict[str, int] = {}
        self.circuit_open_until: Dict[str, datetime] = {}
        self.last_health_check: Dict[str, datetime] = {}
        self.health_results: Dict[str, ComponentHealthCheck] = {}
        
        # Connection pools (reused for efficiency)
        self._redis_client: Optional[redis.Redis] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Performance test circuit breaker initialized for {environment}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize circuit breaker resources."""
        try:
            # Initialize reusable HTTP client
            self._http_client = httpx.AsyncClient(timeout=self.config.http_timeout_ms / 1000)
            logger.debug("Circuit breaker resources initialized")
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker: {e}")
            raise
    
    async def cleanup(self):
        """Clean up circuit breaker resources."""
        try:
            if self._redis_client:
                await self._redis_client.close()
                self._redis_client = None
            
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None
            
            logger.debug("Circuit breaker resources cleaned up")
        except Exception as e:
            logger.error(f"Circuit breaker cleanup failed: {e}")
    
    def is_circuit_open(self, component: str) -> bool:
        """Check if circuit is open for a component."""
        if component not in self.circuit_open_until:
            return False
        
        if datetime.now() > self.circuit_open_until[component]:
            # Circuit breaker timeout expired, close circuit
            del self.circuit_open_until[component]
            self.component_failures[component] = 0
            return False
        
        return True
    
    def record_failure(self, component: str):
        """Record a failure for a component."""
        self.component_failures[component] = self.component_failures.get(component, 0) + 1
        
        if self.component_failures[component] >= self.config.max_consecutive_failures:
            # Open circuit breaker
            self.circuit_open_until[component] = (
                datetime.now() + timedelta(seconds=self.config.circuit_open_duration_seconds)
            )
            logger.warning(
                f"Circuit breaker OPENED for {component} "
                f"after {self.component_failures[component]} failures"
            )
    
    def record_success(self, component: str):
        """Record a success for a component."""
        self.component_failures[component] = 0
        if component in self.circuit_open_until:
            del self.circuit_open_until[component]
    
    async def check_redis_health(self) -> ComponentHealthCheck:
        """Check Redis connectivity and performance."""
        component = "redis"
        start_time = time.time()
        
        if self.is_circuit_open(component):
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.UNAVAILABLE,
                response_time_ms=0,
                error="Circuit breaker open - too many consecutive failures"
            )
        
        try:
            # Get Redis connection string from environment
            redis_url = self.env.get("REDIS_URL", "redis://localhost:6379/0")
            
            if not self._redis_client:
                self._redis_client = redis.from_url(
                    redis_url,
                    socket_timeout=self.config.redis_timeout_ms / 1000,
                    socket_connect_timeout=self.config.redis_timeout_ms / 1000,
                    decode_responses=True
                )
            
            # Test basic Redis operations
            async with asyncio.timeout(self.config.redis_timeout_ms / 1000):
                # Test connectivity
                await self._redis_client.ping()
                
                # Test basic operations
                test_key = f"circuit_breaker_test_{int(time.time())}"
                await self._redis_client.set(test_key, "test_value", ex=10)
                result = await self._redis_client.get(test_key)
                await self._redis_client.delete(test_key)
                
                if result != "test_value":
                    raise Exception("Redis read/write test failed")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time < 100:
                status = InfrastructureStatus.HEALTHY
            elif response_time < 1000:
                status = InfrastructureStatus.DEGRADED
            else:
                status = InfrastructureStatus.DEGRADED
            
            self.record_success(component)
            
            return ComponentHealthCheck(
                component=component,
                status=status,
                response_time_ms=response_time,
                details={"redis_url": redis_url}
            )
            
        except asyncio.TimeoutError:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.TIMEOUT,
                response_time_ms=(time.time() - start_time) * 1000,
                error=f"Redis health check timeout after {self.config.redis_timeout_ms}ms"
            )
        except Exception as e:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.ERROR,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def check_postgres_health(self) -> ComponentHealthCheck:
        """Check PostgreSQL connectivity and performance."""
        component = "postgres"
        start_time = time.time()
        
        if self.is_circuit_open(component):
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.UNAVAILABLE,
                response_time_ms=0,
                error="Circuit breaker open - too many consecutive failures"
            )
        
        try:
            # Get PostgreSQL connection details from environment
            pg_host = self.env.get("POSTGRES_HOST", "localhost")
            pg_port = int(self.env.get("POSTGRES_PORT", "5432"))
            pg_db = self.env.get("POSTGRES_DB", "netra_test")
            pg_user = self.env.get("POSTGRES_USER", "postgres")
            pg_password = self.env.get("POSTGRES_PASSWORD", "password")
            
            # Create connection with timeout
            conn_string = f"host={pg_host} port={pg_port} dbname={pg_db} user={pg_user} password={pg_password}"
            
            async with asyncio.timeout(self.config.postgres_timeout_ms / 1000):
                # Use synchronous connection for simplicity (wrapped in timeout)
                def connect_and_test():
                    conn = psycopg2.connect(
                        conn_string,
                        connect_timeout=self.config.postgres_timeout_ms // 1000
                    )
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT 1")
                            result = cursor.fetchone()
                            if result[0] != 1:
                                raise Exception("PostgreSQL test query failed")
                    finally:
                        conn.close()
                
                # Run in thread pool to avoid blocking
                await asyncio.get_event_loop().run_in_executor(None, connect_and_test)
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time < 100:
                status = InfrastructureStatus.HEALTHY
            elif response_time < 1000:
                status = InfrastructureStatus.DEGRADED
            else:
                status = InfrastructureStatus.DEGRADED
            
            self.record_success(component)
            
            return ComponentHealthCheck(
                component=component,
                status=status,
                response_time_ms=response_time,
                details={"postgres_host": pg_host, "postgres_port": pg_port}
            )
            
        except asyncio.TimeoutError:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.TIMEOUT,
                response_time_ms=(time.time() - start_time) * 1000,
                error=f"PostgreSQL health check timeout after {self.config.postgres_timeout_ms}ms"
            )
        except Exception as e:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.ERROR,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def check_http_service_health(self, service_name: str, url: str) -> ComponentHealthCheck:
        """Check HTTP service health (backend, auth service, etc.)."""
        component = f"http_{service_name}"
        start_time = time.time()
        
        if self.is_circuit_open(component):
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.UNAVAILABLE,
                response_time_ms=0,
                error="Circuit breaker open - too many consecutive failures"
            )
        
        try:
            async with asyncio.timeout(self.config.http_timeout_ms / 1000):
                response = await self._http_client.get(url)
                
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time < 500:
                    status = InfrastructureStatus.HEALTHY
                elif response_time < 2000:
                    status = InfrastructureStatus.DEGRADED
                else:
                    status = InfrastructureStatus.DEGRADED
                
                self.record_success(component)
            else:
                status = InfrastructureStatus.ERROR
                self.record_failure(component)
            
            return ComponentHealthCheck(
                component=component,
                status=status,
                response_time_ms=response_time,
                details={"url": url, "status_code": response.status_code},
                error=None if response.status_code == 200 else f"HTTP {response.status_code}"
            )
            
        except asyncio.TimeoutError:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.TIMEOUT,
                response_time_ms=(time.time() - start_time) * 1000,
                error=f"HTTP service {service_name} timeout after {self.config.http_timeout_ms}ms"
            )
        except Exception as e:
            self.record_failure(component)
            return ComponentHealthCheck(
                component=component,
                status=InfrastructureStatus.ERROR,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def perform_preflight_checks(self, required_components: Optional[List[str]] = None) -> Dict[str, ComponentHealthCheck]:
        """
        Perform pre-flight infrastructure health checks.
        
        Args:
            required_components: List of required components. If None, checks all common components.
            
        Returns:
            Dictionary of component names to health check results
        """
        if required_components is None:
            required_components = ["redis", "postgres", "backend"]
        
        logger.info(f"Starting pre-flight health checks for: {required_components}")
        
        results = {}
        
        # Perform health checks concurrently for speed
        check_tasks = []
        
        if "redis" in required_components:
            check_tasks.append(("redis", self.check_redis_health()))
        
        if "postgres" in required_components:
            check_tasks.append(("postgres", self.check_postgres_health()))
        
        if "backend" in required_components:
            backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            check_tasks.append(("backend", self.check_http_service_health("backend", f"{backend_url}/health")))
        
        if "auth" in required_components:
            auth_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
            check_tasks.append(("auth", self.check_http_service_health("auth", f"{auth_url}/health")))
        
        # Execute all checks concurrently
        if check_tasks:
            task_results = await asyncio.gather(
                *[task for _, task in check_tasks],
                return_exceptions=True
            )
            
            for i, (component_name, _) in enumerate(check_tasks):
                result = task_results[i]
                if isinstance(result, Exception):
                    results[component_name] = ComponentHealthCheck(
                        component=component_name,
                        status=InfrastructureStatus.ERROR,
                        response_time_ms=0,
                        error=str(result)
                    )
                else:
                    results[component_name] = result
        
        # Cache results
        self.health_results.update(results)
        
        # Log summary
        healthy_count = sum(1 for r in results.values() if r.is_healthy())
        total_count = len(results)
        
        if healthy_count == total_count:
            logger.info(f"Pre-flight checks passed: {healthy_count}/{total_count} components healthy")
        else:
            logger.warning(f"Pre-flight checks found issues: {healthy_count}/{total_count} components healthy")
            for name, result in results.items():
                if not result.is_healthy():
                    logger.warning(f"  {name}: {result.status.value} - {result.error or 'No error details'}")
        
        return results
    
    def should_skip_test(self, required_components: List[str]) -> tuple[bool, str]:
        """
        Determine if a test should be skipped based on infrastructure health.
        
        Args:
            required_components: List of required infrastructure components
            
        Returns:
            Tuple of (should_skip, reason)
        """
        unavailable_components = []
        error_details = []
        
        for component in required_components:
            if component in self.health_results:
                result = self.health_results[component]
                if not result.is_healthy():
                    unavailable_components.append(component)
                    error_details.append(f"{component}: {result.status.value} ({result.error})")
            else:
                # Component not checked yet
                unavailable_components.append(component)
                error_details.append(f"{component}: not checked")
        
        if unavailable_components:
            reason = (
                f"Infrastructure not ready for testing. "
                f"Unavailable components: {', '.join(unavailable_components)}. "
                f"Details: {'; '.join(error_details)}"
            )
            return True, reason
        
        return False, ""
    
    @asynccontextmanager
    async def protected_test_execution(self, test_name: str, required_components: List[str]):
        """
        Context manager that performs pre-flight checks and fails fast if infrastructure unavailable.
        
        Args:
            test_name: Name of the test being protected
            required_components: List of required infrastructure components
            
        Raises:
            RuntimeError: If infrastructure is not ready for testing
        """
        logger.info(f"Starting protected test execution: {test_name}")
        
        try:
            # Perform pre-flight checks
            health_results = await self.perform_preflight_checks(required_components)
            
            # Check if test should be skipped
            should_skip, skip_reason = self.should_skip_test(required_components)
            
            if should_skip:
                raise RuntimeError(
                    f"Test {test_name} cannot execute due to infrastructure issues: {skip_reason}. "
                    "This prevents the test from hanging indefinitely. "
                    "Fix infrastructure issues or adjust test requirements."
                )
            
            logger.info(f"Infrastructure ready for test {test_name}")
            yield health_results
            
        except Exception as e:
            logger.error(f"Protected test execution failed for {test_name}: {e}")
            raise
        finally:
            logger.debug(f"Protected test execution completed for {test_name}")


# Convenience functions for common use cases

async def check_infrastructure_ready_for_e2e_tests() -> bool:
    """
    Check if infrastructure is ready for E2E tests.
    
    Returns:
        True if infrastructure is ready, False otherwise
    """
    async with PerformanceTestCircuitBreaker() as circuit_breaker:
        results = await circuit_breaker.perform_preflight_checks(["redis", "postgres", "backend"])
        return all(r.is_healthy() for r in results.values())


async def fail_fast_if_infrastructure_unavailable(required_components: List[str] = None):
    """
    Fail fast if required infrastructure components are unavailable.
    
    Args:
        required_components: List of required components (default: ["redis", "postgres"])
        
    Raises:
        RuntimeError: If infrastructure is not ready
    """
    if required_components is None:
        required_components = ["redis", "postgres"]
    
    async with PerformanceTestCircuitBreaker() as circuit_breaker:
        async with circuit_breaker.protected_test_execution("infrastructure_check", required_components):
            pass  # Context manager handles the checks


# Export main classes and functions
__all__ = [
    "PerformanceTestCircuitBreaker",
    "CircuitBreakerConfig", 
    "ComponentHealthCheck",
    "InfrastructureStatus",
    "check_infrastructure_ready_for_e2e_tests",
    "fail_fast_if_infrastructure_unavailable"
]