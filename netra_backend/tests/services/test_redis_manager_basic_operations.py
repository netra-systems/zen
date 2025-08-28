"""
Tests for basic Redis Manager operations
Tests Redis GET, SET, DELETE operations and connection management
"""

import sys
from pathlib import Path

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.redis_manager import RedisManager

from netra_backend.tests.helpers.redis_test_fixtures import (
    mock_redis_client,
    redis_manager,
)
from netra_backend.tests.helpers.redis_test_helpers import (
    create_disabled_redis_manager,
    setup_failing_redis_client,
    setup_redis_settings_mock,
    setup_test_data,
    verify_command_in_history,
    verify_disabled_operations,
    verify_redis_delete_result,
    verify_redis_get_result,
    verify_redis_operation_basic,
    verify_redis_set_result,
    verify_redis_set_with_ttl,
)

class TestRedisManagerOperations:
    """Test basic Redis manager operations"""
    @pytest.mark.asyncio
    async def test_redis_manager_initialization(self):
        """Test Redis manager initialization"""
        manager = RedisManager()
        assert hasattr(manager, 'enabled')
        assert hasattr(manager, 'redis_client')
        assert manager.redis_client == None
    @pytest.mark.asyncio
    async def test_redis_connection_success(self, mock_redis_client):
        """Test successful Redis connection"""
        manager = RedisManager()
        manager.enabled = True
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('redis.asyncio.Redis', return_value=mock_redis_client):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.config.settings') as mock_settings:
                setup_redis_settings_mock(mock_settings)
                await manager.connect()
        
        assert manager.redis_client is mock_redis_client
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test Redis connection failure handling"""
        manager = RedisManager()
        manager.enabled = True
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('redis.asyncio.Redis') as mock_redis_class:
            from test_framework.mocks import MockRedisClient
            mock_client = MockRedisClient()
            setup_failing_redis_client(mock_client, "connection")
            mock_redis_class.return_value = mock_client
            
            # Mock: Component isolation for testing without external dependencies
            with patch('app.config.settings') as mock_settings:
                setup_redis_settings_mock(mock_settings)
                await manager.connect()
                assert manager.redis_client == None
    @pytest.mark.asyncio
    async def test_redis_get_operation(self, redis_manager, mock_redis_client):
        """Test Redis GET operation"""
        test_key = "test_key"
        test_value = "test_value"
        setup_test_data(mock_redis_client, test_key, test_value)
        
        result = await redis_manager.get(test_key)
        
        verify_redis_get_result(result, test_value)
        verify_redis_operation_basic(mock_redis_client, 1)
        verify_command_in_history(mock_redis_client, ('get', test_key))
    @pytest.mark.asyncio
    async def test_redis_get_nonexistent_key(self, redis_manager, mock_redis_client):
        """Test Redis GET operation for nonexistent key"""
        result = await redis_manager.get("nonexistent_key")
        
        verify_redis_get_result(result, None)
        verify_redis_operation_basic(mock_redis_client, 1)
    @pytest.mark.asyncio
    async def test_redis_set_operation(self, redis_manager, mock_redis_client):
        """Test Redis SET operation"""
        test_key = "set_test_key"
        test_value = "set_test_value"
        
        result = await redis_manager.set(test_key, test_value)
        
        verify_redis_set_result(result, mock_redis_client, test_key, test_value)
        verify_redis_operation_basic(mock_redis_client, 1)
        verify_command_in_history(mock_redis_client, ('set', test_key, test_value, None))
    @pytest.mark.asyncio
    async def test_redis_set_with_expiration(self, redis_manager, mock_redis_client):
        """Test Redis SET operation with expiration"""
        test_key = "expire_test_key"
        test_value = "expire_test_value"
        expiration = 300
        
        result = await redis_manager.set(test_key, test_value, ex=expiration)
        
        verify_redis_set_result(result, mock_redis_client, test_key, test_value)
        verify_redis_set_with_ttl(mock_redis_client, test_key, expiration)
    @pytest.mark.asyncio
    async def test_redis_set_backward_compatibility(self, redis_manager, mock_redis_client):
        """Test Redis SET backward compatibility with 'expire' parameter"""
        test_key = "compat_test_key"
        test_value = "compat_test_value"
        expiration = 600
        
        result = await redis_manager.set(test_key, test_value, expire=expiration)
        
        verify_redis_set_result(result, mock_redis_client, test_key, test_value)
        verify_redis_set_with_ttl(mock_redis_client, test_key, expiration)
    @pytest.mark.asyncio
    async def test_redis_delete_operation(self, redis_manager, mock_redis_client):
        """Test Redis DELETE operation"""
        test_key = "delete_test_key"
        test_value = "delete_test_value"
        setup_test_data(mock_redis_client, test_key, test_value)
        
        result = await redis_manager.delete(test_key)
        
        verify_redis_delete_result(result, mock_redis_client, test_key, 1)
        verify_command_in_history(mock_redis_client, ('delete', test_key))
    @pytest.mark.asyncio
    async def test_redis_delete_nonexistent_key(self, redis_manager, mock_redis_client):
        """Test Redis DELETE operation for nonexistent key"""
        result = await redis_manager.delete("nonexistent_delete_key")
        
        verify_redis_delete_result(result, mock_redis_client, "nonexistent_delete_key", 0)
        verify_redis_operation_basic(mock_redis_client, 1)
    @pytest.mark.asyncio
    async def test_redis_operations_when_disabled(self):
        """Test Redis operations when service is disabled"""
        manager = create_disabled_redis_manager()
        
        get_result = await manager.get("test_key")
        set_result = await manager.set("test_key", "test_value")
        delete_result = await manager.delete("test_key")
        
        verify_disabled_operations(get_result, set_result, delete_result)
    @pytest.mark.asyncio
    async def test_redis_disconnect(self, redis_manager, mock_redis_client):
        """Test Redis disconnection"""
        assert redis_manager.redis_client != None
        
        await redis_manager.disconnect()
        
        assert mock_redis_client.connection_count == 0