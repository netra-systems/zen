"""Performance optimization manager for comprehensive system optimization.

This module provides centralized performance optimization capabilities including:
- Database query optimization and caching
- Connection pool monitoring and tuning
- Memory usage optimization
- Async operation improvements
- WebSocket message batching
"""

import asyncio
from typing import Dict, Optional, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.performance_cache import MemoryCache
from netra_backend.app.performance_query_optimizer import QueryOptimizer
from netra_backend.app.performance_batch_processor import BatchProcessor

logger = central_logger.get_logger(__name__)

# Re-export components for backward compatibility
__all__ = [
    'MemoryCache',
    'QueryOptimizer', 
    'BatchProcessor',
    'PerformanceOptimizationManager',
    'performance_manager'
]


class PerformanceOptimizationManager:
    """Central performance optimization manager."""
    
    def __init__(self):
        self.query_optimizer = QueryOptimizer()
        self.batch_processor = BatchProcessor()
        self.connection_pool_monitor = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize performance optimization components."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Performance optimization manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown performance optimization components."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            await self._wait_for_cleanup_task()
        
        await self.batch_processor.flush_all()
        logger.info("Performance optimization manager shut down")
    
    async def _wait_for_cleanup_task(self) -> None:
        """Wait for cleanup task to complete."""
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._run_cleanup_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
    
    async def _run_cleanup_cycle(self) -> None:
        """Run a single cleanup cycle."""
        expired_count = await self.query_optimizer.cache.clear_expired()
        if expired_count > 0:
            logger.debug(f"Cleaned up {expired_count} expired cache entries")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            "query_optimizer": self.query_optimizer.get_performance_report(),
            "cache_stats": self.query_optimizer.cache.get_stats(),
            "batch_processor_stats": self.batch_processor.get_batch_stats()
        }


# Global instance
performance_manager = PerformanceOptimizationManager()