"""
Test ClickHouse Cache User Isolation

This module tests Phase 1 implementation of ClickHouse cache isolation
to ensure proper separation of cached query results between different users.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) 
- Business Goal: Prevent data leakage between users via cache
- Value Impact: Guarantees user data privacy and security
- Revenue Impact: Prevents security breaches that could damage trust
"""

import pytest
import hashlib
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.clickhouse import ClickHouseCache, _clickhouse_cache


class TestClickHouseCacheIsolation:
    """Test suite for ClickHouse cache user isolation."""

    @pytest.fixture
    def fresh_cache(self):
        """Create a fresh cache instance for testing."""
        cache = ClickHouseCache(max_size=10)
        cache.clear()
        return cache

    @pytest.fixture(autouse=True)
    def clear_global_cache(self):
        """Clear global cache before each test."""
        _clickhouse_cache.clear()

    def test_cache_key_generation_with_user_id(self, fresh_cache):
        """Test that cache keys include user_id for proper isolation."""
        query = "SELECT * FROM test"
        params = {"param1": "value1"}
        
        # Test key generation with different users
        user1_key = fresh_cache._generate_key("user1", query, params)
        user2_key = fresh_cache._generate_key("user2", query, params)
        system_key = fresh_cache._generate_key(None, query, params)
        
        # Keys should be different for different users
        assert user1_key != user2_key
        assert user1_key != system_key
        assert user2_key != system_key
        
        # Keys should contain user identifiers
        assert "user1" in user1_key
        assert "user2" in user2_key
        assert "system" in system_key
        
        # Keys should have expected format
        assert user1_key.startswith("ch:user1:")
        assert user2_key.startswith("ch:user2:")
        assert system_key.startswith("ch:system:")

    def test_cache_isolation_between_users(self, fresh_cache):
        """Test that cached data is properly isolated between users."""
        query = "SELECT * FROM users"
        user1_data = [{"id": 1, "name": "User One"}]
        user2_data = [{"id": 2, "name": "User Two"}]
        
        # Cache different data for different users with same query
        fresh_cache.set("user1", query, user1_data)
        fresh_cache.set("user2", query, user2_data)
        
        # Each user should only see their own data
        cached_user1 = fresh_cache.get("user1", query)
        cached_user2 = fresh_cache.get("user2", query)
        
        assert cached_user1 == user1_data
        assert cached_user2 == user2_data
        assert cached_user1 != cached_user2

    def test_cache_isolation_with_same_query_different_users(self, fresh_cache):
        """Test that same query returns different results for different users."""
        query = "SELECT * FROM sensitive_data"
        
        # User1 caches their data
        user1_data = [{"sensitive": "user1_secret"}]
        fresh_cache.set("user1", query, user1_data)
        
        # User2 should not see user1's data
        cached_user2 = fresh_cache.get("user2", query)
        assert cached_user2 is None
        
        # User2 caches their own data
        user2_data = [{"sensitive": "user2_secret"}]
        fresh_cache.set("user2", query, user2_data)
        
        # Verify isolation is maintained
        assert fresh_cache.get("user1", query) == user1_data
        assert fresh_cache.get("user2", query) == user2_data

    def test_cache_backward_compatibility_with_none_user(self, fresh_cache):
        """Test that None user_id maps to 'system' for backward compatibility."""
        query = "SELECT 1"
        data = [{"result": 1}]
        
        # Set with None user_id
        fresh_cache.set(None, query, data)
        
        # Should be retrievable with None user_id
        cached = fresh_cache.get(None, query)
        assert cached == data
        
        # Should also work with explicit "system" user_id
        cached_system = fresh_cache.get("system", query)
        assert cached_system == data

    def test_cache_stats_user_specific(self, fresh_cache):
        """Test that cache statistics can be retrieved per user."""
        # Add data for different users
        fresh_cache.set("user1", "SELECT * FROM table1", [{"data": 1}])
        fresh_cache.set("user1", "SELECT * FROM table2", [{"data": 2}])
        fresh_cache.set("user2", "SELECT * FROM table1", [{"data": 3}])
        
        # Test global stats
        global_stats = fresh_cache.stats()
        assert global_stats["size"] == 3
        
        # Test user-specific stats
        user1_stats = fresh_cache.stats("user1")
        assert user1_stats["user_id"] == "user1"
        assert user1_stats["user_cache_entries"] == 2
        assert user1_stats["user_cache_percentage"] > 0
        
        user2_stats = fresh_cache.stats("user2")
        assert user2_stats["user_id"] == "user2"
        assert user2_stats["user_cache_entries"] == 1
        
        # Non-existent user should have 0 entries
        user3_stats = fresh_cache.stats("user3")
        assert user3_stats["user_id"] == "user3"
        assert user3_stats["user_cache_entries"] == 0

    def test_cache_clear_user_specific(self, fresh_cache):
        """Test that cache can be cleared for specific users."""
        # Add data for multiple users
        fresh_cache.set("user1", "SELECT * FROM table1", [{"data": 1}])
        fresh_cache.set("user1", "SELECT * FROM table2", [{"data": 2}])
        fresh_cache.set("user2", "SELECT * FROM table1", [{"data": 3}])
        fresh_cache.set("user3", "SELECT * FROM table1", [{"data": 4}])
        
        # Verify all data is cached
        assert fresh_cache.stats()["size"] == 4
        
        # Clear cache for user1 only
        fresh_cache.clear("user1")
        
        # User1's data should be gone, others should remain
        assert fresh_cache.get("user1", "SELECT * FROM table1") is None
        assert fresh_cache.get("user1", "SELECT * FROM table2") is None
        assert fresh_cache.get("user2", "SELECT * FROM table1") == [{"data": 3}]
        assert fresh_cache.get("user3", "SELECT * FROM table1") == [{"data": 4}]
        
        # Cache size should be reduced
        assert fresh_cache.stats()["size"] == 2

    def test_cache_isolation_with_parameters(self, fresh_cache):
        """Test that cache isolation works correctly with query parameters."""
        query = "SELECT * FROM users WHERE status = %(status)s"
        params = {"status": "active"}
        
        user1_data = [{"id": 1, "status": "active"}]
        user2_data = [{"id": 2, "status": "active"}]
        
        # Cache same query+params for different users
        fresh_cache.set("user1", query, user1_data, params)
        fresh_cache.set("user2", query, user2_data, params)
        
        # Verify isolation
        assert fresh_cache.get("user1", query, params) == user1_data
        assert fresh_cache.get("user2", query, params) == user2_data
        
        # Different user should not see cached data
        assert fresh_cache.get("user3", query, params) is None

    def test_cache_expiration_per_user(self, fresh_cache):
        """Test that cache expiration works independently per user."""
        import time
        
        query = "SELECT NOW()"
        user1_data = [{"time": "10:00:00"}]
        user2_data = [{"time": "10:00:01"}]
        
        # Cache with very short TTL
        fresh_cache.set("user1", query, user1_data, ttl=0.1)
        fresh_cache.set("user2", query, user2_data, ttl=1.0)  # Longer TTL
        
        # Both should be available initially
        assert fresh_cache.get("user1", query) == user1_data
        assert fresh_cache.get("user2", query) == user2_data
        
        # Wait for user1's cache to expire
        time.sleep(0.2)
        
        # User1's data should be expired, user2's should remain
        assert fresh_cache.get("user1", query) is None
        assert fresh_cache.get("user2", query) == user2_data

    def test_global_cache_integration(self):
        """Test that global cache instance maintains user isolation."""
        query = "SELECT global_test"
        
        # Use global cache instance
        _clickhouse_cache.set("user1", query, [{"global": "user1"}])
        _clickhouse_cache.set("user2", query, [{"global": "user2"}])
        
        # Verify isolation through global instance
        assert _clickhouse_cache.get("user1", query) == [{"global": "user1"}]
        assert _clickhouse_cache.get("user2", query) == [{"global": "user2"}]
        assert _clickhouse_cache.get("user3", query) is None
        
        # Verify user-specific stats work with global instance
        user1_stats = _clickhouse_cache.stats("user1")
        assert user1_stats["user_cache_entries"] == 1
        
        user2_stats = _clickhouse_cache.stats("user2")
        assert user2_stats["user_cache_entries"] == 1

    def test_cache_key_consistency(self, fresh_cache):
        """Test that cache keys are consistent across multiple calls."""
        query = "SELECT consistency_test"
        params = {"test": "value"}
        
        # Generate keys multiple times
        key1 = fresh_cache._generate_key("user1", query, params)
        key2 = fresh_cache._generate_key("user1", query, params)
        key3 = fresh_cache._generate_key("user1", query, params)
        
        # All keys should be identical
        assert key1 == key2 == key3
        
        # Different user should generate different key
        different_user_key = fresh_cache._generate_key("user2", query, params)
        assert different_user_key != key1

    def test_cache_security_no_user_leakage(self, fresh_cache):
        """Test that there's no way to access other users' cached data."""
        sensitive_query = "SELECT * FROM financial_data"
        
        # User1 caches sensitive financial data
        user1_sensitive = [{"account": "123456", "balance": 10000}]
        fresh_cache.set("user1", sensitive_query, user1_sensitive)
        
        # Try various ways to access as different user - all should fail
        assert fresh_cache.get("user2", sensitive_query) is None
        assert fresh_cache.get("", sensitive_query) is None
        assert fresh_cache.get("system", sensitive_query) is None
        
        # Even with None user_id (system) should not see user1's data
        assert fresh_cache.get(None, sensitive_query) is None
        
        # User2 should be able to cache their own data without conflict
        user2_sensitive = [{"account": "789012", "balance": 5000}]
        fresh_cache.set("user2", sensitive_query, user2_sensitive)
        
        # Verify both users still have isolated data
        assert fresh_cache.get("user1", sensitive_query) == user1_sensitive
        assert fresh_cache.get("user2", sensitive_query) == user2_sensitive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])