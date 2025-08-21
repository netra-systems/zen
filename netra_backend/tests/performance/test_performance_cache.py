"""
Performance Tests - Cache and Query Optimization
Tests for memory cache and database query optimization functionality.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import asyncio
import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.core.performance_optimization_manager import (

# Add project root to path
    MemoryCache, QueryOptimizer
)


class TestMemoryCache:
    """Test memory cache performance and functionality."""
    
    @pytest.fixture
    def cache(self):
        """Create cache instance for testing."""
        return MemoryCache(max_size=100, default_ttl=60)
        
    async def test_cache_basic_operations(self, cache):
        """Test basic cache operations."""
        # Test set and get
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
        
        # Test non-existent key
        result = await cache.get("nonexistent")
        assert result is None
        
    async def test_cache_ttl_expiration(self, cache):
        """Test TTL expiration functionality."""
        # Set with short TTL
        await cache.set("temp_key", "temp_value", ttl=1)
        
        # Should exist immediately
        result = await cache.get("temp_key")
        assert result == "temp_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("temp_key")
        assert result is None
        
    async def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Add one more item to trigger eviction
        await cache.set("overflow_key", "overflow_value")
        
        # First item should be evicted
        result = await cache.get("key_0")
        assert result is None
        
        # Last item should still exist
        result = await cache.get("overflow_key")
        assert result == "overflow_value"
        
    async def test_cache_performance(self, cache):
        """Test cache performance under load."""
        # Populate cache
        items = 1000
        start_time = time.time()
        
        for i in range(items):
            await cache.set(f"perf_key_{i}", f"perf_value_{i}")
        
        set_time = time.time() - start_time
        
        # Read all items
        start_time = time.time()
        
        for i in range(items):
            result = await cache.get(f"perf_key_{i}")
            assert result == f"perf_value_{i}"
        
        get_time = time.time() - start_time
        
        # Performance expectations
        assert set_time < 1.0  # Should set 1000 items in under 1 second
        assert get_time < 0.5  # Should read 1000 items in under 0.5 seconds
        
        # Check cache stats
        stats = cache.get_stats()
        assert stats["total_hits"] >= items


class TestQueryOptimizer:
    """Test database query optimization."""
    
    @pytest.fixture
    def optimizer(self):
        """Create query optimizer for testing."""
        return QueryOptimizer(cache_size=100, cache_ttl=300)
        
    async def test_query_caching(self, optimizer):
        """Test query result caching."""
        query = "SELECT * FROM users WHERE id = %s"
        params = {"id": 123}
        
        # Mock executor
        mock_result = {"id": 123, "name": "Test User"}
        executor = AsyncMock(return_value=mock_result)
        
        # First execution should call executor
        result1 = await optimizer.execute_with_cache(query, params, executor)
        assert result1 == mock_result
        assert executor.call_count == 1
        
        # Second execution should use cache
        result2 = await optimizer.execute_with_cache(query, params, executor)
        assert result2 == mock_result
        assert executor.call_count == 1  # Still 1, not called again
        
    async def test_query_metrics_tracking(self, optimizer):
        """Test query performance metrics tracking."""
        # Use different queries to avoid caching
        base_query = "INSERT INTO test_table VALUES"
        
        # Mock slow executor
        async def slow_executor():
            await asyncio.sleep(0.1)  # 100ms
            return {"result": "data"}
        
        # Execute different queries multiple times to avoid cache hits
        for i in range(5):
            query = f"{base_query} ({i})"
            await optimizer.execute_with_cache(query, None, slow_executor)
        
        # Check that we have metrics for multiple queries
        assert len(optimizer.query_metrics) == 5
        
        # Check that total execution time is reasonable
        total_execution_time = sum(
            m.total_execution_time for m in optimizer.query_metrics.values()
        )
        assert total_execution_time >= 0.5
    
    def test_read_query_detection(self, optimizer):
        """Test read query detection logic."""
        assert optimizer._is_read_query("SELECT * FROM users")
        assert optimizer._is_read_query("  select id from table  ")
        assert optimizer._is_read_query("SHOW TABLES")
        assert optimizer._is_read_query("DESCRIBE table_name")
        
        assert not optimizer._is_read_query("INSERT INTO users VALUES (...)")
        assert not optimizer._is_read_query("UPDATE users SET name = 'test'")
        assert not optimizer._is_read_query("DELETE FROM users WHERE id = 1")
    
    def test_cache_ttl_determination(self, optimizer):
        """Test cache TTL determination logic."""
        # User-related queries should have shorter TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM users") == 60
        
        # Config queries should have longer TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM config") == 600
        
        # Audit queries should have very short TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM audit_logs") == 30
        
        # Default TTL for other queries
        assert optimizer._determine_cache_ttl("SELECT * FROM products") == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
