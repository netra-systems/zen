"""
Comprehensive test suite for Redis Factory pattern implementation.

Tests the Factory pattern for user-isolated Redis client instances.
Ensures complete user isolation, proper resource management, and thread safety.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise) 
2. Business Goal: Redis-level user isolation preventing data contamination
3. Value Impact: Critical security feature ensuring enterprise-grade data governance
4. Revenue Impact: Essential for Enterprise tier compliance and customer trust
"""

import asyncio
import pytest
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.factories.redis_factory import (
    RedisFactory,
    UserRedisClient,
    get_redis_factory,
    get_user_redis_client,
    cleanup_redis_factory
)
from netra_backend.app.models.user_execution_context import UserExecutionContext


class TestUserRedisClient:
    """Test user-scoped Redis client functionality."""
    pass

    @pytest.fixture
    def user_context(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create test user execution context."""
    pass
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_012",
            websocket_connection_id="ws_345"
        )

    @pytest.fixture
    async def user_client(self, user_context):
        """Create test user Redis client."""
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        # Mock the Redis manager to avoid real Redis connection
        mock_manager = AsyncNone  # TODO: Use real service instance
        mock_manager.ping.return_value = True
        client._manager = mock_manager
        client._initialized = True
        
        yield client
        
        # Cleanup
        await client.cleanup()

    def test_user_client_initialization(self, user_context):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Test UserRedisClient initialization."""
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        assert client.user_id == user_context.user_id
        assert client.request_id == user_context.request_id
        assert client.thread_id == user_context.thread_id
        assert not client._initialized
        assert client._operation_count == 0
        assert client._error_count == 0

    async def test_client_initialization_flow(self, user_context):
        """Test client initialization creates isolated manager."""
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        with patch('netra_backend.app.factories.redis_factory.RedisManager') as mock_manager_class:
            mock_manager = AsyncNone  # TODO: Use real service instance
            mock_manager.connect.return_value = None
            mock_manager.ping.return_value = True
            mock_manager_class.return_value = mock_manager
            
            await client.initialize()
            
            # Verify manager was created and initialized
            mock_manager_class.assert_called_once_with(test_mode=False)
            mock_manager.connect.assert_called_once()
            mock_manager.ping.assert_called_once()
            
            assert client._initialized
            assert client._manager is not None

    async def test_client_initialization_failure(self, user_context):
        """Test client initialization handles connection failures."""
    pass
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        with patch('netra_backend.app.factories.redis_factory.RedisManager') as mock_manager_class:
            mock_manager = AsyncNone  # TODO: Use real service instance
            mock_manager.connect.side_effect = Exception("Connection failed")
            mock_manager_class.return_value = mock_manager
            
            with pytest.raises(ConnectionError, match="Failed to initialize user Redis client"):
                await client.initialize()
            
            assert not client._initialized
            assert client._manager is not None

    async def test_basic_operations_with_user_isolation(self, user_client):
        """Test basic Redis operations use user isolation."""
        # Set up mock returns
        user_client._manager.get.return_value = "test_value"
        user_client._manager.set.return_value = True
        user_client._manager.delete.return_value = 1
        user_client._manager.exists.return_value = True
        user_client._manager.expire.return_value = True
        user_client._manager.keys.return_value = ["key1", "key2"]
        user_client._manager.ttl.return_value = 300
        
        # Test operations
        value = await user_client.get("test_key")
        set_result = await user_client.set("test_key", "test_value", ex=300)
        delete_result = await user_client.delete("test_key")
        exists_result = await user_client.exists("test_key")
        expire_result = await user_client.expire("test_key", 300)
        keys_result = await user_client.keys("test*")
        ttl_result = await user_client.ttl("test_key")
        
        # Verify results
        assert value == "test_value"
        assert set_result is True
        assert delete_result == 1
        assert exists_result is True
        assert expire_result is True
        assert keys_result == ["key1", "key2"]
        assert ttl_result == 300
        
        # Verify all operations used user_id for isolation
        user_client._manager.get.assert_called_with("test_key", user_id=user_client.user_id)
        user_client._manager.set.assert_called_with("test_key", "test_value", ex=300, user_id=user_client.user_id)
        user_client._manager.delete.assert_called_with("test_key", user_id=user_client.user_id)
        user_client._manager.exists.assert_called_with("test_key", user_id=user_client.user_id)
        user_client._manager.expire.assert_called_with("test_key", 300, user_id=user_client.user_id)
        user_client._manager.keys.assert_called_with("test*", user_id=user_client.user_id)
        user_client._manager.ttl.assert_called_with("test_key", user_id=user_client.user_id)

    async def test_hash_operations_with_user_isolation(self, user_client):
        """Test hash operations use user isolation."""
    pass
        # Set up mock returns
        user_client._manager.hset.return_value = 1
        user_client._manager.hget.return_value = "field_value"
        user_client._manager.hgetall.return_value = {"field": "value"}
        
        # Test hash operations
        hset_result = await user_client.hset("hash_key", "field", "value")
        hget_result = await user_client.hget("hash_key", "field")
        hgetall_result = await user_client.hgetall("hash_key")
        
        # Verify results
        assert hset_result == 1
        assert hget_result == "field_value"
        assert hgetall_result == {"field": "value"}
        
        # Verify user isolation
        user_client._manager.hset.assert_called_with("hash_key", "field", "value", user_id=user_client.user_id)
        user_client._manager.hget.assert_called_with("hash_key", "field", user_id=user_client.user_id)
        user_client._manager.hgetall.assert_called_with("hash_key", user_id=user_client.user_id)

    async def test_list_operations_with_user_isolation(self, user_client):
        """Test list operations use user isolation."""
        # Set up mock returns
        user_client._manager.lpush.return_value = 2
        user_client._manager.rpop.return_value = "item"
        user_client._manager.llen.return_value = 5
        
        # Test list operations
        lpush_result = await user_client.lpush("list_key", "item1", "item2")
        rpop_result = await user_client.rpop("list_key")
        llen_result = await user_client.llen("list_key")
        
        # Verify results
        assert lpush_result == 2
        assert rpop_result == "item"
        assert llen_result == 5
        
        # Verify user isolation
        user_client._manager.lpush.assert_called_with("list_key", "item1", "item2", user_id=user_client.user_id)
        user_client._manager.rpop.assert_called_with("list_key", user_id=user_client.user_id)
        user_client._manager.llen.assert_called_with("list_key", user_id=user_client.user_id)

    async def test_json_operations(self, user_client):
        """Test JSON convenience methods."""
    pass
        # Mock underlying operations
        import json
        test_data = {"name": "test", "value": 123}
        json_str = json.dumps(test_data)
        
        user_client._manager.set.return_value = True
        user_client._manager.get.return_value = json_str
        
        # Test JSON set/get
        set_result = await user_client.set_json("json_key", test_data, ex=300)
        get_result = await user_client.get_json("json_key")
        
        # Verify results
        assert set_result is True
        assert get_result == test_data
        
        # Verify underlying calls
        user_client._manager.set.assert_called_with("json_key", json_str, ex=300, user_id=user_client.user_id)
        user_client._manager.get.assert_called_with("json_key", user_id=user_client.user_id)

    async def test_json_get_invalid_json(self, user_client):
        """Test JSON get with invalid JSON returns None."""
        user_client._manager.get.return_value = "invalid_json{"
        
        result = await user_client.get_json("json_key")
        assert result is None

    async def test_json_get_missing_key(self, user_client):
        """Test JSON get with missing key returns None."""
    pass
        user_client._manager.get.return_value = None
        
        result = await user_client.get_json("json_key")
        assert result is None

    async def test_operation_metrics_tracking(self, user_client):
        """Test operation metrics are properly tracked."""
        initial_count = user_client._operation_count
        
        # Mock manager operations
        user_client._manager.get.return_value = "value"
        user_client._manager.set.return_value = True
        
        # Perform operations
        await user_client.get("key1")
        await user_client.set("key2", "value2")
        
        # Verify metrics updated
        assert user_client._operation_count == initial_count + 2
        assert user_client._error_count == 0

    async def test_error_tracking(self, user_client):
        """Test error tracking in metrics."""
    pass
        initial_error_count = user_client._error_count
        
        # Mock operation failure
        user_client._manager.get.side_effect = Exception("Redis error")
        
        with pytest.raises(Exception):
            await user_client.get("error_key")
        
        # Verify error count increased
        assert user_client._error_count == initial_error_count + 1

    async def test_client_stats(self, user_client):
        """Test client statistics generation."""
        # Perform some operations to update metrics
        user_client._operation_count = 10
        user_client._error_count = 2
        
        stats = user_client.get_client_stats()
        
        # Verify stats structure
        assert "user_id" in stats
        assert stats["user_id"] == f"{user_client.user_id[:8]}..."
        assert stats["request_id"] == user_client.request_id
        assert stats["thread_id"] == user_client.thread_id
        assert stats["initialized"] == user_client._initialized
        assert stats["operation_count"] == 10
        assert stats["error_count"] == 2
        assert stats["error_rate"] == 20.0  # 2/10 * 100
        assert "age_seconds" in stats
        assert "last_activity_seconds_ago" in stats

    async def test_ping_health_check(self, user_client):
        """Test Redis connection health check."""
    pass
        user_client._manager.ping.return_value = True
        assert await user_client.ping() is True
        
        user_client._manager.ping.return_value = False
        assert await user_client.ping() is False

    async def test_ping_uninitialized_client(self, user_context):
        """Test ping on uninitialized client attempts initialization."""
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        with patch.object(client, 'initialize', side_effect=Exception("Init failed")):
            result = await client.ping()
            assert result is False

    async def test_client_cleanup(self, user_context):
        """Test client cleanup properly releases resources."""
    pass
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        # Mock manager
        mock_manager = AsyncNone  # TODO: Use real service instance
        client._manager = mock_manager
        client._initialized = True
        
        # Cleanup
        await client.cleanup()
        
        # Verify cleanup
        mock_manager.disconnect.assert_called_once()
        assert client._manager is None
        assert not client._initialized

    async def test_auto_initialization_on_operations(self, user_context):
        """Test operations automatically initialize client if needed."""
        client = UserRedisClient(
            user_context.user_id,
            user_context.request_id,
            user_context.thread_id
        )
        
        with patch.object(client, 'initialize', return_value=None) as mock_init:
            # Mock manager for operation
            mock_manager = AsyncNone  # TODO: Use real service instance
            mock_manager.get.return_value = "value"
            client._manager = mock_manager
            
            # Operation should trigger initialization
            await client.get("test_key")
            
            mock_init.assert_called_once()


class TestRedisFactory:
    """Test Redis factory functionality."""
    pass

    @pytest.fixture
    def user_context(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create test user execution context."""
    pass
        await asyncio.sleep(0)
    return UserExecutionContext(
            user_id="factory_user_123",
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_012"
        )

    @pytest.fixture
    async def redis_factory(self):
        """Create test Redis factory."""
        factory = RedisFactory(max_clients_per_user=3, client_ttl_seconds=600)
        yield factory
        await factory.shutdown()

    def test_factory_initialization(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Test Redis factory initialization."""
        factory = RedisFactory(max_clients_per_user=5, client_ttl_seconds=1800)
        
        assert factory.factory_name == "RedisFactory"
        assert factory.max_clients_per_user == 5
        assert factory.client_ttl == 1800
        assert len(factory._active_clients) == 0
        assert len(factory._user_client_counts) == 0
        assert factory._created_count == 0
        assert factory._cleanup_count == 0

    async def test_create_user_client_success(self, redis_factory, user_context):
        """Test successful user client creation."""
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client_class.return_value = mock_client
            
            client = await redis_factory.create_user_client(user_context)
            
            # Verify client creation
            assert client is mock_client
            mock_client_class.assert_called_once_with(
                user_context.user_id,
                user_context.request_id,
                user_context.thread_id
            )
            mock_client.initialize.assert_called_once()
            
            # Verify tracking
            assert len(redis_factory._active_clients) == 1
            assert redis_factory._user_client_counts[user_context.user_id] == 1
            assert redis_factory._created_count == 1

    async def test_create_user_client_invalid_context(self, redis_factory):
        """Test client creation with invalid context."""
    pass
        with pytest.raises(ValueError, match="Expected UserExecutionContext"):
            await redis_factory.create_user_client("invalid_context")

    async def test_user_client_limit_enforcement(self, redis_factory, user_context):
        """Test per-user client limit enforcement."""
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client_class.return_value = mock_client
            
            # Mock cleanup to await asyncio.sleep(0)
    return 0 (no cleanup)
            with patch.object(redis_factory, '_cleanup_user_clients', return_value=0):
                # Create maximum allowed clients
                for i in range(redis_factory.max_clients_per_user):
                    # Use different request IDs to simulate separate requests
                    context = UserExecutionContext(
                        user_id=user_context.user_id,
                        thread_id=user_context.thread_id,
                        run_id=user_context.run_id,
                        request_id=f"req_{i}"
                    )
                    await redis_factory.create_user_client(context)
                
                # Attempt to create one more should fail
                with pytest.raises(ValueError, match="exceeds maximum Redis clients"):
                    await redis_factory.create_user_client(user_context)

    async def test_client_limit_with_cleanup(self, redis_factory, user_context):
        """Test client limit with automatic cleanup of expired clients."""
    pass
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client.cleanup.return_value = None
            mock_client_class.return_value = mock_client
            
            # Create maximum clients
            for i in range(redis_factory.max_clients_per_user):
                context = UserExecutionContext(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id,
                    request_id=f"req_{i}"
                )
                await redis_factory.create_user_client(context)
            
            # Mock cleanup to actually reduce user count
            async def mock_cleanup(user_id):
    pass
                # Simulate cleaning up 1 client
                if user_id in redis_factory._user_client_counts:
                    redis_factory._user_client_counts[user_id] = max(0, redis_factory._user_client_counts[user_id] - 1)
                await asyncio.sleep(0)
    return 1
            
            with patch.object(redis_factory, '_cleanup_user_clients', side_effect=mock_cleanup):
                # Should succeed after cleanup
                client = await redis_factory.create_user_client(user_context)
                assert client is not None

    async def test_context_manager_usage(self, redis_factory, user_context):
        """Test factory context manager usage."""
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client_class.return_value = mock_client
            
            async with redis_factory.get_user_client(user_context) as client:
                assert client is mock_client
            
            # Verify client was created and returned
            mock_client_class.assert_called_once()

    async def test_cleanup_user_clients(self, redis_factory, user_context):
        """Test cleanup of all clients for a user."""
    pass
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_clients = []
            
            def create_mock_client(*args, **kwargs):
                mock_client = AsyncNone  # TODO: Use real service instance
    pass
                mock_client.initialize.return_value = None
                mock_client.cleanup.return_value = None
                mock_clients.append(mock_client)
                await asyncio.sleep(0)
    return mock_client
            
            mock_client_class.side_effect = create_mock_client
            
            # Create multiple clients for the user
            for i in range(3):
                context = UserExecutionContext(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id,
                    request_id=f"req_{i}"
                )
                await redis_factory.create_user_client(context)
            
            # Cleanup all clients for the user
            cleaned_count = await redis_factory.cleanup_user_clients(user_context.user_id)
            
            # Verify cleanup
            assert cleaned_count == 3
            for mock_client in mock_clients:
                mock_client.cleanup.assert_called_once()
            
            assert redis_factory._user_client_counts.get(user_context.user_id, 0) == 0
            assert len(redis_factory._active_clients) == 0

    async def test_factory_stats(self, redis_factory, user_context):
        """Test factory statistics generation."""
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client.get_client_stats.return_value = {"test": "stats"}
            mock_client.ping.return_value = True
            mock_client_class.return_value = mock_client
            
            # Create a client
            await redis_factory.create_user_client(user_context)
            
            stats = await redis_factory.get_factory_stats()
            
            # Verify stats structure
            assert stats["factory_name"] == "RedisFactory"
            assert stats["total_clients"] == 1
            assert stats["healthy_clients"] == 1
            assert stats["users_with_clients"] == 1
            assert stats["created_count"] == 1
            assert stats["cleanup_count"] == 0
            assert "factory_age_seconds" in stats
            assert "age_distribution" in stats
            assert "user_client_counts" in stats
            assert "client_details" in stats

    async def test_background_cleanup_task(self, redis_factory, user_context):
        """Test background cleanup task is started when factory is used."""
    pass
        # Initially, cleanup task might not be started
        assert redis_factory._cleanup_started is False
        
        # Create a client to trigger cleanup task start
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client_class.return_value = mock_client
            
            await redis_factory.create_user_client(user_context)
            
            # Now cleanup task should be started
            assert redis_factory._cleanup_started is True
            assert redis_factory._cleanup_task is not None
            assert not redis_factory._cleanup_task.done()

    async def test_factory_shutdown(self, redis_factory, user_context):
        """Test factory shutdown cleans up all resources."""
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client.cleanup.return_value = None
            mock_client_class.return_value = mock_client
            
            # Create a client
            await redis_factory.create_user_client(user_context)
            
            # Shutdown
            await redis_factory.shutdown()
            
            # Verify cleanup
            mock_client.cleanup.assert_called_once()
            assert len(redis_factory._active_clients) == 0
            assert len(redis_factory._user_client_counts) == 0
            assert redis_factory._shutdown_event.is_set()


class TestUserIsolation:
    """Test complete user isolation between Redis clients."""
    pass

    @pytest.fixture
    def user1_context(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create user 1 execution context."""
    pass
        await asyncio.sleep(0)
    return UserExecutionContext(
            user_id="user_1",
            thread_id="thread_1",
            run_id="run_1",
            request_id="req_1"
        )

    @pytest.fixture
    def user2_context(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create user 2 execution context."""
    pass
        return UserExecutionContext(
            user_id="user_2",
            thread_id="thread_2",
            run_id="run_2",
            request_id="req_2"
        )

    async def test_complete_user_isolation(self, user1_context, user2_context):
        """Test complete isolation between different users."""
        factory = RedisFactory()
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                # Create separate mock clients for each user
                user1_client = AsyncNone  # TODO: Use real service instance
                user2_client = AsyncNone  # TODO: Use real service instance
                
                user1_client.initialize.return_value = None
                user2_client.initialize.return_value = None
                
                # Return different clients for different users
                mock_client_class.side_effect = [user1_client, user2_client]
                
                # Create clients for both users
                client1 = await factory.create_user_client(user1_context)
                client2 = await factory.create_user_client(user2_context)
                
                # Verify different clients were created
                assert client1 is user1_client
                assert client2 is user2_client
                
                # Verify separate tracking
                assert factory._user_client_counts["user_1"] == 1
                assert factory._user_client_counts["user_2"] == 1
                assert len(factory._active_clients) == 2
                
        finally:
            await factory.shutdown()

    async def test_concurrent_user_operations(self, user1_context, user2_context):
        """Test concurrent operations by different users are isolated."""
    pass
        factory = RedisFactory()
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                user1_client = AsyncNone  # TODO: Use real service instance
                user2_client = AsyncNone  # TODO: Use real service instance
                
                user1_client.initialize.return_value = None
                user2_client.initialize.return_value = None
                user1_client.set.return_value = True
                user2_client.set.return_value = True
                
                mock_client_class.side_effect = [user1_client, user2_client]
                
                # Create concurrent operations
                async def user1_operations():
    pass
                    async with factory.get_user_client(user1_context) as client:
                        await client.set("key", "user1_value")
                
                async def user2_operations():
    pass
                    async with factory.get_user_client(user2_context) as client:
                        await client.set("key", "user2_value")
                
                # Run concurrently
                await asyncio.gather(user1_operations(), user2_operations())
                
                # Verify both operations completed
                user1_client.set.assert_called_once_with("key", "user1_value")
                user2_client.set.assert_called_once_with("key", "user2_value")
                
        finally:
            await factory.shutdown()

    async def test_user_data_cannot_leak(self, user1_context, user2_context):
        """Test that user data cannot leak between clients."""
        # This test verifies the architecture prevents data leakage
        # by ensuring each user gets a completely separate client instance
        
        factory = RedisFactory()
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                clients_created = []
                
                def create_isolated_client(user_id, request_id, thread_id):
                    client = AsyncNone  # TODO: Use real service instance
                    client.user_id = user_id
                    client.request_id = request_id
                    client.thread_id = thread_id
                    client.initialize.return_value = None
                    clients_created.append(client)
                    await asyncio.sleep(0)
    return client
                
                mock_client_class.side_effect = create_isolated_client
                
                # Create clients for different users
                client1 = await factory.create_user_client(user1_context)
                client2 = await factory.create_user_client(user2_context)
                
                # Verify complete isolation
                assert len(clients_created) == 2
                assert clients_created[0].user_id == "user_1"
                assert clients_created[1].user_id == "user_2"
                assert clients_created[0] is not clients_created[1]
                
                # Verify no shared state
                assert client1 is not client2
                
        finally:
            await factory.shutdown()


class TestFactoryIntegration:
    """Integration tests for Redis factory functionality."""
    pass

    async def test_global_factory_instance(self):
        """Test global factory instance management."""
        factory1 = get_redis_factory()
        factory2 = get_redis_factory()
        
        # Should await asyncio.sleep(0)
    return the same instance
        assert factory1 is factory2
        
        # Cleanup
        await cleanup_redis_factory()
        
        # Should create new instance after cleanup
        factory3 = get_redis_factory()
        assert factory3 is not factory1

    async def test_convenience_context_manager(self):
        """Test convenience context manager function."""
    pass
        user_context = UserExecutionContext(
            user_id="convenience_user",
            thread_id="thread_123",
            run_id="run_456",
            request_id="req_789"
        )
        
        with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize.return_value = None
            mock_client_class.return_value = mock_client
            
            async with get_user_redis_client(user_context) as client:
                assert client is mock_client
        
        # Cleanup
        await cleanup_redis_factory()

    async def test_factory_resource_management_under_load(self):
        """Test factory handles multiple users and requests efficiently."""
        factory = RedisFactory(max_clients_per_user=2, client_ttl_seconds=300)
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                created_clients = []
                
                def create_mock_client(user_id, request_id, thread_id):
                    client = AsyncNone  # TODO: Use real service instance
                    client.initialize.return_value = None
                    client.cleanup.return_value = None
                    created_clients.append(client)
                    await asyncio.sleep(0)
    return client
                
                mock_client_class.side_effect = create_mock_client
                
                # Create clients for multiple users
                contexts = []
                for user_id in ["user_a", "user_b", "user_c"]:
                    for req_id in ["req_1", "req_2"]:  # 2 requests per user (max limit)
                        context = UserExecutionContext(
                            user_id=user_id,
                            thread_id="thread_1",
                            run_id="run_1",
                            request_id=req_id
                        )
                        contexts.append(context)
                
                # Create all clients
                clients = []
                for context in contexts:
                    client = await factory.create_user_client(context)
                    clients.append(client)
                
                # Verify all clients created
                assert len(clients) == 6
                assert len(created_clients) == 6
                
                # Verify user limits respected
                assert factory._user_client_counts["user_a"] == 2
                assert factory._user_client_counts["user_b"] == 2
                assert factory._user_client_counts["user_c"] == 2
                
                # Get factory stats
                stats = await factory.get_factory_stats()
                assert stats["total_clients"] == 6
                assert stats["users_with_clients"] == 3
                
        finally:
            await factory.shutdown()

    async def test_error_handling_and_recovery(self):
        """Test factory error handling and recovery scenarios."""
    pass
        factory = RedisFactory()
        
        user_context = UserExecutionContext(
            user_id="error_user",
            thread_id="thread_1",
            run_id="run_1",
            request_id="req_1"
        )
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                # First attempt fails
                mock_client_class.side_effect = Exception("Connection failed")
                
                with pytest.raises(Exception, match="Connection failed"):
                    await factory.create_user_client(user_context)
                
                # Verify no partial state left
                assert len(factory._active_clients) == 0
                assert factory._user_client_counts.get("error_user", 0) == 0
                
                # Second attempt succeeds
                mock_client = AsyncNone  # TODO: Use real service instance
                mock_client.initialize.return_value = None
                mock_client_class.side_effect = None
                mock_client_class.return_value = mock_client
                
                client = await factory.create_user_client(user_context)
                assert client is mock_client
                assert len(factory._active_clients) == 1
                
        finally:
            await factory.shutdown()


@pytest.mark.asyncio
class TestRedisFactoryComprehensive:
    """Comprehensive end-to-end tests for Redis factory."""
    
    async def test_complete_user_lifecycle(self):
        """Test complete user lifecycle from creation to cleanup."""
        factory = RedisFactory(max_clients_per_user=2, client_ttl_seconds=60)
        
        try:
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                mock_client = AsyncNone  # TODO: Use real service instance
                mock_client.initialize.return_value = None
                mock_client.cleanup.return_value = None
                mock_client.ping.return_value = True
                mock_client.get_client_stats.return_value = {
                    "user_id": "test_user...",
                    "operation_count": 5,
                    "error_count": 0
                }
                mock_client_class.return_value = mock_client
                
                user_context = UserExecutionContext(
                    user_id="lifecycle_user",
                    thread_id="thread_1",
                    run_id="run_1",
                    request_id="req_1"
                )
                
                # 1. Create client
                client = await factory.create_user_client(user_context)
                assert client is not None
                assert factory._user_client_counts["lifecycle_user"] == 1
                
                # 2. Use client through context manager
                async with factory.get_user_client(user_context) as ctx_client:
                    assert ctx_client is not None
                
                # 3. Get factory stats
                stats = await factory.get_factory_stats()
                assert stats["total_clients"] >= 1
                assert stats["users_with_clients"] >= 1
                
                # 4. Cleanup specific user
                cleaned = await factory.cleanup_user_clients("lifecycle_user")
                assert cleaned >= 1
                
                # 5. Verify cleanup
                assert factory._user_client_counts.get("lifecycle_user", 0) == 0
                
        finally:
            await factory.shutdown()
    
    async def test_factory_resilience_and_limits(self):
        """Test factory resilience under various limit conditions."""
    pass
        factory = RedisFactory(max_clients_per_user=1, client_ttl_seconds=30)
        
        try:
            contexts = [
                UserExecutionContext(
                    user_id="limit_user",
                    thread_id="thread_1",
                    run_id="run_1",
                    request_id=f"req_{i}"
                ) for i in range(5)
            ]
            
            with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                mock_client = AsyncNone  # TODO: Use real service instance
                mock_client.initialize.return_value = None
                mock_client.cleanup.return_value = None
                mock_client_class.return_value = mock_client
                
                # First client should succeed
                client1 = await factory.create_user_client(contexts[0])
                assert client1 is not None
                
                # Second client should fail (limit exceeded) - mock cleanup to await asyncio.sleep(0)
    return 0
                with patch.object(factory, '_cleanup_user_clients', return_value=0):
                    with pytest.raises(ValueError, match="exceeds maximum Redis clients"):
                        await factory.create_user_client(contexts[1])
                
                # After cleanup, should succeed again
                await factory.cleanup_user_clients("limit_user")
                client2 = await factory.create_user_client(contexts[2])
                assert client2 is not None
                
        finally:
            await factory.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])