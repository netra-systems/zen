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
        query = 'SELECT * FROM test'
        params = {'param1': 'value1'}
        user1_key = fresh_cache._generate_key('user1', query, params)
        user2_key = fresh_cache._generate_key('user2', query, params)
        system_key = fresh_cache._generate_key(None, query, params)
        assert user1_key != user2_key
        assert user1_key != system_key
        assert user2_key != system_key
        assert 'user1' in user1_key
        assert 'user2' in user2_key
        assert 'system' in system_key
        assert user1_key.startswith('ch:user1:')
        assert user2_key.startswith('ch:user2:')
        assert system_key.startswith('ch:system:')

    def test_cache_isolation_between_users(self, fresh_cache):
        """Test that cached data is properly isolated between users."""
        query = 'SELECT * FROM users'
        user1_data = [{'id': 1, 'name': 'User One'}]
        user2_data = [{'id': 2, 'name': 'User Two'}]
        fresh_cache.set('user1', query, user1_data)
        fresh_cache.set('user2', query, user2_data)
        cached_user1 = fresh_cache.get('user1', query)
        cached_user2 = fresh_cache.get('user2', query)
        assert cached_user1 == user1_data
        assert cached_user2 == user2_data
        assert cached_user1 != cached_user2

    def test_cache_isolation_with_same_query_different_users(self, fresh_cache):
        """Test that same query returns different results for different users."""
        query = 'SELECT * FROM sensitive_data'
        user1_data = [{'sensitive': 'user1_secret'}]
        fresh_cache.set('user1', query, user1_data)
        cached_user2 = fresh_cache.get('user2', query)
        assert cached_user2 is None
        user2_data = [{'sensitive': 'user2_secret'}]
        fresh_cache.set('user2', query, user2_data)
        assert fresh_cache.get('user1', query) == user1_data
        assert fresh_cache.get('user2', query) == user2_data

    def test_cache_backward_compatibility_with_none_user(self, fresh_cache):
        """Test that None user_id maps to 'system' for backward compatibility."""
        query = 'SELECT 1'
        data = [{'result': 1}]
        fresh_cache.set(None, query, data)
        cached = fresh_cache.get(None, query)
        assert cached == data
        cached_system = fresh_cache.get('system', query)
        assert cached_system == data

    def test_cache_stats_user_specific(self, fresh_cache):
        """Test that cache statistics can be retrieved per user."""
        fresh_cache.set('user1', 'SELECT * FROM table1', [{'data': 1}])
        fresh_cache.set('user1', 'SELECT * FROM table2', [{'data': 2}])
        fresh_cache.set('user2', 'SELECT * FROM table1', [{'data': 3}])
        global_stats = fresh_cache.stats()
        assert global_stats['size'] == 3
        user1_stats = fresh_cache.stats('user1')
        assert user1_stats['user_id'] == 'user1'
        assert user1_stats['user_cache_entries'] == 2
        assert user1_stats['user_cache_percentage'] > 0
        user2_stats = fresh_cache.stats('user2')
        assert user2_stats['user_id'] == 'user2'
        assert user2_stats['user_cache_entries'] == 1
        user3_stats = fresh_cache.stats('user3')
        assert user3_stats['user_id'] == 'user3'
        assert user3_stats['user_cache_entries'] == 0

    def test_cache_clear_user_specific(self, fresh_cache):
        """Test that cache can be cleared for specific users."""
        fresh_cache.set('user1', 'SELECT * FROM table1', [{'data': 1}])
        fresh_cache.set('user1', 'SELECT * FROM table2', [{'data': 2}])
        fresh_cache.set('user2', 'SELECT * FROM table1', [{'data': 3}])
        fresh_cache.set('user3', 'SELECT * FROM table1', [{'data': 4}])
        assert fresh_cache.stats()['size'] == 4
        fresh_cache.clear('user1')
        assert fresh_cache.get('user1', 'SELECT * FROM table1') is None
        assert fresh_cache.get('user1', 'SELECT * FROM table2') is None
        assert fresh_cache.get('user2', 'SELECT * FROM table1') == [{'data': 3}]
        assert fresh_cache.get('user3', 'SELECT * FROM table1') == [{'data': 4}]
        assert fresh_cache.stats()['size'] == 2

    def test_cache_isolation_with_parameters(self, fresh_cache):
        """Test that cache isolation works correctly with query parameters."""
        query = 'SELECT * FROM users WHERE status = %(status)s'
        params = {'status': 'active'}
        user1_data = [{'id': 1, 'status': 'active'}]
        user2_data = [{'id': 2, 'status': 'active'}]
        fresh_cache.set('user1', query, user1_data, params)
        fresh_cache.set('user2', query, user2_data, params)
        assert fresh_cache.get('user1', query, params) == user1_data
        assert fresh_cache.get('user2', query, params) == user2_data
        assert fresh_cache.get('user3', query, params) is None

    def test_cache_expiration_per_user(self, fresh_cache):
        """Test that cache expiration works independently per user."""
        import time
        query = 'SELECT NOW()'
        user1_data = [{'time': '10:00:00'}]
        user2_data = [{'time': '10:00:01'}]
        fresh_cache.set('user1', query, user1_data, ttl=0.1)
        fresh_cache.set('user2', query, user2_data, ttl=1.0)
        assert fresh_cache.get('user1', query) == user1_data
        assert fresh_cache.get('user2', query) == user2_data
        time.sleep(0.2)
        assert fresh_cache.get('user1', query) is None
        assert fresh_cache.get('user2', query) == user2_data

    def test_global_cache_integration(self):
        """Test that global cache instance maintains user isolation."""
        query = 'SELECT global_test'
        _clickhouse_cache.set('user1', query, [{'global': 'user1'}])
        _clickhouse_cache.set('user2', query, [{'global': 'user2'}])
        assert _clickhouse_cache.get('user1', query) == [{'global': 'user1'}]
        assert _clickhouse_cache.get('user2', query) == [{'global': 'user2'}]
        assert _clickhouse_cache.get('user3', query) is None
        user1_stats = _clickhouse_cache.stats('user1')
        assert user1_stats['user_cache_entries'] == 1
        user2_stats = _clickhouse_cache.stats('user2')
        assert user2_stats['user_cache_entries'] == 1

    def test_cache_key_consistency(self, fresh_cache):
        """Test that cache keys are consistent across multiple calls."""
        query = 'SELECT consistency_test'
        params = {'test': 'value'}
        key1 = fresh_cache._generate_key('user1', query, params)
        key2 = fresh_cache._generate_key('user1', query, params)
        key3 = fresh_cache._generate_key('user1', query, params)
        assert key1 == key2 == key3
        different_user_key = fresh_cache._generate_key('user2', query, params)
        assert different_user_key != key1

    def test_cache_security_no_user_leakage(self, fresh_cache):
        """Test that there's no way to access other users' cached data."""
        sensitive_query = 'SELECT * FROM financial_data'
        user1_sensitive = [{'account': '123456', 'balance': 10000}]
        fresh_cache.set('user1', sensitive_query, user1_sensitive)
        assert fresh_cache.get('user2', sensitive_query) is None
        assert fresh_cache.get('', sensitive_query) is None
        assert fresh_cache.get('system', sensitive_query) is None
        assert fresh_cache.get(None, sensitive_query) is None
        user2_sensitive = [{'account': '789012', 'balance': 5000}]
        fresh_cache.set('user2', sensitive_query, user2_sensitive)
        assert fresh_cache.get('user1', sensitive_query) == user1_sensitive
        assert fresh_cache.get('user2', sensitive_query) == user2_sensitive
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')