# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive test suite for Redis Factory pattern implementation.

# REMOVED_SYNTAX_ERROR: Tests the Factory pattern for user-isolated Redis client instances.
# REMOVED_SYNTAX_ERROR: Ensures complete user isolation, proper resource management, and thread safety.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: 1. Segment: All customer segments (Free through Enterprise)
    # REMOVED_SYNTAX_ERROR: 2. Business Goal: Redis-level user isolation preventing data contamination
    # REMOVED_SYNTAX_ERROR: 3. Value Impact: Critical security feature ensuring enterprise-grade data governance
    # REMOVED_SYNTAX_ERROR: 4. Revenue Impact: Essential for Enterprise tier compliance and customer trust
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.factories.redis_factory import ( )
    # REMOVED_SYNTAX_ERROR: RedisFactory,
    # REMOVED_SYNTAX_ERROR: UserRedisClient,
    # REMOVED_SYNTAX_ERROR: get_redis_factory,
    # REMOVED_SYNTAX_ERROR: get_user_redis_client,
    # REMOVED_SYNTAX_ERROR: cleanup_redis_factory
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.models.user_execution_context import UserExecutionContext


# REMOVED_SYNTAX_ERROR: class TestUserRedisClient:
    # REMOVED_SYNTAX_ERROR: """Test user-scoped Redis client functionality."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_012",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="ws_345"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def user_client(self, user_context):
    # REMOVED_SYNTAX_ERROR: """Create test user Redis client."""
    # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
    # REMOVED_SYNTAX_ERROR: user_context.user_id,
    # REMOVED_SYNTAX_ERROR: user_context.request_id,
    # REMOVED_SYNTAX_ERROR: user_context.thread_id
    

    # Mock the Redis manager to avoid real Redis connection
    # REMOVED_SYNTAX_ERROR: mock_manager = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_manager.ping.return_value = True
    # REMOVED_SYNTAX_ERROR: client._manager = mock_manager
    # REMOVED_SYNTAX_ERROR: client._initialized = True

    # REMOVED_SYNTAX_ERROR: yield client

    # Cleanup
    # REMOVED_SYNTAX_ERROR: await client.cleanup()

# REMOVED_SYNTAX_ERROR: def test_user_client_initialization(self, user_context):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Test UserRedisClient initialization."""
    # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
    # REMOVED_SYNTAX_ERROR: user_context.user_id,
    # REMOVED_SYNTAX_ERROR: user_context.request_id,
    # REMOVED_SYNTAX_ERROR: user_context.thread_id
    

    # REMOVED_SYNTAX_ERROR: assert client.user_id == user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert client.request_id == user_context.request_id
    # REMOVED_SYNTAX_ERROR: assert client.thread_id == user_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert not client._initialized
    # REMOVED_SYNTAX_ERROR: assert client._operation_count == 0
    # REMOVED_SYNTAX_ERROR: assert client._error_count == 0

    # Removed problematic line: async def test_client_initialization_flow(self, user_context):
        # REMOVED_SYNTAX_ERROR: """Test client initialization creates isolated manager."""
        # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
        # REMOVED_SYNTAX_ERROR: user_context.user_id,
        # REMOVED_SYNTAX_ERROR: user_context.request_id,
        # REMOVED_SYNTAX_ERROR: user_context.thread_id
        

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.RedisManager') as mock_manager_class:
            # REMOVED_SYNTAX_ERROR: mock_manager = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_manager.connect.return_value = None
            # REMOVED_SYNTAX_ERROR: mock_manager.ping.return_value = True
            # REMOVED_SYNTAX_ERROR: mock_manager_class.return_value = mock_manager

            # REMOVED_SYNTAX_ERROR: await client.initialize()

            # Verify manager was created and initialized
            # REMOVED_SYNTAX_ERROR: mock_manager_class.assert_called_once_with(test_mode=False)
            # REMOVED_SYNTAX_ERROR: mock_manager.connect.assert_called_once()
            # REMOVED_SYNTAX_ERROR: mock_manager.ping.assert_called_once()

            # REMOVED_SYNTAX_ERROR: assert client._initialized
            # REMOVED_SYNTAX_ERROR: assert client._manager is not None

            # Removed problematic line: async def test_client_initialization_failure(self, user_context):
                # REMOVED_SYNTAX_ERROR: """Test client initialization handles connection failures."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
                # REMOVED_SYNTAX_ERROR: user_context.user_id,
                # REMOVED_SYNTAX_ERROR: user_context.request_id,
                # REMOVED_SYNTAX_ERROR: user_context.thread_id
                

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.RedisManager') as mock_manager_class:
                    # REMOVED_SYNTAX_ERROR: mock_manager = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_manager.connect.side_effect = Exception("Connection failed")
                    # REMOVED_SYNTAX_ERROR: mock_manager_class.return_value = mock_manager

                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConnectionError, match="Failed to initialize user Redis client"):
                        # REMOVED_SYNTAX_ERROR: await client.initialize()

                        # REMOVED_SYNTAX_ERROR: assert not client._initialized
                        # REMOVED_SYNTAX_ERROR: assert client._manager is not None

                        # Removed problematic line: async def test_basic_operations_with_user_isolation(self, user_client):
                            # REMOVED_SYNTAX_ERROR: """Test basic Redis operations use user isolation."""
                            # Set up mock returns
                            # REMOVED_SYNTAX_ERROR: user_client._manager.get.return_value = "test_value"
                            # REMOVED_SYNTAX_ERROR: user_client._manager.set.return_value = True
                            # REMOVED_SYNTAX_ERROR: user_client._manager.delete.return_value = 1
                            # REMOVED_SYNTAX_ERROR: user_client._manager.exists.return_value = True
                            # REMOVED_SYNTAX_ERROR: user_client._manager.expire.return_value = True
                            # REMOVED_SYNTAX_ERROR: user_client._manager.keys.return_value = ["key1", "key2"]
                            # REMOVED_SYNTAX_ERROR: user_client._manager.ttl.return_value = 300

                            # Test operations
                            # REMOVED_SYNTAX_ERROR: value = await user_client.get("test_key")
                            # REMOVED_SYNTAX_ERROR: set_result = await user_client.set("test_key", "test_value", ex=300)
                            # REMOVED_SYNTAX_ERROR: delete_result = await user_client.delete("test_key")
                            # REMOVED_SYNTAX_ERROR: exists_result = await user_client.exists("test_key")
                            # REMOVED_SYNTAX_ERROR: expire_result = await user_client.expire("test_key", 300)
                            # REMOVED_SYNTAX_ERROR: keys_result = await user_client.keys("test*")
                            # REMOVED_SYNTAX_ERROR: ttl_result = await user_client.ttl("test_key")

                            # Verify results
                            # REMOVED_SYNTAX_ERROR: assert value == "test_value"
                            # REMOVED_SYNTAX_ERROR: assert set_result is True
                            # REMOVED_SYNTAX_ERROR: assert delete_result == 1
                            # REMOVED_SYNTAX_ERROR: assert exists_result is True
                            # REMOVED_SYNTAX_ERROR: assert expire_result is True
                            # REMOVED_SYNTAX_ERROR: assert keys_result == ["key1", "key2"]
                            # REMOVED_SYNTAX_ERROR: assert ttl_result == 300

                            # Verify all operations used user_id for isolation
                            # REMOVED_SYNTAX_ERROR: user_client._manager.get.assert_called_with("test_key", user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.set.assert_called_with("test_key", "test_value", ex=300, user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.delete.assert_called_with("test_key", user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.exists.assert_called_with("test_key", user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.expire.assert_called_with("test_key", 300, user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.keys.assert_called_with("test*", user_id=user_client.user_id)
                            # REMOVED_SYNTAX_ERROR: user_client._manager.ttl.assert_called_with("test_key", user_id=user_client.user_id)

                            # Removed problematic line: async def test_hash_operations_with_user_isolation(self, user_client):
                                # REMOVED_SYNTAX_ERROR: """Test hash operations use user isolation."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # Set up mock returns
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hset.return_value = 1
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hget.return_value = "field_value"
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hgetall.return_value = {"field": "value"}

                                # Test hash operations
                                # REMOVED_SYNTAX_ERROR: hset_result = await user_client.hset("hash_key", "field", "value")
                                # REMOVED_SYNTAX_ERROR: hget_result = await user_client.hget("hash_key", "field")
                                # REMOVED_SYNTAX_ERROR: hgetall_result = await user_client.hgetall("hash_key")

                                # Verify results
                                # REMOVED_SYNTAX_ERROR: assert hset_result == 1
                                # REMOVED_SYNTAX_ERROR: assert hget_result == "field_value"
                                # REMOVED_SYNTAX_ERROR: assert hgetall_result == {"field": "value"}

                                # Verify user isolation
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hset.assert_called_with("hash_key", "field", "value", user_id=user_client.user_id)
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hget.assert_called_with("hash_key", "field", user_id=user_client.user_id)
                                # REMOVED_SYNTAX_ERROR: user_client._manager.hgetall.assert_called_with("hash_key", user_id=user_client.user_id)

                                # Removed problematic line: async def test_list_operations_with_user_isolation(self, user_client):
                                    # REMOVED_SYNTAX_ERROR: """Test list operations use user isolation."""
                                    # Set up mock returns
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.lpush.return_value = 2
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.rpop.return_value = "item"
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.llen.return_value = 5

                                    # Test list operations
                                    # REMOVED_SYNTAX_ERROR: lpush_result = await user_client.lpush("list_key", "item1", "item2")
                                    # REMOVED_SYNTAX_ERROR: rpop_result = await user_client.rpop("list_key")
                                    # REMOVED_SYNTAX_ERROR: llen_result = await user_client.llen("list_key")

                                    # Verify results
                                    # REMOVED_SYNTAX_ERROR: assert lpush_result == 2
                                    # REMOVED_SYNTAX_ERROR: assert rpop_result == "item"
                                    # REMOVED_SYNTAX_ERROR: assert llen_result == 5

                                    # Verify user isolation
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.lpush.assert_called_with("list_key", "item1", "item2", user_id=user_client.user_id)
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.rpop.assert_called_with("list_key", user_id=user_client.user_id)
                                    # REMOVED_SYNTAX_ERROR: user_client._manager.llen.assert_called_with("list_key", user_id=user_client.user_id)

                                    # Removed problematic line: async def test_json_operations(self, user_client):
                                        # REMOVED_SYNTAX_ERROR: """Test JSON convenience methods."""
                                        # REMOVED_SYNTAX_ERROR: pass
                                        # Mock underlying operations
                                        # REMOVED_SYNTAX_ERROR: import json
                                        # REMOVED_SYNTAX_ERROR: test_data = {"name": "test", "value": 123}
                                        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(test_data)

                                        # REMOVED_SYNTAX_ERROR: user_client._manager.set.return_value = True
                                        # REMOVED_SYNTAX_ERROR: user_client._manager.get.return_value = json_str

                                        # Test JSON set/get
                                        # REMOVED_SYNTAX_ERROR: set_result = await user_client.set_json("json_key", test_data, ex=300)
                                        # REMOVED_SYNTAX_ERROR: get_result = await user_client.get_json("json_key")

                                        # Verify results
                                        # REMOVED_SYNTAX_ERROR: assert set_result is True
                                        # REMOVED_SYNTAX_ERROR: assert get_result == test_data

                                        # Verify underlying calls
                                        # REMOVED_SYNTAX_ERROR: user_client._manager.set.assert_called_with("json_key", json_str, ex=300, user_id=user_client.user_id)
                                        # REMOVED_SYNTAX_ERROR: user_client._manager.get.assert_called_with("json_key", user_id=user_client.user_id)

                                        # Removed problematic line: async def test_json_get_invalid_json(self, user_client):
                                            # REMOVED_SYNTAX_ERROR: """Test JSON get with invalid JSON returns None."""
                                            # REMOVED_SYNTAX_ERROR: user_client._manager.get.return_value = "invalid_json{" )

                                            # REMOVED_SYNTAX_ERROR: result = await user_client.get_json("json_key")
                                            # REMOVED_SYNTAX_ERROR: assert result is None

                                            # Removed problematic line: async def test_json_get_missing_key(self, user_client):
                                                # REMOVED_SYNTAX_ERROR: """Test JSON get with missing key returns None."""
                                                # REMOVED_SYNTAX_ERROR: pass
                                                # REMOVED_SYNTAX_ERROR: user_client._manager.get.return_value = None

                                                # REMOVED_SYNTAX_ERROR: result = await user_client.get_json("json_key")
                                                # REMOVED_SYNTAX_ERROR: assert result is None

                                                # Removed problematic line: async def test_operation_metrics_tracking(self, user_client):
                                                    # REMOVED_SYNTAX_ERROR: """Test operation metrics are properly tracked."""
                                                    # REMOVED_SYNTAX_ERROR: initial_count = user_client._operation_count

                                                    # Mock manager operations
                                                    # REMOVED_SYNTAX_ERROR: user_client._manager.get.return_value = "value"
                                                    # REMOVED_SYNTAX_ERROR: user_client._manager.set.return_value = True

                                                    # Perform operations
                                                    # REMOVED_SYNTAX_ERROR: await user_client.get("key1")
                                                    # REMOVED_SYNTAX_ERROR: await user_client.set("key2", "value2")

                                                    # Verify metrics updated
                                                    # REMOVED_SYNTAX_ERROR: assert user_client._operation_count == initial_count + 2
                                                    # REMOVED_SYNTAX_ERROR: assert user_client._error_count == 0

                                                    # Removed problematic line: async def test_error_tracking(self, user_client):
                                                        # REMOVED_SYNTAX_ERROR: """Test error tracking in metrics."""
                                                        # REMOVED_SYNTAX_ERROR: pass
                                                        # REMOVED_SYNTAX_ERROR: initial_error_count = user_client._error_count

                                                        # Mock operation failure
                                                        # REMOVED_SYNTAX_ERROR: user_client._manager.get.side_effect = Exception("Redis error")

                                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
                                                            # REMOVED_SYNTAX_ERROR: await user_client.get("error_key")

                                                            # Verify error count increased
                                                            # REMOVED_SYNTAX_ERROR: assert user_client._error_count == initial_error_count + 1

                                                            # Removed problematic line: async def test_client_stats(self, user_client):
                                                                # REMOVED_SYNTAX_ERROR: """Test client statistics generation."""
                                                                # Perform some operations to update metrics
                                                                # REMOVED_SYNTAX_ERROR: user_client._operation_count = 10
                                                                # REMOVED_SYNTAX_ERROR: user_client._error_count = 2

                                                                # REMOVED_SYNTAX_ERROR: stats = user_client.get_client_stats()

                                                                # Verify stats structure
                                                                # REMOVED_SYNTAX_ERROR: assert "user_id" in stats
                                                                # REMOVED_SYNTAX_ERROR: assert stats["user_id"] == "formatted_string"
                                                                # REMOVED_SYNTAX_ERROR: assert stats["request_id"] == user_client.request_id
                                                                # REMOVED_SYNTAX_ERROR: assert stats["thread_id"] == user_client.thread_id
                                                                # REMOVED_SYNTAX_ERROR: assert stats["initialized"] == user_client._initialized
                                                                # REMOVED_SYNTAX_ERROR: assert stats["operation_count"] == 10
                                                                # REMOVED_SYNTAX_ERROR: assert stats["error_count"] == 2
                                                                # REMOVED_SYNTAX_ERROR: assert stats["error_rate"] == 20.0  # 2/10 * 100
                                                                # REMOVED_SYNTAX_ERROR: assert "age_seconds" in stats
                                                                # REMOVED_SYNTAX_ERROR: assert "last_activity_seconds_ago" in stats

                                                                # Removed problematic line: async def test_ping_health_check(self, user_client):
                                                                    # REMOVED_SYNTAX_ERROR: """Test Redis connection health check."""
                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                    # REMOVED_SYNTAX_ERROR: user_client._manager.ping.return_value = True
                                                                    # REMOVED_SYNTAX_ERROR: assert await user_client.ping() is True

                                                                    # REMOVED_SYNTAX_ERROR: user_client._manager.ping.return_value = False
                                                                    # REMOVED_SYNTAX_ERROR: assert await user_client.ping() is False

                                                                    # Removed problematic line: async def test_ping_uninitialized_client(self, user_context):
                                                                        # REMOVED_SYNTAX_ERROR: """Test ping on uninitialized client attempts initialization."""
                                                                        # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
                                                                        # REMOVED_SYNTAX_ERROR: user_context.user_id,
                                                                        # REMOVED_SYNTAX_ERROR: user_context.request_id,
                                                                        # REMOVED_SYNTAX_ERROR: user_context.thread_id
                                                                        

                                                                        # REMOVED_SYNTAX_ERROR: with patch.object(client, 'initialize', side_effect=Exception("Init failed")):
                                                                            # REMOVED_SYNTAX_ERROR: result = await client.ping()
                                                                            # REMOVED_SYNTAX_ERROR: assert result is False

                                                                            # Removed problematic line: async def test_client_cleanup(self, user_context):
                                                                                # REMOVED_SYNTAX_ERROR: """Test client cleanup properly releases resources."""
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
                                                                                # REMOVED_SYNTAX_ERROR: user_context.user_id,
                                                                                # REMOVED_SYNTAX_ERROR: user_context.request_id,
                                                                                # REMOVED_SYNTAX_ERROR: user_context.thread_id
                                                                                

                                                                                # Mock manager
                                                                                # REMOVED_SYNTAX_ERROR: mock_manager = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: client._manager = mock_manager
                                                                                # REMOVED_SYNTAX_ERROR: client._initialized = True

                                                                                # Cleanup
                                                                                # REMOVED_SYNTAX_ERROR: await client.cleanup()

                                                                                # Verify cleanup
                                                                                # REMOVED_SYNTAX_ERROR: mock_manager.disconnect.assert_called_once()
                                                                                # REMOVED_SYNTAX_ERROR: assert client._manager is None
                                                                                # REMOVED_SYNTAX_ERROR: assert not client._initialized

                                                                                # Removed problematic line: async def test_auto_initialization_on_operations(self, user_context):
                                                                                    # REMOVED_SYNTAX_ERROR: """Test operations automatically initialize client if needed."""
                                                                                    # REMOVED_SYNTAX_ERROR: client = UserRedisClient( )
                                                                                    # REMOVED_SYNTAX_ERROR: user_context.user_id,
                                                                                    # REMOVED_SYNTAX_ERROR: user_context.request_id,
                                                                                    # REMOVED_SYNTAX_ERROR: user_context.thread_id
                                                                                    

                                                                                    # REMOVED_SYNTAX_ERROR: with patch.object(client, 'initialize', return_value=None) as mock_init:
                                                                                        # Mock manager for operation
                                                                                        # REMOVED_SYNTAX_ERROR: mock_manager = AsyncNone  # TODO: Use real service instance
                                                                                        # REMOVED_SYNTAX_ERROR: mock_manager.get.return_value = "value"
                                                                                        # REMOVED_SYNTAX_ERROR: client._manager = mock_manager

                                                                                        # Operation should trigger initialization
                                                                                        # REMOVED_SYNTAX_ERROR: await client.get("test_key")

                                                                                        # REMOVED_SYNTAX_ERROR: mock_init.assert_called_once()


# REMOVED_SYNTAX_ERROR: class TestRedisFactory:
    # REMOVED_SYNTAX_ERROR: """Test Redis factory functionality."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="factory_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_012"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_factory(self):
    # REMOVED_SYNTAX_ERROR: """Create test Redis factory."""
    # REMOVED_SYNTAX_ERROR: factory = RedisFactory(max_clients_per_user=3, client_ttl_seconds=600)
    # REMOVED_SYNTAX_ERROR: yield factory
    # REMOVED_SYNTAX_ERROR: await factory.shutdown()

# REMOVED_SYNTAX_ERROR: def test_factory_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Test Redis factory initialization."""
    # REMOVED_SYNTAX_ERROR: factory = RedisFactory(max_clients_per_user=5, client_ttl_seconds=1800)

    # REMOVED_SYNTAX_ERROR: assert factory.factory_name == "RedisFactory"
    # REMOVED_SYNTAX_ERROR: assert factory.max_clients_per_user == 5
    # REMOVED_SYNTAX_ERROR: assert factory.client_ttl == 1800
    # REMOVED_SYNTAX_ERROR: assert len(factory._active_clients) == 0
    # REMOVED_SYNTAX_ERROR: assert len(factory._user_client_counts) == 0
    # REMOVED_SYNTAX_ERROR: assert factory._created_count == 0
    # REMOVED_SYNTAX_ERROR: assert factory._cleanup_count == 0

    # Removed problematic line: async def test_create_user_client_success(self, redis_factory, user_context):
        # REMOVED_SYNTAX_ERROR: """Test successful user client creation."""
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
            # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
            # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

            # REMOVED_SYNTAX_ERROR: client = await redis_factory.create_user_client(user_context)

            # Verify client creation
            # REMOVED_SYNTAX_ERROR: assert client is mock_client
            # REMOVED_SYNTAX_ERROR: mock_client_class.assert_called_once_with( )
            # REMOVED_SYNTAX_ERROR: user_context.user_id,
            # REMOVED_SYNTAX_ERROR: user_context.request_id,
            # REMOVED_SYNTAX_ERROR: user_context.thread_id
            
            # REMOVED_SYNTAX_ERROR: mock_client.initialize.assert_called_once()

            # Verify tracking
            # REMOVED_SYNTAX_ERROR: assert len(redis_factory._active_clients) == 1
            # REMOVED_SYNTAX_ERROR: assert redis_factory._user_client_counts[user_context.user_id] == 1
            # REMOVED_SYNTAX_ERROR: assert redis_factory._created_count == 1

            # Removed problematic line: async def test_create_user_client_invalid_context(self, redis_factory):
                # REMOVED_SYNTAX_ERROR: """Test client creation with invalid context."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="Expected UserExecutionContext"):
                    # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client("invalid_context")

                    # Removed problematic line: async def test_user_client_limit_enforcement(self, redis_factory, user_context):
                        # REMOVED_SYNTAX_ERROR: """Test per-user client limit enforcement."""
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                            # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                            # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                            # Mock cleanup to await asyncio.sleep(0)
                            # REMOVED_SYNTAX_ERROR: return 0 (no cleanup)
                            # REMOVED_SYNTAX_ERROR: with patch.object(redis_factory, '_cleanup_user_clients', return_value=0):
                                # Create maximum allowed clients
                                # REMOVED_SYNTAX_ERROR: for i in range(redis_factory.max_clients_per_user):
                                    # Use different request IDs to simulate separate requests
                                    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
                                    # REMOVED_SYNTAX_ERROR: request_id="formatted_string"
                                    
                                    # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(context)

                                    # Attempt to create one more should fail
                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="exceeds maximum Redis clients"):
                                        # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(user_context)

                                        # Removed problematic line: async def test_client_limit_with_cleanup(self, redis_factory, user_context):
                                            # REMOVED_SYNTAX_ERROR: """Test client limit with automatic cleanup of expired clients."""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                                                # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                                                # REMOVED_SYNTAX_ERROR: mock_client.cleanup.return_value = None
                                                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                                                # Create maximum clients
                                                # REMOVED_SYNTAX_ERROR: for i in range(redis_factory.max_clients_per_user):
                                                    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                                    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                                                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                                                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
                                                    # REMOVED_SYNTAX_ERROR: request_id="formatted_string"
                                                    
                                                    # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(context)

                                                    # Mock cleanup to actually reduce user count
# REMOVED_SYNTAX_ERROR: async def mock_cleanup(user_id):
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate cleaning up 1 client
    # REMOVED_SYNTAX_ERROR: if user_id in redis_factory._user_client_counts:
        # REMOVED_SYNTAX_ERROR: redis_factory._user_client_counts[user_id] = max(0, redis_factory._user_client_counts[user_id] - 1)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return 1

        # REMOVED_SYNTAX_ERROR: with patch.object(redis_factory, '_cleanup_user_clients', side_effect=mock_cleanup):
            # Should succeed after cleanup
            # REMOVED_SYNTAX_ERROR: client = await redis_factory.create_user_client(user_context)
            # REMOVED_SYNTAX_ERROR: assert client is not None

            # Removed problematic line: async def test_context_manager_usage(self, redis_factory, user_context):
                # REMOVED_SYNTAX_ERROR: """Test factory context manager usage."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                    # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                    # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                    # REMOVED_SYNTAX_ERROR: async with redis_factory.get_user_client(user_context) as client:
                        # REMOVED_SYNTAX_ERROR: assert client is mock_client

                        # Verify client was created and returned
                        # REMOVED_SYNTAX_ERROR: mock_client_class.assert_called_once()

                        # Removed problematic line: async def test_cleanup_user_clients(self, redis_factory, user_context):
                            # REMOVED_SYNTAX_ERROR: """Test cleanup of all clients for a user."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                # REMOVED_SYNTAX_ERROR: mock_clients = []

# REMOVED_SYNTAX_ERROR: def create_mock_client(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
    # REMOVED_SYNTAX_ERROR: mock_client.cleanup.return_value = None
    # REMOVED_SYNTAX_ERROR: mock_clients.append(mock_client)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock_client

    # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = create_mock_client

    # Create multiple clients for the user
    # REMOVED_SYNTAX_ERROR: for i in range(3):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
        # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
        # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
        # REMOVED_SYNTAX_ERROR: request_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(context)

        # Cleanup all clients for the user
        # REMOVED_SYNTAX_ERROR: cleaned_count = await redis_factory.cleanup_user_clients(user_context.user_id)

        # Verify cleanup
        # REMOVED_SYNTAX_ERROR: assert cleaned_count == 3
        # REMOVED_SYNTAX_ERROR: for mock_client in mock_clients:
            # REMOVED_SYNTAX_ERROR: mock_client.cleanup.assert_called_once()

            # REMOVED_SYNTAX_ERROR: assert redis_factory._user_client_counts.get(user_context.user_id, 0) == 0
            # REMOVED_SYNTAX_ERROR: assert len(redis_factory._active_clients) == 0

            # Removed problematic line: async def test_factory_stats(self, redis_factory, user_context):
                # REMOVED_SYNTAX_ERROR: """Test factory statistics generation."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                    # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                    # REMOVED_SYNTAX_ERROR: mock_client.get_client_stats.return_value = {"test": "stats"}
                    # REMOVED_SYNTAX_ERROR: mock_client.ping.return_value = True
                    # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                    # Create a client
                    # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(user_context)

                    # REMOVED_SYNTAX_ERROR: stats = await redis_factory.get_factory_stats()

                    # Verify stats structure
                    # REMOVED_SYNTAX_ERROR: assert stats["factory_name"] == "RedisFactory"
                    # REMOVED_SYNTAX_ERROR: assert stats["total_clients"] == 1
                    # REMOVED_SYNTAX_ERROR: assert stats["healthy_clients"] == 1
                    # REMOVED_SYNTAX_ERROR: assert stats["users_with_clients"] == 1
                    # REMOVED_SYNTAX_ERROR: assert stats["created_count"] == 1
                    # REMOVED_SYNTAX_ERROR: assert stats["cleanup_count"] == 0
                    # REMOVED_SYNTAX_ERROR: assert "factory_age_seconds" in stats
                    # REMOVED_SYNTAX_ERROR: assert "age_distribution" in stats
                    # REMOVED_SYNTAX_ERROR: assert "user_client_counts" in stats
                    # REMOVED_SYNTAX_ERROR: assert "client_details" in stats

                    # Removed problematic line: async def test_background_cleanup_task(self, redis_factory, user_context):
                        # REMOVED_SYNTAX_ERROR: """Test background cleanup task is started when factory is used."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # Initially, cleanup task might not be started
                        # REMOVED_SYNTAX_ERROR: assert redis_factory._cleanup_started is False

                        # Create a client to trigger cleanup task start
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                            # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                            # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                            # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(user_context)

                            # Now cleanup task should be started
                            # REMOVED_SYNTAX_ERROR: assert redis_factory._cleanup_started is True
                            # REMOVED_SYNTAX_ERROR: assert redis_factory._cleanup_task is not None
                            # REMOVED_SYNTAX_ERROR: assert not redis_factory._cleanup_task.done()

                            # Removed problematic line: async def test_factory_shutdown(self, redis_factory, user_context):
                                # REMOVED_SYNTAX_ERROR: """Test factory shutdown cleans up all resources."""
                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                    # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                                    # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                                    # REMOVED_SYNTAX_ERROR: mock_client.cleanup.return_value = None
                                    # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                                    # Create a client
                                    # REMOVED_SYNTAX_ERROR: await redis_factory.create_user_client(user_context)

                                    # Shutdown
                                    # REMOVED_SYNTAX_ERROR: await redis_factory.shutdown()

                                    # Verify cleanup
                                    # REMOVED_SYNTAX_ERROR: mock_client.cleanup.assert_called_once()
                                    # REMOVED_SYNTAX_ERROR: assert len(redis_factory._active_clients) == 0
                                    # REMOVED_SYNTAX_ERROR: assert len(redis_factory._user_client_counts) == 0
                                    # REMOVED_SYNTAX_ERROR: assert redis_factory._shutdown_event.is_set()


# REMOVED_SYNTAX_ERROR: class TestUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test complete user isolation between Redis clients."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user1_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create user 1 execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_1",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
    # REMOVED_SYNTAX_ERROR: run_id="run_1",
    # REMOVED_SYNTAX_ERROR: request_id="req_1"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user2_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create user 2 execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_2",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_2",
    # REMOVED_SYNTAX_ERROR: run_id="run_2",
    # REMOVED_SYNTAX_ERROR: request_id="req_2"
    

    # Removed problematic line: async def test_complete_user_isolation(self, user1_context, user2_context):
        # REMOVED_SYNTAX_ERROR: """Test complete isolation between different users."""
        # REMOVED_SYNTAX_ERROR: factory = RedisFactory()

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                # Create separate mock clients for each user
                # REMOVED_SYNTAX_ERROR: user1_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: user2_client = AsyncNone  # TODO: Use real service instance

                # REMOVED_SYNTAX_ERROR: user1_client.initialize.return_value = None
                # REMOVED_SYNTAX_ERROR: user2_client.initialize.return_value = None

                # Return different clients for different users
                # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = [user1_client, user2_client]

                # Create clients for both users
                # REMOVED_SYNTAX_ERROR: client1 = await factory.create_user_client(user1_context)
                # REMOVED_SYNTAX_ERROR: client2 = await factory.create_user_client(user2_context)

                # Verify different clients were created
                # REMOVED_SYNTAX_ERROR: assert client1 is user1_client
                # REMOVED_SYNTAX_ERROR: assert client2 is user2_client

                # Verify separate tracking
                # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["user_1"] == 1
                # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["user_2"] == 1
                # REMOVED_SYNTAX_ERROR: assert len(factory._active_clients) == 2

                # REMOVED_SYNTAX_ERROR: finally:
                    # REMOVED_SYNTAX_ERROR: await factory.shutdown()

                    # Removed problematic line: async def test_concurrent_user_operations(self, user1_context, user2_context):
                        # REMOVED_SYNTAX_ERROR: """Test concurrent operations by different users are isolated."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: factory = RedisFactory()

                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                # REMOVED_SYNTAX_ERROR: user1_client = AsyncNone  # TODO: Use real service instance
                                # REMOVED_SYNTAX_ERROR: user2_client = AsyncNone  # TODO: Use real service instance

                                # REMOVED_SYNTAX_ERROR: user1_client.initialize.return_value = None
                                # REMOVED_SYNTAX_ERROR: user2_client.initialize.return_value = None
                                # REMOVED_SYNTAX_ERROR: user1_client.set.return_value = True
                                # REMOVED_SYNTAX_ERROR: user2_client.set.return_value = True

                                # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = [user1_client, user2_client]

                                # Create concurrent operations
# REMOVED_SYNTAX_ERROR: async def user1_operations():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: async with factory.get_user_client(user1_context) as client:
        # REMOVED_SYNTAX_ERROR: await client.set("key", "user1_value")

# REMOVED_SYNTAX_ERROR: async def user2_operations():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: async with factory.get_user_client(user2_context) as client:
        # REMOVED_SYNTAX_ERROR: await client.set("key", "user2_value")

        # Run concurrently
        # REMOVED_SYNTAX_ERROR: await asyncio.gather(user1_operations(), user2_operations())

        # Verify both operations completed
        # REMOVED_SYNTAX_ERROR: user1_client.set.assert_called_once_with("key", "user1_value")
        # REMOVED_SYNTAX_ERROR: user2_client.set.assert_called_once_with("key", "user2_value")

        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: await factory.shutdown()

            # Removed problematic line: async def test_user_data_cannot_leak(self, user1_context, user2_context):
                # REMOVED_SYNTAX_ERROR: """Test that user data cannot leak between clients."""
                # This test verifies the architecture prevents data leakage
                # by ensuring each user gets a completely separate client instance

                # REMOVED_SYNTAX_ERROR: factory = RedisFactory()

                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                        # REMOVED_SYNTAX_ERROR: clients_created = []

# REMOVED_SYNTAX_ERROR: def create_isolated_client(user_id, request_id, thread_id):
    # REMOVED_SYNTAX_ERROR: client = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: client.user_id = user_id
    # REMOVED_SYNTAX_ERROR: client.request_id = request_id
    # REMOVED_SYNTAX_ERROR: client.thread_id = thread_id
    # REMOVED_SYNTAX_ERROR: client.initialize.return_value = None
    # REMOVED_SYNTAX_ERROR: clients_created.append(client)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return client

    # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = create_isolated_client

    # Create clients for different users
    # REMOVED_SYNTAX_ERROR: client1 = await factory.create_user_client(user1_context)
    # REMOVED_SYNTAX_ERROR: client2 = await factory.create_user_client(user2_context)

    # Verify complete isolation
    # REMOVED_SYNTAX_ERROR: assert len(clients_created) == 2
    # REMOVED_SYNTAX_ERROR: assert clients_created[0].user_id == "user_1"
    # REMOVED_SYNTAX_ERROR: assert clients_created[1].user_id == "user_2"
    # REMOVED_SYNTAX_ERROR: assert clients_created[0] is not clients_created[1]

    # Verify no shared state
    # REMOVED_SYNTAX_ERROR: assert client1 is not client2

    # REMOVED_SYNTAX_ERROR: finally:
        # REMOVED_SYNTAX_ERROR: await factory.shutdown()


# REMOVED_SYNTAX_ERROR: class TestFactoryIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for Redis factory functionality."""
    # REMOVED_SYNTAX_ERROR: pass

    # Removed problematic line: async def test_global_factory_instance(self):
        # REMOVED_SYNTAX_ERROR: """Test global factory instance management."""
        # REMOVED_SYNTAX_ERROR: factory1 = get_redis_factory()
        # REMOVED_SYNTAX_ERROR: factory2 = get_redis_factory()

        # Should await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return the same instance
        # REMOVED_SYNTAX_ERROR: assert factory1 is factory2

        # Cleanup
        # REMOVED_SYNTAX_ERROR: await cleanup_redis_factory()

        # Should create new instance after cleanup
        # REMOVED_SYNTAX_ERROR: factory3 = get_redis_factory()
        # REMOVED_SYNTAX_ERROR: assert factory3 is not factory1

        # Removed problematic line: async def test_convenience_context_manager(self):
            # REMOVED_SYNTAX_ERROR: """Test convenience context manager function."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="convenience_user",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
            # REMOVED_SYNTAX_ERROR: run_id="run_456",
            # REMOVED_SYNTAX_ERROR: request_id="req_789"
            

            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                # REMOVED_SYNTAX_ERROR: async with get_user_redis_client(user_context) as client:
                    # REMOVED_SYNTAX_ERROR: assert client is mock_client

                    # Cleanup
                    # REMOVED_SYNTAX_ERROR: await cleanup_redis_factory()

                    # Removed problematic line: async def test_factory_resource_management_under_load(self):
                        # REMOVED_SYNTAX_ERROR: """Test factory handles multiple users and requests efficiently."""
                        # REMOVED_SYNTAX_ERROR: factory = RedisFactory(max_clients_per_user=2, client_ttl_seconds=300)

                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                # REMOVED_SYNTAX_ERROR: created_clients = []

# REMOVED_SYNTAX_ERROR: def create_mock_client(user_id, request_id, thread_id):
    # REMOVED_SYNTAX_ERROR: client = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: client.initialize.return_value = None
    # REMOVED_SYNTAX_ERROR: client.cleanup.return_value = None
    # REMOVED_SYNTAX_ERROR: created_clients.append(client)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return client

    # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = create_mock_client

    # Create clients for multiple users
    # REMOVED_SYNTAX_ERROR: contexts = []
    # REMOVED_SYNTAX_ERROR: for user_id in ["user_a", "user_b", "user_c"]:
        # REMOVED_SYNTAX_ERROR: for req_id in ["req_1", "req_2"]:  # 2 requests per user (max limit)
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
        # REMOVED_SYNTAX_ERROR: run_id="run_1",
        # REMOVED_SYNTAX_ERROR: request_id=req_id
        
        # REMOVED_SYNTAX_ERROR: contexts.append(context)

        # Create all clients
        # REMOVED_SYNTAX_ERROR: clients = []
        # REMOVED_SYNTAX_ERROR: for context in contexts:
            # REMOVED_SYNTAX_ERROR: client = await factory.create_user_client(context)
            # REMOVED_SYNTAX_ERROR: clients.append(client)

            # Verify all clients created
            # REMOVED_SYNTAX_ERROR: assert len(clients) == 6
            # REMOVED_SYNTAX_ERROR: assert len(created_clients) == 6

            # Verify user limits respected
            # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["user_a"] == 2
            # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["user_b"] == 2
            # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["user_c"] == 2

            # Get factory stats
            # REMOVED_SYNTAX_ERROR: stats = await factory.get_factory_stats()
            # REMOVED_SYNTAX_ERROR: assert stats["total_clients"] == 6
            # REMOVED_SYNTAX_ERROR: assert stats["users_with_clients"] == 3

            # REMOVED_SYNTAX_ERROR: finally:
                # REMOVED_SYNTAX_ERROR: await factory.shutdown()

                # Removed problematic line: async def test_error_handling_and_recovery(self):
                    # REMOVED_SYNTAX_ERROR: """Test factory error handling and recovery scenarios."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: factory = RedisFactory()

                    # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="error_user",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
                    # REMOVED_SYNTAX_ERROR: run_id="run_1",
                    # REMOVED_SYNTAX_ERROR: request_id="req_1"
                    

                    # REMOVED_SYNTAX_ERROR: try:
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                            # First attempt fails
                            # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = Exception("Connection failed")

                            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception, match="Connection failed"):
                                # REMOVED_SYNTAX_ERROR: await factory.create_user_client(user_context)

                                # Verify no partial state left
                                # REMOVED_SYNTAX_ERROR: assert len(factory._active_clients) == 0
                                # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts.get("error_user", 0) == 0

                                # Second attempt succeeds
                                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                                # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                                # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = None
                                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                                # REMOVED_SYNTAX_ERROR: client = await factory.create_user_client(user_context)
                                # REMOVED_SYNTAX_ERROR: assert client is mock_client
                                # REMOVED_SYNTAX_ERROR: assert len(factory._active_clients) == 1

                                # REMOVED_SYNTAX_ERROR: finally:
                                    # REMOVED_SYNTAX_ERROR: await factory.shutdown()


                                    # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestRedisFactoryComprehensive:
    # REMOVED_SYNTAX_ERROR: """Comprehensive end-to-end tests for Redis factory."""

    # Removed problematic line: async def test_complete_user_lifecycle(self):
        # REMOVED_SYNTAX_ERROR: """Test complete user lifecycle from creation to cleanup."""
        # REMOVED_SYNTAX_ERROR: factory = RedisFactory(max_clients_per_user=2, client_ttl_seconds=60)

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                # REMOVED_SYNTAX_ERROR: mock_client.cleanup.return_value = None
                # REMOVED_SYNTAX_ERROR: mock_client.ping.return_value = True
                # REMOVED_SYNTAX_ERROR: mock_client.get_client_stats.return_value = { )
                # REMOVED_SYNTAX_ERROR: "user_id": "test_user...",
                # REMOVED_SYNTAX_ERROR: "operation_count": 5,
                # REMOVED_SYNTAX_ERROR: "error_count": 0
                
                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="lifecycle_user",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
                # REMOVED_SYNTAX_ERROR: run_id="run_1",
                # REMOVED_SYNTAX_ERROR: request_id="req_1"
                

                # 1. Create client
                # REMOVED_SYNTAX_ERROR: client = await factory.create_user_client(user_context)
                # REMOVED_SYNTAX_ERROR: assert client is not None
                # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["lifecycle_user"] == 1

                # 2. Use client through context manager
                # REMOVED_SYNTAX_ERROR: async with factory.get_user_client(user_context) as ctx_client:
                    # REMOVED_SYNTAX_ERROR: assert ctx_client is not None

                    # 3. Get factory stats
                    # REMOVED_SYNTAX_ERROR: stats = await factory.get_factory_stats()
                    # REMOVED_SYNTAX_ERROR: assert stats["total_clients"] >= 1
                    # REMOVED_SYNTAX_ERROR: assert stats["users_with_clients"] >= 1

                    # 4. Cleanup specific user
                    # REMOVED_SYNTAX_ERROR: cleaned = await factory.cleanup_user_clients("lifecycle_user")
                    # REMOVED_SYNTAX_ERROR: assert cleaned >= 1

                    # 5. Verify cleanup
                    # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts.get("lifecycle_user", 0) == 0

                    # REMOVED_SYNTAX_ERROR: finally:
                        # REMOVED_SYNTAX_ERROR: await factory.shutdown()

                        # Removed problematic line: async def test_factory_resilience_and_limits(self):
                            # REMOVED_SYNTAX_ERROR: """Test factory resilience under various limit conditions."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: factory = RedisFactory(max_clients_per_user=1, client_ttl_seconds=30)

                            # REMOVED_SYNTAX_ERROR: try:
                                # REMOVED_SYNTAX_ERROR: contexts = [ )
                                # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
                                # REMOVED_SYNTAX_ERROR: user_id="limit_user",
                                # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
                                # REMOVED_SYNTAX_ERROR: run_id="run_1",
                                # REMOVED_SYNTAX_ERROR: request_id="formatted_string"
                                # REMOVED_SYNTAX_ERROR: ) for i in range(5)
                                

                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.redis_factory.UserRedisClient') as mock_client_class:
                                    # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                                    # REMOVED_SYNTAX_ERROR: mock_client.initialize.return_value = None
                                    # REMOVED_SYNTAX_ERROR: mock_client.cleanup.return_value = None
                                    # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                                    # First client should succeed
                                    # REMOVED_SYNTAX_ERROR: client1 = await factory.create_user_client(contexts[0])
                                    # REMOVED_SYNTAX_ERROR: assert client1 is not None

                                    # Second client should fail (limit exceeded) - mock cleanup to await asyncio.sleep(0)
                                    # REMOVED_SYNTAX_ERROR: return 0
                                    # REMOVED_SYNTAX_ERROR: with patch.object(factory, '_cleanup_user_clients', return_value=0):
                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="exceeds maximum Redis clients"):
                                            # REMOVED_SYNTAX_ERROR: await factory.create_user_client(contexts[1])

                                            # After cleanup, should succeed again
                                            # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_clients("limit_user")
                                            # REMOVED_SYNTAX_ERROR: client2 = await factory.create_user_client(contexts[2])
                                            # REMOVED_SYNTAX_ERROR: assert client2 is not None

                                            # REMOVED_SYNTAX_ERROR: finally:
                                                # REMOVED_SYNTAX_ERROR: await factory.shutdown()


                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])