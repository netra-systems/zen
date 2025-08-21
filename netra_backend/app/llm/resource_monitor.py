"""Resource monitoring for LLM operations.

Monitors and manages LLM resource usage including
request pools, cache managers, and performance metrics.
"""

import asyncio
from typing import Any, Dict

from netra_backend.app.llm.resource_cache import LLMCacheManager
from netra_backend.app.llm.resource_pool import RequestPool
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ResourceMonitor:
    """Monitors and manages LLM resource usage."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.request_pools: Dict[str, RequestPool] = {}
        self.cache_managers: Dict[str, LLMCacheManager] = {}
        self._metrics: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    def get_request_pool(self, config_name: str) -> RequestPool:
        """Get or create request pool for config."""
        if config_name not in self.request_pools:
            self.request_pools[config_name] = self._create_pool(config_name)
        return self.request_pools[config_name]
    
    def _create_pool(self, config_name: str) -> RequestPool:
        """Create request pool based on config type."""
        if 'fast' in config_name.lower():
            return RequestPool(max_concurrent=10, requests_per_minute=120)
        elif 'slow' in config_name.lower():
            return RequestPool(max_concurrent=3, requests_per_minute=30)
        return RequestPool(max_concurrent=5, requests_per_minute=60)
    
    def get_cache_manager(self, config_name: str) -> LLMCacheManager:
        """Get or create cache manager for config."""
        if config_name not in self.cache_managers:
            self.cache_managers[config_name] = LLMCacheManager()
        return self.cache_managers[config_name]
    
    async def record_request(self, config_name: str, 
                            success: bool, duration_ms: float) -> None:
        """Record request metrics."""
        async with self._lock:
            if config_name not in self._metrics:
                self._metrics[config_name] = self._init_metrics()
            self._update_request_metrics(config_name, success, duration_ms)
    
    def _update_request_metrics(self, config_name: str, 
                               success: bool, duration_ms: float) -> None:
        """Update request metrics for config."""
        metrics = self._metrics[config_name]
        metrics['total_requests'] += 1
        metrics['total_duration_ms'] += duration_ms
        self._update_success_metrics(metrics, success)
    
    def _update_success_metrics(self, metrics: Dict, success: bool) -> None:
        """Update success/failure metrics."""
        if success:
            metrics['successful_requests'] += 1
        else:
            metrics['failed_requests'] += 1
    
    def _init_metrics(self) -> Dict:
        """Initialize metrics dictionary."""
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration_ms': 0
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get resource usage metrics."""
        async with self._lock:
            pools_data = self._collect_pool_metrics()
            caches_data = await self._collect_cache_metrics()
            return {
                'pools': pools_data,
                'caches': caches_data,
                'metrics': self._metrics.copy()
            }
    
    def _collect_pool_metrics(self) -> Dict[str, Dict]:
        """Collect pool metrics data."""
        return {
            name: {
                'max_concurrent': pool.max_concurrent,
                'requests_per_minute': pool.requests_per_minute
            }
            for name, pool in self.request_pools.items()
        }
    
    async def _collect_cache_metrics(self) -> Dict[str, Any]:
        """Collect cache metrics data."""
        return {
            name: await cache.get_stats()
            for name, cache in self.cache_managers.items()
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        for cache in self.cache_managers.values():
            await cache.clear()
        self._metrics.clear()
        logger.info("Resource manager cleaned up")


# Global resource monitor instance
resource_monitor = ResourceMonitor()