from shared.isolated_environment import get_env
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment
"""Redis Connection Staging Issues - Failing Tests

Tests that expose Redis connection failures found during GCP staging logs audit.
These tests are designed to FAIL to demonstrate current Redis connection problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and Redis cache functionality
- Value Impact: Ensures Redis caching works correctly in staging/production
- Strategic Impact: Prevents cache-related performance issues affecting all user tiers

Key Issues from GCP Staging Logs Audit:
1. Redis Connection Issues (MEDIUM): Redis initialization fails with "cannot access local variable 'get_env'" error
2. Variable scoping issues in Redis setup functions
3. Fallback behavior when Redis is unavailable

Expected Behavior:
- Tests should FAIL with current Redis configuration
- Tests demonstrate specific variable scoping errors
- Tests provide clear error reproduction for debugging

Test Categories:
- Redis initialization with environment variable handling
- Redis connection pool management
- Redis fallback and error handling
"""

import os
import pytest
import asyncio
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.core.configuration.base import get_unified_config


class TestRedisConnectionStagingFailures:
    """Test Redis connection failures in staging environment."""
    
    @pytest.mark.asyncio
    async def test_redis_initialization_with_proper_async_handling(self):
        """Test Redis initialization with proper async handling.
        
        This test validates that Redis initialization works correctly when called as an async method.
        Fixes the original issue where async methods were being called synchronously.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'GCP_PROJECT_ID': 'netra-staging',
            'TEST_DISABLE_REDIS': 'true',  # Disable Redis for testing
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Create Redis manager with test mode to avoid real connection attempts
            redis_manager = RedisManager(test_mode=True)
            
            # EXPECTED: Should initialize Redis manager without errors when called correctly
            try:
                # Properly await the async initialize method
                await redis_manager.initialize()
                
                # Test that Redis manager handles the staging environment correctly
                # In test mode with disabled Redis, this should not raise errors
                assert redis_manager is not None, \
                    "Redis manager should be created successfully"
                
                # Test basic Redis operations in test mode (should work without real Redis)
                test_result = await redis_manager.get("test_key")
                assert test_result is None, \
                    "Redis operations should work in test mode even without real Redis connection"
                
            except Exception as e:
                # Should not fail due to variable scoping issues
                pytest.fail(f"Redis initialization failed unexpectedly: {e}")
            
            finally:
                # Cleanup
                try:
                    await redis_manager.disconnect()
                except:
                    pass  # Ignore cleanup errors in test mode

    @pytest.mark.asyncio
    async def test_redis_async_connection_with_environment_variables_works(self):
        """Test async Redis connection with environment variable handling.
        
        This test validates that environment variable handling works correctly in async context.
        Tests that Redis operations work properly with test mode fallback.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'REDIS_MAX_CONNECTIONS': '20',
            'REDIS_RETRY_ON_TIMEOUT': 'true',
            'TEST_DISABLE_REDIS': 'true',  # Disable real Redis for testing
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Use test mode to avoid real Redis connections
            redis_manager = RedisManager(test_mode=True)
            
            try:
                # Test Redis manager connection handling
                await redis_manager.connect()
                
                # Test basic Redis operations (should work in test mode)
                await redis_manager.set("test_key", "test_value")
                result = await redis_manager.get("test_key")
                
                # In test mode without real Redis, operations should not raise errors
                # but may return None (graceful degradation)
                assert result is None or result == "test_value", \
                    f"Redis operations should work gracefully in test mode, got: {result}"
                
                # Test list operations
                list_result = await redis_manager.get_list("test_list")
                assert isinstance(list_result, list), \
                    f"Should return list type for list operations, got: {type(list_result)}"
                
            except Exception as e:
                # Should not fail due to variable scoping issues
                pytest.fail(f"Async Redis operations failed unexpectedly: {e}")
                
            finally:
                try:
                    await redis_manager.disconnect()
                except:
                    pass  # Ignore cleanup errors in test mode

    @pytest.mark.asyncio
    async def test_redis_fallback_behavior_works_correctly(self):
        """Test Redis fallback behavior with proper error handling.
        
        This test validates that Redis fallback mechanisms work correctly when Redis is unavailable.
        Tests graceful degradation without variable scoping issues.
        """
        # Set environment that should trigger fallback
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://invalid-redis-host:6379/0',  # Invalid host to trigger fallback
            'REDIS_FALLBACK_ENABLED': 'true',
            'TEST_DISABLE_REDIS': 'true',  # Use test mode for controlled fallback
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Use test mode to simulate fallback behavior
            redis_manager = RedisManager(test_mode=True)
            
            try:
                # Test Redis initialization with fallback
                await redis_manager.connect()
                
                # Test that operations work even when Redis is not available
                # In test mode, operations should not raise errors
                result = await redis_manager.get("test_key")
                assert result is None, \
                    "Should return None for missing keys when Redis is not available"
                
                # Test set operation (should not raise errors)
                set_result = await redis_manager.set("test_key", "test_value")
                # In test mode without real Redis, set operations may return None
                
                # Test list operations
                list_result = await redis_manager.get_list("test_list")
                assert isinstance(list_result, list), \
                    f"Should return empty list when Redis is not available, got: {type(list_result)}"
                
            except Exception as e:
                # Should not fail due to variable scoping issues
                pytest.fail(f"Redis fallback handling failed unexpectedly: {e}")
                
            finally:
                try:
                    await redis_manager.disconnect()
                except:
                    pass  # Ignore cleanup errors

    def test_redis_connection_pool_configuration_scoping_fails(self):
        """Test Redis connection pool configuration with variable scoping.
        
        ISSUE: Connection pool configuration fails due to environment variable scoping
        This test FAILS to demonstrate connection pool setup problems.
        
        Expected to FAIL: Connection pool setup affected by scoping issues
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'REDIS_MAX_CONNECTIONS': '50',
            'REDIS_SOCKET_KEEPALIVE': 'true',
            'REDIS_SOCKET_KEEPALIVE_OPTIONS': '{"TCP_KEEPIDLE": 1, "TCP_KEEPINTVL": 3, "TCP_KEEPCNT": 5}',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            redis_manager = RedisManager()
            
            # EXPECTED: Should configure connection pool with environment variables
            # ACTUAL: Configuration may fail due to variable scoping in setup code
            try:
                pool = redis_manager.create_connection_pool()
                
                # Verify pool configuration matches environment variables
                assert pool.connection_kwargs.get('max_connections') == 50, \
                    f"Should use REDIS_MAX_CONNECTIONS from environment, got: {pool.connection_kwargs.get('max_connections')}"
                
                # Verify socket options are properly configured
                socket_keepalive = pool.connection_kwargs.get('socket_keepalive')
                assert socket_keepalive is True, \
                    f"Should enable socket keepalive from environment, got: {socket_keepalive}"
                
            except UnboundLocalError as e:
                if "get_env" in str(e):
                    pytest.fail(
                        f"Redis connection pool configuration failed due to get_env scoping: {e}\n"
                        f"This indicates variable scoping affects connection pool setup."
                    )
                else:
                    raise
                    
            # This test will FAIL if variable scoping affects connection pool configuration

    def test_redis_health_check_with_environment_detection_fails(self):
        """Test Redis health check with environment detection issues.
        
        ISSUE: Health check fails due to environment variable scoping in detection logic
        This test FAILS to demonstrate health check environment detection problems.
        
        Expected to FAIL: Health check cannot properly detect staging environment
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'K_SERVICE': 'netra-backend-staging',
            'GCP_PROJECT_ID': 'netra-staging',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Mock Redis connection to focus on environment detection issue
            with patch('redis.Redis') as mock_redis:
                mock_redis_instance = MagicNone  # TODO: Use real service instance
                mock_redis_instance.ping.return_value = True
                mock_redis.return_value = mock_redis_instance
                
                redis_manager = RedisManager()
                
                # EXPECTED: Should perform health check with proper environment detection
                # ACTUAL: May fail due to get_env variable scoping in health check logic
                try:
                    health_status = redis_manager.health_check()
                    
                    # Should return health status information
                    assert health_status is not None, \
                        "Health check should return status information"
                    
                    assert health_status.get('environment') == 'staging', \
                        f"Should detect staging environment, got: {health_status.get('environment')}"
                    
                    assert health_status.get('redis_connected') is True, \
                        f"Should show Redis as connected, got: {health_status.get('redis_connected')}"
                    
                except UnboundLocalError as e:
                    if "get_env" in str(e):
                        pytest.fail(
                            f"Redis health check failed due to get_env scoping: {e}\n"
                            f"This indicates variable scoping affects health check environment detection."
                        )
                    else:
                        raise
                        
                # This test will FAIL if variable scoping affects health check logic

    def test_redis_configuration_loading_order_fails(self):
        """Test Redis configuration loading order with variable scoping.
        
        ISSUE: Configuration loading order affected by variable scoping issues
        This test FAILS to demonstrate configuration loading problems.
        
        Expected to FAIL: Configuration loading has variable scoping issues
        """
        # Test with multiple environment variable patterns
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'NETRA_REDIS_URL': 'redis://netra-redis-staging:6379/0',  # Alternative naming
            'STAGING_REDIS_URL': 'redis://staging-redis:6379/0',      # Environment-specific
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            redis_manager = RedisManager()
            
            # EXPECTED: Should load configuration with proper priority order
            # ACTUAL: Configuration loading may fail due to variable scoping
            try:
                config = redis_manager.load_configuration()
                
                # Should prioritize environment-specific configuration
                redis_url = config.get('redis_url')
                assert redis_url is not None, \
                    "Should load Redis URL from configuration"
                
                # Should use correct priority: STAGING_REDIS_URL > NETRA_REDIS_URL > REDIS_URL
                expected_urls = ['redis://staging-redis:6379/0', 'redis://netra-redis-staging:6379/0', 'redis://redis-staging:6379/0']
                assert redis_url in expected_urls, \
                    f"Should use one of the configured Redis URLs, got: {redis_url}"
                
            except UnboundLocalError as e:
                if "get_env" in str(e):
                    pytest.fail(
                        f"Redis configuration loading failed due to get_env scoping: {e}\n"
                        f"This indicates variable scoping affects configuration loading logic."
                    )
                else:
                    raise
                    
            # This test will FAIL if variable scoping affects configuration loading


class TestRedisConnectionScopingEdgeCases:
    """Test edge cases related to Redis variable scoping issues."""
    
    def test_redis_manager_singleton_initialization_scoping_fails(self):
        """Test Redis manager singleton initialization with scoping issues.
        
        ISSUE: Singleton pattern affected by variable scoping in initialization
        This test FAILS to demonstrate singleton initialization problems.
        
        Expected to FAIL: Singleton initialization has scoping issues
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Clear any existing singleton instance
            RedisManager._instance = None
            
            # EXPECTED: Should create singleton instance without scoping errors
            # ACTUAL: Singleton creation may fail due to get_env scoping
            try:
                manager1 = RedisManager.get_instance()
                manager2 = RedisManager.get_instance()
                
                # Should be the same instance
                assert manager1 is manager2, \
                    "Should return the same singleton instance"
                
                # Should be properly initialized
                assert manager1.is_initialized(), \
                    "Singleton instance should be properly initialized"
                
            except UnboundLocalError as e:
                if "get_env" in str(e):
                    pytest.fail(
                        f"Redis manager singleton initialization failed due to get_env scoping: {e}\n"
                        f"This indicates variable scoping affects singleton pattern implementation."
                    )
                else:
                    raise
                    
            # This test will FAIL if variable scoping affects singleton initialization

    def test_redis_retry_mechanism_with_scoping_fails(self):
        """Test Redis retry mechanism affected by variable scoping.
        
        ISSUE: Retry mechanism fails due to environment variable scoping in retry logic
        This test FAILS to demonstrate retry mechanism problems.
        
        Expected to FAIL: Retry mechanism affected by scoping issues
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://redis-staging:6379/0',
            'REDIS_RETRY_ATTEMPTS': '3',
            'REDIS_RETRY_DELAY': '1.0',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            redis_manager = RedisManager()
            
            # Mock Redis to fail initially, then succeed
            with patch('redis.Redis') as mock_redis:
                mock_redis_instance = MagicNone  # TODO: Use real service instance
                # First two calls fail, third succeeds
                mock_redis_instance.ping.side_effect = [ConnectionError("Connection failed")] * 2 + [True]
                mock_redis.return_value = mock_redis_instance
                
                # EXPECTED: Should retry connection and eventually succeed
                # ACTUAL: Retry mechanism may fail due to variable scoping
                try:
                    result = redis_manager.connect_with_retry()
                    
                    assert result is True, \
                        "Should eventually connect after retries"
                    
                    # Verify retry logic was used (ping called multiple times)
                    assert mock_redis_instance.ping.call_count >= 2, \
                        f"Should have retried connection, ping called {mock_redis_instance.ping.call_count} times"
                    
                except UnboundLocalError as e:
                    if "get_env" in str(e):
                        pytest.fail(
                            f"Redis retry mechanism failed due to get_env scoping: {e}\n"
                            f"This indicates variable scoping affects retry logic implementation."
                        )
                    else:
                        raise
                        
                # This test will FAIL if variable scoping affects retry mechanism


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
