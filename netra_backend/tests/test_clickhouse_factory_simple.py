"""
Simplified Tests for ClickHouse Factory Pattern Implementation

This test suite focuses on the essential functionality of the ClickHouse Factory:
- User isolation at the cache and client level
- Factory pattern implementation
- Resource management and cleanup
- Thread-safe concurrent access

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure enterprise-grade data isolation
- Value Impact: Zero risk of cross-user data contamination
- Revenue Impact: Critical for Enterprise revenue, prevents security incidents
"""

import asyncio
import pytest
from datetime import datetime
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


class TestUserClickHouseCache:
    """Test user-scoped ClickHouse cache isolation."""
    
    def test_cache_initialization(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Test cache initialization with user context."""
    pass
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
    
    async def test_cache_user_isolation(self):
        """Test that different users have isolated caches."""
    pass
        cache1 = UserClickHouseCache("user_123")
        cache2 = UserClickHouseCache("user_456")
        
        # Set data in first cache
        await cache1.set("SELECT 1", [{"user1": "data"}])
        
        # Second cache should not see the data
        result = await cache2.get("SELECT 1")
        assert result is None
        
        # Set different data in second cache
        await cache2.set("SELECT 1", [{"user2": "data"}])
        
        # Caches should have different data
        result1 = await cache1.get("SELECT 1")
        result2 = await cache2.get("SELECT 1")
        
        assert result1 == [{"user1": "data"}]
        assert result2 == [{"user2": "data"}]


class TestUserClickHouseClient:
    """Test user-scoped ClickHouse client isolation."""
    
    def test_client_creation(self):
        """Test client creation with proper user context."""
        client = UserClickHouseClient("user_123", "req_456", "thread_789")
        
        assert client.user_id == "user_123"
        assert client.request_id == "req_456"
        assert client.thread_id == "thread_789"
        assert not client._initialized
        assert isinstance(client._cache, UserClickHouseCache)
        assert client._cache.user_id == "user_123"
    
    async def test_client_initialization(self):
        """Test client initialization with mocked components."""
    pass
        client = UserClickHouseClient("user_123", "req_456", "thread_789")
        
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
                
                assert client._initialized
                assert client._client is mock_interceptor
                
                # Cleanup
                await client.cleanup()
                assert not client._initialized
    
    async def test_client_query_execution_with_cache(self):
        """Test query execution with user-scoped caching."""
        client = UserClickHouseClient("user_123", "req_456", "thread_789")
        
        # Mock initialization
        with patch.object(client, '_get_clickhouse_config'), \
             patch.object(client, '_create_base_client'):
            
            with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                mock_interceptor = AsyncNone  # TODO: Use real service instance
                mock_interceptor.test_connection = AsyncMock(return_value=True)
                mock_interceptor.execute = AsyncMock(return_value=[{"result": 42}])
                mock_interceptor_class.return_value = mock_interceptor
                
                await client.initialize()
                
                # First query should hit the database
                result1 = await client.execute("SELECT 1")
                assert result1 == [{"result": 42}]
                assert mock_interceptor.execute.call_count == 1
                
                # Second identical query should hit cache
                result2 = await client.execute("SELECT 1")
                assert result2 == [{"result": 42}]
                # Should still be 1 call to database (cached)
                assert mock_interceptor.execute.call_count == 1
                
                # Cache stats should show hit
                cache_stats = await client.get_cache_stats()
                assert cache_stats["hits"] == 1
                assert cache_stats["misses"] == 1
                
                await client.cleanup()
    
    def test_client_stats_tracking(self):
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
    
    async def test_create_user_client(self, clickhouse_factory, sample_user_context):
        """Test creating user-scoped ClickHouse clients."""
    pass
        # Mock the client initialization to avoid real connections
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.user_id = sample_user_context.user_id
            mock_client.request_id = sample_user_context.request_id
            mock_client.initialize = AsyncNone  # TODO: Use real service instance
            mock_client_class.return_value = mock_client
            
            # Create client for user
            client = await clickhouse_factory.create_user_client(sample_user_context)
            
            assert client is mock_client
            mock_client.initialize.assert_called_once()
            
            # Factory should track the client
            assert len(clickhouse_factory._active_clients) == 1
            assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
    
    async def test_user_client_limit_enforcement(self, clickhouse_factory, sample_user_context):
        """Test that factory enforces per-user client limits."""
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            mock_client_class.side_effect = lambda *args: AsyncNone  # TODO: Use real service instance
            
            # Disable cleanup during this test to ensure limit enforcement
            with patch.object(clickhouse_factory, '_cleanup_user_clients') as mock_cleanup:
                mock_cleanup.return_value = 0  # No clients cleaned up
                
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
                
                # Verify we have 2 clients for this user
                assert len(clickhouse_factory._active_clients) == 2
                assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 2
                
                # Third client should fail
                context3 = UserExecutionContext(
                    user_id=sample_user_context.user_id,
                    request_id="req_3",
                    thread_id="thread_3", 
                    run_id="run_3"
                )
                
                with pytest.raises(ValueError, match="exceeds maximum ClickHouse clients"):
                    await clickhouse_factory.create_user_client(context3)
    
    async def test_concurrent_user_isolation(self, clickhouse_factory, sample_user_context, another_user_context):
        """Test that different users get completely isolated clients."""
    pass
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            def create_mock_client(*args):
                mock = AsyncNone  # TODO: Use real service instance
    pass
                mock.user_id = args[0]  # user_id is first argument
                await asyncio.sleep(0)
    return mock
            
            mock_client_class.side_effect = create_mock_client
            
            # Create clients for different users
            client1 = await clickhouse_factory.create_user_client(sample_user_context)
            client2 = await clickhouse_factory.create_user_client(another_user_context)
            
            # Clients should be completely different instances
            assert client1 is not client2
            assert client1.user_id != client2.user_id
            
            # Factory should track both users
            assert len(clickhouse_factory._active_clients) == 2
            assert len(clickhouse_factory._user_client_counts) == 2
            
            # Each user should have 1 client
            assert clickhouse_factory._user_client_counts[sample_user_context.user_id] == 1
            assert clickhouse_factory._user_client_counts[another_user_context.user_id] == 1
    
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
    
    async def test_factory_context_manager(self, clickhouse_factory, sample_user_context):
        """Test factory context manager usage."""
    pass
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_client.initialize = AsyncNone  # TODO: Use real service instance
            mock_client_class.return_value = mock_client
            
            async with clickhouse_factory.get_user_client(sample_user_context) as client:
                assert client is mock_client
                mock_client.initialize.assert_called_once()


class TestConcurrentAccess:
    """Test concurrent access by multiple users."""
    
    async def test_concurrent_client_creation(self):
        """Test concurrent client creation by multiple users."""
        factory = ClickHouseFactory(max_clients_per_user=5, client_ttl_seconds=60)
        
        with patch('netra_backend.app.factories.clickhouse_factory.UserClickHouseClient') as mock_client_class:
            def create_mock_client(*args):
                mock = AsyncNone  # TODO: Use real service instance
                mock.user_id = args[0]  # user_id is first argument
                await asyncio.sleep(0)
    return mock
            
            mock_client_class.side_effect = create_mock_client
            
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
                await asyncio.sleep(0.01)  # Simulate some work
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


# Test markers for different environments
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.unit
]