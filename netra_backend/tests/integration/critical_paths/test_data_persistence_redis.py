"""
L3 Integration Test: Redis Data Persistence
Tests Redis data persistence and caching
"""

import asyncio
import json
import time

import pytest
import redis.asyncio as redis

from netra_backend.app.services.redis_service import RedisService
from shared.isolated_environment import get_env


class TestDataPersistenceRedisL3:
    """Test Redis data persistence scenarios"""

    @pytest.fixture(autouse=True)
    async def setup_redis_service(self):
        """Setup Redis service with availability check."""
        self.redis_service = RedisService()
        
        # Check if Redis is available before running tests
        try:
            await self.redis_service.connect()
            is_available = await self.redis_service.ping()
            if not is_available:
                pytest.skip("Redis service is not available - skipping Redis integration tests")
        except Exception as e:
            pytest.skip(f"Redis connection failed: {e} - skipping Redis integration tests")
        
        yield
        
        # Cleanup after tests
        try:
            await self.redis_service.disconnect()
        except Exception:
            pass  # Ignore cleanup errors

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_key_value_persistence(self):
        """Test basic key-value persistence"""
        # Set value
        result = await self.redis_service.set("test_key", "test_value")
        assert result is True, "Failed to set value in Redis"

        # Get value
        value = await self.redis_service.get("test_key")
        assert value == "test_value", f"Expected 'test_value', got {value}"

        # Delete key
        deleted_count = await self.redis_service.delete("test_key")
        assert deleted_count > 0, "Failed to delete key from Redis"

        # Verify deleted
        value = await self.redis_service.get("test_key")
        assert value is None, f"Expected None after deletion, got {value}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_complex_data_serialization(self):
        """Test complex data type serialization"""
        complex_data = {
            "user_id": "123",
            "preferences": {
                "theme": "dark",
                "notifications": True
            },
            "tags": ["python", "redis", "testing"]
        }

        # Store complex data
        result = await self.redis_service.set_json("user:123:prefs", complex_data)
        assert result is True, "Failed to store JSON data in Redis"

        # Retrieve and verify
        retrieved = await self.redis_service.get_json("user:123:prefs")
        assert retrieved is not None, "Failed to retrieve JSON data from Redis"
        assert retrieved == complex_data, f"JSON data mismatch: {retrieved} != {complex_data}"
        assert retrieved["preferences"]["theme"] == "dark"
        assert "python" in retrieved["tags"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_ttl_expiration(self):
        """Test TTL and key expiration"""
        # Set with TTL
        result = await self.redis_service.setex("temp_key", value="temp_value", ttl=1)
        assert result is True, "Failed to set key with TTL"

        # Should exist immediately
        value = await self.redis_service.get("temp_key")
        assert value == "temp_value", f"Key should exist immediately, got {value}"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        value = await self.redis_service.get("temp_key")
        assert value is None, f"Key should be expired, got {value}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_atomic_operations(self):
        """Test atomic operations (increment, decrement)"""
        counter_key = "counter:test"

        # Initialize counter
        result = await self.redis_service.set(counter_key, "0")
        assert result is True, "Failed to initialize counter"

        # Concurrent increments
        tasks = [self.redis_service.incr(counter_key) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Final value should be 10
        final_value = await self.redis_service.get(counter_key)
        assert final_value is not None, "Counter value should not be None"
        assert int(final_value) == 10, f"Expected counter to be 10, got {final_value}"

        # All increments should be unique (1, 2, 3, ..., 10)
        expected_results = list(range(1, 11))
        assert sorted(results) == expected_results, f"Increment results should be unique: {sorted(results)} != {expected_results}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_list_operations(self):
        """Test Redis list operations"""
        list_key = "queue:test"

        # Push items
        await self.redis_service.lpush(list_key, "item1")
        await self.redis_service.lpush(list_key, "item2")
        await self.redis_service.rpush(list_key, "item3")

        # Get list length
        length = await self.redis_service.llen(list_key)
        assert length == 3, f"Expected list length 3, got {length}"

        # Pop items (lpush puts item2 at the front, so lpop should return item2)
        left_item = await self.redis_service.lpop(list_key)
        assert left_item == "item2", f"Expected 'item2', got {left_item}"

        # rpush puts item3 at the end, so rpop should return item3
        right_item = await self.redis_service.rpop(list_key)
        assert right_item == "item3", f"Expected 'item3', got {right_item}"

        # Clean up
        await self.redis_service.delete(list_key)