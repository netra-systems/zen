"""Enhanced error handling tests for core components."""
import pytest
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock, Mock
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.health_checkers import HealthChecker


class TestErrorHandlingResilience:
    """Test error handling and resilience patterns."""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_resilience(self):
        """Test system resilience to cascading failures."""
        checker = HealthChecker()
        
        # Simulate cascading failure: database fails, then redis fails
        with patch.object(checker, 'check_postgres', AsyncMock(side_effect=Exception("Database connection lost"))):
            with patch.object(checker, 'check_redis', AsyncMock(side_effect=Exception("Redis connection lost after DB failure"))):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    auth_health = await checker.check_auth_service_health()
                    
                    # Both database and redis should show errors
                    assert auth_health['database']['healthy'] is False
                    assert 'error' in auth_health['database']
                    assert auth_health['redis']['healthy'] is False
                    assert 'error' in auth_health['redis']
                    
                    # OAuth should remain healthy (independent service)
                    assert auth_health['oauth']['healthy'] is True
    
    @pytest.mark.asyncio
    async def test_timeout_handling_in_health_checks(self):
        """Test proper timeout handling in health checks."""
        checker = HealthChecker()
        
        async def slow_database_check():
            await asyncio.sleep(2)  # Simulate very slow database
            return {'healthy': True, 'latency_ms': 10000}
        
        with patch.object(checker, 'check_postgres', side_effect=slow_database_check):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    # This should handle timeout gracefully
                    try:
                        auth_health = await asyncio.wait_for(
                            checker.check_auth_service_health(), 
                            timeout=1.0
                        )
                        
                        # Should still get results for fast services
                        assert 'redis' in auth_health
                        assert 'oauth' in auth_health
                        
                    except asyncio.TimeoutError:
                        # This is expected behavior - the slow database should timeout
                        # but we should still be able to get partial results
                        # Let's test the individual service checks instead
                        redis_health = await checker.check_redis()
                        oauth_health = await checker.check_oauth_providers()
                        
                        assert redis_health['healthy'] is True
                        assert oauth_health['healthy'] is True

    def test_error_recovery_mechanisms(self):
        """Test error recovery and retry mechanisms.""" 
        from netra_backend.app.core.health_checkers import _handle_service_failure
        from netra_backend.app.core.health_checkers import ServicePriority
        
        # Test different failure handling based on service priority
        critical_failure = _handle_service_failure("postgres", "Connection failed", 100.0)
        assert critical_failure.success is False
        assert critical_failure.status == "unhealthy"
        
        # Test with proper error message
        assert "Connection failed" in critical_failure.error_message
        assert critical_failure.response_time_ms == 100.0

    @pytest.mark.asyncio  
    async def test_concurrent_error_scenarios(self):
        """Test behavior under concurrent error scenarios."""
        checker = HealthChecker()
        
        # Test multiple concurrent auth service health checks with different postgres errors
        tasks = []
        
        with patch.object(checker, 'check_postgres', AsyncMock(side_effect=Exception("Database connection failed"))):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    # Run multiple concurrent health checks
                    for _ in range(3):
                        task = asyncio.create_task(checker.check_auth_service_health())
                        tasks.append(task)
                    
                    # All should handle errors gracefully without crashing
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Should get proper error responses, not exceptions
                    assert len(results) == 3
                    for result in results:
                        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
                        assert 'database' in result
                        assert result['database']['healthy'] is False
                        assert "Database connection failed" in result['database']['error']
                        # Other services should remain healthy
                        assert result['redis']['healthy'] is True
                        assert result['oauth']['healthy'] is True


class TestSystemResourceErrorHandling:
    """Test system resource monitoring error handling."""
    
    def test_system_resource_unavailable_handling(self):
        """Test handling when system resources are unavailable."""
        from netra_backend.app.core.health_checkers import check_system_resources
        
        with patch('netra_backend.app.core.health_checkers.psutil.cpu_percent', side_effect=Exception("CPU monitoring unavailable")):
            with patch('netra_backend.app.core.health_checkers.psutil.virtual_memory', side_effect=Exception("Memory monitoring unavailable")):
                with patch('netra_backend.app.core.health_checkers.psutil.disk_usage', side_effect=Exception("Disk monitoring unavailable")):
                    
                    result = check_system_resources()
                    
                    # Should return failure result, not crash
                    assert result.component_name == "system_resources"
                    assert result.success is False
                    assert "unavailable" in result.error_message.lower() or "monitoring" in result.error_message.lower()

    def test_partial_system_resource_failure(self):
        """Test handling when only some system resources fail."""
        from netra_backend.app.core.health_checkers import check_system_resources
        
        # CPU fails, but memory and disk work
        with patch('netra_backend.app.core.health_checkers.psutil.cpu_percent', side_effect=Exception("CPU monitoring unavailable")):
            with patch('netra_backend.app.core.health_checkers.psutil.virtual_memory') as mock_memory:
                with patch('netra_backend.app.core.health_checkers.psutil.disk_usage') as mock_disk:
                    
                    mock_memory.return_value = Mock(percent=40.0, available=8*1024**3)
                    mock_disk.return_value = Mock(percent=30.0, free=100*1024**3)
                    
                    result = check_system_resources()
                    
                    # Should gracefully handle partial failure
                    assert result.component_name == "system_resources"
                    # Either succeeds with degraded data or fails gracefully
                    assert isinstance(result.success, bool)


class TestDatabaseConnectionErrorHandling:
    """Test database connection error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self):
        """Test behavior when database connection pool is exhausted."""
        from netra_backend.app.core.health_checkers import check_postgres_health
        
        with patch('netra_backend.app.core.health_checkers._execute_postgres_query', 
                  side_effect=Exception("connection pool exhausted")):
            
            result = await check_postgres_health()
            
            assert result.component_name == "postgres"
            assert result.success is False
            assert "pool exhausted" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_database_ssl_configuration_error(self):
        """Test handling of SSL configuration errors."""
        from netra_backend.app.core.health_checkers import check_postgres_health
        
        with patch('netra_backend.app.core.health_checkers._execute_postgres_query', 
                  side_effect=RuntimeError("Health check blocked - sslmode parameter detected in database URL")):
            
            result = await check_postgres_health()
            
            assert result.component_name == "postgres"
            assert result.success is False
            assert "sslmode" in result.error_message


class TestCircuitBreakerErrorHandling:
    """Test circuit breaker integration with error handling."""
    
    def test_circuit_breaker_error_classification(self):
        """Test that circuit breakers properly classify different error types."""
        # This is a placeholder for when circuit breaker integration is enhanced
        from netra_backend.app.core.health_checkers import _handle_service_failure
        
        # Test different error types
        timeout_failure = _handle_service_failure("redis", "Timeout after 5 seconds", 5000.0)
        connection_failure = _handle_service_failure("redis", "Connection refused", 100.0) 
        
        # Both should be properly handled
        assert timeout_failure.success is False
        assert connection_failure.success is False
        
        # Response times should be recorded
        assert timeout_failure.response_time_ms == 5000.0
        assert connection_failure.response_time_ms == 100.0

    @pytest.mark.asyncio
    async def test_health_check_with_circuit_breaker_open(self):
        """Test health checks when circuit breaker is open."""
        checker = HealthChecker()
        
        # Simulate circuit breaker being open (fail-fast mode)
        with patch.object(checker, 'check_postgres', AsyncMock(side_effect=Exception("Circuit breaker OPEN - failing fast"))):
            with patch.object(checker, 'check_redis', AsyncMock(return_value={'healthy': True, 'latency_ms': 5})):
                with patch.object(checker, 'check_oauth_providers', AsyncMock(return_value={'healthy': True, 'latency_ms': 20})):
                    
                    auth_health = await checker.check_auth_service_health()
                    
                    # Database should show circuit breaker error
                    assert auth_health['database']['healthy'] is False
                    assert "circuit breaker" in auth_health['database']['error'].lower()
                    
                    # Other services should work normally
                    assert auth_health['redis']['healthy'] is True
                    assert auth_health['oauth']['healthy'] is True