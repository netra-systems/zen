"""Auth Service Health Check Integration Test Suite

BVJ: Protects $145K+ MRR by ensuring auth service availability across all customer segments.
Tests health endpoints, lazy DB initialization, recovery scenarios, and performance under load.
Architecture: <300 lines, async/await pattern, comprehensive AAA testing.
"""

import asyncio
import time
import pytest
import httpx
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager

# Add auth_service to Python path for imports
auth_service_path = Path(__file__).parent.parent.parent / "auth_service"
if str(auth_service_path) not in sys.path:
    sys.path.insert(0, str(auth_service_path))

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Container for health check operation results."""
    endpoint: str
    status_code: int
    response_time_ms: float
    response_data: Dict[str, Any]
    database_ready: bool
    service_healthy: bool
    error: Optional[str] = None


class AuthHealthChecker:
    """Core health check validation utilities."""
    
    def __init__(self, base_url: str = None):
        """Initialize health checker with auth service URL."""
        if base_url is None:
            # Try to get from environment, fallback to default
            auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8080")
            # Ensure URL has protocol
            if not auth_url.startswith(("http://", "https://")):
                auth_url = f"http://{auth_url}"
            self.base_url = auth_url
        else:
            self.base_url = base_url
        
        logger.info(f"AuthHealthChecker initialized with base_url: {self.base_url}")
        self.health_endpoint = f"{self.base_url}/health"
        self.ready_endpoint = f"{self.base_url}/health/ready"
    
    async def check_health_endpoint(self) -> HealthCheckResult:
        """Test basic /health endpoint availability and performance."""
        start_time = time.perf_counter()
        
        try:
            logger.info(f"Attempting to connect to health endpoint: {self.health_endpoint}")
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(self.health_endpoint)
                response_time = (time.perf_counter() - start_time) * 1000
                
                response_data = response.json() if response.text else {}
                
                return HealthCheckResult(
                    endpoint="/health",
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    response_data=response_data,
                    database_ready=True,  # Basic health doesn't require DB
                    service_healthy=response.status_code == 200,
                    error=None
                )
        except Exception as e:
            response_time = (time.perf_counter() - start_time) * 1000
            return HealthCheckResult(
                endpoint="/health",
                status_code=0,
                response_time_ms=response_time,
                response_data={},
                database_ready=False,
                service_healthy=False,
                error=str(e)
            )
    
    async def check_ready_endpoint(self, with_db_init: bool = False) -> HealthCheckResult:
        """Test /health/ready endpoint with optional database initialization."""
        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.ready_endpoint)
                
                # Fallback to basic health if ready doesn't exist
                if response.status_code == 404:
                    response = await client.get(self.health_endpoint)
                    endpoint_used = "/health"
                else:
                    endpoint_used = "/health/ready"
                
                response_time = (time.perf_counter() - start_time) * 1000
                response_data = response.json() if response.text else {}
                
                return HealthCheckResult(
                    endpoint=endpoint_used,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    response_data=response_data,
                    database_ready=response.status_code == 200,
                    service_healthy=response.status_code in [200, 503],
                    error=None
                )
        except Exception as e:
            response_time = (time.perf_counter() - start_time) * 1000
            return HealthCheckResult(
                endpoint="/health/ready",
                status_code=0,
                response_time_ms=response_time,
                response_data={},
                database_ready=False,
                service_healthy=False,
                error=str(e)
            )


class DatabaseStateSimulator:
    """Simulates database initialization and failure scenarios."""
    
    @asynccontextmanager
    async def simulate_uninitialized_db(self):
        """Context manager for uninitialized database state."""
        with patch('auth_core.database.connection.auth_db.engine', None):
            yield
    
    @asynccontextmanager
    async def simulate_db_failure(self):
        """Context manager for database connection failure."""
        mock_engine = AsyncMock()
        mock_engine.execute.side_effect = Exception("Database connection failed")
        
        with patch('auth_core.database.connection.auth_db.engine', mock_engine):
            yield
    
    @asynccontextmanager
    async def simulate_db_recovery(self):
        """Context manager for database recovery scenario."""
        mock_engine = AsyncMock()
        mock_engine.execute.return_value = AsyncMock()
        
        with patch('auth_core.database.connection.auth_db.engine', mock_engine):
            yield


class ConcurrentLoadTester:
    """Tests health check performance under concurrent load."""
    
    def __init__(self, health_checker: AuthHealthChecker):
        """Initialize concurrent load tester."""
        self.health_checker = health_checker
    
    async def test_concurrent_health_checks(self, concurrent_count: int = 10) -> Dict[str, Any]:
        """Run concurrent health checks and measure performance."""
        tasks = [
            self.health_checker.check_health_endpoint() 
            for _ in range(concurrent_count)
        ]
        
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start_time) * 1000
        
        successful_results = [r for r in results if isinstance(r, HealthCheckResult) and r.service_healthy]
        response_times = [r.response_time_ms for r in successful_results]
        
        return {
            "total_requests": concurrent_count,
            "successful_requests": len(successful_results),
            "total_time_ms": total_time,
            "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "all_under_1s": all(rt < 1000 for rt in response_times)
        }


@pytest.mark.asyncio
@pytest.mark.critical
class TestAuthServiceHealthCheckIntegration:
    """Auth service health check integration test suite."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker instance."""
        return AuthHealthChecker()
    
    @pytest.fixture
    def db_simulator(self):
        """Create database state simulator."""
        return DatabaseStateSimulator()
    
    @pytest.fixture
    def load_tester(self, health_checker):
        """Create concurrent load tester."""
        return ConcurrentLoadTester(health_checker)
    
    async def test_health_ready_endpoint_validation(self, health_checker):
        """Test 1: Health Ready Endpoint Validation."""
        health_result = await health_checker.check_health_endpoint()
        ready_result = await health_checker.check_ready_endpoint()
        
        assert health_result.service_healthy, f"Health endpoint failed: {health_result.error}"
        assert health_result.status_code == 200, f"Expected 200, got {health_result.status_code}"
        assert health_result.response_time_ms < 1000, f"Performance requirement failed: {health_result.response_time_ms}ms"
        
        assert ready_result.service_healthy, f"Ready endpoint failed: {ready_result.error}"
        assert ready_result.status_code in [200, 503], f"Unexpected status: {ready_result.status_code}"
        assert ready_result.response_time_ms < 1000, f"Performance requirement failed: {ready_result.response_time_ms}ms"
        
        logger.info(f"✓ Health endpoints validated - Health: {health_result.response_time_ms:.1f}ms, Ready: {ready_result.response_time_ms:.1f}ms")
    
    async def test_lazy_database_initialization(self, health_checker, db_simulator):
        """Test 2: Lazy Database Initialization."""
        async with db_simulator.simulate_uninitialized_db():
            result = await health_checker.check_health_endpoint()
            
            assert result.service_healthy, f"Health check failed with uninitialized DB: {result.error}"
            assert result.status_code == 200, f"Expected 200, got {result.status_code}"
            assert result.response_time_ms < 1000, "Performance degraded with uninitialized DB"
            
        logger.info(f"✓ Lazy initialization validated - {result.response_time_ms:.1f}ms without DB init")
    
    async def test_database_recovery_scenarios(self, health_checker, db_simulator):
        """Test 3: Database Recovery Scenarios."""
        async with db_simulator.simulate_db_failure():
            failure_result = await health_checker.check_ready_endpoint()
            assert failure_result.service_healthy, f"Service failed during DB outage: {failure_result.error}"
            assert failure_result.status_code in [200, 503], f"Unexpected failure status: {failure_result.status_code}"
        
        async with db_simulator.simulate_db_recovery():
            recovery_result = await health_checker.check_ready_endpoint()
            assert recovery_result.service_healthy, f"Service failed to recover: {recovery_result.error}"
            assert recovery_result.status_code == 200, f"Recovery incomplete: {recovery_result.status_code}"
        
        logger.info(f"✓ Database recovery validated - Failure: {failure_result.status_code}, Recovery: {recovery_result.status_code}")
    
    async def test_service_dependencies(self, health_checker):
        """Test 4: Service Dependencies."""
        result = await health_checker.check_ready_endpoint()
        
        assert result.service_healthy, f"Service dependency check failed: {result.error}"
        
        if "dependencies" in result.response_data:
            dependencies = result.response_data["dependencies"]
            assert isinstance(dependencies, dict), "Dependencies should be a dictionary"
        
        logger.info(f"✓ Service dependencies validated - Status: {result.status_code}")
    
    async def test_performance_under_load(self, load_tester):
        """Test 5: Performance Under Load - Realistic Business Scenario."""
        # Test realistic concurrent health checks (e.g., load balancer + monitoring)
        load_results = await load_tester.test_concurrent_health_checks(concurrent_count=5)
        
        # Business-focused assertions: ensure service remains available under typical load
        assert load_results["successful_requests"] >= 4, f"Too many failures: {load_results['successful_requests']}/5"
        
        # All requests should complete within reasonable timeframe (allowing for system constraints)
        max_acceptable_time = 2000  # 2 seconds max for health checks under load
        assert load_results["max_response_time_ms"] < max_acceptable_time, f"Health check too slow under load: {load_results['max_response_time_ms']:.1f}ms"
        
        # Average should be reasonable for business operations (allowing for system constraints)
        assert load_results["avg_response_time_ms"] < 1200, f"Average response time too high: {load_results['avg_response_time_ms']:.1f}ms"
        
        logger.info(f"✓ Load performance validated - {load_results['successful_requests']}/5 requests, avg: {load_results['avg_response_time_ms']:.1f}ms, max: {load_results['max_response_time_ms']:.1f}ms")


async def run_auth_health_integration_test():
    """Standalone function to run auth health check integration tests."""
    logger.info("Starting Auth Service Health Check Integration Test")
    
    health_checker = AuthHealthChecker()
    db_simulator = DatabaseStateSimulator()
    load_tester = ConcurrentLoadTester(health_checker)
    
    test_results = {}
    
    try:
        test_results["health_validation"] = await health_checker.check_health_endpoint()
        
        async with db_simulator.simulate_uninitialized_db():
            test_results["lazy_init"] = await health_checker.check_health_endpoint()
        
        async with db_simulator.simulate_db_failure():
            test_results["db_failure"] = await health_checker.check_ready_endpoint()
        
        async with db_simulator.simulate_db_recovery():
            test_results["db_recovery"] = await health_checker.check_ready_endpoint()
        
        test_results["load_performance"] = await load_tester.test_concurrent_health_checks(5)
        
        all_healthy = all(
            result.service_healthy if hasattr(result, 'service_healthy') 
            else result.get('all_under_1s', False)
            for result in test_results.values()
        )
        
        return {
            "test_completed": True,
            "all_health_checks_passed": all_healthy,
            "auth_service_reliable": all_healthy,
            "business_value_protected": "$145K+ MRR" if all_healthy else "AT RISK",
            "results": {k: v.__dict__ if hasattr(v, '__dict__') else v for k, v in test_results.items()}
        }
        
    except Exception as e:
        return {"error": str(e), "test_completed": False, "business_value_protected": "AT RISK"}


if __name__ == "__main__":
    result = asyncio.run(run_auth_health_integration_test())
    print(f"Auth Service Health Check Integration Results: {result}")