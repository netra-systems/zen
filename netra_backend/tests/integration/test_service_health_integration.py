"""
Integration tests for service health monitoring and validation.

Tests health check functionality:
- Health check endpoint validation
- Service dependency health verification
- Circuit breaker behavior under failures
- Service recovery and healing
- Health aggregation across services
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from startup_checks import StartupChecker

from test_framework.mock_utils import mock_justified

# Add project root to path



class HealthMonitor:
    """Mock health monitor for integration testing."""
    pass


class HealthCheckService:
    """Mock health check service for integration testing."""
    
    async def get_health_status(self):
        return {'status': 'healthy', 'timestamp': time.time(), 'services': {}, 'checks': 0}
    
    async def _check_database(self):
        return {'status': 'healthy', 'response_time_ms': 10}
    
    async def _check_database_with_circuit_breaker(self):
        return {'status': 'healthy', 'response_time_ms': 10}
    
    async def _check_all_services(self):
        return {}


class TestServiceHealthIntegration:
    """Integration tests for service health monitoring."""

    @pytest.fixture
    def health_monitor(self):
        """Create health monitor instance for testing."""
        return HealthMonitor()

    @pytest.fixture
    def mock_healthy_services(self):
        """Mock all services as healthy for baseline testing."""
        return {
            'database': {'status': 'healthy', 'response_time_ms': 5, 'last_check': time.time()},
            'redis': {'status': 'healthy', 'response_time_ms': 2, 'last_check': time.time()},
            'clickhouse': {'status': 'healthy', 'response_time_ms': 15, 'last_check': time.time()},
            'llm_providers': {'status': 'healthy', 'response_time_ms': 150, 'last_check': time.time()}
        }

    async def test_health_check_endpoint_validation(self, mock_healthy_services):
        """
        Test health check endpoint returns correct status and metrics.
        
        Validates:
        - Health endpoint responds with proper structure
        - Service statuses are aggregated correctly
        - Response times are included
        - Dependency health is reported
        """
        with patch('app.services.health_check_service.HealthCheckService._check_all_services',
                  AsyncMock(return_value=mock_healthy_services)):
            
            health_service = HealthCheckService()
            health_response = await health_service.get_health_status()
            
            self._verify_health_response_structure(health_response)
            self._verify_all_services_healthy(health_response, mock_healthy_services)
            self._verify_response_times_present(health_response)
            self._verify_overall_status(health_response, expected='healthy')

    def _verify_health_response_structure(self, response: Dict[str, Any]):
        """Verify health response has required structure."""
        required_fields = ['status', 'timestamp', 'services', 'checks']
        for field in required_fields:
            assert field in response, f"Health response missing required field: {field}"
        
        assert response['status'] in ['healthy', 'unhealthy', 'degraded']
        assert isinstance(response['services'], dict)
        assert len(response['services']) > 0, "No service health data found"

    def _verify_all_services_healthy(self, response: Dict[str, Any], expected_services: Dict[str, Any]):
        """Verify all expected services are reported as healthy."""
        for service_name, expected_data in expected_services.items():
            assert service_name in response['services'], f"Service {service_name} not in health response"
            service_data = response['services'][service_name]
            assert service_data['status'] == 'healthy', f"Service {service_name} not healthy: {service_data}"

    def _verify_response_times_present(self, response: Dict[str, Any]):
        """Verify response times are included for all services."""
        for service_name, service_data in response['services'].items():
            assert 'response_time_ms' in service_data, f"Response time missing for {service_name}"
            assert isinstance(service_data['response_time_ms'], (int, float))
            assert service_data['response_time_ms'] >= 0

    def _verify_overall_status(self, response: Dict[str, Any], expected: str):
        """Verify overall health status matches expectation."""
        assert response['status'] == expected, \
            f"Expected overall status {expected}, got {response['status']}"

    async def test_service_dependency_health_checks(self):
        """Test health checks validate all service dependencies correctly."""
        # Test database health check
        health_check = self._create_database_health_check()
        
        with patch('app.services.health_check_service.database_client', health_check['healthy_mock']):
            health_service = HealthCheckService()
            result = await health_service._check_database()
            
            assert result['status'] == 'healthy'
            assert 'response_time_ms' in result

    @mock_justified("External database not available in test environment")
    def _create_database_health_check(self):
        """Create mocks for database health check testing."""
        healthy_mock = AsyncMock()
        healthy_mock.execute.return_value = Mock(fetchone=Mock(return_value=(1,)))
        
        unhealthy_mock = AsyncMock()
        unhealthy_mock.execute.side_effect = Exception("Database connection failed")
        
        return {'healthy_mock': healthy_mock, 'unhealthy_mock': unhealthy_mock}

    @mock_justified("External Redis not available in test environment")  
    def _create_redis_health_check(self):
        """Create mocks for Redis health check testing."""
        healthy_mock = AsyncMock()
        healthy_mock.ping.return_value = True
        
        unhealthy_mock = AsyncMock()
        unhealthy_mock.ping.side_effect = Exception("Redis connection failed")
        
        return {'healthy_mock': healthy_mock, 'unhealthy_mock': unhealthy_mock}

    @mock_justified("External ClickHouse not available in test environment")
    def _create_clickhouse_health_check(self):
        """Create mocks for ClickHouse health check testing.""" 
        healthy_mock = AsyncMock()
        healthy_mock.query.return_value = [{'result': 1}]
        
        unhealthy_mock = AsyncMock()
        unhealthy_mock.query.side_effect = Exception("ClickHouse connection failed")
        
        return {'healthy_mock': healthy_mock, 'unhealthy_mock': unhealthy_mock}

    @mock_justified("External LLM providers not available in test environment")
    def _create_llm_providers_health_check(self):
        """Create mocks for LLM providers health check testing."""
        healthy_mock = AsyncMock()
        healthy_mock.health_check.return_value = {'status': 'healthy'}
        
        unhealthy_mock = AsyncMock() 
        unhealthy_mock.health_check.side_effect = Exception("LLM provider unavailable")
        
        return {'healthy_mock': healthy_mock, 'unhealthy_mock': unhealthy_mock}

    async def test_circuit_breaker_behavior_on_failures(self):
        """
        Test circuit breaker behavior when services fail.
        
        Validates:
        - Circuit opens after failure threshold
        - Requests fail fast when circuit is open
        - Circuit moves to half-open state after timeout
        - Circuit closes after successful requests
        - Health status reflects circuit breaker state
        """
        with patch('app.core.circuit_breaker.CircuitBreaker') as mock_cb_class:
            circuit_breaker = Mock()
            mock_cb_class.return_value = circuit_breaker
            
            # Test circuit breaker states
            await self._test_circuit_closed_state(circuit_breaker)
            await self._test_circuit_open_state(circuit_breaker)  
            await self._test_circuit_half_open_state(circuit_breaker)

    async def _test_circuit_closed_state(self, circuit_breaker: Mock):
        """Test circuit breaker in closed (normal) state."""
        circuit_breaker.get_status.return_value = {'state': 'closed', 'failure_count': 0}
        circuit_breaker.call = AsyncMock(side_effect=lambda func: func())
        
        health_service = HealthCheckService()
        with patch.object(health_service, '_check_database', 
                         AsyncMock(return_value={'status': 'healthy', 'response_time_ms': 10})):
            
            result = await health_service._check_database_with_circuit_breaker()
            assert result['status'] == 'healthy'
            circuit_breaker.call.assert_called_once()

    async def _test_circuit_open_state(self, circuit_breaker: Mock):
        """Test circuit breaker in open (failing fast) state."""
        circuit_breaker.get_status.return_value = {'state': 'open', 'failure_count': 5}
        circuit_breaker.call.side_effect = Exception("Circuit breaker is open")
        
        health_service = HealthCheckService()
        
        result = await health_service._check_database_with_circuit_breaker()
        assert result['status'] == 'unhealthy'
        assert 'circuit breaker' in result.get('message', '').lower()

    async def _test_circuit_half_open_state(self, circuit_breaker: Mock):
        """Test circuit breaker in half-open (testing) state."""
        circuit_breaker.get_status.return_value = {'state': 'half-open', 'failure_count': 3}
        circuit_breaker.call = AsyncMock(side_effect=lambda func: func())
        
        health_service = HealthCheckService()
        with patch.object(health_service, '_check_database',
                         AsyncMock(return_value={'status': 'healthy', 'response_time_ms': 8})):
            
            result = await health_service._check_database_with_circuit_breaker()
            assert result['status'] == 'healthy'

    async def test_service_recovery_after_failures(self):
        """
        Test service recovery detection and healing process.
        
        Validates:
        - Failed services are detected and marked unhealthy
        - Recovery is detected when service comes back online
        - Health status transitions correctly during recovery
        - Metrics track recovery times and success rates
        """
        health_service = HealthCheckService()
        
        # Simulate service failure
        with patch.object(health_service, '_check_redis',
                         AsyncMock(return_value={'status': 'unhealthy', 'error': 'Connection failed'})):
            
            failure_result = await health_service.get_health_status()
            assert failure_result['services']['redis']['status'] == 'unhealthy'
            assert failure_result['status'] in ['unhealthy', 'degraded']
            
        # Simulate service recovery
        with patch.object(health_service, '_check_redis', 
                         AsyncMock(return_value={'status': 'healthy', 'response_time_ms': 5})):
            
            recovery_result = await health_service.get_health_status()
            assert recovery_result['services']['redis']['status'] == 'healthy'
            
            # Overall status should improve if other services are healthy
            if all(svc['status'] == 'healthy' for svc in recovery_result['services'].values()):
                assert recovery_result['status'] == 'healthy'

    async def test_health_aggregation_across_services(self):
        """
        Test health status aggregation logic across multiple services.
        
        Validates:
        - Overall healthy when all services healthy
        - Overall unhealthy when critical services fail
        - Degraded status when non-critical services fail
        - Proper weight given to different service types
        """
        test_scenarios = [
            {
                'name': 'all_healthy',
                'services': {
                    'database': 'healthy', 'redis': 'healthy', 
                    'clickhouse': 'healthy', 'llm_providers': 'healthy'
                },
                'expected_overall': 'healthy'
            },
            {
                'name': 'critical_database_down',
                'services': {
                    'database': 'unhealthy', 'redis': 'healthy',
                    'clickhouse': 'healthy', 'llm_providers': 'healthy'  
                },
                'expected_overall': 'unhealthy'
            },
            {
                'name': 'non_critical_service_down',
                'services': {
                    'database': 'healthy', 'redis': 'healthy',
                    'clickhouse': 'unhealthy', 'llm_providers': 'healthy'
                },
                'expected_overall': 'degraded'
            }
        ]
        
        for scenario in test_scenarios:
            await self._test_health_aggregation_scenario(scenario)

    async def _test_health_aggregation_scenario(self, scenario: Dict[str, Any]):
        """Test individual health aggregation scenario."""
        # Mock each service to return the specified status
        mock_services = {}
        for service_name, status in scenario['services'].items():
            mock_services[service_name] = {
                'status': status, 
                'response_time_ms': 10 if status == 'healthy' else 1000,
                'last_check': time.time()
            }
        
        with patch('app.services.health_check_service.HealthCheckService._check_all_services',
                  AsyncMock(return_value=mock_services)):
            
            health_service = HealthCheckService()
            result = await health_service.get_health_status()
            
            assert result['status'] == scenario['expected_overall'], \
                f"Scenario {scenario['name']}: expected {scenario['expected_overall']}, got {result['status']}"

    async def test_health_check_performance_and_timeouts(self):
        """Test health check performance and timeout handling."""
        timeout_mock = AsyncMock(side_effect=asyncio.TimeoutError("Health check timed out"))
        
        with patch('app.services.health_check_service.HealthCheckService._check_clickhouse', timeout_mock):
            health_service = HealthCheckService()
            result = await health_service.get_health_status()
            
            # ClickHouse should be unhealthy (timed out)
            assert result['services']['clickhouse']['status'] == 'unhealthy'

    async def test_health_monitoring_in_startup_integration(self):
        """Test integration between health monitoring and startup checks."""
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        startup_checker = StartupChecker(app)
        
        # Mock external services for startup
        with patch.multiple(
            'app.startup_checks.service_checks.ServiceChecker',
            check_redis=AsyncMock(return_value=Mock(success=True, name="check_redis", message="Redis OK")),
            check_clickhouse=AsyncMock(return_value=Mock(success=True, name="check_clickhouse", message="ClickHouse OK"))
        ):
            startup_result = await startup_checker.run_all_checks()
            assert startup_result["success"] is True
            
            health_service = HealthCheckService()
            with patch.object(health_service, '_check_all_services',
                             AsyncMock(return_value={'redis': {'status': 'healthy', 'response_time_ms': 5}})):
                health_result = await health_service.get_health_status()
                assert health_result['status'] == 'healthy'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])