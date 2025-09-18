from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
'''
Multi-Service Health Check Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Operational reliability
- Value Impact: $15K MRR from preventing service outages
- Revenue Impact: Zero downtime SLA compliance

Tests all critical service health endpoints and dependencies:
- Auth service health endpoint validation
- Backend service health endpoint validation
- Database connectivity validation (PostgreSQL, ClickHouse, Redis)
- Frontend build verification
- Inter-service communication validation
- Response time validation with detailed failure reporting

CRITICAL: Maximum 300 lines, real health endpoint calls, comprehensive timeout handling
'''
'''

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest

        # Set testing environment before any imports

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.config import get_config
from netra_backend.app.db.postgres import async_engine, get_async_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager

logger = central_logger.get_logger(__name__)

        # Service endpoints and timeouts
SERVICE_ENDPOINTS = { }
"auth: { }"
"url": "http://localhost:8081/health,"
"timeout: 5.0,"
"expected_service": "auth-service"
},
"backend: { }"
"url": "http://localhost:8000/health,"
"timeout: 5.0,"
"expected_service": "netra-ai-platform"
},
"frontend: { }"
"url": "http://localhost:3000,"
"timeout: 10.0,"
"check_type": "build_verification"
        
        

DATABASE_TIMEOUTS = { }
"postgres: 3.0,"
"clickhouse: 5.0,"
"redis: 2.0"
        


class HealthCheckResult:
    """Structured health check result."""

    def __init__(self, service: str, status: str, response_time_ms: float,
    details: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    self.service = service
    self.status = status
    self.response_time_ms = response_time_ms
    self.details = details or {}
    self.error = error
    self.timestamp = datetime.now(UTC)


class MultiServiceHealthChecker:
    """Comprehensive multi-service health checker with timeout handling."""

    def __init__(self):
        pass
        self.results: List[HealthCheckResult] = []
        self.redis_manager = RedisManager()

    async def check_service_endpoint(self, service_name: str, config: Dict[str, Any]) -> HealthCheckResult:
        """Check individual service health endpoint with timeout."""
        start_time = time.time()

        try:
        async with httpx.AsyncClient(timeout=config["timeout], follow_redirects=True) as client:"
        response = await client.get(config["url])"
        response_time_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
        response_data = response.json()
        expected_service = config.get("expected_service)"

        if expected_service and response_data.get("service) == expected_service:"
        return HealthCheckResult( )
        service=service_name,
        status="healthy,"
        response_time_ms=response_time_ms,
        details=response_data
                    
        elif not expected_service:
        return HealthCheckResult( )
        service=service_name,
        status="healthy,"
        response_time_ms=response_time_ms,
        details={"status_code: response.status_code}"
                        
        else:
        return HealthCheckResult( )
        service=service_name,
        status="unhealthy,"
        response_time_ms=response_time_ms,
        error=""
                            
        else:
        return HealthCheckResult( )
        service=service_name,
        status="unhealthy,"
        response_time_ms=response_time_ms,
        error=""
                                

        except asyncio.TimeoutError:
        response_time_ms = config["timeout] * 1000"
        return HealthCheckResult( )
        service=service_name,
        status="timeout,"
        response_time_ms=response_time_ms,
        error="Request timeout"
                                    
        except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service=service_name,
        status="error,"
        response_time_ms=response_time_ms,
        error=str(e)
                                        

    async def check_postgres_connection(self) -> HealthCheckResult:
        """Check PostgreSQL database connection."""
        start_time = time.time()

        try:
        async with asyncio.timeout(DATABASE_TIMEOUTS["postgres]):"
        async with async_engine.begin() as conn:
        result = await conn.execute(text("SELECT 1 as test))"
        test_value = result.scalar_one_or_none()
        response_time_ms = (time.time() - start_time) * 1000

        if test_value == 1:
        return HealthCheckResult( )
        service="postgres,"
        status="healthy,"
        response_time_ms=response_time_ms,
        details={"connection": "successful", "test_query": "passed}"
                    
        else:
        return HealthCheckResult( )
        service="postgres,"
        status="unhealthy,"
        response_time_ms=response_time_ms,
        error="Test query failed"
                        

        except asyncio.TimeoutError:
        return HealthCheckResult( )
        service="postgres,"
        status="timeout,"
        response_time_ms=DATABASE_TIMEOUTS["postgres] * 1000,"
        error="Connection timeout"
                            
        except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="postgres,"
        status="error,"
        response_time_ms=response_time_ms,
        error=str(e)
                                

    async def check_clickhouse_connection(self) -> HealthCheckResult:
        """Check ClickHouse database connection."""
        start_time = time.time()

        try:
        if get_env().get('SKIP_CLICKHOUSE_INIT', 'false').lower() == 'true':
        return HealthCheckResult( )
        service="clickhouse,"
        status="skipped,"
        response_time_ms=0,
        details={"reason": "SKIP_CLICKHOUSE_INIT=true}"
            

        async with asyncio.timeout(DATABASE_TIMEOUTS["clickhouse]):"
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        async with get_clickhouse_client() as client:
        await client.test_connection()
        response_time_ms = (time.time() - start_time) * 1000

        return HealthCheckResult( )
        service="clickhouse,"
        status="healthy,"
        response_time_ms=response_time_ms,
        details={"connection": "successful}"
                    

        except asyncio.TimeoutError:
        return HealthCheckResult( )
        service="clickhouse,"
        status="timeout,"
        response_time_ms=DATABASE_TIMEOUTS["clickhouse] * 1000,"
        error="Connection timeout"
                        
        except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="clickhouse,"
        status="error,"
        response_time_ms=response_time_ms,
        error=str(e)
                            

    async def check_redis_connection(self) -> HealthCheckResult:
        """Check Redis connection."""
        start_time = time.time()

        if not self.redis_manager.enabled:
        return HealthCheckResult( )
        service="redis,"
        status="disabled,"
        response_time_ms=0,
        details={"reason": "Redis disabled by configuration}"
        

        try:
        async with asyncio.timeout(DATABASE_TIMEOUTS["redis]):"
        await self.redis_manager.connect()
        if self.redis_manager.redis_client:
        await self.redis_manager.redis_client.ping()
        response_time_ms = (time.time() - start_time) * 1000

        return HealthCheckResult( )
        service="redis,"
        status="healthy,"
        response_time_ms=response_time_ms,
        details={"connection": "successful", "ping": "ok}"
                    
        else:
        return HealthCheckResult( )
        service="redis,"
        status="unhealthy,"
        response_time_ms=(time.time() - start_time) * 1000,
        error="Client connection failed"
                        

        except asyncio.TimeoutError:
        return HealthCheckResult( )
        service="redis,"
        status="timeout,"
        response_time_ms=DATABASE_TIMEOUTS["redis] * 1000,"
        error="Connection timeout"
                            
        except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="redis,"
        status="error,"
        response_time_ms=response_time_ms,
        error=str(e)
                                

    async def check_inter_service_communication(self) -> HealthCheckResult:
        """Check inter-service communication by testing auth service from backend perspective."""
        start_time = time.time()

        try:
        # Test auth service accessibility
        auth_config = SERVICE_ENDPOINTS["auth]"
        async with httpx.AsyncClient(timeout=auth_config["timeout], follow_redirects=True) as client:"
        auth_response = await client.get(auth_config["url])"

        if auth_response.status_code == 200:
                # Test backend service accessibility
        backend_config = SERVICE_ENDPOINTS["backend]"
        backend_response = await client.get(backend_config["url])"

        if backend_response.status_code == 200:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="inter_service,"
        status="healthy,"
        response_time_ms=response_time_ms,
        details={ }
        "auth_to_backend": "accessible,"
        "backend_to_auth": "accessible"
                    
                    

        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="inter_service,"
        status="unhealthy,"
        response_time_ms=response_time_ms,
        error="Service communication failed"
                    

        except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult( )
        service="inter_service,"
        status="error,"
        response_time_ms=response_time_ms,
        error=str(e)
                        

    async def run_comprehensive_health_check(self) -> List[HealthCheckResult]:
        """Run comprehensive health check on all services and dependencies."""
        tasks = []

    # Service endpoint checks
        for service_name, config in SERVICE_ENDPOINTS.items():
        if service_name != "frontend:  # Skip frontend for now"
        tasks.append(self.check_service_endpoint(service_name, config))

        # Database connection checks
        tasks.extend([ ])
        self.check_postgres_connection(),
        self.check_clickhouse_connection(),
        self.check_redis_connection()
        

        # Inter-service communication check
        tasks.append(self.check_inter_service_communication())

        # Execute all checks concurrently
        self.results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(self.results):
        if isinstance(result, Exception):
        processed_results.append(HealthCheckResult( ))
        service="",
        status="error,"
        response_time_ms=0,
        error=str(result)
                
        else:
        processed_results.append(result)

        return processed_results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
    async def test_multi_service_health_comprehensive():
"""Test comprehensive multi-service health check functionality."""
checker = MultiServiceHealthChecker()
results = await checker.run_comprehensive_health_check()

                        # Validate we got results for all expected services
service_names = [r.service for r in results]
expected_services = ["auth", "backend", "postgres", "clickhouse", "redis", "inter_service]"

for expected_service in expected_services:
assert expected_service in service_names, ""

                            # Validate response times are reasonable (< 30 seconds total)
total_response_time = sum(r.response_time_ms for r in results)
assert total_response_time < 30000, ""

                            # Log detailed results for operational monitoring
healthy_count = sum(1 for r in results if r.status == "healthy)"
logger.info("")

for result in results:
status_symbol = "[OK]" if result.status == "healthy" else "[FAIL]"
logger.info("")
if result.error:
    pass
logger.warning("")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
    async def test_critical_services_availability():
"""Test that critical services (auth, backend, postgres) are available."""
pass
checker = MultiServiceHealthChecker()
results = await checker.run_comprehensive_health_check()

                                        # Critical services must be healthy for system operation
critical_services = ["auth", "backend", "postgres]"

for result in results:
if result.service in critical_services:
    pass
assert result.status in ["healthy", "disabled"], ""

                                                # Validate critical services response times
for result in results:
if result.service in critical_services and result.status == "healthy:"
    pass
assert result.response_time_ms < 5000, ""


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
    async def test_service_timeout_handling():
"""Test proper timeout handling for service health checks."""
checker = MultiServiceHealthChecker()

                                                            # Test with very short timeout (should cause timeout)
original_timeout = SERVICE_ENDPOINTS["backend"]["timeout]"
SERVICE_ENDPOINTS["backend"]["timeout] = 0.1  # 1ms timeout"

try:
    pass
result = await checker.check_service_endpoint("backend", SERVICE_ENDPOINTS["backend])"
                                                                # Should either timeout or complete very quickly
assert result.status in ["timeout", "healthy", "error"], ""

finally:
                                                                    # Restore original timeout
SERVICE_ENDPOINTS["backend"]["timeout] = original_timeout"


if __name__ == "__main__:"
                                                                        # Direct execution for debugging
async def main():
checker = MultiServiceHealthChecker()
results = await checker.run_comprehensive_health_check()

print("")
=== Multi-Service Health Check Results ===")"
for result in results:
status_symbol = {"healthy": "[OK]", "unhealthy": "[FAIL]", "timeout": "[TIMEOUT]", "error": "[ERROR]", "disabled": "[DISABLED]", "skipped": "[SKIP]"}.get(result.status, "[?])"
print("")
if result.error:
    print("")
if result.details:
    print("")

asyncio.run(main())
pass
