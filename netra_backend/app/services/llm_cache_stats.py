"""LLM Cache Statistics Module.

Handles cache statistics tracking and retrieval.
Each function must be  <= 8 lines as per architecture requirements.
"""

import json
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class LLMCacheStats:
    """Statistics tracking for LLM cache operations."""
    
    def __init__(self, stats_prefix: str = "llm_stats:") -> None:
        """Initialize cache statistics tracker."""
        self.redis_manager = redis_manager
        self.stats_prefix = stats_prefix

    async def update_stats(self, llm_config_name: str, hit: bool) -> None:
        """Update cache statistics."""
        stats_key = f"{self.stats_prefix}{llm_config_name}"
        redis_client = await self._get_redis_client()
        if not redis_client:
            return
        await self._update_stats_data(redis_client, stats_key, hit)

    async def _get_redis_client(self):
        """Get Redis client for stats operations."""
        return await self.redis_manager.get_client()

    async def _update_stats_data(self, redis_client, stats_key: str, hit: bool) -> None:
        """Update stats data and store in Redis."""
        try:
            stats = await self._get_current_stats(redis_client, stats_key)
            updated_stats = self._increment_stats(stats, hit)
            await self._store_updated_stats(redis_client, stats_key, updated_stats)
        except Exception as e:
            logger.error(f"Error updating cache stats: {e}")

    async def _get_current_stats(self, redis_client, stats_key: str) -> Dict[str, int]:
        """Get current stats or initialize empty stats."""
        stats_data = await redis_client.get(stats_key)
        if stats_data:
            return json.loads(stats_data)
        return {"hits": 0, "misses": 0, "total": 0}

    def _increment_stats(self, stats: Dict[str, int], hit: bool) -> Dict[str, Any]:
        """Increment stats counters and calculate hit rate."""
        stats["total"] += 1
        if hit:
            stats["hits"] += 1
        else:
            stats["misses"] += 1
        stats["hit_rate"] = stats["hits"] / stats["total"] if stats["total"] > 0 else 0
        return stats

    async def _store_updated_stats(self, redis_client, stats_key: str, stats: Dict[str, Any]) -> None:
        """Store updated stats with 7-day TTL."""
        await redis_client.set(
            stats_key,
            json.dumps(stats),
            ex=604800  # 7 days
        )

    async def get_cache_stats(self, llm_config_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            return self._get_empty_stats()
        
        if llm_config_name:
            return await self._get_single_config_stats(redis_client, llm_config_name)
        return await self._get_all_config_stats(redis_client)

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure."""
        return {"hits": 0, "misses": 0, "total": 0, "hit_rate": 0}

    async def _get_single_config_stats(self, redis_client, llm_config_name: str) -> Dict[str, Any]:
        """Get stats for a specific LLM config."""
        try:
            stats_key = f"{self.stats_prefix}{llm_config_name}"
            stats_data = await redis_client.get(stats_key)
            return json.loads(stats_data) if stats_data else self._get_empty_stats()
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self._get_empty_stats()

    async def _get_all_config_stats(self, redis_client) -> Dict[str, Any]:
        """Get stats for all LLM configs."""
        try:
            pattern = f"{self.stats_prefix}*"
            keys = await redis_client.keys(pattern)
            return await self._collect_all_stats(redis_client, keys)
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    async def _collect_all_stats(self, redis_client, keys: list) -> Dict[str, Any]:
        """Collect stats from all keys."""
        all_stats = {}
        for key in keys:
            config_name = key.replace(self.stats_prefix, "")
            stats_data = await redis_client.get(key)
            if stats_data:
                all_stats[config_name] = json.loads(stats_data)
        return all_stats