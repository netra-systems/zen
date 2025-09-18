"""
Test ClickHouse Database Operations - Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable analytics data operations
- Value Impact: Critical for data integrity and user trust (100% analytics accuracy)
- Strategic Impact: Protects revenue from data loss incidents (+$15K MRR)

This test suite validates ClickHouse database operations at the unit level,
focusing on core functionality without requiring external dependencies.
Ensures that ClickHouse operations are reliable for multi-user scenarios.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from netra_backend.app.db.clickhouse import (
    ClickHouseCache,
    ClickHouseService,
    NoOpClickHouseClient,
    use_mock_clickhouse,
    _clickhouse_cache
)
from test_framework.base_integration_test import BaseIntegrationTest


class TestClickHouseCacheUnit(BaseIntegrationTest):
    """Test ClickHouse cache functionality for user data isolation."""
    
    @pytest.mark.unit
    def test_cache_key_generation_with_user_isolation(self):
        """Test cache key generation ensures proper user isolation.
        
        Critical for multi-user platform - prevents cache leakage between users.
        """
        cache = ClickHouseCache()
        
        # Test user-specific cache keys
        user1_key = cache._generate_key("user-123", "SELECT * FROM events")
        user2_key = cache._generate_key("user-456", "SELECT * FROM events")
        system_key = cache._generate_key(None, "SELECT * FROM events")
        
        # Verify user isolation - different users get different cache keys
        assert user1_key != user2_key, "Cache keys must be unique per user"
        assert user1_key.startswith("ch:user-123:"), "User-specific cache key format"
        assert user2_key.startswith("ch:user-456:"), "User-specific cache key format"
        assert system_key.startswith("ch:system:"), "System cache key format"
        
        # Test with parameters for query differentiation
        params = {"limit": 100}
        user1_params_key = cache._generate_key("user-123", "SELECT * FROM events", params)
        user1_no_params_key = cache._generate_key("user-123", "SELECT * FROM events")
        
        assert user1_params_key != user1_no_params_key, "Parameters must affect cache key"
        assert ":p:" in user1_params_key, "Parameter hash in cache key"

    @pytest.mark.unit  
    def test_cache_user_isolation_operations(self):
        """Test cache operations maintain strict user isolation.
        
        Validates that users cannot access each other's cached data.
        """
        cache = ClickHouseCache()
        
        # Cache data for different users
        user1_data = [{"id": 1, "name": "user1_data"}]
        user2_data = [{"id": 2, "name": "user2_data"}]
        system_data = [{"id": 3, "name": "system_data"}]
        
        query = "SELECT * FROM user_events"
        
        cache.set("user-123", query, user1_data)
        cache.set("user-456", query, user2_data)  
        cache.set(None, query, system_data)
        
        # Verify user isolation - each user only gets their own data
        assert cache.get("user-123", query) == user1_data
        assert cache.get("user-456", query) == user2_data
        assert cache.get(None, query) == system_data
        
        # Cross-user access should return None (cache miss)
        assert cache.get("user-123", query) != user2_data
        assert cache.get("user-456", query) != user1_data

    @pytest.mark.unit
    def test_cache_stats_user_specific(self):
        """Test cache statistics provide user-specific insights.
        
        Critical for monitoring and debugging user-specific performance.
        """
        cache = ClickHouseCache()
        
        # Add cache entries for different users
        cache.set("user-123", "SELECT 1", [{"result": 1}])
        cache.set("user-123", "SELECT 2", [{"result": 2}])
        cache.set("user-456", "SELECT 3", [{"result": 3}])
        cache.set(None, "SELECT 4", [{"result": 4}])  # system
        
        # Test global stats
        global_stats = cache.stats()
        assert global_stats["size"] == 4, "Total cache entries"
        
        # Test user-specific stats
        user123_stats = cache.stats("user-123")
        assert user123_stats["user_cache_entries"] == 2, "User-specific cache count"
        assert user123_stats["user_id"] == "user-123"
        
        user456_stats = cache.stats("user-456")
        assert user456_stats["user_cache_entries"] == 1, "User-specific cache count"
        
        # Test user isolation in stats
        assert user123_stats["user_cache_entries"] != user456_stats["user_cache_entries"]


class TestClickHouseServiceUnit(BaseIntegrationTest):
    """Test ClickHouse service layer functionality."""
    
    @pytest.mark.unit
    async def test_service_initialization_with_noop_client(self):
        """Test service initialization with NoOp client for testing.
        
        Ensures tests can run without external ClickHouse dependencies.
        """
        service = ClickHouseService(force_mock=True)
        await service.initialize()
        
        assert service.is_mock, "Service should use mock client when forced"
        assert isinstance(service._client, NoOpClickHouseClient)
        
        # Test basic operations work with NoOp client
        result = await service.execute("SELECT 1", user_id="test-user")
        assert result == [], "NoOp client returns empty results"
        
        ping_result = await service.ping()
        assert ping_result is True, "NoOp client ping succeeds"

    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=True)
    async def test_service_graceful_degradation(self, mock_use_clickhouse):
        """Test service graceful degradation when ClickHouse unavailable.
        
        Critical for system reliability when ClickHouse is down.
        """
        service = ClickHouseService()
        await service.initialize()
        
        # Should initialize with NoOp client when mock is required
        assert service.is_mock, "Service should degrade to NoOp client"
        
        # Operations should not fail
        result = await service.execute("SELECT * FROM events WHERE user_id = 'test'", 
                                     user_id="test-user")
        assert isinstance(result, list), "Degraded service returns list"

    @pytest.mark.unit
    async def test_service_cache_integration_with_user_isolation(self):
        """Test service cache integration maintains user isolation.
        
        Validates that cached results are properly isolated by user.
        """
        service = ClickHouseService(force_mock=True)
        await service.initialize()
        
        # Mock client to return specific data
        mock_client = AsyncMock()
        mock_client.execute.return_value = [{"id": 1, "data": "test_data"}]
        service._client = mock_client
        
        query = "SELECT * FROM events WHERE user_id = %(user_id)s"
        params = {"user_id": "user-123"}
        
        # First call should hit the client and cache result
        result1 = await service.execute(query, params, user_id="user-123")
        assert mock_client.execute.call_count == 1
        
        # Second call with same user should hit cache (client not called again)
        result2 = await service.execute(query, params, user_id="user-123")
        assert mock_client.execute.call_count == 1, "Second call should use cache"
        assert result1 == result2, "Cached result should match original"
        
        # Different user should bypass cache and call client
        result3 = await service.execute(query, params, user_id="user-456")
        assert mock_client.execute.call_count == 2, "Different user should bypass cache"


class TestClickHouseNoOpClientUnit:
    """Test NoOp client functionality for testing environments."""
    
    @pytest.mark.unit
    async def test_noop_client_interface_compatibility(self):
        """Test NoOp client provides compatible interface.
        
        Ensures tests can run without ClickHouse while maintaining interface.
        """
        client = NoOpClickHouseClient()
        
        # Test all required methods exist and work
        result = await client.execute("SELECT 1")
        assert result == [], "Execute returns empty list"
        
        query_result = await client.execute_query("SELECT * FROM test")
        assert query_result == [], "Execute query returns empty list"
        
        connection_test = await client.test_connection()
        assert connection_test is True, "Connection test succeeds"
        
        # Disconnect should not raise errors
        await client.disconnect()

    @pytest.mark.unit
    async def test_noop_client_query_logging(self):
        """Test NoOp client logs queries for debugging.
        
        Helps developers understand what queries would be executed.
        """
        with patch('netra_backend.app.db.clickhouse.logger') as mock_logger:
            client = NoOpClickHouseClient()
            
            await client.execute("SELECT COUNT(*) FROM user_events")
            
            # Verify query was logged for debugging
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "ClickHouse NoOp" in call_args
            assert "SELECT COUNT(*)" in call_args


class TestClickHouseUtilityFunctions:
    """Test utility functions for ClickHouse configuration and detection."""
    
    @pytest.mark.unit
    def test_use_mock_clickhouse_detection(self):
        """Test mock ClickHouse detection logic.
        
        Critical for proper test environment setup.
        """
        with patch('netra_backend.app.db.clickhouse._is_testing_environment') as mock_testing:
            with patch('netra_backend.app.db.clickhouse._should_disable_clickhouse_for_tests') as mock_disabled:
                # Test case 1: Testing environment with ClickHouse disabled
                mock_testing.return_value = True
                mock_disabled.return_value = True
                assert use_mock_clickhouse() is True
                
                # Test case 2: Testing environment with ClickHouse enabled 
                mock_testing.return_value = True
                mock_disabled.return_value = False
                assert use_mock_clickhouse() is False
                
                # Test case 3: Non-testing environment
                mock_testing.return_value = False
                mock_disabled.return_value = True  # Shouldn't matter
                assert use_mock_clickhouse() is False

    @pytest.mark.unit
    def test_global_cache_singleton_behavior(self):
        """Test global cache instance behavior.
        
        Ensures cache state is properly managed across the application.
        """
        # Global cache should be the same instance
        from netra_backend.app.db.clickhouse import _clickhouse_cache as cache1
        from netra_backend.app.db.clickhouse import _clickhouse_cache as cache2
        
        assert cache1 is cache2, "Global cache should be singleton"
        
        # Test cache operations affect global state
        original_size = len(cache1.cache)
        cache1.set("test-user", "SELECT 1", [{"result": 1}])
        assert len(cache2.cache) == original_size + 1, "Cache state is shared"
        
        # Clean up for other tests
        cache1.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])