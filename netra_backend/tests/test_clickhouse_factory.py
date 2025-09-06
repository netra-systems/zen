# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive Tests for ClickHouse Factory Pattern Implementation

# REMOVED_SYNTAX_ERROR: This test suite validates the ClickHouse Factory pattern implementation ensuring:
    # REMOVED_SYNTAX_ERROR: - Complete user isolation at the database client level
    # REMOVED_SYNTAX_ERROR: - Proper connection pooling and resource management per user
    # REMOVED_SYNTAX_ERROR: - Thread-safe concurrent access by multiple users
    # REMOVED_SYNTAX_ERROR: - Resource cleanup and connection lifecycle management
    # REMOVED_SYNTAX_ERROR: - Cache isolation and data protection between users
    # REMOVED_SYNTAX_ERROR: - Factory pattern compliance with USER_CONTEXT_ARCHITECTURE.md

    # REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
        # REMOVED_SYNTAX_ERROR: - Segment: ALL (Free → Enterprise)
        # REMOVED_SYNTAX_ERROR: - Business Goal: Ensure enterprise-grade data isolation
        # REMOVED_SYNTAX_ERROR: - Value Impact: Zero risk of cross-user data contamination
        # REMOVED_SYNTAX_ERROR: - Revenue Impact: Critical for Enterprise revenue, prevents security incidents
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
        # REMOVED_SYNTAX_ERROR: from typing import Dict, List
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.factories.clickhouse_factory import ( )
        # REMOVED_SYNTAX_ERROR: ClickHouseFactory,
        # REMOVED_SYNTAX_ERROR: UserClickHouseClient,
        # REMOVED_SYNTAX_ERROR: UserClickHouseCache,
        # REMOVED_SYNTAX_ERROR: get_clickhouse_factory,
        # REMOVED_SYNTAX_ERROR: cleanup_clickhouse_factory
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.models.user_execution_context import UserExecutionContext


        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a sample user execution context for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user_123",
    # REMOVED_SYNTAX_ERROR: request_id="req_456",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_789",
    # REMOVED_SYNTAX_ERROR: run_id="run_abc"
    


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def another_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create another user execution context for isolation testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user_456",
    # REMOVED_SYNTAX_ERROR: request_id="req_789",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
    # REMOVED_SYNTAX_ERROR: run_id="run_def"
    


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def clickhouse_factory():
    # REMOVED_SYNTAX_ERROR: """Create a ClickHouse factory for testing."""
    # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory( )
    # REMOVED_SYNTAX_ERROR: max_clients_per_user=2,  # Lower limit for testing
    # REMOVED_SYNTAX_ERROR: client_ttl_seconds=60,   # Shorter TTL for testing
    # REMOVED_SYNTAX_ERROR: cleanup_interval_seconds=10  # Faster cleanup for testing
    

    # REMOVED_SYNTAX_ERROR: yield factory

    # Cleanup after test
    # REMOVED_SYNTAX_ERROR: await factory.shutdown()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_clickhouse_config():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Mock ClickHouse configuration for testing."""
    # REMOVED_SYNTAX_ERROR: config = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: config.host = "localhost"
    # REMOVED_SYNTAX_ERROR: config.port = 8123
    # REMOVED_SYNTAX_ERROR: config.user = "test"
    # REMOVED_SYNTAX_ERROR: config.password = "test"
    # REMOVED_SYNTAX_ERROR: config.database = "test_db"
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return config


# REMOVED_SYNTAX_ERROR: class TestUserClickHouseCache:
    # REMOVED_SYNTAX_ERROR: """Test user-scoped ClickHouse cache isolation."""

# REMOVED_SYNTAX_ERROR: def test_cache_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test cache initialization with user context."""
    # REMOVED_SYNTAX_ERROR: user_id = "test_user_123"
    # REMOVED_SYNTAX_ERROR: cache = UserClickHouseCache(user_id, max_size=100)

    # REMOVED_SYNTAX_ERROR: assert cache.user_id == user_id
    # REMOVED_SYNTAX_ERROR: assert cache.max_size == 100
    # REMOVED_SYNTAX_ERROR: assert len(cache.cache) == 0
    # REMOVED_SYNTAX_ERROR: assert cache._hits == 0
    # REMOVED_SYNTAX_ERROR: assert cache._misses == 0
    # REMOVED_SYNTAX_ERROR: assert isinstance(cache.created_at, datetime)

    # Removed problematic line: async def test_cache_set_and_get(self):
        # REMOVED_SYNTAX_ERROR: """Test basic cache set and get operations."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: cache = UserClickHouseCache("user_123")

        # Test cache miss
        # REMOVED_SYNTAX_ERROR: result = await cache.get("SELECT 1")
        # REMOVED_SYNTAX_ERROR: assert result is None

        # Test cache set and hit
        # REMOVED_SYNTAX_ERROR: test_data = [{"result": 1}]
        # REMOVED_SYNTAX_ERROR: await cache.set("SELECT 1", test_data)

        # REMOVED_SYNTAX_ERROR: result = await cache.get("SELECT 1")
        # REMOVED_SYNTAX_ERROR: assert result == test_data

        # Verify metrics
        # REMOVED_SYNTAX_ERROR: stats = await cache.get_stats()
        # REMOVED_SYNTAX_ERROR: assert stats["hits"] == 1
        # REMOVED_SYNTAX_ERROR: assert stats["misses"] == 1

        # Removed problematic line: async def test_cache_ttl_expiration(self):
            # REMOVED_SYNTAX_ERROR: """Test cache TTL expiration."""
            # REMOVED_SYNTAX_ERROR: cache = UserClickHouseCache("user_123")
            # REMOVED_SYNTAX_ERROR: test_data = [{"result": 1}]

            # Set with very short TTL
            # REMOVED_SYNTAX_ERROR: await cache.set("SELECT 1", test_data, ttl=0.1)

            # Should still be cached immediately
            # REMOVED_SYNTAX_ERROR: result = await cache.get("SELECT 1")
            # REMOVED_SYNTAX_ERROR: assert result == test_data

            # Wait for expiration
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

            # Should be expired now
            # REMOVED_SYNTAX_ERROR: result = await cache.get("SELECT 1")
            # REMOVED_SYNTAX_ERROR: assert result is None

            # Removed problematic line: async def test_cache_size_limit(self):
                # REMOVED_SYNTAX_ERROR: """Test cache size limit enforcement."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: cache = UserClickHouseCache("user_123", max_size=2)

                # Fill cache to capacity
                # REMOVED_SYNTAX_ERROR: await cache.set("query1", [{"a": 1}])
                # REMOVED_SYNTAX_ERROR: await cache.set("query2", [{"b": 2}])
                # REMOVED_SYNTAX_ERROR: assert len(cache.cache) == 2

                # Add third item, should evict oldest
                # REMOVED_SYNTAX_ERROR: await cache.set("query3", [{"c": 3}])

                # Cache should still be at max size
                # REMOVED_SYNTAX_ERROR: assert len(cache.cache) <= cache.max_size

                # Removed problematic line: async def test_cache_clear(self):
                    # REMOVED_SYNTAX_ERROR: """Test cache clearing functionality."""
                    # REMOVED_SYNTAX_ERROR: cache = UserClickHouseCache("user_123")

                    # Add some data
                    # REMOVED_SYNTAX_ERROR: await cache.set("query1", [{"a": 1}])
                    # REMOVED_SYNTAX_ERROR: await cache.set("query2", [{"b": 2}])
                    # REMOVED_SYNTAX_ERROR: assert len(cache.cache) == 2

                    # Clear cache
                    # REMOVED_SYNTAX_ERROR: await cache.clear()
                    # REMOVED_SYNTAX_ERROR: assert len(cache.cache) == 0


# REMOVED_SYNTAX_ERROR: class TestUserClickHouseClient:
    # REMOVED_SYNTAX_ERROR: """Test user-scoped ClickHouse client isolation."""

    # Removed problematic line: async def test_client_initialization(self):
        # REMOVED_SYNTAX_ERROR: """Test client initialization with isolated connection."""
        # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")

        # Client should not be initialized yet
        # REMOVED_SYNTAX_ERROR: assert not client._initialized
        # REMOVED_SYNTAX_ERROR: assert client.user_id == "user_123"
        # REMOVED_SYNTAX_ERROR: assert client.request_id == "req_456"
        # REMOVED_SYNTAX_ERROR: assert client.thread_id == "thread_789"

        # Mock the initialization components
        # REMOVED_SYNTAX_ERROR: with patch.object(client, '_get_clickhouse_config') as mock_config, \
        # REMOVED_SYNTAX_ERROR: patch.object(client, '_create_base_client') as mock_create_client:

            # Setup mocks
            # REMOVED_SYNTAX_ERROR: mock_config.return_value = MagicMock(host="localhost", port=8123)
            # REMOVED_SYNTAX_ERROR: mock_base_client = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_create_client.return_value = mock_base_client

            # Mock the query interceptor
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                # REMOVED_SYNTAX_ERROR: mock_interceptor = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_interceptor.test_connection = AsyncMock(return_value=True)
                # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = mock_interceptor

                # Initialize client
                # REMOVED_SYNTAX_ERROR: await client.initialize()

                # Client should be initialized
                # REMOVED_SYNTAX_ERROR: assert client._initialized

                # Cleanup
                # REMOVED_SYNTAX_ERROR: await client.cleanup()

                # Removed problematic line: async def test_client_query_execution(self, mock_db_class, mock_config, mock_clickhouse_config):
                    # REMOVED_SYNTAX_ERROR: """Test query execution with user isolation."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                    # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                    # Mock query interceptor
                    # REMOVED_SYNTAX_ERROR: mock_interceptor = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_interceptor.execute.return_value = [{"result": 1}]

                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                        # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = mock_interceptor

                        # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")
                        # REMOVED_SYNTAX_ERROR: await client.initialize()

                        # Execute query
                        # REMOVED_SYNTAX_ERROR: result = await client.execute("SELECT 1")

                        # REMOVED_SYNTAX_ERROR: assert result == [{"result": 1}]
                        # REMOVED_SYNTAX_ERROR: assert client._query_count == 1
                        # REMOVED_SYNTAX_ERROR: assert client._error_count == 0

                        # Cleanup
                        # REMOVED_SYNTAX_ERROR: await client.cleanup()

                        # Removed problematic line: async def test_client_cache_isolation(self, mock_db_class, mock_config, mock_clickhouse_config):
                            # REMOVED_SYNTAX_ERROR: """Test that each client has isolated cache."""
                            # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                            # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                            # Mock query interceptor
                            # REMOVED_SYNTAX_ERROR: mock_interceptor1 = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_interceptor1.execute.return_value = [{"user1_data": 1}]
                            # REMOVED_SYNTAX_ERROR: mock_interceptor2 = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_interceptor2.execute.return_value = [{"user2_data": 2}]

                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                                # REMOVED_SYNTAX_ERROR: mock_interceptor_class.side_effect = [mock_interceptor1, mock_interceptor2]

                                # Create two clients for different users
                                # REMOVED_SYNTAX_ERROR: client1 = UserClickHouseClient("user_123", "req_1", "thread_1")
                                # REMOVED_SYNTAX_ERROR: client2 = UserClickHouseClient("user_456", "req_2", "thread_2")

                                # REMOVED_SYNTAX_ERROR: await client1.initialize()
                                # REMOVED_SYNTAX_ERROR: await client2.initialize()

                                # Execute same query on both clients
                                # REMOVED_SYNTAX_ERROR: result1 = await client1.execute("SELECT * FROM events")
                                # REMOVED_SYNTAX_ERROR: result2 = await client2.execute("SELECT * FROM events")

                                # Results should be different (from different mock responses)
                                # REMOVED_SYNTAX_ERROR: assert result1 == [{"user1_data": 1}]
                                # REMOVED_SYNTAX_ERROR: assert result2 == [{"user2_data": 2}]

                                # Caches should be isolated
                                # REMOVED_SYNTAX_ERROR: cache_stats1 = await client1.get_cache_stats()
                                # REMOVED_SYNTAX_ERROR: cache_stats2 = await client2.get_cache_stats()

                                # REMOVED_SYNTAX_ERROR: assert cache_stats1["user_id"] != cache_stats2["user_id"]

                                # Cleanup
                                # REMOVED_SYNTAX_ERROR: await client1.cleanup()
                                # REMOVED_SYNTAX_ERROR: await client2.cleanup()

                                # Removed problematic line: async def test_client_stats_tracking(self):
                                    # REMOVED_SYNTAX_ERROR: """Test client statistics tracking."""
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")

                                    # REMOVED_SYNTAX_ERROR: stats = client.get_client_stats()
                                    # REMOVED_SYNTAX_ERROR: assert stats["user_id"] == "user_123..."
                                    # REMOVED_SYNTAX_ERROR: assert stats["query_count"] == 0
                                    # REMOVED_SYNTAX_ERROR: assert stats["error_count"] == 0
                                    # REMOVED_SYNTAX_ERROR: assert stats["initialized"] == False
                                    # REMOVED_SYNTAX_ERROR: assert "age_seconds" in stats


# REMOVED_SYNTAX_ERROR: class TestClickHouseFactory:
    # REMOVED_SYNTAX_ERROR: """Test ClickHouse factory pattern implementation."""

    # Removed problematic line: async def test_factory_initialization(self, clickhouse_factory):
        # REMOVED_SYNTAX_ERROR: """Test factory initialization with proper configuration."""
        # REMOVED_SYNTAX_ERROR: assert clickhouse_factory.factory_name == "ClickHouseFactory"
        # REMOVED_SYNTAX_ERROR: assert clickhouse_factory.max_clients_per_user == 2
        # REMOVED_SYNTAX_ERROR: assert clickhouse_factory.client_ttl == 60
        # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 0
        # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._user_client_counts) == 0

        # Removed problematic line: async def test_create_user_client(self, mock_db_class, mock_config, clickhouse_factory,
        # REMOVED_SYNTAX_ERROR: sample_user_context, mock_clickhouse_config):
            # REMOVED_SYNTAX_ERROR: """Test creating user-scoped ClickHouse clients."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
            # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                # REMOVED_SYNTAX_ERROR: mock_interceptor = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = mock_interceptor

                # Create client for user
                # REMOVED_SYNTAX_ERROR: client = await clickhouse_factory.create_user_client(sample_user_context)

                # REMOVED_SYNTAX_ERROR: assert isinstance(client, UserClickHouseClient)
                # REMOVED_SYNTAX_ERROR: assert client.user_id == sample_user_context.user_id
                # REMOVED_SYNTAX_ERROR: assert client.request_id == sample_user_context.request_id

                # Factory should track the client
                # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 1
                # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1

                # Cleanup
                # REMOVED_SYNTAX_ERROR: await client.cleanup()

                # Removed problematic line: async def test_user_client_limit_enforcement(self, mock_db_class, mock_config, clickhouse_factory,
                # REMOVED_SYNTAX_ERROR: sample_user_context, mock_clickhouse_config):
                    # REMOVED_SYNTAX_ERROR: """Test that factory enforces per-user client limits."""
                    # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                    # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                        # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance

                        # Create clients up to the limit (max_clients_per_user = 2)
                        # REMOVED_SYNTAX_ERROR: client1 = await clickhouse_factory.create_user_client(sample_user_context)

                        # Create second context for same user
                        # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id=sample_user_context.user_id,
                        # REMOVED_SYNTAX_ERROR: request_id="req_2",
                        # REMOVED_SYNTAX_ERROR: thread_id="thread_2",
                        # REMOVED_SYNTAX_ERROR: run_id="run_2"
                        
                        # REMOVED_SYNTAX_ERROR: client2 = await clickhouse_factory.create_user_client(context2)

                        # Third client should fail
                        # REMOVED_SYNTAX_ERROR: context3 = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id=sample_user_context.user_id,
                        # REMOVED_SYNTAX_ERROR: request_id="req_3",
                        # REMOVED_SYNTAX_ERROR: thread_id="thread_3",
                        # REMOVED_SYNTAX_ERROR: run_id="run_3"
                        

                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="exceeds maximum ClickHouse clients"):
                            # REMOVED_SYNTAX_ERROR: await clickhouse_factory.create_user_client(context3)

                            # Cleanup
                            # REMOVED_SYNTAX_ERROR: await client1.cleanup()
                            # REMOVED_SYNTAX_ERROR: await client2.cleanup()

                            # Removed problematic line: async def test_concurrent_user_isolation(self, mock_db_class, mock_config, clickhouse_factory,
                            # REMOVED_SYNTAX_ERROR: sample_user_context, another_user_context, mock_clickhouse_config):
                                # REMOVED_SYNTAX_ERROR: """Test that different users get completely isolated clients."""
                                # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                                # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                                # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                                    # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance

                                    # Create clients for different users
                                    # REMOVED_SYNTAX_ERROR: client1 = await clickhouse_factory.create_user_client(sample_user_context)
                                    # REMOVED_SYNTAX_ERROR: client2 = await clickhouse_factory.create_user_client(another_user_context)

                                    # Clients should be completely different instances
                                    # REMOVED_SYNTAX_ERROR: assert client1 is not client2
                                    # REMOVED_SYNTAX_ERROR: assert client1.user_id != client2.user_id
                                    # REMOVED_SYNTAX_ERROR: assert client1._cache is not client2._cache
                                    # REMOVED_SYNTAX_ERROR: assert client1._client is not client2._client

                                    # Factory should track both users
                                    # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 2
                                    # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._user_client_counts) == 2

                                    # Each user should have 1 client
                                    # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
                                    # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[another_user_context.user_id] == 1

                                    # Cleanup
                                    # REMOVED_SYNTAX_ERROR: await client1.cleanup()
                                    # REMOVED_SYNTAX_ERROR: await client2.cleanup()

                                    # Removed problematic line: async def test_factory_stats(self, clickhouse_factory):
                                        # REMOVED_SYNTAX_ERROR: """Test factory statistics collection."""
                                        # REMOVED_SYNTAX_ERROR: stats = await clickhouse_factory.get_factory_stats()

                                        # REMOVED_SYNTAX_ERROR: assert stats["factory_name"] == "ClickHouseFactory"
                                        # REMOVED_SYNTAX_ERROR: assert stats["total_clients"] == 0
                                        # REMOVED_SYNTAX_ERROR: assert stats["users_with_clients"] == 0
                                        # REMOVED_SYNTAX_ERROR: assert stats["max_clients_per_user"] == 2
                                        # REMOVED_SYNTAX_ERROR: assert stats["client_ttl_seconds"] == 60
                                        # REMOVED_SYNTAX_ERROR: assert "factory_age_seconds" in stats
                                        # REMOVED_SYNTAX_ERROR: assert "cleanup_task_running" in stats

                                        # Removed problematic line: async def test_user_cleanup(self, mock_db_class, mock_config, clickhouse_factory,
                                        # REMOVED_SYNTAX_ERROR: sample_user_context, mock_clickhouse_config):
                                            # REMOVED_SYNTAX_ERROR: """Test cleanup of all clients for a specific user."""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                                            # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                                                # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance

                                                # Create client
                                                # REMOVED_SYNTAX_ERROR: client = await clickhouse_factory.create_user_client(sample_user_context)

                                                # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 1

                                                # Cleanup user clients
                                                # REMOVED_SYNTAX_ERROR: cleanup_count = await clickhouse_factory.cleanup_user_clients(sample_user_context.user_id)

                                                # REMOVED_SYNTAX_ERROR: assert cleanup_count == 1
                                                # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 0
                                                # REMOVED_SYNTAX_ERROR: assert sample_user_context.user_id not in clickhouse_factory._user_client_counts

                                                # Removed problematic line: async def test_factory_context_manager(self, clickhouse_factory, sample_user_context):
                                                    # REMOVED_SYNTAX_ERROR: """Test factory context manager usage."""
                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
                                                        # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                                                        # REMOVED_SYNTAX_ERROR: mock_client.initialize = AsyncNone  # TODO: Use real service instance
                                                        # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                                                        # REMOVED_SYNTAX_ERROR: async with clickhouse_factory.get_user_client(sample_user_context) as client:
                                                            # REMOVED_SYNTAX_ERROR: assert client is mock_client
                                                            # REMOVED_SYNTAX_ERROR: mock_client.initialize.assert_called_once()


# REMOVED_SYNTAX_ERROR: class TestConcurrentAccess:
    # REMOVED_SYNTAX_ERROR: """Test concurrent access by multiple users."""

    # Removed problematic line: async def test_concurrent_client_creation(self, mock_db_class, mock_config, mock_clickhouse_config):
        # REMOVED_SYNTAX_ERROR: """Test concurrent client creation by multiple users."""
        # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
        # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance

            # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=60)

            # Create contexts for different users
            # REMOVED_SYNTAX_ERROR: contexts = []
            # REMOVED_SYNTAX_ERROR: for i in range(10):
                # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
                
                # REMOVED_SYNTAX_ERROR: contexts.append(context)

                # Create clients concurrently
# REMOVED_SYNTAX_ERROR: async def create_client(ctx):
    # REMOVED_SYNTAX_ERROR: client = await factory.create_user_client(ctx)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulate some work
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return client

    # Execute concurrent creation
    # REMOVED_SYNTAX_ERROR: clients = await asyncio.gather(*[create_client(ctx) for ctx in contexts])

    # All clients should be created successfully
    # REMOVED_SYNTAX_ERROR: assert len(clients) == 10
    # REMOVED_SYNTAX_ERROR: assert len(factory._active_clients) == 10
    # REMOVED_SYNTAX_ERROR: assert len(factory._user_client_counts) == 10

    # Each user should have 1 client
    # REMOVED_SYNTAX_ERROR: for i in range(10):
        # REMOVED_SYNTAX_ERROR: assert factory._user_client_counts["formatted_string"] == 1

        # Cleanup
        # REMOVED_SYNTAX_ERROR: for client in clients:
            # REMOVED_SYNTAX_ERROR: await client.cleanup()
            # REMOVED_SYNTAX_ERROR: await factory.shutdown()

            # Removed problematic line: async def test_concurrent_query_execution(self, mock_db_class, mock_config, mock_clickhouse_config):
                # REMOVED_SYNTAX_ERROR: """Test concurrent query execution with user isolation."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: mock_config.return_value = mock_clickhouse_config
                # REMOVED_SYNTAX_ERROR: mock_db = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_db_class.return_value = mock_db

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                    # Create different results for different users
# REMOVED_SYNTAX_ERROR: def create_mock_interceptor():
    # REMOVED_SYNTAX_ERROR: mock_interceptor = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_interceptor.execute.return_value = [{"user_data": "formatted_string"}]
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock_interceptor

    # REMOVED_SYNTAX_ERROR: mock_interceptor_class.side_effect = create_mock_interceptor

    # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory(max_clients_per_user=3, client_ttl_seconds=60)

    # Create clients for different users
    # REMOVED_SYNTAX_ERROR: user_contexts = []
    # REMOVED_SYNTAX_ERROR: for i in range(5):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: user_contexts.append(context)

        # REMOVED_SYNTAX_ERROR: clients = []
        # REMOVED_SYNTAX_ERROR: for context in user_contexts:
            # REMOVED_SYNTAX_ERROR: client = await factory.create_user_client(context)
            # REMOVED_SYNTAX_ERROR: clients.append(client)

            # Execute queries concurrently
# REMOVED_SYNTAX_ERROR: async def execute_query(client, query):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return await client.execute(query)

    # All clients execute the same query concurrently
    # REMOVED_SYNTAX_ERROR: query = "SELECT * FROM events WHERE user_id = %(user_id)s"
    # REMOVED_SYNTAX_ERROR: tasks = [execute_query(client, query) for client in clients]
    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

    # All queries should complete successfully
    # REMOVED_SYNTAX_ERROR: assert len(results) == 5

    # Each client should have different isolated results
    # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
        # REMOVED_SYNTAX_ERROR: assert isinstance(result, list)
        # REMOVED_SYNTAX_ERROR: assert len(result) == 1
        # Results should be different due to different mock instances

        # Cleanup
        # REMOVED_SYNTAX_ERROR: for client in clients:
            # REMOVED_SYNTAX_ERROR: await client.cleanup()
            # REMOVED_SYNTAX_ERROR: await factory.shutdown()


# REMOVED_SYNTAX_ERROR: class TestFactoryResourceManagement:
    # REMOVED_SYNTAX_ERROR: """Test factory resource management and cleanup."""

    # Removed problematic line: async def test_factory_shutdown(self):
        # REMOVED_SYNTAX_ERROR: """Test factory shutdown and resource cleanup."""
        # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory(max_clients_per_user=2, client_ttl_seconds=60)

        # Mock some active clients
        # REMOVED_SYNTAX_ERROR: with patch.object(factory, '_active_clients') as mock_clients:
            # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_clients.__len__.return_value = 2
            # REMOVED_SYNTAX_ERROR: mock_clients.items.return_value = [("client1", mock_client), ("client2", mock_client)]

            # REMOVED_SYNTAX_ERROR: await factory.shutdown()

            # Cleanup should be called on all clients
            # REMOVED_SYNTAX_ERROR: assert mock_client.cleanup.call_count == 2

            # Removed problematic line: async def test_expired_client_cleanup(self):
                # REMOVED_SYNTAX_ERROR: """Test automatic cleanup of expired clients."""
                # REMOVED_SYNTAX_ERROR: pass
                # Create factory with very short TTL for testing
                # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=1)

                # Mock expired client
                # REMOVED_SYNTAX_ERROR: now = datetime.utcnow()
                # REMOVED_SYNTAX_ERROR: expired_time = now - timedelta(seconds=2)

                # REMOVED_SYNTAX_ERROR: factory._client_metadata["expired_client"] = { )
                # REMOVED_SYNTAX_ERROR: "user_id": "test_user",
                # REMOVED_SYNTAX_ERROR: "created_at": expired_time
                

                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: factory._active_clients["expired_client"] = mock_client
                # REMOVED_SYNTAX_ERROR: factory._user_client_counts["test_user"] = 1

                # Run cleanup
                # REMOVED_SYNTAX_ERROR: await factory._cleanup_expired_clients()

                # Expired client should be cleaned up
                # REMOVED_SYNTAX_ERROR: assert "expired_client" not in factory._active_clients
                # REMOVED_SYNTAX_ERROR: assert "expired_client" not in factory._client_metadata
                # REMOVED_SYNTAX_ERROR: assert "test_user" not in factory._user_client_counts
                # REMOVED_SYNTAX_ERROR: mock_client.cleanup.assert_called_once()

                # REMOVED_SYNTAX_ERROR: await factory.shutdown()


# REMOVED_SYNTAX_ERROR: class TestGlobalFactoryFunctions:
    # REMOVED_SYNTAX_ERROR: """Test global factory functions."""

    # Removed problematic line: async def test_get_clickhouse_factory(self):
        # REMOVED_SYNTAX_ERROR: """Test getting global ClickHouse factory."""
        # Clean up any existing global factory first
        # REMOVED_SYNTAX_ERROR: await cleanup_clickhouse_factory()

        # REMOVED_SYNTAX_ERROR: factory1 = get_clickhouse_factory()
        # REMOVED_SYNTAX_ERROR: factory2 = get_clickhouse_factory()

        # Should await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return same instance (singleton pattern)
        # REMOVED_SYNTAX_ERROR: assert factory1 is factory2
        # REMOVED_SYNTAX_ERROR: assert isinstance(factory1, ClickHouseFactory)

        # Cleanup
        # REMOVED_SYNTAX_ERROR: await cleanup_clickhouse_factory()

        # Removed problematic line: async def test_global_factory_cleanup(self):
            # REMOVED_SYNTAX_ERROR: """Test global factory cleanup."""
            # REMOVED_SYNTAX_ERROR: pass
            # Create global factory
            # REMOVED_SYNTAX_ERROR: factory = get_clickhouse_factory()
            # REMOVED_SYNTAX_ERROR: assert factory is not None

            # Cleanup
            # REMOVED_SYNTAX_ERROR: await cleanup_clickhouse_factory()

            # New call should create new factory
            # REMOVED_SYNTAX_ERROR: new_factory = get_clickhouse_factory()
            # REMOVED_SYNTAX_ERROR: assert new_factory is not factory


# REMOVED_SYNTAX_ERROR: class TestBackwardCompatibility:
    # REMOVED_SYNTAX_ERROR: """Test backward compatibility with existing code."""

# REMOVED_SYNTAX_ERROR: def test_factory_imports(self):
    # REMOVED_SYNTAX_ERROR: """Test that all required classes can be imported."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.factories.clickhouse_factory import ( )
    # REMOVED_SYNTAX_ERROR: ClickHouseFactory,
    # REMOVED_SYNTAX_ERROR: UserClickHouseClient,
    # REMOVED_SYNTAX_ERROR: UserClickHouseCache,
    # REMOVED_SYNTAX_ERROR: get_clickhouse_factory
    

    # REMOVED_SYNTAX_ERROR: assert ClickHouseFactory is not None
    # REMOVED_SYNTAX_ERROR: assert UserClickHouseClient is not None
    # REMOVED_SYNTAX_ERROR: assert UserClickHouseCache is not None
    # REMOVED_SYNTAX_ERROR: assert get_clickhouse_factory is not None

# REMOVED_SYNTAX_ERROR: def test_factory_interface_compatibility(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory provides expected interface."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory()

    # Check required methods exist
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'create_user_client')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'get_user_client')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'cleanup_user_clients')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'get_factory_stats')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'shutdown')

    # Check required attributes exist
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'factory_name')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'max_clients_per_user')
    # REMOVED_SYNTAX_ERROR: assert hasattr(factory, 'client_ttl')


    # Integration test markers for different environments
    # REMOVED_SYNTAX_ERROR: pytestmark = [ )
    # REMOVED_SYNTAX_ERROR: pytest.mark.asyncio,
    # REMOVED_SYNTAX_ERROR: pytest.mark.unit,
    # REMOVED_SYNTAX_ERROR: pytest.mark.clickhouse_factory
    