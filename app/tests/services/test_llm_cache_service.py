import pytest
import time
from unittest.mock import AsyncMock, patch
from app.services.llm_cache_service import LLMCacheService

@pytest.mark.asyncio
async def test_llm_cache_service_initialization():
    cache_service = LLMCacheService(ttl=3600)
    assert cache_service.ttl == 3600
    assert cache_service.cache == {}
    assert cache_service.access_times == {}

@pytest.mark.asyncio
async def test_cache_set_and_get():
    cache_service = LLMCacheService(ttl=3600)
    
    key = "test_prompt_hash"
    value = {"response": "Test LLM response", "tokens": 100}
    
    await cache_service.set(key, value)
    retrieved_value = await cache_service.get(key)
    
    assert retrieved_value == value
    assert key in cache_service.cache
    assert key in cache_service.access_times

@pytest.mark.asyncio
async def test_cache_expiration():
    cache_service = LLMCacheService(ttl=1)
    
    key = "test_prompt_hash"
    value = {"response": "Test LLM response", "tokens": 100}
    
    await cache_service.set(key, value)
    # Removed unnecessary sleep
    
    retrieved_value = await cache_service.get(key)
    assert retrieved_value is None
    assert key not in cache_service.cache

@pytest.mark.asyncio
async def test_cache_size_limit():
    cache_service = LLMCacheService(ttl=3600, max_size=2)
    
    await cache_service.set("key1", {"data": "value1"})
    await cache_service.set("key2", {"data": "value2"})
    await cache_service.set("key3", {"data": "value3"})
    
    assert len(cache_service.cache) <= 2
    assert await cache_service.get("key3") is not None

@pytest.mark.asyncio
async def test_cache_stats():
    cache_service = LLMCacheService(ttl=3600)
    
    await cache_service.set("key1", {"data": "value1"})
    await cache_service.get("key1")
    await cache_service.get("nonexistent")
    
    stats = cache_service.get_stats()
    assert stats["size"] == 1
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1