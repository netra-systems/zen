"""LLM Response Caching Service

Caches LLM responses to reduce latency and cost by avoiding duplicate API calls.
Uses Redis for distributed caching with configurable TTL.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, Tuple
from app.redis_manager import redis_manager
from app.logging_config import central_logger
from app.config import settings

logger = central_logger.get_logger(__name__)

class LLMCacheService:
    """Service for caching LLM responses"""
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.enabled = getattr(settings, 'llm_cache_enabled', True)
        self.default_ttl = getattr(settings, 'llm_cache_ttl', 3600)  # 1 hour default
        self.cache_prefix = "llm_cache:"
        self.stats_prefix = "llm_stats:"
        
    def _generate_cache_key(self, prompt: str, llm_config_name: str, generation_config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique cache key for the prompt and configuration"""
        # Create a deterministic key from prompt and config
        key_data = {
            "prompt": prompt,
            "llm_config_name": llm_config_name,
            "generation_config": generation_config or {}
        }
        
        # Use SHA256 to create a consistent hash
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"{self.cache_prefix}{llm_config_name}:{key_hash[:16]}"
    
    async def get_cached_response(self, prompt: str, llm_config_name: str, generation_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get cached response if available"""
        if not self.enabled:
            return None
            
        try:
            cache_key = self._generate_cache_key(prompt, llm_config_name, generation_config)
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                logger.debug("Redis client not available, skipping cache lookup")
                return None
            
            # Verify we have the actual Redis client, not the manager
            if not hasattr(redis_client, 'get'):
                logger.error(f"Invalid redis client type: {type(redis_client)}, expected Redis client with 'get' method")
                return None
            
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                # Parse cached data
                cache_entry = json.loads(cached_data)
                response = cache_entry["response"]
                cached_at = cache_entry["cached_at"]
                
                # Update cache hit statistics
                await self._update_stats(llm_config_name, hit=True)
                
                logger.info(f"Cache hit for LLM {llm_config_name} (cached {time.time() - cached_at:.1f}s ago)")
                return response
            else:
                # Update cache miss statistics
                await self._update_stats(llm_config_name, hit=False)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")
            return None
    
    async def cache_response(self, prompt: str, response: str, llm_config_name: str, 
                           generation_config: Optional[Dict[str, Any]] = None, 
                           ttl: Optional[int] = None) -> bool:
        """Cache an LLM response"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(prompt, llm_config_name, generation_config)
            
            # Create cache entry with metadata
            cache_entry = {
                "response": response,
                "cached_at": time.time(),
                "prompt_length": len(prompt),
                "response_length": len(response),
                "llm_config_name": llm_config_name
            }
            
            # Use provided TTL or default
            cache_ttl = ttl or self.default_ttl
            
            # Store in Redis with TTL
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                logger.debug("Redis client not available, skipping cache storage")
                return False
            
            # Verify we have the actual Redis client, not the manager
            if not hasattr(redis_client, 'set'):
                logger.error(f"Invalid redis client type: {type(redis_client)}, expected Redis client with 'set' method")
                return False
            
            await redis_client.set(
                cache_key,
                json.dumps(cache_entry),
                ex=cache_ttl
            )
            
            logger.info(f"Cached response for LLM {llm_config_name} (TTL: {cache_ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    async def _update_stats(self, llm_config_name: str, hit: bool) -> None:
        """Update cache statistics"""
        try:
            stats_key = f"{self.stats_prefix}{llm_config_name}"
            
            # Get current stats or initialize
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                return
            stats_data = await redis_client.get(stats_key)
            if stats_data:
                stats = json.loads(stats_data)
            else:
                stats = {"hits": 0, "misses": 0, "total": 0}
            
            # Update stats
            stats["total"] += 1
            if hit:
                stats["hits"] += 1
            else:
                stats["misses"] += 1
            
            # Calculate hit rate
            stats["hit_rate"] = stats["hits"] / stats["total"] if stats["total"] > 0 else 0
            
            # Store updated stats (keep for 7 days)
            await redis_client.set(
                stats_key,
                json.dumps(stats),
                ex=604800  # 7 days
            )
        except Exception as e:
            logger.error(f"Error updating cache stats: {e}")
    
    async def get_cache_stats(self, llm_config_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if llm_config_name:
                # Get stats for specific LLM config
                stats_key = f"{self.stats_prefix}{llm_config_name}"
                redis_client = await self.redis_manager.get_client()
                if not redis_client:
                    return {"hits": 0, "misses": 0, "total": 0, "hit_rate": 0}
                stats_data = await redis_client.get(stats_key)
                if stats_data:
                    return json.loads(stats_data)
                else:
                    return {"hits": 0, "misses": 0, "total": 0, "hit_rate": 0}
            else:
                # Get stats for all LLM configs
                all_stats = {}
                pattern = f"{self.stats_prefix}*"
                redis_client = await self.redis_manager.get_client()
                if not redis_client:
                    return {}
                keys = await redis_client.keys(pattern)
                
                for key in keys:
                    config_name = key.replace(self.stats_prefix, "")
                    stats_data = await redis_client.get(key)
                    if stats_data:
                        all_stats[config_name] = json.loads(stats_data)
                
                return all_stats
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    async def clear_cache(self, llm_config_name: Optional[str] = None) -> int:
        """Clear cache entries"""
        try:
            if llm_config_name:
                # Clear cache for specific LLM config
                pattern = f"{self.cache_prefix}{llm_config_name}:*"
            else:
                # Clear all cache entries
                pattern = f"{self.cache_prefix}*"
            
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                return 0
            keys = await redis_client.keys(pattern)
            
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a specific pattern"""
        try:
            # Build the full pattern with cache prefix
            full_pattern = f"{self.cache_prefix}*{pattern}*"
            
            redis_client = await self.redis_manager.get_client()
            if not redis_client:
                return 0
            keys = await redis_client.keys(full_pattern)
            
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching pattern '{pattern}'")
                return deleted
            else:
                logger.info(f"No cache entries found matching pattern '{pattern}'")
                return 0
                
        except Exception as e:
            logger.error(f"Error clearing cache with pattern '{pattern}': {e}")
            return 0

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "size_mb": 0,
            "entries": 0
        }

    async def _get_redis_client_for_metrics(self):
        """Get Redis client or return None if unavailable"""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return None
        return redis_client

    async def _collect_cache_keys(self, redis_client) -> Tuple[list, list, int]:
        """Collect cache keys, stats keys, and entry count"""
        cache_keys = await redis_client.keys(f"{self.cache_prefix}*")
        stats_keys = await redis_client.keys(f"{self.stats_prefix}*")
        entries_count = len(cache_keys)
        return cache_keys, stats_keys, entries_count

    async def _aggregate_stats_totals(self, redis_client, stats_keys: list) -> Tuple[int, int, int]:
        """Aggregate total hits, misses, and requests from all stats keys"""
        total_hits = total_misses = total_requests = 0
        for key in stats_keys:
            stats_data = await redis_client.get(key)
            if stats_data:
                stats = json.loads(stats_data)
                total_hits += stats.get("hits", 0)
                total_misses += stats.get("misses", 0)
                total_requests += stats.get("total", 0)
        return total_hits, total_misses, total_requests

    def _calculate_hit_rate(self, total_hits: int, total_requests: int) -> float:
        """Calculate hit rate from totals"""
        return total_hits / total_requests if total_requests > 0 else 0

    async def _sample_cache_entry_sizes(self, redis_client, sample_keys: list) -> int:
        """Sample cache entries to estimate total size"""
        size_estimate = 0
        for key in sample_keys:
            data = await redis_client.get(key)
            if data:
                size_estimate += len(data.encode('utf-8'))
        return size_estimate

    async def _estimate_cache_size(self, redis_client, cache_keys: list, entries_count: int) -> float:
        """Estimate total cache size in MB"""
        if not cache_keys:
            return 0
        sample_size = min(10, len(cache_keys))
        sample_keys = cache_keys[:sample_size]
        size_estimate = await self._sample_cache_entry_sizes(redis_client, sample_keys)
        avg_size = size_estimate / sample_size if sample_size > 0 else 0
        total_size_bytes = avg_size * entries_count
        return total_size_bytes / (1024 * 1024)

    def _format_metrics_result(self, total_hits: int, total_misses: int, 
                              hit_rate: float, size_mb: float, entries_count: int) -> Dict[str, Any]:
        """Format the final metrics result"""
        return {
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate": round(hit_rate, 3),
            "size_mb": round(size_mb, 2),
            "entries": entries_count
        }

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics"""
        try:
            redis_client = await self._get_redis_client_for_metrics()
            if not redis_client:
                return self._get_empty_metrics()
            
            cache_keys, stats_keys, entries_count = await self._collect_cache_keys(redis_client)
            total_hits, total_misses, total_requests = await self._aggregate_stats_totals(redis_client, stats_keys)
            hit_rate = self._calculate_hit_rate(total_hits, total_requests)
            size_mb = await self._estimate_cache_size(redis_client, cache_keys, entries_count)
            return self._format_metrics_result(total_hits, total_misses, hit_rate, size_mb, entries_count)
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return self._get_empty_metrics()
    
    def should_cache_response(self, prompt: str, response: str) -> bool:
        """Determine if a response should be cached based on heuristics"""
        # Don't cache very short responses (likely errors)
        if len(response) < 10:
            return False
        
        # Don't cache if response indicates an error
        error_indicators = ["error", "failed", "exception", "invalid"]
        if any(indicator in response.lower() for indicator in error_indicators):
            return False
        
        # Don't cache streaming responses or very large responses
        if len(response) > 50000:  # 50KB limit
            return False
        
        return True

# Global instance
llm_cache_service = LLMCacheService()
