"""LLM Cache Metrics Module.

Handles comprehensive cache metrics collection and reporting.
Each function must be  <= 8 lines as per architecture requirements.
"""

import json
from typing import Any, Dict, List, Tuple

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class LLMCacheMetrics:
    """Comprehensive cache metrics collection."""
    
    def __init__(self, cache_prefix: str = "llm_cache:", stats_prefix: str = "llm_stats:") -> None:
        """Initialize cache metrics collector."""
        self.redis_manager = redis_manager
        self.cache_prefix = cache_prefix
        self.stats_prefix = stats_prefix

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        try:
            redis_client = await self._get_redis_client_for_metrics()
            if not redis_client:
                return self._get_empty_metrics()
            return await self._collect_comprehensive_metrics(redis_client)
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return self._get_empty_metrics()

    async def _get_redis_client_for_metrics(self):
        """Get Redis client or return None if unavailable."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return None
        return redis_client

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "size_mb": 0,
            "entries": 0
        }

    async def _collect_comprehensive_metrics(self, redis_client) -> Dict[str, Any]:
        """Collect all cache metrics."""
        cache_keys, stats_keys, entries_count = await self._collect_cache_keys(redis_client)
        total_hits, total_misses, total_requests = await self._aggregate_stats_totals(redis_client, stats_keys)
        hit_rate = self._calculate_hit_rate(total_hits, total_requests)
        size_mb = await self._estimate_cache_size(redis_client, cache_keys, entries_count)
        return self._format_metrics_result(total_hits, total_misses, hit_rate, size_mb, entries_count)

    async def _collect_cache_keys(self, redis_client) -> Tuple[List, List, int]:
        """Collect cache keys, stats keys, and entry count."""
        cache_keys = await redis_client.keys(f"{self.cache_prefix}*")
        stats_keys = await redis_client.keys(f"{self.stats_prefix}*")
        entries_count = len(cache_keys)
        return cache_keys, stats_keys, entries_count

    async def _aggregate_stats_totals(self, redis_client, stats_keys: List) -> Tuple[int, int, int]:
        """Aggregate total hits, misses, and requests from all stats keys."""
        total_hits = total_misses = total_requests = 0
        for key in stats_keys:
            hits, misses, requests = await self._get_stats_from_key(redis_client, key)
            total_hits += hits
            total_misses += misses
            total_requests += requests
        return total_hits, total_misses, total_requests

    async def _get_stats_from_key(self, redis_client, key: str) -> Tuple[int, int, int]:
        """Get stats data from a single key."""
        stats_data = await redis_client.get(key)
        if stats_data:
            stats = json.loads(stats_data)
            return stats.get("hits", 0), stats.get("misses", 0), stats.get("total", 0)
        return 0, 0, 0

    def _calculate_hit_rate(self, total_hits: int, total_requests: int) -> float:
        """Calculate hit rate from totals."""
        return total_hits / total_requests if total_requests > 0 else 0

    async def _estimate_cache_size(self, redis_client, cache_keys: List, entries_count: int) -> float:
        """Estimate total cache size in MB."""
        if not cache_keys:
            return 0
        sample_size = min(10, len(cache_keys))
        sample_keys = cache_keys[:sample_size]
        size_estimate = await self._sample_cache_entry_sizes(redis_client, sample_keys)
        return self._calculate_total_size_mb(size_estimate, sample_size, entries_count)

    async def _sample_cache_entry_sizes(self, redis_client, sample_keys: List) -> int:
        """Sample cache entries to estimate total size."""
        size_estimate = 0
        for key in sample_keys:
            data = await redis_client.get(key)
            if data:
                size_estimate += len(data.encode('utf-8'))
        return size_estimate

    def _calculate_total_size_mb(self, size_estimate: int, sample_size: int, entries_count: int) -> float:
        """Calculate total size in MB from sample."""
        avg_size = size_estimate / sample_size if sample_size > 0 else 0
        total_size_bytes = avg_size * entries_count
        return total_size_bytes / (1024 * 1024)

    def _format_metrics_result(self, total_hits: int, total_misses: int, 
                              hit_rate: float, size_mb: float, entries_count: int) -> Dict[str, Any]:
        """Format the final metrics result."""
        return {
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate": round(hit_rate, 3),
            "size_mb": round(size_mb, 2),
            "entries": entries_count
        }