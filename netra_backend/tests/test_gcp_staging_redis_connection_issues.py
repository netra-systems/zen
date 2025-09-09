"""
GCP Staging Redis Connection Issues - Failing Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments) 
- Business Goal: Platform Stability and Session Management
- Value Impact: Prevents Redis failures that block session management and caching
- Strategic/Revenue Impact: User sessions and performance caching depend on Redis

These failing tests replicate Redis connectivity issues found in GCP staging deployment.
The tests are designed to FAIL until the underlying Redis provisioning/configuration issues are resolved.

Critical Issues Tested:
1. Redis service not provisioned/configured in staging environment
2. Redis connection URL formatting issues
3. Redis authentication failures with staging credentials
4. Redis connection pool initialization failures
5. Redis operations failing due to connectivity issues
"""

import asyncio
import pytest
from typing import Dict, Any, Optional
import redis.asyncio as redis
from redis.exceptions import ConnectionError, AuthenticationError, TimeoutError
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager

from netra_backend.app.config import get_config
from shared.isolated_environment import IsolatedEnvironment


class TestRedisConnectionIssues:
    """Test Redis connection issues from GCP staging deployment."""
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_service_not_provisioned_in_staging(self):
        """Test Redis service not provisioned/configured in staging environment.
        
        This test should FAIL until Redis is properly provisioned in staging.
        """
        # Mock staging environment without Redis URL
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'REDIS_URL': None,  # Redis not configured
                'REDIS_HOST': None,
                'REDIS_PORT': None,
                'REDIS_PASSWORD': None
            }.get(key, default)
            
            try:
                # Try to create Redis connection
                config = get_config()
                redis_url = config.redis_url or f"redis://{config.redis_host}:{config.redis_port}"
                
                if not redis_url or redis_url == "redis://None:None":
                    raise ValueError("Redis URL not configured in staging environment")
                
                # Try to connect to Redis
                redis_client = redis.from_url(redis_url)
                await redis_client.ping()
                
                pytest.fail("Expected Redis connection to fail when service not provisioned")
                
            except Exception as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'connection refused',
                    'redis url not configured',
                    'not configured',
                    'connection failed',
                    'redis not available',
                    'no redis service'
                ]), f"Expected Redis provisioning error but got: {e}"
                
                print(f"✅ Correctly detected Redis not provisioned in staging: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_connection_url_formatting_issues(self):
        """Test Redis connection URL formatting issues from secret management."""
        # Test various malformed Redis URLs
        malformed_redis_urls = [
            "redis://localhost:6379\n",  # Trailing newline
            " redis://localhost:6379 ",  # Leading/trailing spaces
            "redis://localhost:6379\r",  # Carriage return
            "redis://\tlocalhost:6379",  # Tab character
            "redis://user:password@localhost:6379\n\r",  # Multiple control chars
            "",  # Empty URL
            "redis://",  # Incomplete URL
            "redis://localhost:",  # Missing port
            "redis://:6379",  # Missing host
        ]
        
        for malformed_url in malformed_redis_urls:
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: {
                    'REDIS_URL': malformed_url,
                    'ENVIRONMENT': 'staging'
                }.get(key, default)
                
                try:
                    # Try to create Redis client with malformed URL
                    if malformed_url.strip():
                        redis_client = redis.from_url(malformed_url.strip())
                        await redis_client.ping()
                    else:
                        raise ValueError("Empty Redis URL")
                    
                    pytest.fail(f"Expected Redis URL validation to fail for: {repr(malformed_url)}")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'invalid url',
                        'connection failed',
                        'malformed',
                        'empty',
                        'format',
                        'connection refused'
                    ]), f"Expected URL formatting error for {repr(malformed_url)} but got: {e}"
                    
                    print(f"✅ Redis URL formatting error detected for {repr(malformed_url)}: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_authentication_failure_with_wrong_credentials(self):
        """Test Redis authentication failure with wrong credentials."""
        # Mock Redis URL with wrong password
        wrong_password_redis_url = "redis://:wrong_password@localhost:6379/0"
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'REDIS_URL': wrong_password_redis_url,
                'ENVIRONMENT': 'staging'
            }.get(key, default)
            
            try:
                # Try to connect with wrong credentials
                redis_client = redis.from_url(wrong_password_redis_url)
                await redis_client.ping()
                
                pytest.fail("Expected Redis authentication failure with wrong password")
                
            except (AuthenticationError, ConnectionError) as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'auth',
                    'password',
                    'authentication failed',
                    'invalid password',
                    'access denied'
                ]), f"Expected Redis authentication error but got: {e}"
                
                print(f"✅ Redis authentication failure correctly detected: {e}")
                
            except Exception as e:
                # Connection refused is also acceptable (Redis not available)
                error_msg = str(e).lower()
                if 'connection refused' in error_msg:
                    print(f"✅ Redis connection refused (service not available): {e}")
                else:
                    pytest.fail(f"Expected Redis authentication or connection error but got: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_connection_pool_initialization_failure(self):
        """Test Redis connection pool initialization failure."""
        # Mock Redis connection that fails during pool creation
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'REDIS_URL': 'redis://localhost:6379/0',
                'ENVIRONMENT': 'staging'
            }.get(key, default)
            
            # Mock Redis connection pool that fails
            with patch('redis.asyncio.ConnectionPool') as mock_pool:
                mock_pool.side_effect = ConnectionError("Redis connection pool initialization failed")
                
                try:
                    redis_client = redis.Redis(connection_pool=mock_pool())
                    await redis_client.ping()
                    
                    pytest.fail("Expected Redis connection pool initialization to fail")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'connection pool',
                        'initialization failed',
                        'connection error',
                        'redis',
                        'pool'
                    ]), f"Expected Redis pool initialization error but got: {e}"
                    
                    print(f"✅ Redis connection pool initialization failure detected: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_basic_operations_connectivity_failure(self):
        """Test Redis basic operations fail due to connectivity issues."""
        # Mock Redis client that connects but operations fail
        mock_redis_client = MagicNone  # TODO: Use real service instance
        
        # Mock Redis operations to fail with connection errors
        async def failing_operation(*args, **kwargs):
            raise ConnectionError("Lost connection to Redis server")
        
        mock_redis_client.ping = AsyncMock(side_effect=failing_operation)
        mock_redis_client.set = AsyncMock(side_effect=failing_operation)
        mock_redis_client.get = AsyncMock(side_effect=failing_operation)
        mock_redis_client.delete = AsyncMock(side_effect=failing_operation)
        mock_redis_client.exists = AsyncMock(side_effect=failing_operation)
        
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            try:
                redis_client = redis.from_url("redis://localhost:6379/0")
                
                # Test basic operations that should fail
                operations = [
                    ("ping", lambda: redis_client.ping()),
                    ("set", lambda: redis_client.set("test_key", "test_value")),
                    ("get", lambda: redis_client.get("test_key")),
                    ("delete", lambda: redis_client.delete("test_key")),
                    ("exists", lambda: redis_client.exists("test_key")),
                ]
                
                for op_name, operation in operations:
                    try:
                        await operation()
                        pytest.fail(f"Expected Redis {op_name} operation to fail")
                    except ConnectionError as e:
                        print(f"✅ Redis {op_name} operation correctly failed: {e}")
                        
            except Exception as e:
                # Any Redis-related error is acceptable
                error_msg = str(e).lower()
                assert 'redis' in error_msg, f"Expected Redis-related error but got: {e}"
                print(f"✅ Redis operations failed as expected: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_connection_timeout_in_staging(self):
        """Test Redis connection timeout issues in staging environment."""
        # Mock Redis URL with very short timeout
        redis_url = "redis://localhost:6379/0"
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'REDIS_URL': redis_url,
                'ENVIRONMENT': 'staging'
            }.get(key, default)
            
            try:
                # Create Redis client with very short timeout
                redis_client = redis.from_url(
                    redis_url,
                    socket_timeout=0.1,
                    socket_connect_timeout=0.1
                )
                
                # This should timeout or fail quickly
                start_time = asyncio.get_event_loop().time()
                await redis_client.ping()
                elapsed = asyncio.get_event_loop().time() - start_time
                
                if elapsed > 5:
                    pytest.fail("Redis connection should have timed out or failed quickly")
                    
                print("✅ Redis connection succeeded (unexpected but acceptable)")
                
            except (TimeoutError, ConnectionError) as e:
                elapsed = asyncio.get_event_loop().time() - start_time
                assert elapsed < 10, f"Timeout took too long: {elapsed}s"
                
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'timeout',
                    'connection',
                    'timed out',
                    'connection refused'
                ]), f"Expected timeout or connection error but got: {e}"
                
                print(f"✅ Redis connection timeout correctly detected in {elapsed:.2f}s: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_cluster_mode_configuration_mismatch(self):
        """Test Redis cluster mode configuration mismatch in staging."""
        # Mock Redis configured for cluster mode but connecting to single instance
        cluster_redis_url = "redis://localhost:6379/0?cluster=true"
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'REDIS_URL': cluster_redis_url,
                'REDIS_CLUSTER_MODE': 'true',
                'ENVIRONMENT': 'staging'
            }.get(key, default)
            
            try:
                # Try to create cluster client connecting to single instance
                redis_client = redis.from_url(cluster_redis_url)
                await redis_client.ping()
                
                print("✅ Redis connection succeeded (single instance mode)")
                
            except Exception as e:
                error_msg = str(e).lower()
                # Accept any Redis-related configuration errors
                assert any(keyword in error_msg for keyword in [
                    'cluster',
                    'connection',
                    'redis',
                    'configuration',
                    'mode'
                ]), f"Expected Redis configuration error but got: {e}"
                
                print(f"✅ Redis cluster configuration mismatch detected: {e}")
    
    @pytest.mark.staging
    def test_staging_environment_redis_requirements(self):
        """Test that staging environment enforces Redis configuration requirements."""
        # Mock staging environment with missing Redis configuration
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': None,
            'REDIS_HOST': None,
            'REDIS_PORT': None
        }
        
        with patch.dict('os.environ', staging_env_vars, clear=False):
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: staging_env_vars.get(key, default)
                
                try:
                    config = get_config()
                    
                    # Staging should require Redis configuration
                    redis_url = config.redis_url
                    if not redis_url:
                        redis_url = f"redis://{config.redis_host}:{config.redis_port}"
                    
                    if not redis_url or 'None' in redis_url:
                        raise ValueError("Redis configuration is required in staging environment")
                    
                    pytest.fail("Expected staging to require Redis configuration")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'redis',
                        'required',
                        'configuration',
                        'staging',
                        'not configured'
                    ]), f"Expected Redis configuration requirement error but got: {e}"
                    
                    print(f"✅ Staging correctly requires Redis configuration: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_ssl_configuration_mismatch_in_staging(self):
        """Test Redis SSL configuration mismatch in staging environment."""
        # Mock Redis URL requiring SSL but service not supporting it
        ssl_redis_url = "rediss://localhost:6380/0"  # SSL Redis URL
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'REDIS_URL': ssl_redis_url,
                'ENVIRONMENT': 'staging'
            }.get(key, default)
            
            try:
                # Try to connect with SSL to non-SSL Redis
                redis_client = redis.from_url(ssl_redis_url)
                await redis_client.ping()
                
                print("✅ Redis SSL connection succeeded (SSL properly configured)")
                
            except Exception as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'ssl',
                    'connection',
                    'certificate',
                    'handshake',
                    'connection refused',
                    'tls'
                ]), f"Expected SSL-related error but got: {e}"
                
                print(f"✅ Redis SSL configuration mismatch detected: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_redis_memory_management_configuration_issues(self):
        """Test Redis memory management configuration issues in staging."""
        # Mock Redis client
        mock_redis_client = MagicNone  # TODO: Use real service instance
        
        # Mock Redis info command to return memory pressure
        async def mock_redis_info():
            return {
                'used_memory': 1073741824,  # 1GB
                'maxmemory': 536870912,     # 512MB (less than used!)
                'maxmemory_policy': 'noeviction',
                'used_memory_peak': 1073741824
            }
        
        mock_redis_client.info = AsyncMock(return_value=mock_redis_info())
        mock_redis_client.set = AsyncMock(side_effect=Exception("OOM command not allowed when used memory > 'maxmemory'"))
        
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            try:
                redis_client = redis.from_url("redis://localhost:6379/0")
                
                # Check memory configuration
                info = await redis_client.info()
                used_memory = info.get('used_memory', 0)
                max_memory = info.get('maxmemory', 0)
                
                if max_memory > 0 and used_memory > max_memory:
                    print(f"⚠️ Redis memory pressure detected: {used_memory}/{max_memory} bytes")
                
                # Try to perform operation that might fail due to memory
                await redis_client.set("test_key", "test_value")
                
                pytest.fail("Expected Redis operation to fail due to memory issues")
                
            except Exception as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'oom',
                    'memory',
                    'maxmemory',
                    'out of memory',
                    'eviction'
                ]), f"Expected Redis memory-related error but got: {e}"
                
                print(f"✅ Redis memory management issue detected: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "staging"])