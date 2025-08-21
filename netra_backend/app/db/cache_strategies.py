"""Database Query Cache Strategies

Eviction and caching strategies for the query cache system.
"""

import asyncio
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

from netra_backend.app.logging_config import central_logger
from netra_backend.app.cache_config import CacheStrategy, CacheMetrics, QueryCacheConfig

logger = central_logger.get_logger(__name__)


class LRUEvictionStrategy:
    """Least Recently Used eviction strategy."""
    
    @staticmethod
    async def evict_lru_entries(redis, cache_prefix: str, evict_count: int, metrics: CacheMetrics) -> None:
        """Evict least recently used entries."""
        cache_keys = await redis.keys(f"{cache_prefix}*")
        
        if len(cache_keys) > evict_count:
            keys_to_evict = cache_keys[:evict_count]
            await redis.delete(*keys_to_evict)
            
            metrics.evictions += len(keys_to_evict)
            metrics.cache_size -= len(keys_to_evict)

    @staticmethod
    async def execute_lru_eviction(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute LRU eviction strategy."""
        try:
            evict_count = config.max_cache_size // 10  # Evict 10%
            await LRUEvictionStrategy.evict_lru_entries(redis, config.cache_prefix, evict_count, metrics)
        except Exception as e:
            logger.error(f"Error during LRU eviction: {e}")


class TTLEvictionStrategy:
    """Time To Live eviction strategy."""
    
    @staticmethod
    async def update_cache_size_metrics(redis, cache_prefix: str, metrics: CacheMetrics) -> None:
        """Update cache size metrics after TTL eviction."""
        actual_size = len(await redis.keys(f"{cache_prefix}*"))
        evicted = metrics.cache_size - actual_size
        
        if evicted > 0:
            metrics.evictions += evicted
            metrics.cache_size = actual_size

    @staticmethod
    async def execute_ttl_eviction(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute TTL eviction strategy."""
        try:
            # Redis handles TTL automatically, but we can clean up our metrics
            await TTLEvictionStrategy.update_cache_size_metrics(redis, config.cache_prefix, metrics)
        except Exception as e:
            logger.error(f"Error during TTL eviction: {e}")


class AdaptiveEvictionStrategy:
    """Adaptive eviction strategy combining LRU and TTL."""
    
    @staticmethod
    async def execute_expired_cleanup(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute expired entries cleanup."""
        await TTLEvictionStrategy.execute_ttl_eviction(redis, config, metrics)

    @staticmethod
    async def execute_lru_if_needed(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute LRU eviction if cache is still too large."""
        if metrics.cache_size > config.max_cache_size:
            await LRUEvictionStrategy.execute_lru_eviction(redis, config, metrics)

    @staticmethod
    async def execute_adaptive_eviction(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute adaptive eviction strategy."""
        try:
            await AdaptiveEvictionStrategy.execute_expired_cleanup(redis, config, metrics)
            await AdaptiveEvictionStrategy.execute_lru_if_needed(redis, config, metrics)
        except Exception as e:
            logger.error(f"Error during adaptive eviction: {e}")


class EvictionStrategyFactory:
    """Factory for creating eviction strategies."""
    
    @staticmethod
    async def execute_eviction(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute eviction based on configured strategy."""
        if config.strategy == CacheStrategy.LRU:
            await LRUEvictionStrategy.execute_lru_eviction(redis, config, metrics)
        elif config.strategy == CacheStrategy.TTL:
            await TTLEvictionStrategy.execute_ttl_eviction(redis, config, metrics)
        elif config.strategy == CacheStrategy.ADAPTIVE:
            await AdaptiveEvictionStrategy.execute_adaptive_eviction(redis, config, metrics)


class CacheCleanupWorker:
    """Background worker for cache cleanup."""
    
    @staticmethod
    async def execute_cleanup_cycle(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute one cleanup cycle."""
        await asyncio.sleep(300)  # Every 5 minutes
        await TTLEvictionStrategy.execute_ttl_eviction(redis, config, metrics)

    @staticmethod
    async def handle_cleanup_error(error: Exception) -> None:
        """Handle cleanup worker error."""
        logger.error(f"Cache cleanup worker error: {error}")

    @staticmethod
    async def run_cleanup_worker(
        redis, 
        config: QueryCacheConfig, 
        metrics: CacheMetrics, 
        running_flag=lambda: True
    ) -> None:
        """Run background cache cleanup worker."""
        while running_flag():
            try:
                await CacheCleanupWorker.execute_cleanup_cycle(redis, config, metrics)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await CacheCleanupWorker.handle_cleanup_error(e)


class CacheMetricsWorker:
    """Background worker for metrics collection."""
    
    @staticmethod
    async def update_cache_size_metric(redis, cache_prefix: str, metrics: CacheMetrics) -> None:
        """Update cache size metric."""
        actual_size = len(await redis.keys(f"{cache_prefix}*"))
        metrics.cache_size = actual_size

    @staticmethod
    async def execute_metrics_cycle(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> None:
        """Execute one metrics collection cycle."""
        await asyncio.sleep(60)  # Every minute
        await CacheMetricsWorker.update_cache_size_metric(redis, config.cache_prefix, metrics)

    @staticmethod
    async def handle_metrics_error(error: Exception) -> None:
        """Handle metrics worker error."""
        logger.error(f"Cache metrics worker error: {error}")

    @staticmethod
    async def run_metrics_worker(
        redis, 
        config: QueryCacheConfig, 
        metrics: CacheMetrics, 
        running_flag=lambda: True
    ) -> None:
        """Run background metrics collection worker."""
        while running_flag():
            try:
                await CacheMetricsWorker.execute_metrics_cycle(redis, config, metrics)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await CacheMetricsWorker.handle_metrics_error(e)


class QueryPatternTracker:
    """Track query patterns and performance."""
    
    def __init__(self):
        self.query_patterns: Dict[str, int] = {}
        self.query_durations: Dict[str, List[float]] = {}

    def track_query_pattern(self, pattern: str) -> None:
        """Track query pattern frequency."""
        self.query_patterns[pattern] = self.query_patterns.get(pattern, 0) + 1

    def _ensure_pattern_list_exists(self, pattern: str) -> None:
        """Ensure pattern list exists in query_durations."""
        if pattern not in self.query_durations:
            self.query_durations[pattern] = []

    def _trim_old_durations(self, pattern: str) -> None:
        """Trim old durations to keep only recent 10."""
        if len(self.query_durations[pattern]) > 10:
            self.query_durations[pattern] = self.query_durations[pattern][-10:]

    def track_query_duration(self, pattern: str, duration: float) -> None:
        """Track query duration for pattern."""
        self._ensure_pattern_list_exists(pattern)
        self.query_durations[pattern].append(duration)
        self._trim_old_durations(pattern)

    def get_top_query_patterns(self, limit: int = 10) -> List[tuple]:
        """Get top query patterns by frequency."""
        return sorted(
            self.query_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def _calculate_pattern_averages(self) -> Dict[str, float]:
        """Calculate average durations for all patterns."""
        avg_durations = {}
        for pattern, durations in self.query_durations.items():
            if durations:
                avg_durations[pattern] = sum(durations) / len(durations)
        return avg_durations

    def _sort_and_limit_averages(self, avg_durations: Dict[str, float], limit: int) -> List[tuple]:
        """Sort averages by duration and apply limit."""
        return sorted(
            avg_durations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def get_avg_durations(self, limit: int = 10) -> List[tuple]:
        """Get average durations for patterns."""
        avg_durations = self._calculate_pattern_averages()
        return self._sort_and_limit_averages(avg_durations, limit)

    def build_metrics_summary(self) -> Dict[str, Any]:
        """Build query pattern metrics summary."""
        return {
            'top_query_patterns': self.get_top_query_patterns(),
            'avg_query_durations': self.get_avg_durations()
        }


class CacheTaskManager:
    """Manage background cache tasks."""
    
    def __init__(self):
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_background_tasks(
        self, 
        redis, 
        config: QueryCacheConfig, 
        metrics: CacheMetrics
    ) -> None:
        """Start background tasks."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(
            CacheCleanupWorker.run_cleanup_worker(redis, config, metrics, lambda: self._running)
        )
        
        if config.metrics_enabled:
            self._metrics_task = asyncio.create_task(
                CacheMetricsWorker.run_metrics_worker(redis, config, metrics, lambda: self._running)
            )

    async def _cancel_task(self, task: Optional[asyncio.Task]) -> None:
        """Cancel a background task."""
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        self._running = False
        await self._cancel_task(self._cleanup_task)
        await self._cancel_task(self._metrics_task)