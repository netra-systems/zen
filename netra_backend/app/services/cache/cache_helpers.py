"""Cache Helper Functions - Utility functions for cache operations"""

import hashlib
import json
import asyncio
from typing import Optional, Dict, Any, List
from netra_backend.app.logging_config import central_logger
from netra_backend.app.cache_models import CacheEntry

logger = central_logger.get_logger(__name__)

class CacheHelpers:
    """Helper functions for cache operations"""
    
    def __init__(self, cache_manager):
        """Initialize with reference to cache manager"""
        self.cache_manager = cache_manager
    
    def build_key_data(self, prompt: str, model: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build key data dictionary"""
        return {
            "prompt": prompt,
            "model": model,
            "params": params or {}
        }

    def hash_key_data(self, key_data: Dict[str, Any]) -> str:
        """Hash key data to generate cache key"""
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def build_entry_metadata(self, model: str, prompt: str, response: Any) -> Dict[str, Any]:
        """Build metadata for cache entry"""
        return {
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(str(response))
        }

    async def record_cache_hit(self, model: str, start_time: float) -> None:
        """Record cache hit statistics"""
        self.cache_manager.stats.hits += 1
        self.cache_manager.stats.total_latency += asyncio.get_event_loop().time() - start_time
        logger.debug(f"Cache hit for model {model}")

    async def handle_cache_miss(self, start_time: float) -> None:
        """Handle cache miss scenario"""
        self.cache_manager.stats.misses += 1
        self.cache_manager.stats.total_latency += asyncio.get_event_loop().time() - start_time
        return None

    def should_cache(self, prompt: str, response: Any) -> bool:
        """Determine if response should be cached"""
        response_str = str(response)
        return (self._check_response_size_valid(response_str) and
                self._check_response_not_error(response_str) and
                self._check_response_not_too_large(response_str))

    def _check_response_size_valid(self, response_str: str) -> bool:
        """Check if response size is valid for caching"""
        return len(response_str) >= 10

    def _check_response_not_error(self, response_str: str) -> bool:
        """Check if response is not an error"""
        error_indicators = ["error", "failed", "exception", "invalid", "rate_limit"]
        return not any(indicator in response_str.lower() for indicator in error_indicators)

    def _check_response_not_too_large(self, response_str: str) -> bool:
        """Check if response is not too large"""
        return len(response_str) <= 100000

    def calculate_ttl(self, prompt: str, response: Any) -> int:
        """Calculate adaptive TTL based on content"""
        if self.cache_manager.strategy.name == 'ADAPTIVE':
            return self._calculate_adaptive_ttl(prompt, response)
        return self.cache_manager.default_ttl

    def _calculate_adaptive_ttl(self, prompt: str, response: Any) -> int:
        """Calculate adaptive TTL with strategy logic"""
        base_ttl = self._adjust_ttl_for_prompt(prompt)
        base_ttl = self._adjust_ttl_for_response_size(base_ttl, response)
        return self._adjust_ttl_for_hit_rate(base_ttl)

    def _adjust_ttl_for_prompt(self, prompt: str) -> int:
        """Adjust TTL based on prompt content"""
        base_ttl = self.cache_manager.default_ttl
        if "current" in prompt.lower() or "latest" in prompt.lower():
            base_ttl = min(base_ttl, 300)
        return base_ttl

    def _adjust_ttl_for_response_size(self, base_ttl: int, response: Any) -> int:
        """Adjust TTL based on response size"""
        response_length = len(str(response))
        if response_length > 10000:
            base_ttl = int(base_ttl * 1.5)
        return base_ttl

    def _adjust_ttl_for_hit_rate(self, base_ttl: int) -> int:
        """Adjust TTL based on cache hit rate"""
        if self.cache_manager.stats.hit_rate > 0.7:
            return int(base_ttl * 1.2)
        elif self.cache_manager.stats.hit_rate < 0.3:
            return int(base_ttl * 0.8)
        return base_ttl