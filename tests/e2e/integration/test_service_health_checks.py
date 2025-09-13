from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
E2E tests for service health check endpoints in DEV MODE.

Tests health endpoints for all services, monitors health status during startup,
validates graceful degradation, and verifies health check reliability.

Follows 450-line file limit and 25-line function limit constraints.
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pytest

# Add project root to path

from dev_launcher import DevLauncher, LauncherConfig
from tests.e2e.dev_launcher_test_fixtures import TestEnvironmentManager


@dataclass
class HealthCheckResult:
    """Health check result with timing and status."""
    service: str
    url: str
    status_code: int
    response_time_ms: float
    response_data: Optional[Dict[str, Any]]
    error: Optional[str]


class ServiceHealthChecker:
    """Manages health check testing for all services."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.expected_endpoints: Dict[str, str] = {}
        self.check_timeout = 10
        self._setup_expected_endpoints()
    
    def _setup_expected_endpoints(self) -> None:
        """Setup expected health endpoints for each service."""
        self.expected_endpoints = {
            "backend": "/health",
            "auth": "/health", 
            "frontend": "/api/health",
            "websocket": "/ws/health"
        }
    
    async def start_session(self) -> None:
        """Start aiohttp session for health checks."""
        timeout = aiohttp.ClientTimeout(total=self.check_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def stop_session(self) -> None:
        """Stop aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def check_service_health(self, service: str, port: int) -> HealthCheckResult:
        """Check health of specific service."""
        endpoint = self.expected_endpoints.get(service, "/health")
        url = f"http://localhost:{port}{endpoint}"
        
        start_time = time.time()
        try:
            return await self._perform_health_check(service, url, start_time)
        except Exception as e:
            return self._create_error_result(service, url, start_time, e)
    
    async def _perform_health_check(self, service: str, url: str, start_time: float) -> HealthCheckResult:
        """Perform actual health check request."""
        async with self.session.get(url) as response:
            response_time = (time.time() - start_time) * 1000
            response_data = await self._extract_response_data(response)
            
            return HealthCheckResult(
                service=service, url=url, status_code=response.status,
                response_time_ms=response_time, response_data=response_data,
                error=None
            )
    
    async def _extract_response_data(self, response: aiohttp.ClientResponse) -> Optional[Dict[str, Any]]:
        """Extract JSON response data safely."""
        try:
            if response.content_type == "application/json":
                return await response.json()
        except:
            pass
        return None
    
    def _create_error_result(self, service: str, url: str, start_time: float, error: Exception) -> HealthCheckResult:
        """Create health check result for error case."""
        response_time = (time.time() - start_time) * 1000
        return HealthCheckResult(
            service=service, url=url, status_code=0,
            response_time_ms=response_time, response_data=None,
            error=str(error)
        )


class TestDevHealthFixture:
    """Test fixture for dev environment health monitoring."""
    
    def __init__(self):
        self.launcher: Optional[DevLauncher] = None
        self.health_checker = ServiceHealthChecker()
        self.test_env = TestEnvironmentManager()
        self.service_ports: Dict[str, int] = {}
        self._setup_test_environment()
    
    def _setup_test_environment(self) -> None:
        """Setup test environment for health checks."""
        self.test_env.setup_test_db()
        self.test_env.setup_test_redis()
        get_env().set("TESTING", "true", "test")
        get_env().set("HEALTH_CHECK_INTERVAL", "5", "test")
    
    async def start_dev_environment(self) -> bool:
        """Start dev environment and extract service ports."""
        config = LauncherConfig(
            dynamic_ports=True, no_browser=True,
            non_interactive=True
        )
        
        self.launcher = DevLauncher(config)
        await self.health_checker.start_session()
        
        try:
            result = await asyncio.wait_for(self.launcher.run(), timeout=180)
            self._extract_service_ports()
            return result == 0
        except asyncio.TimeoutError:
            return False
    
    def _extract_service_ports(self) -> None:
        """Extract allocated ports from launcher."""
        if self.launcher and hasattr(self.launcher, 'process_manager'):
            pm = self.launcher.process_manager
            self.service_ports = getattr(pm, 'allocated_ports', {})
    
    async def cleanup(self) -> None:
        """Cleanup test resources."""
        await self.health_checker.stop_session()
        if self.launcher:
            await self.launcher.cleanup()
        self.test_env.cleanup()


@pytest.fixture
@pytest.mark.e2e
async def test_health_test_fixture():
    """Fixture providing health test environment."""
    fixture = TestDevHealthFixture()
    yield fixture
    await fixture.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_all_services_have_health_endpoints(test_health_test_fixture):
    """Test all services expose working health endpoints."""
    success = await test_health_test_fixture.start_dev_environment()
    assert success, "Dev environment should start successfully"
    
    # Check health of all services
    results = await _check_all_service_health(test_health_test_fixture)
    
    # Verify all services are healthy
    for result in results:
        assert result.status_code == 200, f"{result.service} health check failed"
        assert result.error is None, f"{result.service} health check error: {result.error}"


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_health_checks_during_startup(test_health_test_fixture):
    """Test health endpoints become available during startup sequence."""
    # Start launcher but monitor health during startup
    startup_task = asyncio.create_task(
        test_health_test_fixture.start_dev_environment()
    )
    
    # Monitor health checks during startup
    health_progression = await _monitor_startup_health(test_health_test_fixture)
    
    await startup_task
    
    # Verify health progression follows expected pattern
    assert _verify_health_progression(health_progression)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_health_check_response_times(test_health_test_fixture):
    """Test health endpoints respond within acceptable time limits."""
    success = await test_health_test_fixture.start_dev_environment()
    assert success
    
    results = await _check_all_service_health(test_health_test_fixture)
    
    # Verify response times are reasonable
    for result in results:
        assert result.response_time_ms < 1000, \
            f"{result.service} health check too slow: {result.response_time_ms}ms"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_health_check_content_validation(test_health_test_fixture):
    """Test health endpoint responses contain expected data."""
    success = await test_health_test_fixture.start_dev_environment()
    assert success
    
    results = await _check_all_service_health(test_health_test_fixture)
    
    # Verify response content
    for result in results:
        if result.response_data:
            assert _validate_health_response(result)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_health_monitoring_reliability(test_health_test_fixture):
    """Test health checks remain reliable over time."""
    success = await test_health_test_fixture.start_dev_environment()
    assert success
    
    # Perform multiple health checks over time
    check_results = []
    for i in range(5):
        results = await _check_all_service_health(test_health_test_fixture)
        check_results.append(results)
        await asyncio.sleep(2)
    
    # Verify consistent health status
    assert _verify_consistent_health(check_results)


async def _check_all_service_health(fixture: TestDevHealthFixture) -> List[HealthCheckResult]:
    """Check health of all available services."""
    results = []
    
    for service, port in fixture.service_ports.items():
        result = await fixture.health_checker.check_service_health(service, port)
        results.append(result)
    
    return results


async def _monitor_startup_health(fixture: TestDevHealthFixture) -> List[Tuple[float, List[HealthCheckResult]]]:
    """Monitor health checks during startup sequence."""
    progression = []
    start_time = time.time()
    
    for i in range(12):  # Monitor for 60 seconds
        elapsed = time.time() - start_time
        results = []
        
        # Check available ports
        for service, port in fixture.service_ports.items():
            result = await fixture.health_checker.check_service_health(service, port)
            results.append(result)
        
        progression.append((elapsed, results))
        await asyncio.sleep(5)
    
    return progression


def _verify_health_progression(progression: List[Tuple[float, List[HealthCheckResult]]]) -> bool:
    """Verify health checks improve during startup."""
    if len(progression) < 2:
        return False
    
    # Count healthy services over time
    healthy_counts = []
    for _, results in progression:
        healthy_count = sum(1 for r in results if r.status_code == 200)
        healthy_counts.append(healthy_count)
    
    # Should see improvement over time
    return healthy_counts[-1] >= healthy_counts[0]


def _validate_health_response(result: HealthCheckResult) -> bool:
    """Validate health response contains expected fields."""
    if not result.response_data:
        return False
    
    data = result.response_data
    required_fields = ["status", "timestamp"]
    
    return all(field in data for field in required_fields)


def _verify_consistent_health(check_results: List[List[HealthCheckResult]]) -> bool:
    """Verify health status remains consistent across checks."""
    if len(check_results) < 2:
        return False
    
    # Group results by service
    service_results = {}
    for results in check_results:
        for result in results:
            if result.service not in service_results:
                service_results[result.service] = []
            service_results[result.service].append(result.status_code == 200)
    
    # Check consistency for each service
    for service, statuses in service_results.items():
        if len(set(statuses)) > 1:  # Inconsistent statuses
            return False
    
    return True
