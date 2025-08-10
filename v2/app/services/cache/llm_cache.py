"""Advanced LLM Cache Service

Implements intelligent caching with invalidation strategies.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import asyncio
from enum import Enum
from app.redis_manager import redis_manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class CacheStrategy(Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    ADAPTIVE = "adaptive"

@dataclass
class CacheEntry:
    """Represents a cache entry"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if not self.ttl:
            return False
        
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl
    
    def update_access(self) -> None:
        """Update access statistics"""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1

class CacheStatistics:
    """Tracks cache performance metrics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.total_latency = 0.0
        self.cache_size = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def avg_latency(self) -> float:
        """Calculate average access latency"""
        total = self.hits + self.misses
        return self.total_latency / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "avg_latency": self.avg_latency,
            "cache_size": self.cache_size
        }

class LLMCacheManager:
    """Advanced cache manager for LLM responses"""
    
    def __init__(self,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 max_size: int = 1000,
                 default_ttl: int = 3600):
        self.redis = redis_manager
        self.strategy = strategy
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = CacheStatistics()
        self.cache_prefix = "llm_cache_v2:"
        self.tag_prefix = "llm_tag:"
        self._invalidation_queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start background tasks"""
        self._background_tasks.append(
            asyncio.create_task(self._invalidation_worker())
        )
        self._background_tasks.append(
            asyncio.create_task(self._eviction_worker())
        )
        logger.info("LLM cache manager started")
    
    async def stop(self) -> None:
        """Stop background tasks"""
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        logger.info("LLM cache manager stopped")
    
    def _generate_key(self, 
                     prompt: str, 
                     model: str, 
                     params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key"""
        key_data = {
            "prompt": prompt,
            "model": model,
            "params": params or {}
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"{self.cache_prefix}{model}:{key_hash[:32]}"
    
    async def get_cached_response(self,
                                 prompt: str,
                                 model: str,
                                 params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached response"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            cache_key = self._generate_key(prompt, model, params)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                entry = self._deserialize_entry(cached_data)
                
                if not entry.is_expired():
                    entry.update_access()
                    await self._update_entry(cache_key, entry)
                    
                    self.stats.hits += 1
                    self.stats.total_latency += asyncio.get_event_loop().time() - start_time
                    
                    logger.debug(f"Cache hit for model {model}")
                    return entry.value
                else:
                    await self.invalidate_key(cache_key)
            
            self.stats.misses += 1
            self.stats.total_latency += asyncio.get_event_loop().time() - start_time
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None
    
    async def cache_response(self,
                           prompt: str,
                           response: Any,
                           model: str,
                           params: Optional[Dict[str, Any]] = None,
                           ttl: Optional[int] = None,
                           tags: Optional[List[str]] = None) -> bool:
        """Cache a response"""
        try:
            if not self._should_cache(prompt, response):
                return False
            
            cache_key = self._generate_key(prompt, model, params)
            
            entry = CacheEntry(
                key=cache_key,
                value=response,
                ttl=ttl or self._calculate_ttl(prompt, response),
                tags=tags or [],
                metadata={
                    "model": model,
                    "prompt_length": len(prompt),
                    "response_length": len(str(response))
                }
            )
            
            serialized = self._serialize_entry(entry)
            
            await self.redis.set(
                cache_key,
                serialized,
                ex=entry.ttl
            )
            
            if tags:
                await self._update_tags(cache_key, tags)
            
            self.stats.cache_size += 1
            
            if self.stats.cache_size > self.max_size:
                await self._trigger_eviction()
            
            logger.debug(f"Cached response for model {model}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    async def invalidate_key(self, key: str) -> None:
        """Invalidate a specific cache key"""
        await self._invalidation_queue.put(key)
    
    async def invalidate_tag(self, tag: str) -> None:
        """Invalidate all entries with a specific tag"""
        tag_key = f"{self.tag_prefix}{tag}"
        keys = await self.redis.smembers(tag_key)
        
        for key in keys:
            await self.invalidate_key(key)
        
        await self.redis.delete(tag_key)
        logger.info(f"Invalidated {len(keys)} entries with tag {tag}")
    
    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate entries matching a pattern"""
        keys = await self.redis.keys(f"{self.cache_prefix}{pattern}")
        
        for key in keys:
            await self.invalidate_key(key)
        
        logger.info(f"Invalidated {len(keys)} entries matching pattern {pattern}")
    
    def _should_cache(self, prompt: str, response: Any) -> bool:
        """Determine if response should be cached"""
        response_str = str(response)
        
        if len(response_str) < 10:
            return False
        
        error_indicators = ["error", "failed", "exception", "invalid", "rate_limit"]
        if any(indicator in response_str.lower() for indicator in error_indicators):
            return False
        
        if len(response_str) > 100000:
            return False
        
        return True
    
    def _calculate_ttl(self, prompt: str, response: Any) -> int:
        """Calculate adaptive TTL based on content"""
        if self.strategy == CacheStrategy.ADAPTIVE:
            base_ttl = self.default_ttl
            
            if "current" in prompt.lower() or "latest" in prompt.lower():
                base_ttl = min(base_ttl, 300)
            
            response_length = len(str(response))
            if response_length > 10000:
                base_ttl = int(base_ttl * 1.5)
            
            if self.stats.hit_rate > 0.7:
                base_ttl = int(base_ttl * 1.2)
            elif self.stats.hit_rate < 0.3:
                base_ttl = int(base_ttl * 0.8)
            
            return base_ttl
        
        return self.default_ttl
    
    async def _update_entry(self, key: str, entry: CacheEntry) -> None:
        """Update cache entry statistics"""
        serialized = self._serialize_entry(entry)
        await self.redis.set(key, serialized, ex=entry.ttl)
    
    async def _update_tags(self, key: str, tags: List[str]) -> None:
        """Update tag associations"""
        for tag in tags:
            tag_key = f"{self.tag_prefix}{tag}"
            await self.redis.sadd(tag_key, key)
    
    async def _trigger_eviction(self) -> None:
        """Trigger cache eviction"""
        if self.strategy == CacheStrategy.LRU:
            await self._evict_lru()
        elif self.strategy == CacheStrategy.LFU:
            await self._evict_lfu()
        else:
            await self._evict_adaptive()
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entries"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return
        
        entries: List[Tuple[str, CacheEntry]] = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                entry = self._deserialize_entry(data)
                entries.append((key, entry))
        
        entries.sort(key=lambda x: x[1].accessed_at)
        
        evict_count = len(keys) - int(self.max_size * 0.9)
        for key, _ in entries[:evict_count]:
            await self.redis.delete(key)
            self.stats.evictions += 1
    
    async def _evict_lfu(self) -> None:
        """Evict least frequently used entries"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return
        
        entries: List[Tuple[str, CacheEntry]] = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                entry = self._deserialize_entry(data)
                entries.append((key, entry))
        
        entries.sort(key=lambda x: x[1].access_count)
        
        evict_count = len(keys) - int(self.max_size * 0.9)
        for key, _ in entries[:evict_count]:
            await self.redis.delete(key)
            self.stats.evictions += 1
    
    async def _evict_adaptive(self) -> None:
        """Adaptive eviction strategy"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return
        
        entries: List[Tuple[str, CacheEntry, float]] = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                entry = self._deserialize_entry(data)
                score = self._calculate_eviction_score(entry)
                entries.append((key, entry, score))
        
        entries.sort(key=lambda x: x[2])
        
        evict_count = len(keys) - int(self.max_size * 0.9)
        for key, _, _ in entries[:evict_count]:
            await self.redis.delete(key)
            self.stats.evictions += 1
    
    def _calculate_eviction_score(self, entry: CacheEntry) -> float:
        """Calculate eviction score for adaptive strategy"""
        age = (datetime.utcnow() - entry.created_at).total_seconds()
        recency = (datetime.utcnow() - entry.accessed_at).total_seconds()
        frequency = entry.access_count
        size = entry.metadata.get("response_length", 0)
        
        score = (recency / 3600) * 0.4
        score += (1 / (frequency + 1)) * 0.3
        score += (age / 86400) * 0.2
        score += (size / 10000) * 0.1
        
        return score
    
    async def _invalidation_worker(self) -> None:
        """Background worker for cache invalidation"""
        while True:
            try:
                key = await self._invalidation_queue.get()
                await self.redis.delete(key)
                self.stats.invalidations += 1
                self.stats.cache_size = max(0, self.stats.cache_size - 1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Invalidation worker error: {e}")
    
    async def _eviction_worker(self) -> None:
        """Background worker for cache eviction"""
        while True:
            try:
                await asyncio.sleep(300)
                
                if self.stats.cache_size > self.max_size * 0.95:
                    await self._trigger_eviction()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Eviction worker error: {e}")
    
    def _serialize_entry(self, entry: CacheEntry) -> str:
        """Serialize cache entry"""
        data = {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "accessed_at": entry.accessed_at.isoformat(),
            "access_count": entry.access_count,
            "ttl": entry.ttl,
            "tags": entry.tags,
            "metadata": entry.metadata
        }
        return json.dumps(data)
    
    def _deserialize_entry(self, data: str) -> CacheEntry:
        """Deserialize cache entry"""
        parsed = json.loads(data)
        return CacheEntry(
            key=parsed["key"],
            value=parsed["value"],
            created_at=datetime.fromisoformat(parsed["created_at"]),
            accessed_at=datetime.fromisoformat(parsed["accessed_at"]),
            access_count=parsed["access_count"],
            ttl=parsed["ttl"],
            tags=parsed["tags"],
            metadata=parsed["metadata"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.stats.to_dict()