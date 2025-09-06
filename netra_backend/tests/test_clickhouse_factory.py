"""
Comprehensive Tests for ClickHouse Factory Pattern Implementation

This test suite validates the ClickHouse Factory pattern implementation ensuring:
- Complete user isolation at the database client level
- Proper connection pooling and resource management per user
- Thread-safe concurrent access by multiple users
- Resource cleanup and connection lifecycle management
- Cache isolation and data protection between users
- Factory pattern compliance with USER_CONTEXT_ARCHITECTURE.md

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure enterprise-grade data isolation
- Value Impact: Zero risk of cross-user data contamination
- Revenue Impact: Critical for Enterprise revenue, prevents security incidents
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, List
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.factories.clickhouse_factory import (
    ClickHouseFactory,
    UserClickHouseClient,
    UserClickHouseCache,
    get_clickhouse_factory,
    cleanup_clickhouse_factory
)
from netra_backend.app.models.user_execution_context import UserExecutionContext


@pytest.fixture
def sample_user_context():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a sample user execution context for testing."""
    pass
    return UserExecutionContext(
        user_id="test_user_123",
        request_id="req_456", 
        thread_id="thread_789",
        run_id="run_abc"
    )


@pytest.fixture
def another_user_context():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create another user execution context for isolation testing."""
    pass
    return UserExecutionContext(
        user_id="test_user_456",
        request_id="req_789",
        thread_id="thread_123", 
        run_id="run_def"
    )


@pytest.fixture
async def clickhouse_factory():
    """Create a ClickHouse factory for testing."""
    factory = ClickHouseFactory(
        max_clients_per_user=2,  # Lower limit for testing
        client_ttl_seconds=60,   # Shorter TTL for testing
        cleanup_interval_seconds=10  # Faster cleanup for testing
    )
    
    yield factory
    
    # Cleanup after test
    await factory.shutdown()


@pytest.fixture
 def real_clickhouse_config():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
    """Mock ClickHouse configuration for testing."""
    config = MagicNone  # TODO: Use real service instance
    config.host = "localhost"
    config.port = 8123
    config.user = "test"
    config.password = "test"
    config.database = "test_db"
    await asyncio.sleep(0)
    return config


class TestUserClickHouseCache:
    """Test user-scoped ClickHouse cache isolation."""
    
    def test_cache_initialization(self):
        """Test cache initialization with user context."""
        user_id = "test_user_123"
        cache = UserClickHouseCache(user_id, max_size=100)
        
        assert cache.user_id == user_id
        assert cache.max_size == 100
        assert len(cache.cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0
        assert isinstance(cache.created_at, datetime)
    
    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
    pass
        cache = UserClickHouseCache("user_123")
        
        # Test cache miss
        result = await cache.get("SELECT 1")
        assert result is None
        
        # Test cache set and hit
        test_data = [{"result": 1}]
        await cache.set("SELECT 1", test_data)
        
        result = await cache.get("SELECT 1")
        assert result == test_data
        
        # Verify metrics
        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    async def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = UserClickHouseCache("user_123")
        test_data = [{"result": 1}]
        
        # Set with very short TTL
        await cache.set("SELECT 1", test_data, ttl=0.1)
        
        # Should still be cached immediately
        result = await cache.get("SELECT 1")
        assert result == test_data
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired now
        result = await cache.get("SELECT 1")
        assert result is None
    
    async def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
    pass
        cache = UserClickHouseCache("user_123", max_size=2)
        
        # Fill cache to capacity
        await cache.set("query1", [{"a": 1}])
        await cache.set("query2", [{"b": 2}])
        assert len(cache.cache) == 2
        
        # Add third item, should evict oldest
        await cache.set("query3", [{"c": 3}])
        
        # Cache should still be at max size
        assert len(cache.cache) <= cache.max_size
    
    async def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = UserClickHouseCache("user_123")
        
        # Add some data
        await cache.set("query1", [{"a": 1}])
        await cache.set("query2", [{"b": 2}])
        assert len(cache.cache) == 2
        
        # Clear cache
        await cache.clear()
        assert len(cache.cache) == 0


class TestUserClickHouseClient:
    """Test user-scoped ClickHouse client isolation."""
    
    async def test_client_initialization(self):
        """Test client initialization with isolated connection."""
        client = UserClickHouseClient("user_123", "req_456", "thread_789")
        
        # Client should not be initialized yet
        assert not client._initialized
        assert client.user_id == "user_123"
        assert client.request_id == "req_456"
        assert client.thread_id == "thread_789"
        
        # Mock the initialization components
        with patch.object(client, '_get_clickhouse_config') as mock_config, \
             patch.object(client, '_create_base_client') as mock_create_client:
            
            # Setup mocks
            mock_config.return_value = MagicMock(host="localhost", port=8123)
            mock_base_client = AsyncNone  # TODO: Use real service instance
            mock_create_client.return_value = mock_base_client
            
            # Mock the query interceptor
            with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                mock_interceptor = AsyncNone  # TODO: Use real service instance
                mock_interceptor.test_connection = AsyncMock(return_value=True)
                mock_interceptor_class.return_value = mock_interceptor
                
                # Initialize client
                await client.initialize()
                
                # Client should be initialized
                assert client._initialized
                
                # Cleanup
                await client.cleanup()
    
            async def test_client_query_execution(self, mock_db_class, mock_config, mock_clickhouse_config):
        """Test query execution with user isolation."""
    pass
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        # Mock query interceptor
        mock_interceptor = AsyncNone  # TODO: Use real service instance
        mock_interceptor.execute.return_value = [{"result": 1}]
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.return_value = mock_interceptor
            
            client = UserClickHouseClient("user_123", "req_456", "thread_789")
            await client.initialize()
            
            # Execute query
            result = await client.execute("SELECT 1")
            
            assert result == [{"result": 1}]
            assert client._query_count == 1
            assert client._error_count == 0
            
            # Cleanup
            await client.cleanup()
    
            async def test_client_cache_isolation(self, mock_db_class, mock_config, mock_clickhouse_config):
        """Test that each client has isolated cache."""
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        # Mock query interceptor
        mock_interceptor1 = AsyncNone  # TODO: Use real service instance
        mock_interceptor1.execute.return_value = [{"user1_data": 1}]
        mock_interceptor2 = AsyncNone  # TODO: Use real service instance  
        mock_interceptor2.execute.return_value = [{"user2_data": 2}]
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.side_effect = [mock_interceptor1, mock_interceptor2]
            
            # Create two clients for different users
            client1 = UserClickHouseClient("user_123", "req_1", "thread_1")
            client2 = UserClickHouseClient("user_456", "req_2", "thread_2")
            
            await client1.initialize()
            await client2.initialize()
            
            # Execute same query on both clients
            result1 = await client1.execute("SELECT * FROM events")
            result2 = await client2.execute("SELECT * FROM events")
            
            # Results should be different (from different mock responses)
            assert result1 == [{"user1_data": 1}]
            assert result2 == [{"user2_data": 2}]
            
            # Caches should be isolated
            cache_stats1 = await client1.get_cache_stats()
            cache_stats2 = await client2.get_cache_stats()
            
            assert cache_stats1["user_id"] != cache_stats2["user_id"]
            
            # Cleanup
            await client1.cleanup()
            await client2.cleanup()
    
    async def test_client_stats_tracking(self):
        """Test client statistics tracking."""
    pass
        client = UserClickHouseClient("user_123", "req_456", "thread_789")
        
        stats = client.get_client_stats()
        assert stats["user_id"] == "user_123..."
        assert stats["query_count"] == 0
        assert stats["error_count"] == 0
        assert stats["initialized"] == False
        assert "age_seconds" in stats


class TestClickHouseFactory:
    """Test ClickHouse factory pattern implementation."""
    
    async def test_factory_initialization(self, clickhouse_factory):
        """Test factory initialization with proper configuration."""
        assert clickhouse_factory.factory_name == "ClickHouseFactory"
        assert clickhouse_factory.max_clients_per_user == 2
        assert clickhouse_factory.client_ttl == 60
        assert len(clickhouse_factory._active_clients) == 0
        assert len(clickhouse_factory._user_client_counts) == 0
    
            async def test_create_user_client(self, mock_db_class, mock_config, clickhouse_factory, 
                                     sample_user_context, mock_clickhouse_config):
        """Test creating user-scoped ClickHouse clients."""
    pass
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor = AsyncNone  # TODO: Use real service instance
            mock_interceptor_class.return_value = mock_interceptor
            
            # Create client for user
            client = await clickhouse_factory.create_user_client(sample_user_context)
            
            assert isinstance(client, UserClickHouseClient)
            assert client.user_id == sample_user_context.user_id
            assert client.request_id == sample_user_context.request_id
            
            # Factory should track the client
            assert len(clickhouse_factory._active_clients) == 1
            assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
            
            # Cleanup
            await client.cleanup()
    
            async def test_user_client_limit_enforcement(self, mock_db_class, mock_config, clickhouse_factory,
                                                sample_user_context, mock_clickhouse_config):
        """Test that factory enforces per-user client limits."""
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance
            
            # Create clients up to the limit (max_clients_per_user = 2)
            client1 = await clickhouse_factory.create_user_client(sample_user_context)
            
            # Create second context for same user
            context2 = UserExecutionContext(
                user_id=sample_user_context.user_id,
                request_id="req_2",
                thread_id="thread_2",
                run_id="run_2"
            )
            client2 = await clickhouse_factory.create_user_client(context2)
            
            # Third client should fail
            context3 = UserExecutionContext(
                user_id=sample_user_context.user_id,
                request_id="req_3",
                thread_id="thread_3", 
                run_id="run_3"
            )
            
            with pytest.raises(ValueError, match="exceeds maximum ClickHouse clients"):
                await clickhouse_factory.create_user_client(context3)
            
            # Cleanup
            await client1.cleanup()
            await client2.cleanup()
    
            async def test_concurrent_user_isolation(self, mock_db_class, mock_config, clickhouse_factory,
                                           sample_user_context, another_user_context, mock_clickhouse_config):
        """Test that different users get completely isolated clients."""
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance
            
            # Create clients for different users
            client1 = await clickhouse_factory.create_user_client(sample_user_context)
            client2 = await clickhouse_factory.create_user_client(another_user_context)
            
            # Clients should be completely different instances
            assert client1 is not client2
            assert client1.user_id != client2.user_id
            assert client1._cache is not client2._cache
            assert client1._client is not client2._client
            
            # Factory should track both users
            assert len(clickhouse_factory._active_clients) == 2
            assert len(clickhouse_factory._user_client_counts) == 2
            
            # Each user should have 1 client
            assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
            assert clickhouse_factory._user_client_counts[another_user_context.user_id] == 1
            
            # Cleanup
            await client1.cleanup()
            await client2.cleanup()
    
    async def test_factory_stats(self, clickhouse_factory):
        """Test factory statistics collection."""
        stats = await clickhouse_factory.get_factory_stats()
        
        assert stats["factory_name"] == "ClickHouseFactory"
        assert stats["total_clients"] == 0
        assert stats["users_with_clients"] == 0
        assert stats["max_clients_per_user"] == 2
        assert stats["client_ttl_seconds"] == 60
        assert "factory_age_seconds" in stats
        assert "cleanup_task_running" in stats
    
            async def test_user_cleanup(self, mock_db_class, mock_config, clickhouse_factory,
                               sample_user_context, mock_clickhouse_config):
        """Test cleanup of all clients for a specific user."""
    pass
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance
            
            # Create client
            client = await clickhouse_factory.create_user_client(sample_user_context)
            
            assert len(clickhouse_factory._active_clients) == 1
            
            # Cleanup user clients
            cleanup_count = await clickhouse_factory.cleanup_user_clients(sample_user_context.user_id)
            
            assert cleanup_count == 1
            assert len(clickhouse_factory._active_clients) == 0
            assert sample_user_context.user_id not in clickhouse_factory._user_client_counts
    
    async def test_factory_context_manager(self, clickhouse_factory, sample_user_context):
        """Test factory context manager usage."""
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize = AsyncNone  # TODO: Use real service instance
            mock_client_class.return_value = mock_client
            
            async with clickhouse_factory.get_user_client(sample_user_context) as client:
                assert client is mock_client
                mock_client.initialize.assert_called_once()


class TestConcurrentAccess:
    """Test concurrent access by multiple users."""
    
            async def test_concurrent_client_creation(self, mock_db_class, mock_config, mock_clickhouse_config):
        """Test concurrent client creation by multiple users."""
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            mock_interceptor_class.return_value = AsyncNone  # TODO: Use real service instance
            
            factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=60)
            
            # Create contexts for different users
            contexts = []
            for i in range(10):
                context = UserExecutionContext(
                    user_id=f"user_{i}",
                    request_id=f"req_{i}",
                    thread_id=f"thread_{i}",
                    run_id=f"run_{i}"
                )
                contexts.append(context)
            
            # Create clients concurrently
            async def create_client(ctx):
                client = await factory.create_user_client(ctx)
                await asyncio.sleep(0.1)  # Simulate some work
                await asyncio.sleep(0)
    return client
            
            # Execute concurrent creation
            clients = await asyncio.gather(*[create_client(ctx) for ctx in contexts])
            
            # All clients should be created successfully
            assert len(clients) == 10
            assert len(factory._active_clients) == 10
            assert len(factory._user_client_counts) == 10
            
            # Each user should have 1 client
            for i in range(10):
                assert factory._user_client_counts[f"user_{i}"] == 1
            
            # Cleanup
            for client in clients:
                await client.cleanup()
            await factory.shutdown()
    
            async def test_concurrent_query_execution(self, mock_db_class, mock_config, mock_clickhouse_config):
        """Test concurrent query execution with user isolation."""
    pass
        mock_config.return_value = mock_clickhouse_config
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db_class.return_value = mock_db
        
        with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
            # Create different results for different users
            def create_mock_interceptor():
                mock_interceptor = AsyncNone  # TODO: Use real service instance
    pass
                mock_interceptor.execute.return_value = [{"user_data": f"user_{id(mock_interceptor)}"}]
                await asyncio.sleep(0)
    return mock_interceptor
            
            mock_interceptor_class.side_effect = create_mock_interceptor
            
            factory = ClickHouseFactory(max_clients_per_user=3, client_ttl_seconds=60)
            
            # Create clients for different users
            user_contexts = []
            for i in range(5):
                context = UserExecutionContext(
                    user_id=f"concurrent_user_{i}",
                    request_id=f"req_{i}",
                    thread_id=f"thread_{i}",
                    run_id=f"run_{i}"
                )
                user_contexts.append(context)
            
            clients = []
            for context in user_contexts:
                client = await factory.create_user_client(context)
                clients.append(client)
            
            # Execute queries concurrently
            async def execute_query(client, query):
    pass
                await asyncio.sleep(0)
    return await client.execute(query)
            
            # All clients execute the same query concurrently
            query = "SELECT * FROM events WHERE user_id = %(user_id)s"
            tasks = [execute_query(client, query) for client in clients]
            results = await asyncio.gather(*tasks)
            
            # All queries should complete successfully
            assert len(results) == 5
            
            # Each client should have different isolated results
            for i, result in enumerate(results):
                assert isinstance(result, list)
                assert len(result) == 1
                # Results should be different due to different mock instances
            
            # Cleanup
            for client in clients:
                await client.cleanup()
            await factory.shutdown()


class TestFactoryResourceManagement:
    """Test factory resource management and cleanup."""
    
    async def test_factory_shutdown(self):
        """Test factory shutdown and resource cleanup."""
        factory = ClickHouseFactory(max_clients_per_user=2, client_ttl_seconds=60)
        
        # Mock some active clients
        with patch.object(factory, '_active_clients') as mock_clients:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_clients.__len__.return_value = 2
            mock_clients.items.return_value = [("client1", mock_client), ("client2", mock_client)]
            
            await factory.shutdown()
            
            # Cleanup should be called on all clients
            assert mock_client.cleanup.call_count == 2
    
    async def test_expired_client_cleanup(self):
        """Test automatic cleanup of expired clients."""
    pass
        # Create factory with very short TTL for testing
        factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=1)
        
        # Mock expired client
        now = datetime.utcnow()
        expired_time = now - timedelta(seconds=2)
        
        factory._client_metadata["expired_client"] = {
            "user_id": "test_user",
            "created_at": expired_time
        }
        
        mock_client = AsyncNone  # TODO: Use real service instance
        factory._active_clients["expired_client"] = mock_client
        factory._user_client_counts["test_user"] = 1
        
        # Run cleanup
        await factory._cleanup_expired_clients()
        
        # Expired client should be cleaned up
        assert "expired_client" not in factory._active_clients
        assert "expired_client" not in factory._client_metadata
        assert "test_user" not in factory._user_client_counts
        mock_client.cleanup.assert_called_once()
        
        await factory.shutdown()


class TestGlobalFactoryFunctions:
    """Test global factory functions."""
    
    async def test_get_clickhouse_factory(self):
        """Test getting global ClickHouse factory."""
        # Clean up any existing global factory first
        await cleanup_clickhouse_factory()
        
        factory1 = get_clickhouse_factory()
        factory2 = get_clickhouse_factory()
        
        # Should await asyncio.sleep(0)
    return same instance (singleton pattern)
        assert factory1 is factory2
        assert isinstance(factory1, ClickHouseFactory)
        
        # Cleanup
        await cleanup_clickhouse_factory()
    
    async def test_global_factory_cleanup(self):
        """Test global factory cleanup."""
    pass
        # Create global factory
        factory = get_clickhouse_factory()
        assert factory is not None
        
        # Cleanup
        await cleanup_clickhouse_factory()
        
        # New call should create new factory
        new_factory = get_clickhouse_factory()
        assert new_factory is not factory


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_factory_imports(self):
        """Test that all required classes can be imported."""
        from netra_backend.app.factories.clickhouse_factory import (
            ClickHouseFactory,
            UserClickHouseClient,
            UserClickHouseCache,
            get_clickhouse_factory
        )
        
        assert ClickHouseFactory is not None
        assert UserClickHouseClient is not None
        assert UserClickHouseCache is not None
        assert get_clickhouse_factory is not None
    
    def test_factory_interface_compatibility(self):
        """Test that factory provides expected interface."""
    pass
        factory = ClickHouseFactory()
        
        # Check required methods exist
        assert hasattr(factory, 'create_user_client')
        assert hasattr(factory, 'get_user_client')
        assert hasattr(factory, 'cleanup_user_clients')
        assert hasattr(factory, 'get_factory_stats')
        assert hasattr(factory, 'shutdown')
        
        # Check required attributes exist
        assert hasattr(factory, 'factory_name')
        assert hasattr(factory, 'max_clients_per_user')
        assert hasattr(factory, 'client_ttl')


# Integration test markers for different environments
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.unit,
    pytest.mark.clickhouse_factory
]