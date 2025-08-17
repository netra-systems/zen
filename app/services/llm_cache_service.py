"""LLM Response Caching Service.

Main orchestrator for LLM response caching using modular components.
Each function must be ≤8 lines as per architecture requirements.
"""

from typing import Optional, Dict, Any
from app.config import settings
from app.services.llm_cache_core import LLMCacheCore
from app.services.llm_cache_stats import LLMCacheStats
from app.services.llm_cache_metrics import LLMCacheMetrics
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LLMCacheService:
    """Main orchestrator for LLM response caching."""
    
    def __init__(self) -> None:
        """Initialize cache service with modular components."""
        self.enabled = getattr(settings, 'llm_cache_enabled', True)
        self.cache_core = LLMCacheCore()
        self.cache_stats = LLMCacheStats()
        self.cache_metrics = LLMCacheMetrics()

    async def get_cached_response(self, prompt: str, llm_config_name: str, 
                                generation_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get cached response if available."""
        if not self.enabled:
            return None
        response = await self.cache_core.get_cached_response(prompt, llm_config_name, generation_config)
        if response:
            await self.cache_stats.update_stats(llm_config_name, hit=True)
        else:
            await self.cache_stats.update_stats(llm_config_name, hit=False)
        return response

    async def cache_response(self, prompt: str, response: str, llm_config_name: str,
                           generation_config: Optional[Dict[str, Any]] = None,
                           ttl: Optional[int] = None) -> bool:
        """Cache an LLM response."""
        if not self.enabled:
            return False
        return await self.cache_core.cache_response(prompt, response, llm_config_name, generation_config, ttl)

    async def get_cache_stats(self, llm_config_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.cache_stats.get_cache_stats(llm_config_name)

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        return await self.cache_metrics.get_cache_metrics()

    async def clear_cache(self, llm_config_name: Optional[str] = None) -> int:
        """Clear cache entries."""
        return await self.cache_core.clear_cache(llm_config_name)

    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a specific pattern."""
        return await self.cache_core.clear_cache_pattern(pattern)

    def should_cache_response(self, prompt: str, response: str) -> bool:
        """Determine if a response should be cached based on heuristics."""
        return self.cache_core.should_cache_response(prompt, response)


# Global instance
llm_cache_service = LLMCacheService()
