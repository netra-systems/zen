"""
Test Redis Staging Fixes for Auth Service
Verifies that Redis localhost fallback is prevented in staging/production
"""
import pytest
import os
from unittest.mock import patch, MagicMock
import asyncio


@pytest.mark.asyncio
async def test_redis_no_localhost_fallback_in_staging():
    """Test that localhost fallback is prevented in staging environment"""
    # Mock environment for staging
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        # No REDIS_URL set
        "REDIS_REQUIRED": "false",
        "REDIS_FALLBACK_ENABLED": "false"
    }, clear=True):
        # Import after setting env vars
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        await manager.initialize()
        
        # Should be disabled without Redis URL in staging
        assert not manager.enabled
        assert manager.redis_client is None


@pytest.mark.asyncio
async def test_redis_localhost_rejected_in_staging():
    """Test that localhost Redis URL is rejected in staging unless explicitly allowed"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "REDIS_URL": "redis://localhost:6379",
        "REDIS_REQUIRED": "true",
        "REDIS_FALLBACK_ENABLED": "false"
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        
        # Should raise error about localhost not allowed
        with pytest.raises(ValueError) as exc_info:
            await manager.initialize()
        
        assert "Localhost Redis URL not allowed in staging" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_required_in_staging():
    """Test that Redis can be marked as required in staging"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        # No REDIS_URL
        "REDIS_REQUIRED": "true",
        "REDIS_FALLBACK_ENABLED": "false"
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        
        # Should raise error when required but not configured
        with pytest.raises(ValueError) as exc_info:
            await manager.initialize()
        
        assert "REDIS_URL must be configured in staging" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_graceful_degradation_when_not_required():
    """Test graceful degradation when Redis not required in staging"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        # No REDIS_URL
        "REDIS_REQUIRED": "false"
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
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
async def test_redis_localhost_allowed_in_development():
    """Test that localhost fallback IS allowed in development"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        # No REDIS_URL - should fallback to localhost
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        
        # Mock redis client to avoid actual connection
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = MagicMock()
            async def mock_ping():
                return True
            mock_client.ping = mock_ping
            mock_from_url.return_value = mock_client
            
            await manager.initialize()
            
            # Should use localhost fallback in development
            mock_from_url.assert_called_once()
            call_args = mock_from_url.call_args[0][0]
            assert "localhost" in call_args


@pytest.mark.asyncio
async def test_redis_timeout_handling():
    """Test that Redis connection timeout is handled properly"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "REDIS_URL": "redis://staging-redis:6379",
        "REDIS_REQUIRED": "false"
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        
        # Mock redis client with timeout
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = MagicMock()
            # Simulate timeout
            async def timeout_ping():
                await asyncio.sleep(20)  # Longer than 10 second timeout
            mock_client.ping = timeout_ping
            mock_from_url.return_value = mock_client
            
            # Should handle timeout gracefully when not required
            await manager.initialize()
            
            # Should be disabled after timeout
            assert not manager.enabled
            assert manager.redis_client is None


@pytest.mark.asyncio 
async def test_redis_connection_with_valid_staging_url():
    """Test successful connection with valid staging Redis URL"""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "REDIS_URL": "redis://staging-redis.example.com:6379",
        "REDIS_REQUIRED": "false"
    }, clear=True):
        from auth_service.auth_core.redis_manager import AuthRedisManager
        
        manager = AuthRedisManager()
        
        # Mock successful connection
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = MagicMock()
            async def mock_ping():
                return True
            mock_client.ping = mock_ping
            mock_from_url.return_value = mock_client
            
            await manager.initialize()
            
            # Should be enabled with valid URL
            assert manager.enabled
            assert manager.redis_client is not None
            
            # Verify correct URL was used
            mock_from_url.assert_called_once()
            call_args = mock_from_url.call_args[0][0]
            assert "staging-redis.example.com" in call_args