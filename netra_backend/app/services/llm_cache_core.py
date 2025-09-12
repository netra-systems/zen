"""LLM Cache Core Operations Module.

Handles core cache operations: get, set, clear cache entries.
Each function must be  <= 8 lines as per architecture requirements.
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class LLMCacheCore:
    """Core cache operations for LLM responses."""
    
    def __init__(self, cache_prefix: str = "llm_cache:", default_ttl: int = 3600) -> None:
        """Initialize core cache operations."""
        self.redis_manager = redis_manager
        self.cache_prefix = cache_prefix
        self.default_ttl = default_ttl

    def generate_cache_key(self, prompt: str, llm_config_name: str, 
                          generation_config: Optional[Dict[str, Any]] = None,
                          user_id: Optional[str] = None) -> str:
        """Generate a unique cache key for the prompt and configuration with user isolation."""
        key_data = self._prepare_key_data(prompt, llm_config_name, generation_config)
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        # Ensure user isolation by prefixing with user_id
        user_prefix = f"user:{user_id}:" if user_id else "system:"
        return f"{user_prefix}{self.cache_prefix}{llm_config_name}:{key_hash[:16]}"

    def _prepare_key_data(self, prompt: str, llm_config_name: str, 
                         generation_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare key data for hashing."""
        return {
            "prompt": prompt,
            "llm_config_name": llm_config_name,
            "generation_config": generation_config or {}
        }

    async def get_cached_response(self, prompt: str, llm_config_name: str, 
                                generation_config: Optional[Dict[str, Any]] = None,
                                user_id: Optional[str] = None) -> Optional[str]:
        """Get cached response if available with user isolation."""
        cache_key = self.generate_cache_key(prompt, llm_config_name, generation_config, user_id)
        redis_client = await self._get_redis_client()
        if not redis_client:
            return None
        return await self._retrieve_cached_data(redis_client, cache_key)

    async def _get_redis_client(self):
        """Get Redis client with validation."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            logger.debug("Redis client not available")
            return None
        return redis_client if hasattr(redis_client, 'get') else None

    async def _retrieve_cached_data(self, redis_client, cache_key: str) -> Optional[str]:
        """Retrieve and parse cached data."""
        try:
            cached_data = await redis_client.get(cache_key)
            return self._parse_cache_entry(cached_data) if cached_data else None
        except Exception as e:
            # Handle event loop closed gracefully - this is common during test teardown
            if "Event loop is closed" in str(e) or "RuntimeError" in str(type(e).__name__):
                logger.debug(f"Redis operation failed due to closed event loop during teardown: {e}")
                return None
            logger.error(f"Error retrieving cached response: {e}")
            return None

    def _parse_cache_entry(self, cached_data: str) -> str:
        """Parse cached data and return response."""
        cache_entry = json.loads(cached_data)
        cached_at = cache_entry["cached_at"]
        logger.info(f"Cache hit (cached {time.time() - cached_at:.1f}s ago)")
        return cache_entry["response"]

    async def cache_response(self, prompt: str, response: str, llm_config_name: str,
                           generation_config: Optional[Dict[str, Any]] = None,
                           ttl: Optional[int] = None, user_id: Optional[str] = None) -> bool:
        """Cache an LLM response with user isolation."""
        cache_key = self.generate_cache_key(prompt, llm_config_name, generation_config, user_id)
        cache_entry = self._create_cache_entry(response, prompt, llm_config_name)
        cache_ttl = ttl or self.default_ttl
        return await self._store_cache_entry(cache_key, cache_entry, cache_ttl)

    def _create_cache_entry(self, response: str, prompt: str, llm_config_name: str) -> Dict[str, Any]:
        """Create cache entry with metadata."""
        return {
            "response": response,
            "cached_at": time.time(),
            "prompt_length": len(prompt),
            "response_length": len(response),
            "llm_config_name": llm_config_name
        }

    async def _store_cache_entry(self, cache_key: str, cache_entry: Dict[str, Any], ttl: int) -> bool:
        """Store cache entry in Redis."""
        redis_client = await self._get_redis_client()
        if not redis_client or not hasattr(redis_client, 'set'):
            return False
        return await self._execute_cache_store(redis_client, cache_key, cache_entry, ttl)

    async def _execute_cache_store(self, redis_client, cache_key: str, 
                                 cache_entry: Dict[str, Any], ttl: int) -> bool:
        """Execute the cache storage operation."""
        try:
            await redis_client.set(cache_key, json.dumps(cache_entry), ex=ttl)
            logger.info(f"Cached response (TTL: {ttl}s)")
            return True
        except Exception as e:
            # Handle event loop closed gracefully - this is common during test teardown
            if "Event loop is closed" in str(e) or "RuntimeError" in str(type(e).__name__):
                logger.debug(f"Redis cache store failed due to closed event loop during teardown: {e}")
                return False
            logger.error(f"Error caching response: {e}")
            return False

    async def clear_cache(self, llm_config_name: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Clear cache entries with user isolation."""
        pattern = self._build_clear_pattern(llm_config_name, user_id)
        redis_client = await self._get_redis_client()
        if not redis_client:
            return 0
        return await self._execute_cache_clear(redis_client, pattern)

    def _build_clear_pattern(self, llm_config_name: Optional[str], user_id: Optional[str] = None) -> str:
        """Build pattern for cache clearing with user isolation."""
        user_prefix = f"user:{user_id}:" if user_id else "user:*:"
        if llm_config_name:
            return f"{user_prefix}{self.cache_prefix}{llm_config_name}:*"
        return f"{user_prefix}{self.cache_prefix}*"

    async def _execute_cache_clear(self, redis_client, pattern: str) -> int:
        """Execute cache clearing operation."""
        try:
            keys = await redis_client.keys(pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted
            return 0
        except Exception as e:
            # Handle event loop closed gracefully - this is common during test teardown
            if "Event loop is closed" in str(e) or "RuntimeError" in str(type(e).__name__):
                logger.debug(f"Redis cache clear failed due to closed event loop during teardown: {e}")
                return 0
            logger.error(f"Error clearing cache: {e}")
            return 0

    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a specific pattern."""
        full_pattern = f"{self.cache_prefix}*{pattern}*"
        redis_client = await self._get_redis_client()
        if not redis_client:
            return 0
        return await self._execute_pattern_clear(redis_client, full_pattern, pattern)

    async def _execute_pattern_clear(self, redis_client, full_pattern: str, original_pattern: str) -> int:
        """Execute pattern-based cache clearing."""
        try:
            keys = await redis_client.keys(full_pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching pattern '{original_pattern}'")
                return deleted
            logger.info(f"No cache entries found matching pattern '{original_pattern}'")
            return 0
        except Exception as e:
            # Handle event loop closed gracefully - this is common during test teardown
            if "Event loop is closed" in str(e) or "RuntimeError" in str(type(e).__name__):
                logger.debug(f"Redis pattern clear failed due to closed event loop during teardown: {e}")
                return 0
            logger.error(f"Error clearing cache with pattern '{original_pattern}': {e}")
            return 0

    def should_cache_response(self, prompt: str, response: str) -> bool:
        """Determine if a response should be cached based on heuristics."""
        if len(response) < 10:
            return False
        error_indicators = ["error", "failed", "exception", "invalid"]
        if any(indicator in response.lower() for indicator in error_indicators):
            return False
        return len(response) <= 50000  # 50KB limit