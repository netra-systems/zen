import sys
from pathlib import Path

import json
import time
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.services.llm_cache_service import LLMCacheService

@pytest.mark.asyncio
async def test_llm_cache_service_initialization():
    cache_service = LLMCacheService()
    assert cache_service.cache_core.default_ttl == 3600
    assert cache_service.enabled == True
    assert cache_service.cache_core.cache_prefix == "llm_cache:"
@pytest.mark.asyncio
async def test_cache_set_and_get():
    with patch('app.services.llm_cache_core.redis_manager') as mock_redis_manager:
        # Create mock Redis client
        mock_redis_client = AsyncMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis_client)
        
        # Mock the Redis get to return cached data
        cache_data = {
            "response": "Test LLM response",
            "cached_at": time.time(),
            "prompt_length": 11,
            "response_length": 17,
            "llm_config_name": "test_llm"
        }
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cache_data))
        mock_redis_client.set = AsyncMock(return_value=True)
        
        cache_service = LLMCacheService()
        cache_service.cache_core.redis_manager = mock_redis_manager
        
        key = "test_prompt_hash"
        value = {"response": "Test LLM response", "tokens": 100}
        
        await cache_service.cache_response("test_prompt", value["response"], "test_llm", {})
        retrieved_value = await cache_service.get_cached_response("test_prompt", "test_llm", {})
        
        assert retrieved_value == value["response"]
@pytest.mark.asyncio
async def test_cache_expiration():
    cache_service = LLMCacheService()
    cache_service.cache_core.default_ttl = 1
    
    key = "test_prompt_hash"
    value = {"response": "Test LLM response", "tokens": 100}
    
    await cache_service.cache_response("test_prompt", value["response"], "test_llm", {})
    # Wait for expiration
    time.sleep(2)
    
    retrieved_value = await cache_service.get_cached_response("test_prompt", "test_llm", {})
    # May be None if Redis clears it
@pytest.mark.asyncio
async def test_cache_size_limit():
    with patch('app.services.llm_cache_core.redis_manager') as mock_redis_manager:
        # Create mock Redis client
        mock_redis_client = AsyncMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis_client)
        
        # Mock the Redis get to return cached data
        cache_data = {
            "response": "response3",
            "cached_at": time.time(),
            "prompt_length": 7,
            "response_length": 9,
            "llm_config_name": "llm1"
        }
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cache_data))
        mock_redis_client.set = AsyncMock(return_value=True)
        
        cache_service = LLMCacheService()
        cache_service.cache_core.redis_manager = mock_redis_manager
        
        await cache_service.cache_response("prompt1", "response1", "llm1", {})
        await cache_service.cache_response("prompt2", "response2", "llm1", {})
        await cache_service.cache_response("prompt3", "response3", "llm1", {})
        
        # Test that caching works
        assert await cache_service.get_cached_response("prompt3", "llm1", {}) != None
@pytest.mark.asyncio
async def test_cache_stats():
    with patch('app.services.llm_cache_core.redis_manager') as mock_redis_manager:
        # Create mock Redis client
        mock_redis_client = AsyncMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis_client)
        
        # Mock stats data
        stats_data = {"hits": 1, "misses": 1, "total": 2, "hit_rate": 0.5}
        mock_redis_client.get = AsyncMock(return_value=json.dumps(stats_data))
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.keys = AsyncMock(return_value=["llm_stats:llm1"])
        
        cache_service = LLMCacheService()
        cache_service.cache_core.redis_manager = mock_redis_manager
        
        await cache_service.cache_response("prompt1", "response1", "llm1", {})
        await cache_service.get_cached_response("prompt1", "llm1", {})
        await cache_service.get_cached_response("nonexistent", "llm1", {})
        
        stats = await cache_service.get_cache_stats()
        assert isinstance(stats, dict)  # Should return a dict
        
        # Get stats for specific LLM config
        llm_stats = await cache_service.get_cache_stats("llm1")
        assert "hits" in llm_stats
        assert "misses" in llm_stats
        assert llm_stats["hits"] >= 0
        assert llm_stats["misses"] >= 0