"""Cache Background Workers - Handles invalidation and eviction workers"""

import asyncio
from typing import List

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class CacheBackgroundWorkers:
    """Handles background worker operations for cache management"""
    
    def __init__(self, cache_manager):
        """Initialize with reference to cache manager"""
        self.cache_manager = cache_manager
        self._background_tasks: List[asyncio.Task] = []
        
    async def start_background_tasks(self) -> None:
        """Start all background worker tasks"""
        self._background_tasks.append(
            asyncio.create_task(self._invalidation_worker())
        )
        self._background_tasks.append(
            asyncio.create_task(self._eviction_worker())
        )

    async def stop_background_tasks(self) -> None:
        """Stop all background worker tasks"""
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    async def _invalidation_worker(self) -> None:
        """Background worker for cache invalidation"""
        await self._run_invalidation_loop()

    async def _run_invalidation_loop(self) -> None:
        """Run the main invalidation worker loop"""
        while True:
            try:
                await self._process_invalidation_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Invalidation worker error: {e}")

    async def _process_invalidation_queue(self) -> None:
        """Process one item from invalidation queue"""
        key = await self.cache_manager._invalidation_queue.get()
        await self.cache_manager.redis.delete(key)
        self._update_invalidation_stats()

    def _update_invalidation_stats(self) -> None:
        """Update invalidation statistics"""
        self.cache_manager.stats.invalidations += 1
        self.cache_manager.stats.cache_size = max(0, self.cache_manager.stats.cache_size - 1)

    async def _eviction_worker(self) -> None:
        """Background worker for cache eviction"""
        await self._run_eviction_loop()
    
    async def _run_eviction_loop(self) -> None:
        """Run the main eviction worker loop"""
        while True:
            try:
                await self._process_eviction_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Eviction worker error: {e}")
    
    async def _process_eviction_cycle(self) -> None:
        """Process one eviction cycle"""
        await asyncio.sleep(300)
        if self.cache_manager.stats.cache_size > self.cache_manager.max_size * 0.95:
            await self._trigger_eviction()

    async def _trigger_eviction(self) -> None:
        """Trigger cache eviction based on strategy"""
        evictions = await self.cache_manager.eviction_manager.trigger_eviction(self.cache_manager.strategy)
        self.cache_manager.stats.evictions += evictions