"""
L3 Integration Test: Redis Data Persistence
Tests Redis data persistence and caching
"""""

import sys
from pathlib import Path
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time

import pytest
import redis.asyncio as redis

from netra_backend.app.config import get_config

from netra_backend.app.services.redis_service import RedisService

class TestDataPersistenceRedisL3:
    """Test Redis data persistence scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_key_value_persistence(self):
        """Test basic key-value persistence"""
        redis_service = RedisService()

        # Set value
        await redis_service.set("test_key", "test_value")

        # Get value
        value = await redis_service.get("test_key")
        assert value == "test_value"

        # Delete key
        await redis_service.delete("test_key")

        # Verify deleted
        value = await redis_service.get("test_key")
        assert value is None

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.l3
        @pytest.mark.asyncio
        async def test_complex_data_serialization(self):
            """Test complex data type serialization"""
            redis_service = RedisService()

            complex_data = {
            "user_id": "123",
            "preferences": {
            "theme": "dark",
            "notifications": True
            },
            "tags": ["python", "redis", "testing"]
            }

        # Store complex data
            await redis_service.set_json("user:123:prefs", complex_data)

        # Retrieve and verify
            retrieved = await redis_service.get_json("user:123:prefs")
            assert retrieved == complex_data
            assert retrieved["preferences"]["theme"] == "dark"
            assert "python" in retrieved["tags"]

            @pytest.mark.asyncio
            @pytest.mark.integration
            @pytest.mark.l3
            @pytest.mark.asyncio
            async def test_ttl_expiration(self):
                """Test TTL and key expiration"""
                redis_service = RedisService()

        # Set with TTL
                await redis_service.setex("temp_key", value="temp_value", ttl=1)

        # Should exist immediately
                value = await redis_service.get("temp_key")
                assert value == "temp_value"

        # Wait for expiration
                await asyncio.sleep(1.5)

        # Should be expired
                value = await redis_service.get("temp_key")
                assert value is None

                @pytest.mark.asyncio
                @pytest.mark.integration
                @pytest.mark.l3
                @pytest.mark.asyncio
                async def test_atomic_operations(self):
                    """Test atomic operations (increment, decrement)"""
                    redis_service = RedisService()

                    counter_key = "counter:test"

        # Initialize counter
                    await redis_service.set(counter_key, "0")

        # Concurrent increments
                    tasks = [redis_service.incr(counter_key) for _ in range(10)]
                    results = await asyncio.gather(*tasks)

        # Final value should be 10
                    final_value = await redis_service.get(counter_key)
                    assert int(final_value) == 10

        # All increments should be unique
                    assert len(set(results)) == 10

                    @pytest.mark.asyncio
                    @pytest.mark.integration
                    @pytest.mark.l3
                    @pytest.mark.asyncio
                    async def test_list_operations(self):
                        """Test Redis list operations"""
                        redis_service = RedisService()

                        list_key = "queue:test"

        # Push items
                        await redis_service.lpush(list_key, "item1")
                        await redis_service.lpush(list_key, "item2")
                        await redis_service.rpush(list_key, "item3")

        # Get list length
                        length = await redis_service.llen(list_key)
                        assert length == 3

        # Pop items
                        left_item = await redis_service.lpop(list_key)
                        assert left_item == "item2"

                        right_item = await redis_service.rpop(list_key)
                        assert right_item == "item3"