"""Test Redis connection management and caching operations."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.redis_manager import (
    RedisManager,
    get_redis_client,
    redis_connection_pool
)


@pytest.fixture
async def redis_manager():
    """Create a test Redis manager instance."""
    manager = RedisManager(host="localhost", port=6379, db=1)
    yield manager
    await manager.close()


@pytest.mark.asyncio
class TestRedisConnectionManagement:
    """Test Redis connection pool and connection management."""

    async def test_connection_pool_initialization(self, redis_manager):
        """Test Redis connection pool is properly initialized."""
        assert redis_manager.pool is not None
        assert redis_manager.pool.max_connections > 0
        assert redis_manager.pool.connection_kwargs['db'] == 1

    async def test_connection_acquisition(self, redis_manager):
        """Test acquiring connections from pool."""
        connections = []
        
        try:
            # Acquire multiple connections
            for _ in range(5):
                conn = await redis_manager.get_connection()
                connections.append(conn)
                assert conn is not None
                assert await conn.ping()
            
            # Verify connections are from pool
            assert len(connections) <= redis_manager.pool.max_connections
        finally:
            # Release connections
            for conn in connections:
                await conn.close()

    async def test_connection_pool_exhaustion(self, redis_manager):
        """Test behavior when connection pool is exhausted."""
        max_conn = redis_manager.pool.max_connections
        connections = []
        
        try:
            # Exhaust the pool
            for _ in range(max_conn):
                conn = await redis_manager.get_connection()
                connections.append(conn)
            
            # Next connection should wait or raise timeout
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(
                    redis_manager.get_connection(),
                    timeout=0.1
                )
        finally:
            for conn in connections:
                await conn.close()

    async def test_connection_retry_on_failure(self, redis_manager):
        """Test connection retry logic on failure."""
        with patch.object(redis_manager.pool, 'get_connection', 
                         side_effect=[ConnectionError("Failed"), AsyncMock()]):
            # Should retry and succeed
            conn = await redis_manager.get_connection_with_retry(max_retries=2)
            assert conn is not None

    async def test_connection_health_check(self, redis_manager):
        """Test connection health checking."""
        conn = await redis_manager.get_connection()
        
        # Healthy connection
        assert await redis_manager.check_connection_health(conn)
        
        # Simulate unhealthy connection
        with patch.object(conn, 'ping', side_effect=ConnectionError()):
            assert not await redis_manager.check_connection_health(conn)
        
        await conn.close()

    async def test_concurrent_connection_usage(self, redis_manager):
        """Test concurrent connection usage from pool."""
        async def use_connection(manager, task_id):
            conn = await manager.get_connection()
            try:
                await conn.set(f"test_key_{task_id}", f"value_{task_id}")
                result = await conn.get(f"test_key_{task_id}")
                return result.decode() if result else None
            finally:
                await conn.close()
        
        # Execute concurrent operations
        tasks = [use_connection(redis_manager, i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        assert results == [f"value_{i}" for i in range(20)]


@pytest.mark.asyncio
class TestRedisCacheOperations:
    """Test Redis caching operations."""

    async def test_set_and_get_string(self, redis_manager):
        """Test basic set and get operations."""
        await redis_manager.set("test_key", "test_value")
        value = await redis_manager.get("test_key")
        assert value == "test_value"

    async def test_set_with_expiration(self, redis_manager):
        """Test setting values with TTL."""
        await redis_manager.set("expire_key", "value", ttl=1)
        
        # Value should exist initially
        assert await redis_manager.get("expire_key") == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Value should be expired
        assert await redis_manager.get("expire_key") is None

    async def test_json_serialization(self, redis_manager):
        """Test JSON object caching."""
        test_obj = {
            "id": 1,
            "name": "test",
            "data": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        await redis_manager.set_json("json_key", test_obj)
        retrieved = await redis_manager.get_json("json_key")
        
        assert retrieved == test_obj

    async def test_hash_operations(self, redis_manager):
        """Test Redis hash operations."""
        # Set hash fields
        await redis_manager.hset("user:1", "name", "John")
        await redis_manager.hset("user:1", "email", "john@example.com")
        
        # Get single field
        name = await redis_manager.hget("user:1", "name")
        assert name == "John"
        
        # Get all fields
        user_data = await redis_manager.hgetall("user:1")
        assert user_data == {"name": "John", "email": "john@example.com"}

    async def test_list_operations(self, redis_manager):
        """Test Redis list operations."""
        # Push items to list
        await redis_manager.lpush("queue", "item1")
        await redis_manager.lpush("queue", "item2")
        await redis_manager.rpush("queue", "item3")
        
        # Get list length
        length = await redis_manager.llen("queue")
        assert length == 3
        
        # Pop items
        item = await redis_manager.lpop("queue")
        assert item == "item2"
        
        # Get range
        items = await redis_manager.lrange("queue", 0, -1)
        assert items == ["item1", "item3"]

    async def test_set_operations(self, redis_manager):
        """Test Redis set operations."""
        # Add to set
        await redis_manager.sadd("tags", "python", "redis", "async")
        
        # Check membership
        is_member = await redis_manager.sismember("tags", "python")
        assert is_member
        
        # Get all members
        members = await redis_manager.smembers("tags")
        assert members == {"python", "redis", "async"}
        
        # Remove member
        await redis_manager.srem("tags", "async")
        members = await redis_manager.smembers("tags")
        assert members == {"python", "redis"}

    async def test_atomic_operations(self, redis_manager):
        """Test atomic Redis operations."""
        # Increment
        await redis_manager.set("counter", "0")
        new_val = await redis_manager.incr("counter")
        assert new_val == 1
        
        # Increment by value
        new_val = await redis_manager.incrby("counter", 5)
        assert new_val == 6
        
        # Decrement
        new_val = await redis_manager.decr("counter")
        assert new_val == 5

    async def test_pipeline_operations(self, redis_manager):
        """Test Redis pipeline for batch operations."""
        async with redis_manager.pipeline() as pipe:
            for i in range(100):
                pipe.set(f"key_{i}", f"value_{i}")
            
            # Execute all commands at once
            results = await pipe.execute()
            assert len(results) == 100
            assert all(r for r in results)
        
        # Verify values were set
        for i in range(100):
            value = await redis_manager.get(f"key_{i}")
            assert value == f"value_{i}"

    async def test_transaction_operations(self, redis_manager):
        """Test Redis transactions."""
        async def transfer_balance(manager, from_key, to_key, amount):
            async with manager.pipeline(transaction=True) as pipe:
                # Watch keys for changes
                await pipe.watch(from_key, to_key)
                
                # Get current balances
                from_balance = int(await manager.get(from_key) or 0)
                to_balance = int(await manager.get(to_key) or 0)
                
                if from_balance >= amount:
                    # Start transaction
                    pipe.multi()
                    pipe.decrby(from_key, amount)
                    pipe.incrby(to_key, amount)
                    
                    # Execute transaction
                    results = await pipe.execute()
                    return results is not None
                return False
        
        # Setup initial balances
        await redis_manager.set("account1", "100")
        await redis_manager.set("account2", "50")
        
        # Perform transfer
        success = await transfer_balance(redis_manager, "account1", "account2", 30)
        assert success
        
        # Verify balances
        assert await redis_manager.get("account1") == "70"
        assert await redis_manager.get("account2") == "80"


@pytest.mark.asyncio
class TestRedisPatterns:
    """Test common Redis usage patterns."""

    async def test_cache_aside_pattern(self, redis_manager):
        """Test cache-aside (lazy loading) pattern."""
        async def get_user(user_id: int):
            # Check cache first
            cached = await redis_manager.get_json(f"user:{user_id}")
            if cached:
                return cached
            
            # Simulate database fetch
            user = {"id": user_id, "name": f"User {user_id}"}
            
            # Store in cache
            await redis_manager.set_json(f"user:{user_id}", user, ttl=60)
            return user
        
        # First call should fetch and cache
        user1 = await get_user(1)
        assert user1["name"] == "User 1"
        
        # Second call should use cache
        with patch.object(redis_manager, 'set_json') as mock_set:
            user1_cached = await get_user(1)
            assert user1_cached == user1
            mock_set.assert_not_called()

    async def test_write_through_pattern(self, redis_manager):
        """Test write-through caching pattern."""
        async def update_user(user_id: int, data: dict):
            # Update cache and database simultaneously
            await redis_manager.set_json(f"user:{user_id}", data)
            # Simulate database update
            return True
        
        user_data = {"id": 1, "name": "Updated User"}
        success = await update_user(1, user_data)
        assert success
        
        # Verify cache has updated data
        cached = await redis_manager.get_json("user:1")
        assert cached == user_data

    async def test_distributed_locking(self, redis_manager):
        """Test distributed locking with Redis."""
        lock_key = "resource_lock"
        lock_acquired = []
        
        async def acquire_lock_and_work(worker_id: int):
            # Try to acquire lock
            lock = await redis_manager.set_nx(lock_key, worker_id, ttl=5)
            if lock:
                lock_acquired.append(worker_id)
                await asyncio.sleep(0.1)  # Simulate work
                await redis_manager.delete(lock_key)
                return True
            return False
        
        # Multiple workers try to acquire lock
        tasks = [acquire_lock_and_work(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Only one should acquire the lock
        assert sum(results) == 1
        assert len(lock_acquired) == 1

    async def test_rate_limiting(self, redis_manager):
        """Test rate limiting pattern with Redis."""
        async def check_rate_limit(user_id: str, limit: int, window: int):
            key = f"rate_limit:{user_id}"
            current = await redis_manager.get(key)
            
            if current is None:
                await redis_manager.set(key, 1, ttl=window)
                return True
            elif int(current) < limit:
                await redis_manager.incr(key)
                return True
            return False
        
        # Test rate limiting
        user_id = "user123"
        
        # First 5 requests should pass
        for _ in range(5):
            assert await check_rate_limit(user_id, 5, 60)
        
        # 6th request should be rate limited
        assert not await check_rate_limit(user_id, 5, 60)

    async def test_pub_sub_messaging(self, redis_manager):
        """Test pub/sub messaging pattern."""
        received_messages = []
        
        async def message_handler(channel, message):
            received_messages.append((channel, message))
        
        # Subscribe to channel
        pubsub = redis_manager.pubsub()
        await pubsub.subscribe("test_channel")
        
        # Start listening
        async def listen():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await message_handler(
                        message['channel'].decode(),
                        message['data'].decode()
                    )
        
        # Start listener task
        listener_task = asyncio.create_task(listen())
        
        # Publish messages
        await redis_manager.publish("test_channel", "message1")
        await redis_manager.publish("test_channel", "message2")
        
        # Wait for messages to be received
        await asyncio.sleep(0.1)
        
        # Cleanup
        listener_task.cancel()
        await pubsub.unsubscribe("test_channel")
        await pubsub.close()
        
        assert len(received_messages) == 2
        assert received_messages[0] == ("test_channel", "message1")
        assert received_messages[1] == ("test_channel", "message2")