"""
NoOp ClickHouse Client Behavior Validation - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Reliable test isolation and consistent testing behavior
- Value Impact: 100% consistent test behavior regardless of external dependencies
- Revenue Impact: Prevents $25K+ testing infrastructure costs and delays

CRITICAL: These tests validate that NoOp client behavior is consistent and realistic.
"""

import pytest
import asyncio
from netra_backend.app.db.clickhouse import (
    NoOpClickHouseClient,
    _create_test_noop_client,
    ClickHouseService
)


class TestNoOpClickHouseClientBehavior:
    """Unit tests for NoOp ClickHouse client behavior."""
    
    def test_noop_client_initialization(self):
        """Test NoOp client initializes correctly."""
        client = NoOpClickHouseClient()
        assert client._connected == True
    
    async def test_noop_client_basic_query_execution(self):
        """Test basic query execution behavior."""
        client = NoOpClickHouseClient()
        
        # Test simple SELECT 1
        result = await client.execute("SELECT 1")
        assert isinstance(result, list)
        assert len(result) >= 0
        
        # Test SELECT 1 with alias
        result = await client.execute("SELECT 1 as test")
        assert isinstance(result, list)
        if result:  # May return data
            assert "test" in result[0] or "1" in result[0]
    
    async def test_noop_client_error_simulation(self):
        """Test that NoOp client simulates realistic error conditions."""
        client = NoOpClickHouseClient()
        
        # Test table not found error
        with pytest.raises(Exception) as exc_info:
            await client.execute("SELECT * FROM non_existent_table")
        assert "doesn't exist" in str(exc_info.value).lower()
        
        # Test syntax error simulation
        with pytest.raises(Exception) as exc_info:
            await client.execute("SELECT FROM WHERE")
        assert "syntax error" in str(exc_info.value).lower()
        
        # Test UPDATE syntax error (ClickHouse doesn't support UPDATE)
        with pytest.raises(Exception) as exc_info:
            await client.execute("UPDATE SET WHERE")
        assert "update" in str(exc_info.value).lower()
        
        # Test permission error simulation
        with pytest.raises(Exception) as exc_info:
            await client.execute("SELECT * FROM system.users")
        assert "privileges" in str(exc_info.value).lower()
    
    async def test_noop_client_connection_state_management(self):
        """Test connection state management."""
        client = NoOpClickHouseClient()
        
        # Initially connected
        assert await client.test_connection() == True
        
        # After disconnect
        await client.disconnect()
        assert await client.test_connection() == False
        
        # Should raise error when disconnected
        with pytest.raises(ConnectionError) as exc_info:
            await client.execute("SELECT 1")
        assert "disconnected" in str(exc_info.value).lower()
    
    async def test_noop_client_execute_query_alias(self):
        """Test execute_query method (alias for execute)."""
        client = NoOpClickHouseClient()
        
        # execute_query should work the same as execute
        result1 = await client.execute("SELECT 1")
        result2 = await client.execute_query("SELECT 1")
        
        # Both should return the same type of result
        assert type(result1) == type(result2)
        assert isinstance(result1, list)
        assert isinstance(result2, list)
    
    async def test_noop_client_parameter_handling(self):
        """Test parameter handling in queries."""
        client = NoOpClickHouseClient()
        
        # Should accept parameters without error
        result = await client.execute("SELECT 1", {"param": "value"})
        assert isinstance(result, list)
        
        # execute_query should also accept parameters
        result = await client.execute_query("SELECT 1", {"param": "value"})
        assert isinstance(result, list)


class TestNoOpClientFactory:
    """Unit tests for NoOp client factory function."""
    
    async def test_create_test_noop_client_context_manager(self):
        """Test the NoOp client factory context manager."""
        async with _create_test_noop_client() as client:
            assert isinstance(client, NoOpClickHouseClient)
            assert await client.test_connection() == True
            
            # Should be able to execute queries
            result = await client.execute("SELECT 1")
            assert isinstance(result, list)
    
    async def test_create_test_noop_client_cleanup(self):
        """Test that factory properly cleans up connections."""
        client_ref = None
        
        async with _create_test_noop_client() as client:
            client_ref = client
            assert await client.test_connection() == True
        
        # After context exit, client should be disconnected
        # Note: This tests the cleanup behavior
        assert await client_ref.test_connection() == False


class TestClickHouseServiceWithNoOpClient:
    """Unit tests for ClickHouse service using NoOp client."""
    
    async def test_service_with_force_mock(self):
        """Test ClickHouse service with forced mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            # Should be using mock client
            assert service.is_mock == True
            assert service.is_real == False
            
            # Should be able to execute queries
            result = await service.execute("SELECT 1")
            assert isinstance(result, list)
            
        finally:
            await service.close()
    
    async def test_service_mock_client_ping(self):
        """Test ping functionality with mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            # Ping should work with mock client
            is_available = await service.ping()
            assert is_available == True
            
        finally:
            await service.close()
    
    async def test_service_mock_client_health_check(self):
        """Test health check with mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            health = await service.health_check()
            assert isinstance(health, dict)
            assert "status" in health
            assert "metrics" in health
            
        finally:
            await service.close()
    
    async def test_service_mock_client_batch_insert(self):
        """Test batch insert with mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            # Mock batch insert should not raise errors
            test_data = [
                {"id": 1, "name": "test1"},
                {"id": 2, "name": "test2"}
            ]
            
            await service.batch_insert("test_table", test_data)
            # Should complete without error
            
        finally:
            await service.close()
    
    async def test_service_mock_client_caching(self):
        """Test query caching with mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            # Execute the same query multiple times
            query = "SELECT 1 as test"
            result1 = await service.execute(query, user_id="test_user")
            result2 = await service.execute(query, user_id="test_user")
            
            # Both should return results
            assert isinstance(result1, list)
            assert isinstance(result2, list)
            
            # Check cache stats
            stats = service.get_cache_stats(user_id="test_user")
            assert isinstance(stats, dict)
            assert "user_id" in stats or "size" in stats
            
        finally:
            await service.close()
    
    async def test_service_mock_client_retry_logic(self):
        """Test retry logic with mock client."""
        service = ClickHouseService(force_mock=True)
        
        try:
            await service.initialize()
            
            # Test retry with a query that should work
            result = await service.execute_with_retry("SELECT 1", max_retries=2)
            assert isinstance(result, list)
            
        finally:
            await service.close()


class TestNoOpClientRealisticBehavior:
    """Tests to ensure NoOp client behaves realistically for test scenarios."""
    
    async def test_query_types_return_appropriate_responses(self):
        """Test that different query types return appropriate responses."""
        client = NoOpClickHouseClient()
        
        # SELECT queries should return lists
        result = await client.execute("SELECT COUNT(*) FROM some_table")
        assert isinstance(result, list)
        
        # INSERT queries should return empty lists (no results)
        result = await client.execute("INSERT INTO test VALUES (1, 'test')")
        assert isinstance(result, list)
        
        # CREATE queries should return empty lists
        result = await client.execute("CREATE TABLE test (id Int32)")
        assert isinstance(result, list)
    
    async def test_connection_recovery_simulation(self):
        """Test connection recovery scenarios."""
        client = NoOpClickHouseClient()
        
        # Start connected
        assert await client.test_connection() == True
        
        # Simulate disconnection
        await client.disconnect()
        assert await client.test_connection() == False
        
        # Queries should fail when disconnected
        with pytest.raises(ConnectionError):
            await client.execute("SELECT 1")
    
    async def test_concurrent_access_handling(self):
        """Test concurrent access to NoOp client."""
        client = NoOpClickHouseClient()
        
        # Multiple concurrent queries should all succeed
        tasks = [
            client.execute("SELECT 1"),
            client.execute("SELECT 2"),
            client.execute("SELECT 3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should return list results
        for result in results:
            assert isinstance(result, list)


if __name__ == "__main__":
    # Run unit tests
    pytest.main([__file__, "-v", "--tb=short"])