"""
Test Redis Staging Fixes for Auth Service
Verifies that Redis localhost fallback is prevented in staging/production

CRITICAL: ZERO MOCKS - Uses only real Redis services and isolated environment
"""
import pytest
import os
import asyncio
from shared.isolated_environment import IsolatedEnvironment

# REAL SERVICES ONLY - No mock imports
from test_framework.real_services import get_real_services
from shared.isolated_environment import get_env


@pytest.mark.asyncio
async def test_redis_no_localhost_fallback_in_staging(isolated_test_env):
    """Test that localhost fallback is prevented in staging environment"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    # No REDIS_URL set
    env.set("REDIS_REQUIRED", "false", "test_redis_staging")
    env.set("REDIS_FALLBACK_ENABLED", "false", "test_redis_staging")
    
    # Import after setting env vars
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    await manager.initialize()
    
    # Should be disabled without Redis URL in staging
    assert not manager.enabled
    assert manager.redis_client is None


@pytest.mark.asyncio
async def test_redis_localhost_rejected_in_staging(isolated_test_env):
    """Test that localhost Redis URL is rejected in staging unless explicitly allowed"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    env.set("REDIS_URL", "redis://localhost:6379", "test_redis_staging")
    env.set("REDIS_REQUIRED", "true", "test_redis_staging")
    env.set("REDIS_FALLBACK_ENABLED", "false", "test_redis_staging")
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    
    # Should raise error about localhost not allowed
    with pytest.raises(ValueError) as exc_info:
        await manager.initialize()
    
    assert "Localhost Redis URL not allowed in staging" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_required_in_staging(isolated_test_env):
    """Test that Redis can be marked as required in staging"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    # No REDIS_URL
    env.set("REDIS_REQUIRED", "true", "test_redis_staging")
    env.set("REDIS_FALLBACK_ENABLED", "false", "test_redis_staging")
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    
    # Should raise error when required but not configured
    with pytest.raises(ValueError) as exc_info:
        await manager.initialize()
    
    assert "REDIS_URL must be configured in staging" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_graceful_degradation_when_not_required(isolated_test_env):
    """Test graceful degradation when Redis not required in staging"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    # No REDIS_URL
    env.set("REDIS_REQUIRED", "false", "test_redis_staging")
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    await manager.initialize()
    
    # Should gracefully degrade
    assert not manager.enabled
    assert manager.redis_client is None
    
    # Operations should return None/False
    assert await manager.get("test") is None
    assert await manager.set("test", "value") is False
    assert await manager.exists("test") is False


@pytest.mark.asyncio
async def test_redis_localhost_allowed_in_development(isolated_test_env, real_auth_redis):
    """Test that localhost fallback IS allowed in development"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "development", "test_redis_staging")
    # No REDIS_URL - should fallback to localhost
    env.set("REDIS_URL", "redis://localhost:6381/3", "test_redis_staging")  # Use test Redis
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    
    # REAL REDIS - Use actual test Redis connection
    await manager.initialize()
    
    # Should successfully connect to localhost in development
    assert manager.enabled
    assert manager.redis_client is not None
    
    # Test actual Redis operations
    await manager.set("test_dev", "value_dev")
    value = await manager.get("test_dev")
    assert value == "value_dev"


@pytest.mark.asyncio
async def test_redis_connection_configuration(isolated_test_env, real_auth_redis):
    """Test Redis connection configuration with real Redis"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    env.set("REDIS_URL", "redis://localhost:6381/3", "test_redis_staging")  # Use test Redis
    env.set("REDIS_REQUIRED", "false", "test_redis_staging")
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    
    # REAL REDIS - Test actual connection configuration
    await manager.initialize()
    
    # Should successfully connect to real test Redis
    assert manager.enabled
    assert manager.redis_client is not None
    
    # Test basic Redis operations with real connection
    await manager.set("config_test", "config_value")
    assert await manager.exists("config_test")
    assert await manager.get("config_test") == "config_value"


@pytest.mark.asyncio 
async def test_redis_connection_with_valid_staging_url(isolated_test_env, real_auth_redis):
    """Test successful connection with valid staging Redis URL"""
    # REAL ENVIRONMENT - Use isolated environment manager
    env = isolated_test_env
    env.set("ENVIRONMENT", "staging", "test_redis_staging")
    env.set("REDIS_URL", "redis://localhost:6381/3", "test_redis_staging")  # Use test Redis
    env.set("REDIS_REQUIRED", "false", "test_redis_staging")
    
    from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
    
    manager = AuthRedisManager()
    
    # REAL REDIS - Test actual staging-like connection
    await manager.initialize()
    
    # Should be enabled with valid test URL
    assert manager.enabled
    assert manager.redis_client is not None
    
    # Test actual Redis operations to verify connection
    test_key = "staging_test_key"
    test_value = "staging_test_value"
    
    await manager.set(test_key, test_value)
    retrieved_value = await manager.get(test_key)
    assert retrieved_value == test_value
    
    # Test cleanup
    await manager.delete(test_key)
    assert not await manager.exists(test_key)