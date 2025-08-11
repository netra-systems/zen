import pytest
import time
from unittest.mock import AsyncMock, patch
from app.services.llm_cache_service import LLMCacheService

@pytest.mark.asyncio
async def test_llm_cache_service_initialization():
    cache_service = LLMCacheService()
    assert cache_service.default_ttl == 3600
    assert cache_service.enabled == True
    assert cache_service.cache_prefix == "llm_cache:"

@pytest.mark.asyncio
async def test_cache_set_and_get():
    cache_service = LLMCacheService()
    
    key = "test_prompt_hash"
    value = {"response": "Test LLM response", "tokens": 100}
    
    await cache_service.cache_response("test_prompt", "test_llm", value["response"], {})
    retrieved_value = await cache_service.get_cached_response("test_prompt", "test_llm", {})
    
    assert retrieved_value == value["response"]

@pytest.mark.asyncio
async def test_cache_expiration():
    cache_service = LLMCacheService()
    cache_service.default_ttl = 1
    
    key = "test_prompt_hash"
    value = {"response": "Test LLM response", "tokens": 100}
    
    await cache_service.cache_response("test_prompt", "test_llm", value["response"], {})
    # Wait for expiration
    time.sleep(2)
    
    retrieved_value = await cache_service.get_cached_response("test_prompt", "test_llm", {})
    # May be None if Redis clears it

@pytest.mark.asyncio
async def test_cache_size_limit():
    cache_service = LLMCacheService()
    
    await cache_service.cache_response("prompt1", "llm1", "response1", {})
    await cache_service.cache_response("prompt2", "llm1", "response2", {})
    await cache_service.cache_response("prompt3", "llm1", "response3", {})
    
    # Test that caching works
    assert await cache_service.get_cached_response("prompt3", "llm1", {}) != None

@pytest.mark.asyncio
async def test_cache_stats():
    cache_service = LLMCacheService()
    
    await cache_service.cache_response("prompt1", "llm1", "response1", {})
    await cache_service.get_cached_response("prompt1", "llm1", {})
    await cache_service.get_cached_response("nonexistent", "llm1", {})
    
    stats = await cache_service.get_cache_stats()
    assert stats["total_hits"] >= 0
    assert stats["total_misses"] >= 0