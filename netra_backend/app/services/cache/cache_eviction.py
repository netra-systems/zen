"""
Cache Eviction Strategies
Implements different eviction algorithms for cache management
"""

from datetime import UTC, datetime
from typing import List, Tuple

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.cache.cache_models import CacheEntry, CacheStrategy

logger = central_logger.get_logger(__name__)


class CacheEvictionManager:
    """Manages cache eviction using various strategies"""
    
    def __init__(self, redis_client, cache_prefix: str, max_size: int):
        self.redis = redis_client
        self.cache_prefix = cache_prefix
        self.max_size = max_size
    
    async def trigger_eviction(self, strategy: CacheStrategy) -> None:
        """Trigger cache eviction based on strategy"""
        if strategy == CacheStrategy.LRU:
            await self._evict_lru()
        elif strategy == CacheStrategy.LFU:
            await self._evict_lfu()
        else:
            await self._evict_adaptive()
    
    async def _evict_lru(self) -> int:
        """Evict least recently used entries"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return 0
        
        entries = await self._load_entries_with_keys(keys)
        entries.sort(key=lambda x: x[1].accessed_at)
        
        return await self._evict_entries(entries)
    
    async def _evict_lfu(self) -> int:
        """Evict least frequently used entries"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return 0
        
        entries = await self._load_entries_with_keys(keys)
        entries.sort(key=lambda x: x[1].access_count)
        
        return await self._evict_entries(entries)
    
    async def _evict_adaptive(self) -> int:
        """Adaptive eviction strategy"""
        keys = await self.redis.keys(f"{self.cache_prefix}*")
        
        if len(keys) <= self.max_size:
            return 0
        
        entries: List[Tuple[str, CacheEntry, float]] = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                entry = self._deserialize_entry(data)
                score = self._calculate_eviction_score(entry)
                entries.append((key, entry, score))
        
        entries.sort(key=lambda x: x[2])
        
        evict_count = len(keys) - int(self.max_size * 0.9)
        evictions = 0
        for key, _, _ in entries[:evict_count]:
            await self.redis.delete(key)
            evictions += 1
        
        return evictions
    
    async def _load_entries_with_keys(self, keys: List[str]) -> List[Tuple[str, CacheEntry]]:
        """Load cache entries with their keys"""
        entries: List[Tuple[str, CacheEntry]] = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                entry = self._deserialize_entry(data)
                entries.append((key, entry))
        return entries
    
    async def _evict_entries(self, entries: List[Tuple[str, CacheEntry]]) -> int:
        """Evict specified entries"""
        evict_count = len(entries) - int(self.max_size * 0.9)
        evictions = 0
        for key, _ in entries[:evict_count]:
            await self.redis.delete(key)
            evictions += 1
        return evictions
    
    def _calculate_eviction_score(self, entry: CacheEntry) -> float:
        """Calculate eviction score for adaptive strategy"""
        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        recency = (datetime.now(UTC) - entry.accessed_at).total_seconds()
        frequency = entry.access_count
        size = entry.metadata.get("response_length", 0)
        
        score = (recency / 3600) * 0.4
        score += (1 / (frequency + 1)) * 0.3
        score += (age / 86400) * 0.2
        score += (size / 10000) * 0.1
        
        return score
    
    def _deserialize_entry(self, data: str) -> CacheEntry:
        """Deserialize cache entry"""
        import json
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