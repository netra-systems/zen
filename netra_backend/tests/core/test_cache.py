"""
Unit tests for cache
Coverage Target: 80%
Business Value: Platform stability and performance
"""

import pytest
from datetime import datetime, timedelta, timezone
from netra_backend.app.core.cache import (
    InMemoryCache,
    CacheManager,
    CacheEntry,
    CacheStats,
    cache_manager,
    get_cache_manager,
    get_default_cache
)

class TestInMemoryCache:
    """Test suite for InMemoryCache"""
    
    @pytest.fixture
    def cache_instance(self):
        """Create test cache instance"""
        return InMemoryCache(max_size=10, default_ttl=3600)
    
    @pytest.mark.asyncio
    async def test_initialization(self, cache_instance):
        """Test proper initialization"""
        assert cache_instance is not None
        assert cache_instance.max_size == 10
        assert cache_instance.default_ttl == 3600
        stats = await cache_instance.get_stats()
        assert stats.total_entries == 0
        assert stats.hit_count == 0
        assert stats.miss_count == 0
    
    @pytest.mark.asyncio
    async def test_basic_set_get(self, cache_instance):
        """Test basic set and get operations"""
        # Test setting and getting a value
        result = await cache_instance.set("test_key", "test_value")
        assert result is True
        
        value = await cache_instance.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_instance):
        """Test getting a non-existent key returns None"""
        value = await cache_instance.get("nonexistent_key")
        assert value is None
        
        stats = await cache_instance.get_stats()
        assert stats.miss_count == 1
    
    @pytest.mark.asyncio
    async def test_exists(self, cache_instance):
        """Test exists functionality"""
        await cache_instance.set("test_key", "test_value")
        
        assert await cache_instance.exists("test_key") is True
        assert await cache_instance.exists("nonexistent_key") is False
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_instance):
        """Test delete functionality"""
        await cache_instance.set("test_key", "test_value")
        assert await cache_instance.exists("test_key") is True
        
        result = await cache_instance.delete("test_key")
        assert result is True
        assert await cache_instance.exists("test_key") is False
        
        # Test deleting non-existent key
        result = await cache_instance.delete("nonexistent_key")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear(self, cache_instance):
        """Test clear functionality"""
        await cache_instance.set("key1", "value1")
        await cache_instance.set("key2", "value2")
        
        stats = await cache_instance.get_stats()
        assert stats.total_entries == 2
        
        await cache_instance.clear()
        stats = await cache_instance.get_stats()
        assert stats.total_entries == 0
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_instance):
        """Test TTL expiration"""
        # Set with very short TTL
        await cache_instance.set("expire_key", "expire_value", ttl=1)
        
        # Should exist immediately
        assert await cache_instance.exists("expire_key") is True
        value = await cache_instance.get("expire_key")
        assert value == "expire_value"
        
        # Wait for expiration (in real test might need to mock datetime)
        import asyncio
        await asyncio.sleep(1.1)
        
        # Should be expired now
        assert await cache_instance.exists("expire_key") is False
        value = await cache_instance.get("expire_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, cache_instance):
        """Test hit rate calculation"""
        await cache_instance.set("test_key", "test_value")
        
        # Hit
        await cache_instance.get("test_key")
        # Miss
        await cache_instance.get("nonexistent_key")
        
        stats = await cache_instance.get_stats()
        assert stats.hit_count == 1
        assert stats.miss_count == 1
        assert stats.hit_rate == 50.0


class TestCacheManager:
    """Test suite for CacheManager"""
    
    @pytest.fixture
    def manager_instance(self):
        """Create test manager instance"""
        return CacheManager()
    
    def test_initialization(self, manager_instance):
        """Test proper initialization"""
        assert manager_instance is not None
        assert manager_instance.get_cache() is None
    
    @pytest.mark.asyncio
    async def test_register_and_get_cache(self, manager_instance):
        """Test cache registration and retrieval"""
        cache = InMemoryCache()
        manager_instance.register_cache("test_cache", cache)
        
        retrieved = manager_instance.get_cache("test_cache")
        assert retrieved is cache
    
    @pytest.mark.asyncio
    async def test_default_cache(self, manager_instance):
        """Test default cache functionality"""
        cache = InMemoryCache()
        manager_instance.register_cache("default", cache, is_default=True)
        
        default = manager_instance.get_cache()
        assert default is cache
    
    @pytest.mark.asyncio
    async def test_manager_operations(self, manager_instance):
        """Test manager-level cache operations"""
        cache = InMemoryCache()
        manager_instance.register_cache("test", cache, is_default=True)
        
        # Test set/get through manager
        result = await manager_instance.set("test_key", "test_value")
        assert result is True
        
        value = await manager_instance.get("test_key")
        assert value == "test_value"


class TestGlobalCacheManager:
    """Test suite for global cache manager"""
    
    def test_get_cache_manager(self):
        """Test getting global cache manager"""
        manager = get_cache_manager()
        assert manager is not None
        assert isinstance(manager, CacheManager)
    
    def test_get_default_cache(self):
        """Test getting default cache"""
        cache = get_default_cache()
        assert cache is not None
        # Default cache should be registered during module initialization


class TestCacheModels:
    """Test suite for cache data models"""
    
    def test_cache_entry(self):
        """Test CacheEntry model"""
        entry = CacheEntry(
            key="test_key",
            value="test_value"
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.hit_count == 0
        assert entry.created_at is not None
    
    def test_cache_stats(self):
        """Test CacheStats model"""
        stats = CacheStats()
        assert stats.total_entries == 0
        assert stats.hit_rate == 0.0
        
        # Test hit rate calculation
        stats.hit_count = 3
        stats.miss_count = 7
        stats.calculate_hit_rate()
        assert stats.hit_rate == 30.0
