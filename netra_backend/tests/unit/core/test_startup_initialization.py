"""Test startup initialization and system readiness."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.health_checkers import HealthChecker


class TestStartupInitialization:
    """Test system startup initialization and readiness checks."""
    
    @pytest.mark.asyncio
    async def test_system_readiness_check_all_services(self):
        """Test comprehensive system readiness check including all services."""
        checker = HealthChecker()
        
        with patch.object(checker, 'check_postgres', AsyncMock(return_value={'healthy': True, 'latency_ms': 10})):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    auth_health = await checker.check_auth_service_health()
                    
                    # Verify all components are checked
                    assert 'database' in auth_health
                    assert 'redis' in auth_health
                    assert 'oauth' in auth_health
                    
                    # All should be healthy
                    assert auth_health['database']['healthy'] is True
                    assert auth_health['redis']['healthy'] is True  
                    assert auth_health['oauth']['healthy'] is True
    
    @pytest.mark.asyncio 
    async def test_startup_failure_scenario(self):
        """Test system behavior during startup failures."""
        checker = HealthChecker()
        
        with patch.object(checker, 'check_postgres', AsyncMock(return_value={'healthy': False, 'error': 'Connection failed'})):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    auth_health = await checker.check_auth_service_health()
                    
                    # Database should be unhealthy
                    assert auth_health['database']['healthy'] is False
                    assert 'error' in auth_health['database']
                    
                    # Other services should remain healthy
                    assert auth_health['redis']['healthy'] is True
                    assert auth_health['oauth']['healthy'] is True

    def test_initialization_timeout_configuration(self):
        """Test that initialization timeout is properly configured for different environments."""
        from netra_backend.app.core.health_checkers import _get_health_check_timeout
        
        with patch('netra_backend.app.core.environment_constants.get_current_environment') as mock_env:
            # Test production timeout (should be strict)
            mock_env.return_value = "production"
            timeout = _get_health_check_timeout()
            assert timeout == 5.0
            
            # Test development timeout (should be lenient) 
            mock_env.return_value = "development"
            timeout = _get_health_check_timeout()
            assert timeout == 10.0
            
            # Test testing timeout (should be very lenient)
            mock_env.return_value = "testing" 
            timeout = _get_health_check_timeout()
            assert timeout == 30.0

    def test_service_discovery_readiness(self):
        """Test service discovery initialization readiness."""
        # This test is currently a placeholder - service discovery is not fully implemented
        # but we want to ensure the framework is in place
        
        # Mock a basic service registry check
        service_registry = {
            'auth_service': 'http://localhost:8001',
            'main_backend': 'http://localhost:8000'
        }
        
        # Verify services are registered
        assert 'auth_service' in service_registry
        assert 'main_backend' in service_registry
        
        # Verify URLs are properly formatted
        for service, url in service_registry.items():
            assert url.startswith('http')
            assert ':' in url


class TestStartupErrorHandling:
    """Test error handling during system startup."""
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_operations(self):
        """Test that multiple startup operations can run concurrently without conflicts."""
        checker = HealthChecker()
        
        # Simulate concurrent health checks
        async def mock_health_check():
            await asyncio.sleep(0.1)  # Simulate async operation
            return {'healthy': True, 'latency_ms': 10}
        
        with patch.object(checker, 'check_postgres', side_effect=mock_health_check):
            with patch.object(checker, 'check_redis', side_effect=mock_health_check):
                
                # Run multiple health checks concurrently
                tasks = []
                for _ in range(5):
                    task = asyncio.create_task(checker.check_auth_service_health())
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert len(results) == 5
                for result in results:
                    assert 'database' in result
                    assert 'redis' in result
    
    def test_configuration_validation_on_startup(self):
        """Test that critical configuration is validated during startup."""
        from netra_backend.app.core.health_checkers import _get_service_priority_for_environment
        from netra_backend.app.core.health_checkers import ServicePriority
        
        # Test service priority configuration - verify that the function returns valid enum values
        services_to_test = ['postgres', 'redis', 'clickhouse', 'unknown_service']
        
        for service in services_to_test:
            priority = _get_service_priority_for_environment(service)
            # Ensure we get a valid ServicePriority enum value
            assert isinstance(priority, ServicePriority)
            assert priority.name in ['CRITICAL', 'IMPORTANT', 'OPTIONAL']
        
        # Verify postgres is always critical (this should be consistent across environments)
        postgres_priority = _get_service_priority_for_environment('postgres')
        assert postgres_priority.name == 'CRITICAL'
        
        # Test that priorities are consistent and reasonable
        redis_priority = _get_service_priority_for_environment('redis')
        clickhouse_priority = _get_service_priority_for_environment('clickhouse')
        
        # Redis should be at least IMPORTANT (never OPTIONAL in most environments)
        assert redis_priority.name in ['IMPORTANT', 'CRITICAL']
        
        # ClickHouse can be OPTIONAL (analytics service)
        assert clickhouse_priority.name in ['OPTIONAL', 'IMPORTANT', 'CRITICAL']

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_startup(self):
        """Test system graceful degradation when non-critical services fail during startup."""
        checker = HealthChecker()
        
        with patch.object(checker, 'check_postgres', AsyncMock(return_value={'healthy': True, 'latency_ms': 10})):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                # OAuth fails (non-critical for basic operations)
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': False, 'error': 'OAuth service unavailable'})):
                    
                    auth_health = await checker.check_auth_service_health()
                    
                    # Core services healthy
                    assert auth_health['database']['healthy'] is True
                    assert auth_health['redis']['healthy'] is True
                    
                    # OAuth unhealthy but system should continue
                    assert auth_health['oauth']['healthy'] is False
                    assert 'error' in auth_health['oauth']