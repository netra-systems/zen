# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Simplified Tests for ClickHouse Factory Pattern Implementation

# REMOVED_SYNTAX_ERROR: This test suite focuses on the essential functionality of the ClickHouse Factory:
    # REMOVED_SYNTAX_ERROR: - User isolation at the cache and client level
    # REMOVED_SYNTAX_ERROR: - Factory pattern implementation
    # REMOVED_SYNTAX_ERROR: - Resource management and cleanup
    # REMOVED_SYNTAX_ERROR: - Thread-safe concurrent access

    # REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
        # REMOVED_SYNTAX_ERROR: - Segment: ALL (Free → Enterprise)
        # REMOVED_SYNTAX_ERROR: - Business Goal: Ensure enterprise-grade data isolation
        # REMOVED_SYNTAX_ERROR: - Value Impact: Zero risk of cross-user data contamination
        # REMOVED_SYNTAX_ERROR: - Revenue Impact: Critical for Enterprise revenue, prevents security incidents
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from datetime import datetime
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


# REMOVED_SYNTAX_ERROR: class TestUserClickHouseCache:
    # REMOVED_SYNTAX_ERROR: """Test user-scoped ClickHouse cache isolation."""

# REMOVED_SYNTAX_ERROR: def test_cache_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Test cache initialization with user context."""
    # REMOVED_SYNTAX_ERROR: pass
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

        # Removed problematic line: async def test_cache_user_isolation(self):
            # REMOVED_SYNTAX_ERROR: """Test that different users have isolated caches."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: cache1 = UserClickHouseCache("user_123")
            # REMOVED_SYNTAX_ERROR: cache2 = UserClickHouseCache("user_456")

            # Set data in first cache
            # REMOVED_SYNTAX_ERROR: await cache1.set("SELECT 1", [{"user1": "data"}])

            # Second cache should not see the data
            # REMOVED_SYNTAX_ERROR: result = await cache2.get("SELECT 1")
            # REMOVED_SYNTAX_ERROR: assert result is None

            # Set different data in second cache
            # REMOVED_SYNTAX_ERROR: await cache2.set("SELECT 1", [{"user2": "data"}])

            # Caches should have different data
            # REMOVED_SYNTAX_ERROR: result1 = await cache1.get("SELECT 1")
            # REMOVED_SYNTAX_ERROR: result2 = await cache2.get("SELECT 1")

            # REMOVED_SYNTAX_ERROR: assert result1 == [{"user1": "data"}]
            # REMOVED_SYNTAX_ERROR: assert result2 == [{"user2": "data"}]


# REMOVED_SYNTAX_ERROR: class TestUserClickHouseClient:
    # REMOVED_SYNTAX_ERROR: """Test user-scoped ClickHouse client isolation."""

# REMOVED_SYNTAX_ERROR: def test_client_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test client creation with proper user context."""
    # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")

    # REMOVED_SYNTAX_ERROR: assert client.user_id == "user_123"
    # REMOVED_SYNTAX_ERROR: assert client.request_id == "req_456"
    # REMOVED_SYNTAX_ERROR: assert client.thread_id == "thread_789"
    # REMOVED_SYNTAX_ERROR: assert not client._initialized
    # REMOVED_SYNTAX_ERROR: assert isinstance(client._cache, UserClickHouseCache)
    # REMOVED_SYNTAX_ERROR: assert client._cache.user_id == "user_123"

    # Removed problematic line: async def test_client_initialization(self):
        # REMOVED_SYNTAX_ERROR: """Test client initialization with mocked components."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")

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

                # REMOVED_SYNTAX_ERROR: assert client._initialized
                # REMOVED_SYNTAX_ERROR: assert client._client is mock_interceptor

                # Cleanup
                # REMOVED_SYNTAX_ERROR: await client.cleanup()
                # REMOVED_SYNTAX_ERROR: assert not client._initialized

                # Removed problematic line: async def test_client_query_execution_with_cache(self):
                    # REMOVED_SYNTAX_ERROR: """Test query execution with user-scoped caching."""
                    # REMOVED_SYNTAX_ERROR: client = UserClickHouseClient("user_123", "req_456", "thread_789")

                    # Mock initialization
                    # REMOVED_SYNTAX_ERROR: with patch.object(client, '_get_clickhouse_config'), \
                    # REMOVED_SYNTAX_ERROR: patch.object(client, '_create_base_client'):

                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                            # REMOVED_SYNTAX_ERROR: mock_interceptor = AsyncNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: mock_interceptor.test_connection = AsyncMock(return_value=True)
                            # REMOVED_SYNTAX_ERROR: mock_interceptor.execute = AsyncMock(return_value=[{"result": 42}])
                            # REMOVED_SYNTAX_ERROR: mock_interceptor_class.return_value = mock_interceptor

                            # REMOVED_SYNTAX_ERROR: await client.initialize()

                            # First query should hit the database
                            # REMOVED_SYNTAX_ERROR: result1 = await client.execute("SELECT 1")
                            # REMOVED_SYNTAX_ERROR: assert result1 == [{"result": 42}]
                            # REMOVED_SYNTAX_ERROR: assert mock_interceptor.execute.call_count == 1

                            # Second identical query should hit cache
                            # REMOVED_SYNTAX_ERROR: result2 = await client.execute("SELECT 1")
                            # REMOVED_SYNTAX_ERROR: assert result2 == [{"result": 42}]
                            # Should still be 1 call to database (cached)
                            # REMOVED_SYNTAX_ERROR: assert mock_interceptor.execute.call_count == 1

                            # Cache stats should show hit
                            # REMOVED_SYNTAX_ERROR: cache_stats = await client.get_cache_stats()
                            # REMOVED_SYNTAX_ERROR: assert cache_stats["hits"] == 1
                            # REMOVED_SYNTAX_ERROR: assert cache_stats["misses"] == 1

                            # REMOVED_SYNTAX_ERROR: await client.cleanup()

# REMOVED_SYNTAX_ERROR: def test_client_stats_tracking(self):
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

        # Removed problematic line: async def test_create_user_client(self, clickhouse_factory, sample_user_context):
            # REMOVED_SYNTAX_ERROR: """Test creating user-scoped ClickHouse clients."""
            # REMOVED_SYNTAX_ERROR: pass
            # Mock the client initialization to avoid real connections
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client.user_id = sample_user_context.user_id
                # REMOVED_SYNTAX_ERROR: mock_client.request_id = sample_user_context.request_id
                # REMOVED_SYNTAX_ERROR: mock_client.initialize = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                # Create client for user
                # REMOVED_SYNTAX_ERROR: client = await clickhouse_factory.create_user_client(sample_user_context)

                # REMOVED_SYNTAX_ERROR: assert client is mock_client
                # REMOVED_SYNTAX_ERROR: mock_client.initialize.assert_called_once()

                # Factory should track the client
                # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 1
                # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1

                # Removed problematic line: async def test_user_client_limit_enforcement(self, clickhouse_factory, sample_user_context):
                    # REMOVED_SYNTAX_ERROR: """Test that factory enforces per-user client limits."""
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
                        # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = lambda x: None AsyncNone  # TODO: Use real service instance

                        # Disable cleanup during this test to ensure limit enforcement
                        # REMOVED_SYNTAX_ERROR: with patch.object(clickhouse_factory, '_cleanup_user_clients') as mock_cleanup:
                            # REMOVED_SYNTAX_ERROR: mock_cleanup.return_value = 0  # No clients cleaned up

                            # Create clients up to the limit (max_clients_per_user = 2)
                            # REMOVED_SYNTAX_ERROR: client1 = await clickhouse_factory.create_user_client(sample_user_context)

                            # Create second context for same user
                            # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: user_id=sample_user_context.user_id,
                            # REMOVED_SYNTAX_ERROR: request_id="req_2",
                            # REMOVED_SYNTAX_ERROR: thread_id="thread_2",
                            # REMOVED_SYNTAX_ERROR: run_id="run_2"
                            
                            # REMOVED_SYNTAX_ERROR: client2 = await clickhouse_factory.create_user_client(context2)

                            # Verify we have 2 clients for this user
                            # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 2
                            # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 2

                            # Third client should fail
                            # REMOVED_SYNTAX_ERROR: context3 = UserExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: user_id=sample_user_context.user_id,
                            # REMOVED_SYNTAX_ERROR: request_id="req_3",
                            # REMOVED_SYNTAX_ERROR: thread_id="thread_3",
                            # REMOVED_SYNTAX_ERROR: run_id="run_3"
                            

                            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="exceeds maximum ClickHouse clients"):
                                # REMOVED_SYNTAX_ERROR: await clickhouse_factory.create_user_client(context3)

                                # Removed problematic line: async def test_concurrent_user_isolation(self, clickhouse_factory, sample_user_context, another_user_context):
                                    # REMOVED_SYNTAX_ERROR: """Test that different users get completely isolated clients."""
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
# REMOVED_SYNTAX_ERROR: def create_mock_client(*args):
    # REMOVED_SYNTAX_ERROR: mock = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock.user_id = args[0]  # user_id is first argument
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock

    # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = create_mock_client

    # Create clients for different users
    # REMOVED_SYNTAX_ERROR: client1 = await clickhouse_factory.create_user_client(sample_user_context)
    # REMOVED_SYNTAX_ERROR: client2 = await clickhouse_factory.create_user_client(another_user_context)

    # Clients should be completely different instances
    # REMOVED_SYNTAX_ERROR: assert client1 is not client2
    # REMOVED_SYNTAX_ERROR: assert client1.user_id != client2.user_id

    # Factory should track both users
    # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._active_clients) == 2
    # REMOVED_SYNTAX_ERROR: assert len(clickhouse_factory._user_client_counts) == 2

    # Each user should have 1 client
    # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
    # REMOVED_SYNTAX_ERROR: assert clickhouse_factory._user_client_counts[another_user_context.user_id] == 1

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

        # Removed problematic line: async def test_factory_context_manager(self, clickhouse_factory, sample_user_context):
            # REMOVED_SYNTAX_ERROR: """Test factory context manager usage."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
                # REMOVED_SYNTAX_ERROR: mock_client = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client.initialize = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_client_class.return_value = mock_client

                # REMOVED_SYNTAX_ERROR: async with clickhouse_factory.get_user_client(sample_user_context) as client:
                    # REMOVED_SYNTAX_ERROR: assert client is mock_client
                    # REMOVED_SYNTAX_ERROR: mock_client.initialize.assert_called_once()


# REMOVED_SYNTAX_ERROR: class TestConcurrentAccess:
    # REMOVED_SYNTAX_ERROR: """Test concurrent access by multiple users."""

    # Removed problematic line: async def test_concurrent_client_creation(self):
        # REMOVED_SYNTAX_ERROR: """Test concurrent client creation by multiple users."""
        # REMOVED_SYNTAX_ERROR: factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=60)

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
# REMOVED_SYNTAX_ERROR: def create_mock_client(*args):
    # REMOVED_SYNTAX_ERROR: mock = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock.user_id = args[0]  # user_id is first argument
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock

    # REMOVED_SYNTAX_ERROR: mock_client_class.side_effect = create_mock_client

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
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Simulate some work
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


    # Test markers for different environments
    # REMOVED_SYNTAX_ERROR: pytestmark = [ )
    # REMOVED_SYNTAX_ERROR: pytest.mark.asyncio,
    # REMOVED_SYNTAX_ERROR: pytest.mark.unit
    