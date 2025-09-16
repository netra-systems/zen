"""
Service health monitoring race condition tests.

Tests critical race conditions in health monitoring that cause false positive failures,
preventing service disruptions that lead to customer churn and revenue loss.
"""
import pytest
import asyncio
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.helpers.core.service_independence_helpers import ServiceHealthChecker
from tests.e2e.config import get_test_config


@pytest.mark.critical
@pytest.mark.e2e
async def test_concurrent_health_checks_no_race_condition():
    """Test concurrent health checks don't interfere with each other."""
    health_checker = ServiceHealthChecker()
    
    # Launch multiple concurrent health checks
    tasks = [
        health_checker.check_service_health("auth_service"),
        health_checker.check_service_health("backend_service"),
        health_checker.check_service_health("frontend_service")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All checks should complete without exceptions
    for result in results:
        assert not isinstance(result, Exception), f"Health check failed with: {result}"
        assert result.status in ["healthy", "unhealthy"], "Must return valid status"


@pytest.mark.critical
@pytest.mark.e2e
async def test_health_check_timeout_prevents_cascade_failure():
    """Test health check timeouts don't cause cascade failures."""
    health_checker = ServiceHealthChecker(timeout=2.0)
    
    # Mock slow-responding service
    with patch('tests.e2e.helpers.core.service_independence_helpers.check_service_endpoint') as mock_check:
        mock_check.side_effect = lambda url: asyncio.sleep(5)  # Exceeds timeout
        
        # Health check should timeout gracefully
        result = await health_checker.check_service_health("slow_service")
        
        assert result.status == "timeout", "Must handle timeout gracefully"
        assert result.response_time >= 2.0, "Must respect timeout value"


@pytest.mark.critical
@pytest.mark.e2e
async def test_health_check_state_consistency_under_load():
    """Test health check state remains consistent under high load."""
    health_checker = ServiceHealthChecker()
    service_name = "load_test_service"
    
    # Rapid concurrent health checks
    check_count = 20
    tasks = [
        health_checker.check_service_health(service_name) 
        for _ in range(check_count)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All results should be consistent for same service
    statuses = {result.status for result in results}
    assert len(statuses) <= 2, "Status should be consistent or show clean transitions"


@pytest.mark.critical
@pytest.mark.e2e
async def test_health_monitoring_recovery_after_transient_failure():
    """Test health monitoring correctly detects service recovery."""
    health_checker = ServiceHealthChecker()
    service_name = "recovery_test_service"
    
    # Simulate transient failure then recovery
    failure_count = 0
    
    def mock_health_endpoint():
        nonlocal failure_count
        failure_count += 1
        if failure_count <= 2:
            raise Exception("Service temporarily down")
        return {"status": "healthy"}
    
    with patch('tests.e2e.helpers.core.service_independence_helpers.check_service_endpoint') as mock_check:
        mock_check.side_effect = mock_health_endpoint
        
        # First checks should fail
        result1 = await health_checker.check_service_health(service_name)
        result2 = await health_checker.check_service_health(service_name)
        
        # Third check should succeed
        result3 = await health_checker.check_service_health(service_name)
        
        assert result3.status == "healthy", "Must detect service recovery"
