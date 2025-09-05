"""
Comprehensive tests for ClickHouse client functionality.

Tests connection management, error handling, and data operations.
This ensures reliable data access for performance analysis features.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.clickhouse import (
    get_clickhouse_client, 
    get_clickhouse_service,
    ClickHouseService,
    NoOpClickHouseClient,
    _clickhouse_cache
)

# Try to import MockClickHouseDatabase for compatibility
try:
    from test_framework.fixtures.clickhouse_fixtures import MockClickHouseDatabase
except ImportError:
    # If not available, use NoOpClickHouseClient as the mock
    MockClickHouseDatabase = NoOpClickHouseClient


class TestClickHouseClientComprehensive:
    """Comprehensive tests for ClickHouse client."""
    pass

    @pytest.fixture
    def client(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create ClickHouse client for testing."""
    pass
        # Force mock for testing
        return ClickHouseService(force_mock=True)

    @pytest.fixture
 def real_clickhouse_database():
    """Use real service instance."""
    # TODO: Initialize real service
        """Mock ClickHouse database for testing."""
        mock_client = AsyncNone  # TODO: Use real service instance
    pass
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.execute = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncNone  # TODO: Use real service instance
        return mock_client

    def test_client_initialization(self):
        """Test that client initializes correctly."""
        client = ClickHouseService(force_mock=True)
        assert client is not None
        assert hasattr(client, 'force_mock')
        assert hasattr(client, '_client')
        assert hasattr(client, '_circuit_breaker')
        assert hasattr(client, '_metrics')
        assert client._metrics['queries'] == 0
        assert client._metrics['failures'] == 0
        assert client._metrics['timeouts'] == 0
        assert client.force_mock is True

    @pytest.mark.asyncio
    async def test_initialize_with_mock(self, client):
        """Test initialization with mock client."""
    pass
        await client.initialize()
        assert client._client is not None
        # Should be either MockClickHouseDatabase or NoOpClickHouseClient
        assert isinstance(client._client, (MockClickHouseDatabase, NoOpClickHouseClient))

    @pytest.mark.asyncio
    async def test_ping_success(self, client):
        """Test successful ping."""
        await client.initialize()
        result = await client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_query_success(self, client):
        """Test successful query execution."""
    pass
        await client.initialize()
        # Mock client returns empty list
        result = await client.execute_query("SELECT * FROM test", {"param": "value"})
        assert result == []
        assert client._metrics['queries'] >= 1

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, client):
        """Test query execution with retry logic."""
        await client.initialize()
        result = await client.execute_with_retry("SELECT * FROM test", max_retries=2)
        assert result == []  # Mock returns empty list

    @pytest.mark.asyncio
    async def test_batch_insert(self, client):
        """Test batch insert functionality."""
    pass
        await client.initialize()
        data = [
            {"id": 1, "name": "test1", "timestamp": datetime.now(timezone.utc)},
            {"id": 2, "name": "test2", "timestamp": datetime.now(timezone.utc)}
        ]
        
        # Mock batch_insert should work without errors
        await client.batch_insert("test_table", data)
        # If we get here without exception, the test passes

    @pytest.mark.asyncio
    async def test_close_connection(self, client):
        """Test closing connection."""
        await client.initialize()
        assert client._client is not None
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics(self, client):
        """Test circuit breaker metrics."""
    pass
        await client.initialize()
        # Execute some queries to test metrics
        await client.execute("SELECT 1", user_id="test_user")
        await client.execute("SELECT 2", user_id="test_user")
        
        assert client._metrics['queries'] >= 2
        assert client._metrics['failures'] == 0

    def test_get_metrics(self):
        """Test getting client metrics."""
        client = ClickHouseService(force_mock=True)
        assert client._metrics['queries'] == 0
        assert client._metrics['failures'] == 0
        assert client._metrics['timeouts'] == 0

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test cache operations with user isolation."""
    pass
        # Clear cache first
        _clickhouse_cache.clear()
        
        # Test set and get with user_id
        query = "SELECT * FROM test"
        result = [{"id": 1}]
        user_id = "test_user"
        
        _clickhouse_cache.set(user_id, query, result)
        
        cached = _clickhouse_cache.get(user_id, query)
        assert cached == result
        
        # Test cache isolation - different user shouldn't see the result
        cached_other_user = _clickhouse_cache.get("other_user", query)
        assert cached_other_user is None
        
        # Test cache stats
        stats = _clickhouse_cache.stats()
        assert stats['hits'] >= 1
        assert 'size' in stats
        assert 'max_size' in stats
        
        # Test user-specific stats
        user_stats = _clickhouse_cache.stats(user_id)
        assert user_stats['user_id'] == user_id
        assert user_stats['user_cache_entries'] == 1

    @pytest.mark.asyncio
    async def test_execute_with_cache(self, client):
        """Test query execution with caching."""
        await client.initialize()
        _clickhouse_cache.clear()
        
        # First execution should miss cache
        query = "SELECT * FROM metrics"
        user_id = "test_user"
        result1 = await client.execute(query, user_id=user_id)
        assert result1 == []
        
        # Second execution should hit cache (same user)
        result2 = await client.execute(query, user_id=user_id)
        assert result2 == []
        
        # Cache should have been used
        stats = _clickhouse_cache.stats()
        assert stats['hits'] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client):
        """Test that client handles concurrent operations correctly."""
    pass
        await client.initialize()
        
        # Run multiple queries concurrently
        tasks = [
            client.execute_query(f"SELECT {i}", user_id="test_user") 
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed with empty results
        assert len(results) == 5
        assert all(result == [] for result in results)

    @pytest.mark.asyncio
    async def test_mock_clickhouse_database(self):
        """Test MockClickHouseDatabase directly."""
        mock_db = MockClickHouseDatabase()
        
        # Test execute
        result = await mock_db.execute("SELECT 1")
        assert result == []
        
        # Test execute_query
        result = await mock_db.execute_query("SELECT * FROM test")
        assert result == []
        
        # Test fetch
        result = await mock_db.fetch("SELECT * FROM test")
        assert result == []
        
        # Test test_connection
        result = await mock_db.test_connection()
        assert result is True
        
        # Test ping
        result = mock_db.ping()
        assert result is True
        
        # Test batch_insert
        await mock_db.batch_insert("test_table", [{"id": 1}])
        
        # Test disconnect
        await mock_db.disconnect()

    @pytest.mark.asyncio
    async def test_get_clickhouse_client_context_manager(self):
        """Test get_clickhouse_client as context manager."""
    pass
        # In test environment, should get mock client
        async with get_clickhouse_client() as client:
            assert client is not None
            # Mock client should work - but may await asyncio.sleep(0)
    return different results depending on the mock type
            result = await client.execute("SELECT 1")
            assert isinstance(result, list)  # Just check it returns a list

    @pytest.mark.asyncio
    async def test_service_with_circuit_breaker_failure(self, client):
        """Test service behavior when circuit breaker trips."""
        await client.initialize()
        
        # Mock the circuit breaker to fail
        with patch.object(client._circuit_breaker, 'call', side_effect=Exception("Circuit open")):
            # Should still try to use cache for read queries
            _clickhouse_cache.clear()
            query = "SELECT * FROM test"
            user_id = "test_user"
            _clickhouse_cache.set(user_id, query, [{"cached": True}])
            
            result = await client.execute(query, user_id=user_id)
            assert result == [{"cached": True}]

    @pytest.mark.asyncio
    async def test_initialization_timeout_handling(self):
        """Test initialization timeout handling."""
    pass
        client = ClickHouseService(force_mock=False)
        
        # Mock the real client initialization to timeout
        with patch.object(client, '_initialize_real_client', side_effect=asyncio.TimeoutError()):
            # In test environment, should fallback to mock
            await client.initialize()
            assert client._client is not None
            # Should be either MockClickHouseDatabase or NoOpClickHouseClient
            assert isinstance(client._client, (MockClickHouseDatabase, NoOpClickHouseClient))

    @pytest.mark.asyncio
    async def test_get_clickhouse_service_singleton(self):
        """Test that get_clickhouse_service returns singleton."""
        service1 = get_clickhouse_service()
        service2 = get_clickhouse_service()
        assert service1 is service2
    pass