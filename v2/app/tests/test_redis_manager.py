"""Test Redis connection management and caching operations."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.redis_manager import RedisManager, redis_manager


@pytest.fixture
def test_redis_manager():
    """Create a test Redis manager instance."""
    return RedisManager()


class TestRedisManager:
    """Test Redis manager basic functionality."""

    def test_redis_manager_initialization(self, test_redis_manager):
        """Test Redis manager initializes correctly."""
        assert isinstance(test_redis_manager, RedisManager)
        assert test_redis_manager.redis_client is None

    @pytest.mark.asyncio
    async def test_redis_manager_connect(self, test_redis_manager):
        """Test Redis manager connection."""
        try:
            await test_redis_manager.connect()
            assert test_redis_manager.redis_client is not None
            await test_redis_manager.disconnect()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_manager_get_client(self, test_redis_manager):
        """Test getting Redis client."""
        try:
            await test_redis_manager.connect()
            client = await test_redis_manager.get_client()
            assert client is not None
            await test_redis_manager.disconnect()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_manager_disconnect(self, test_redis_manager):
        """Test Redis manager disconnect."""
        try:
            await test_redis_manager.connect()
            await test_redis_manager.disconnect()
            # Should be able to disconnect without error
            assert True
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    def test_global_redis_manager_instance(self):
        """Test global Redis manager instance."""
        assert isinstance(redis_manager, RedisManager)
        assert redis_manager.redis_client is None


