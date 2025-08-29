"""
Unit tests for cache
Coverage Target: 80%
Business Value: Platform stability and performance
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.core.cache import InMemoryCache, CacheManager, CacheStats

class TestInMemoryCache:
    """Test suite for InMemoryCache"""
    
    @pytest.fixture
    async def cache(self):
        """Create test cache instance"""
        return InMemoryCache(max_size=10, default_ttl=60)
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test proper initialization"""
        cache = InMemoryCache(max_size=10, default_ttl=60)
        assert cache is not None
        assert cache.max_size == 10
        assert cache.default_ttl == 60
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations"""
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation"""
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        deleted = await cache.delete("key1")
        assert deleted is True
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists check"""
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clear operation"""
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None


class TestCacheManager:
    """Test suite for CacheManager"""
    
    @pytest.fixture
    def manager(self):
        """Create test manager instance"""
        return CacheManager()
    
    def test_initialization(self, manager):
        """Test proper initialization"""
        assert manager is not None
        assert manager._caches == {}
    
    def test_register_cache(self, manager):
        """Test cache registration"""
        cache = InMemoryCache()
        manager.register_cache("test", cache, is_default=True)
        assert manager.get_cache("test") == cache
        assert manager._default_cache == cache
    
    @pytest.mark.asyncio
    async def test_get_set_via_manager(self, manager):
        """Test get/set through manager"""
        cache = InMemoryCache()
        manager.register_cache("test", cache, is_default=True)
        await manager.set("key1", "value1")
        result = await manager.get("key1")
        assert result == "value1"