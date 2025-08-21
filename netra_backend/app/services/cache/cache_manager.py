"""LLM Cache Manager - Main cache management service with intelligent caching strategies"""

import asyncio
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.cache.cache_eviction import CacheEvictionManager
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from netra_backend.app.services.cache.cache_models import CacheEntry, CacheStrategy
from netra_backend.app.services.cache.cache_serialization import CacheSerializer
from netra_backend.app.services.cache.cache_statistics import CacheStatistics
from netra_backend.app.services.cache.cache_workers import CacheBackgroundWorkers

logger = central_logger.get_logger(__name__)

class LLMCacheManager:
    """Advanced cache manager for LLM responses"""
    
    def __init__(self,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 max_size: int = 1000,
                 default_ttl: int = 3600):
        self._init_core_config(strategy, max_size, default_ttl)
        self._init_cache_components()
        self._init_background_systems()

    def _init_core_config(self, strategy: CacheStrategy, max_size: int, default_ttl: int) -> None:
        """Initialize core configuration"""
        self.redis = redis_manager
        self.strategy = strategy
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = CacheStatistics()

    def _init_cache_components(self) -> None:
        """Initialize cache components"""
        self.cache_prefix = "llm_cache_v2:"
        self.tag_prefix = "llm_tag:"
        self.serializer = CacheSerializer()
        self.eviction_manager = CacheEvictionManager(
            self.redis, self.cache_prefix, self.max_size
        )

    def _init_background_systems(self) -> None:
        """Initialize background task systems"""
        self._invalidation_queue: asyncio.Queue = asyncio.Queue()
        self.workers = CacheBackgroundWorkers(self)
        self.helpers = CacheHelpers(self)
    
    async def start(self) -> None:
        """Start background tasks"""
        await self.workers.start_background_tasks()
        logger.info("LLM cache manager started")
    
    async def stop(self) -> None:
        """Stop background tasks"""
        await self.workers.stop_background_tasks()
        logger.info("LLM cache manager stopped")
    
    def _generate_key(self, 
                     prompt: str, 
                     model: str, 
                     params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from parameters"""
        key_data = self.helpers.build_key_data(prompt, model, params)
        key_hash = self.helpers.hash_key_data(key_data)
        return f"{self.cache_prefix}{model}:{key_hash[:32]}"
    
    async def get_cached_response(self,
                                 prompt: str,
                                 model: str,
                                 params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached response if available"""
        start_time = asyncio.get_event_loop().time()
        try:
            return await self._try_get_cached_response(prompt, model, params, start_time)
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None

    async def _try_get_cached_response(self, prompt: str, model: str, 
                                      params: Optional[Dict[str, Any]], start_time: float) -> Optional[Any]:
        """Try to get cached response with error handling"""
        cache_key = self._generate_key(prompt, model, params)
        cached_data = await self.redis.get(cache_key)
        return await self._process_cached_data(cached_data, cache_key, model, start_time)

    async def _process_cached_data(self, cached_data: Optional[str], cache_key: str, 
                                  model: str, start_time: float) -> Optional[Any]:
        """Process cached data and return result"""
        if cached_data:
            return await self._handle_cache_hit(cached_data, cache_key, model, start_time)
        return await self.helpers.handle_cache_miss(start_time)

    async def _handle_cache_hit(self, cached_data: str, cache_key: str, 
                               model: str, start_time: float) -> Optional[Any]:
        """Handle cache hit scenario"""
        entry = self.serializer.deserialize_entry(cached_data)
        if not entry.is_expired():
            return await self._process_valid_entry(entry, cache_key, model, start_time)
        await self.invalidate_key(cache_key)
        return await self.helpers.handle_cache_miss(start_time)

    async def _process_valid_entry(self, entry: CacheEntry, cache_key: str, 
                                  model: str, start_time: float) -> Any:
        """Process valid cache entry"""
        entry.update_access()
        await self._update_entry(cache_key, entry)
        await self.helpers.record_cache_hit(model, start_time)
        return entry.value
    
    async def cache_response(self,
                           prompt: str,
                           response: Any,
                           model: str,
                           params: Optional[Dict[str, Any]] = None,
                           ttl: Optional[int] = None,
                           tags: Optional[List[str]] = None) -> bool:
        """Cache a response with optional tags"""
        try:
            return await self._try_cache_response(prompt, response, model, params, ttl, tags)
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    async def _try_cache_response(self, prompt: str, response: Any, model: str,
                                 params: Optional[Dict[str, Any]], ttl: Optional[int], 
                                 tags: Optional[List[str]]) -> bool:
        """Try to cache response with validation"""
        if not self.helpers.should_cache(prompt, response):
            return False
        return await self._execute_cache_storage(prompt, response, model, params, ttl, tags)

    async def _execute_cache_storage(self, prompt: str, response: Any, model: str,
                                    params: Optional[Dict[str, Any]], ttl: Optional[int], 
                                    tags: Optional[List[str]]) -> bool:
        """Execute cache storage process"""
        cache_key = self._generate_key(prompt, model, params)
        entry = self._create_cache_entry(cache_key, response, model, prompt, ttl, tags)
        await self._store_cache_entry(cache_key, entry)
        await self._handle_tags_and_stats(cache_key, tags, model)
        return True
    
    def _create_cache_entry(self, cache_key: str, response: Any, model: str, 
                           prompt: str, ttl: Optional[int], tags: Optional[List[str]]) -> CacheEntry:
        """Create cache entry with metadata"""
        metadata = self.helpers.build_entry_metadata(model, prompt, response)
        return CacheEntry(
            key=cache_key, value=response, ttl=ttl or self.helpers.calculate_ttl(prompt, response), 
            tags=tags or [], metadata=metadata
        )
    
    async def _store_cache_entry(self, cache_key: str, entry: CacheEntry) -> None:
        """Store cache entry in Redis"""
        serialized = self.serializer.serialize_entry(entry)
        await self.redis.set(
            cache_key,
            serialized,
            ex=entry.ttl
        )
    
    async def _handle_tags_and_stats(self, cache_key: str, tags: Optional[List[str]], model: str) -> None:
        """Handle tag updates and statistics"""
        if tags:
            await self._update_tags(cache_key, tags)
        
        await self._update_cache_stats()
        logger.debug(f"Cached response for model {model}")
    
    async def _update_cache_stats(self) -> None:
        """Update cache statistics and trigger eviction if needed"""
        self.stats.cache_size += 1
        if self.stats.cache_size > self.max_size:
            await self._trigger_eviction()
    
    async def invalidate_key(self, key: str) -> None:
        """Invalidate a specific cache key"""
        await self._invalidation_queue.put(key)
    
    async def invalidate_tag(self, tag: str) -> None:
        """Invalidate all entries with a specific tag"""
        tag_key = f"{self.tag_prefix}{tag}"
        keys = await self.redis.smembers(tag_key)
        await self._invalidate_tagged_keys(keys)
        await self.redis.delete(tag_key)
        logger.info(f"Invalidated {len(keys)} entries with tag {tag}")
    
    async def _invalidate_tagged_keys(self, keys: List[str]) -> None:
        """Invalidate all keys in the list"""
        for key in keys:
            await self.invalidate_key(key)
    
    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate entries matching a pattern"""
        keys = await self.redis.keys(f"{self.cache_prefix}{pattern}")
        
        for key in keys:
            await self.invalidate_key(key)
        
        logger.info(f"Invalidated {len(keys)} entries matching pattern {pattern}")

    async def _update_entry(self, key: str, entry: CacheEntry) -> None:
        """Update cache entry statistics"""
        serialized = self.serializer.serialize_entry(entry)
        await self.redis.set(key, serialized, ex=entry.ttl)

    async def _update_tags(self, key: str, tags: List[str]) -> None:
        """Update tag associations for cache key"""
        for tag in tags:
            tag_key = f"{self.tag_prefix}{tag}"
            await self.redis.sadd(tag_key, key)

    async def _trigger_eviction(self) -> None:
        """Trigger cache eviction based on strategy"""
        evictions = await self.eviction_manager.trigger_eviction(self.strategy)
        self.stats.evictions += evictions

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.stats.to_dict()