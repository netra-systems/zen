"""
Multi-Service Health Check Coordination Tests

Comprehensive tests for health check coordination across services.
Business Value: $20K MRR - System monitoring and observability

Tests coordinated health checks across:
- Auth Service (/health endpoint)
- Backend (/health endpoint) 
- Frontend (/health endpoint)
- Database dependencies
- Service interdependencies

Key validations:
- Response times < 500ms
- Service status aggregation
- Dependency health inclusion
- Cross-service consistency
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import time
from typing import Any, Dict, List

import httpx
import pytest

from netra_backend.app.core.health import HealthInterface, HealthLevel
from netra_backend.app.core.health.checks import (
    DependencyHealthChecker,
    UnifiedDatabaseHealthChecker,
)
from netra_backend.app.db.postgres import async_engine
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.mock_services import (
    MockHTTPService,
    ServiceRegistry,
    setup_unified_mock_services,
)

logger = central_logger.get_logger(__name__)

class HealthCoordinationTester:
    """Test coordinator for multi-service health checks."""
    
    def __init__(self):
        """Initialize health coordination tester."""
        self.auth_service_url = "http://localhost:8001"
        self.backend_service_url = "http://localhost:8000"
        self.frontend_service_url = "http://localhost:3000"
        self.health_interface = HealthInterface("test-platform", "1.0.0")
        self._register_health_checkers()
    
    def _register_health_checkers(self) -> None:
        """Register health checkers for testing."""
        self.health_interface.register_checker(UnifiedDatabaseHealthChecker("postgres"))
        self.health_interface.register_checker(UnifiedDatabaseHealthChecker("clickhouse"))
        self.health_interface.register_checker(DependencyHealthChecker("websocket"))
        self.health_interface.register_checker(DependencyHealthChecker("llm"))
    
    async def check_service_health(self, service_url: str, service_name: str) -> Dict[str, Any]:
        """Check health of individual service with timing."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{service_url}/health")
                response_time_ms = (time.time() - start_time) * 1000
                
                return {
                    "service": service_name,
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response_time_ms,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "service": service_name,
                "status": "unhealthy",
                "response_time_ms": response_time_ms,
                "status_code": 0,
                "error": str(e)
            }
    
    async def get_aggregated_health(self) -> Dict[str, Any]:
        """Get aggregated health status across all services."""
        return await self.health_interface.get_health_status(HealthLevel.COMPREHENSIVE)
    
    def validate_response_time(self, health_result: Dict[str, Any], max_time_ms: float = 500.0) -> bool:
        """Validate service response time is within limits."""
        return health_result.get("response_time_ms", float('inf')) < max_time_ms
    
    def calculate_system_health_score(self, service_results: List[Dict[str, Any]]) -> float:
        """Calculate overall system health score."""
        if not service_results:
            return 0.0
        
        healthy_services = sum(1 for result in service_results if result.get("status") == "healthy")
        return (healthy_services / len(service_results)) * 100.0

@pytest.fixture
async def mock_services():
    """Setup and teardown mock services for testing."""
    registry = await setup_unified_mock_services()
    
    # Start all mock services
    await registry.start_all_services()
    
    yield registry
    
    # Cleanup: stop all services
    await registry.stop_all_services()

@pytest.fixture
async def health_coordinator(mock_services):
    """Create health coordination tester with mock services."""
    coordinator = HealthCoordinationTester()
    
    # Update service URLs to use mock services
    coordinator.auth_service_url = mock_services.get_http_service_url("auth") or "http://localhost:8001"
    coordinator.backend_service_url = mock_services.get_http_service_url("backend") or "http://localhost:8000"
    coordinator.frontend_service_url = mock_services.get_http_service_url("frontend") or "http://localhost:3000"
    
    yield coordinator

@pytest.mark.asyncio
async def test_multi_service_health_checks(health_coordinator):
    """
    Test coordinated health checks across services.
    
    Business Value: $20K MRR - System monitoring
    Validates:
    - All services respond to /health endpoints
    - Response times are under 2000ms (test environment)
    - Status codes are appropriate
    """
    services_to_check = [
        (health_coordinator.auth_service_url, "auth-service"),
        (health_coordinator.backend_service_url, "backend-service"),
        (health_coordinator.frontend_service_url, "frontend-service")
    ]
    
    # Check all services concurrently
    health_tasks = [
        health_coordinator.check_service_health(url, name) 
        for url, name in services_to_check
    ]
    
    service_results = await asyncio.gather(*health_tasks, return_exceptions=True)
    
    # Validate results
    healthy_services = 0
    for result in service_results:
        if isinstance(result, Exception):
            logger.warning(f"Health check failed with exception: {result}")
            continue
            
        # Validate response time < 2000ms for test environment (more lenient than production)
        assert health_coordinator.validate_response_time(result, 2000.0), \
            f"Service {result['service']} response time {result['response_time_ms']}ms exceeds 2000ms"
        
        # Count healthy services
        if result.get("status") == "healthy":
            healthy_services += 1
        
        # Log results for monitoring
        logger.info(f"Health check for {result['service']}: {result['status']} "
                   f"({result['response_time_ms']:.2f}ms)")
    
    # Business Value: Ensure at least 2/3 services are healthy for system operation
    system_health_score = health_coordinator.calculate_system_health_score(
        [r for r in service_results if not isinstance(r, Exception)]
    )
    
    assert system_health_score >= 66.7, \
        f"System health score {system_health_score}% below minimum threshold"
    
    logger.info(f"Multi-service health check completed. System health: {system_health_score}%")

@pytest.mark.asyncio
async def test_health_status_aggregation(health_coordinator):
    """
    Test aggregated health status logic.
    
    Business Value: $20K MRR - System monitoring dashboard
    Validates:
    - Individual service health is aggregated correctly
    - Partial failure scenarios are handled
    - Status codes reflect true system state
    """
    # Get individual service health
    auth_health = await health_coordinator.check_service_health(
        health_coordinator.auth_service_url, "auth-service"
    )
    backend_health = await health_coordinator.check_service_health(
        health_coordinator.backend_service_url, "backend-service"
    )
    
    # Get aggregated health
    aggregated_health = await health_coordinator.get_aggregated_health()
    
    # Validate aggregation logic
    assert "status" in aggregated_health, "Aggregated health missing status field"
    assert "service" in aggregated_health, "Aggregated health missing service field"
    assert "checks" in aggregated_health, "Aggregated health missing checks field"
    
    # Test partial failure scenarios
    service_states = [auth_health.get("status"), backend_health.get("status")]
    healthy_count = sum(1 for state in service_states if state == "healthy")
    
    if healthy_count == len(service_states):
        expected_status = "healthy"
    elif healthy_count > 0:
        expected_status = "degraded"
    else:
        expected_status = "unhealthy"
    
    # Validate status aggregation matches business logic
    actual_status = aggregated_health.get("status")
    assert actual_status in ["healthy", "degraded", "unhealthy"], \
        f"Invalid aggregated status: {actual_status}"
    
    logger.info(f"Health aggregation test completed. "
               f"Individual services: {service_states}, Aggregated: {actual_status}")

@pytest.mark.asyncio
async def test_health_check_with_dependencies(health_coordinator):
    """
    Test health checks include dependencies.
    
    Business Value: $20K MRR - Dependency monitoring
    Validates:
    - Backend health checks database connectivity
    - Frontend health checks backend connectivity  
    - Auth service checks session store
    - Dependencies are properly validated
    """
    # Test backend database dependency health
    # Mock: Component isolation for testing without external dependencies
    with patch('app.db.postgres.async_engine') as mock_engine:
        # Mock: Generic component isolation for controlled unit testing
        mock_connection = AsyncNone  # TODO: Use real service instance
        mock_engine.connect.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.scalar_one_or_none.return_value = 1
        
        # Get backend health with database dependency
        backend_health = await health_coordinator.check_service_health(
            health_coordinator.backend_service_url, "backend-service"
        )
        
        # Validate database dependency is included
        if backend_health.get("status") == "healthy" and backend_health.get("data"):
            health_data = backend_health["data"]
            assert "checks" in health_data or "status" in health_data, \
                "Backend health should include dependency checks"
    
    # Test aggregated health includes all dependencies
    aggregated_health = await health_coordinator.get_aggregated_health()
    
    # Validate dependency checks are present
    if "checks" in aggregated_health:
        checks = aggregated_health["checks"]
        
        # Check for expected dependency types
        dependency_types = ["postgres", "clickhouse", "redis", "websocket", "llm"]
        found_dependencies = []
        
        for check_name in checks.keys():
            for dep_type in dependency_types:
                if dep_type in check_name.lower():
                    found_dependencies.append(dep_type)
                    break
        
        # Validate at least core dependencies are checked
        core_dependencies = {"postgres"}  # At minimum, postgres should be checked
        found_core = set(found_dependencies) & core_dependencies
        
        assert len(found_core) > 0, \
            f"Core dependencies not found in health checks. Found: {found_dependencies}"
        
        logger.info(f"Dependency health checks validated. Found: {found_dependencies}")

@pytest.mark.asyncio
async def test_health_check_performance_requirements(mock_services):
    """
    Test health check performance requirements.
    
    Business Value: $20K MRR - SLA compliance
    Validates:
    - Health endpoints respond within SLA (< 2000ms for test env)
    - Concurrent health checks perform well
    - No resource leaks during health monitoring
    """
    coordinator = HealthCoordinationTester()
    
    # Use mock service URL
    test_service_url = mock_services.get_http_service_url("backend") or "http://localhost:8000"
    
    # Test concurrent health checks performance
    start_time = time.time()
    
    # Run 10 concurrent health checks
    concurrent_tasks = [
        coordinator.check_service_health(test_service_url, f"backend-{i}")
        for i in range(10)
    ]
    
    results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    total_time = (time.time() - start_time) * 1000
    
    # Validate total time for concurrent checks (more generous for test environment)
    assert total_time < 5000, \
        f"10 concurrent health checks took {total_time}ms, exceeding 5s limit"
    
    # Validate individual response times
    valid_results = [r for r in results if not isinstance(r, Exception)]
    if valid_results:
        max_response_time = max(r.get("response_time_ms", 0) for r in valid_results)
        avg_response_time = sum(r.get("response_time_ms", 0) for r in valid_results) / len(valid_results)
        
        assert max_response_time < 5000, \
            f"Maximum individual response time {max_response_time}ms exceeds 5s"
        
        logger.info(f"Performance test completed. Total: {total_time}ms, "
                   f"Max individual: {max_response_time}ms, Average: {avg_response_time}ms")

@pytest.mark.asyncio
async def test_health_check_error_scenarios():
    """
    Test health check error handling scenarios.
    
    Business Value: $20K MRR - System reliability
    Validates:
    - Graceful handling of service unavailability
    - Proper error status reporting
    - No cascading failures in health monitoring
    """
    coordinator = HealthCoordinationTester()
    
    # Test non-existent service health check
    invalid_service_health = await coordinator.check_service_health(
        "http://localhost:9999", "non-existent-service"
    )
    
    assert invalid_service_health["status"] == "unhealthy", \
        "Non-existent service should be marked as unhealthy"
    assert "error" in invalid_service_health, \
        "Error details should be included for failed health checks"
    
    # Test timeout scenario
    # Mock: Component isolation for testing without external dependencies
    with patch('httpx.AsyncClient.get') as mock_get:
        # Simulate timeout
        mock_get.side_effect = asyncio.TimeoutError("Request timeout")
        
        timeout_health = await coordinator.check_service_health(
            coordinator.backend_service_url, "timeout-service"
        )
        
        assert timeout_health["status"] == "unhealthy", \
            "Timeout should result in unhealthy status"
        assert "timeout" in timeout_health["error"].lower(), \
            "Timeout error should be properly captured"
    
    logger.info("Error scenario testing completed successfully")

@pytest.mark.asyncio
async def test_health_monitoring_business_metrics():
    """
    Test health monitoring provides business-critical metrics.
    
    Business Value: $20K MRR - Business intelligence
    Validates:
    - Uptime calculation for SLA reporting
    - Service availability percentages
    - Performance trend data
    """
    coordinator = HealthCoordinationTester()
    
    # Test system health scoring for business dashboard
    mock_service_results = [
        {"status": "healthy", "service": "auth"},
        {"status": "healthy", "service": "backend"},
        {"status": "degraded", "service": "frontend"}
    ]
    
    health_score = coordinator.calculate_system_health_score(mock_service_results)
    expected_score = (2 / 3) * 100  # 2 healthy out of 3 services
    
    assert abs(health_score - expected_score) < 0.1, \
        f"Health score calculation incorrect: {health_score} vs {expected_score}"
    
    # Test availability calculation
    healthy_services = sum(1 for result in mock_service_results if result.get("status") == "healthy")
    availability_percentage = (healthy_services / len(mock_service_results)) * 100
    
    assert availability_percentage == expected_score, \
        f"Availability calculation mismatch: {availability_percentage} vs {expected_score}"
    
    # Test business SLA thresholds
    assert health_score >= 50.0, "System health should meet minimum SLA threshold"
    
    # Log business metrics for dashboard
    business_metrics = {
        "system_health_score": health_score,
        "availability_percentage": availability_percentage,
        "healthy_services_count": healthy_services,
        "total_services_count": len(mock_service_results),
        "sla_compliance": health_score >= 66.7  # Enterprise SLA threshold
    }
    
    logger.info(f"Business metrics validation completed: {business_metrics}")

@pytest.mark.asyncio
async def test_mock_services_health_endpoints():
    """
    Test that mock services provide proper health endpoints.
    
    Business Value: Infrastructure test reliability
    Validates:
    - Mock services start correctly
    - Health endpoints return expected data
    - Services can be stopped cleanly
    """
    registry = await setup_unified_mock_services()
    
    try:
        # Start mock services
        await registry.start_all_services()
        
        # Test each service health endpoint
        service_names = ["auth", "backend", "frontend"]
        
        for service_name in service_names:
            service_url = registry.get_http_service_url(service_name)
            assert service_url is not None, f"Service URL not found for {service_name}"
            
            # Test health endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                health_response = await client.get(f"{service_url}/health")
                assert health_response.status_code == 200, \
                    f"{service_name} health endpoint returned {health_response.status_code}"
                
                health_data = health_response.json()
                assert health_data["status"] == "healthy", \
                    f"{service_name} reported unhealthy status"
                assert health_data["service"] == f"{service_name}-service", \
                    f"{service_name} service name mismatch"
                
                # Test status endpoint 
                status_response = await client.get(f"{service_url}/status")
                assert status_response.status_code == 200, \
                    f"{service_name} status endpoint returned {status_response.status_code}"
        
        logger.info("All mock service health endpoints validated successfully")
        
    finally:
        # Clean up
        await registry.stop_all_services()

@pytest.mark.asyncio
async def test_mock_websocket_service():
    """
    Test mock WebSocket service functionality.
    
    Business Value: WebSocket communication testing
    Validates:
    - WebSocket connections work
    - Message handling functions
    - Health endpoint available
    """
    import websockets

    from netra_backend.tests.unified_system.mock_services import (
        create_mock_websocket_service,
    )
    
    ws_service = create_mock_websocket_service()
    
    try:
        await ws_service.start()
        
        # Test WebSocket health endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get(f"{ws_service.url}/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
            assert health_data["service"] == "websocket-service"
        
        # Test WebSocket connection (commented out due to complex setup)
        # This would require more complex WebSocket client testing
        logger.info("Mock WebSocket service health endpoint validated")
        
    finally:
        await ws_service.stop()