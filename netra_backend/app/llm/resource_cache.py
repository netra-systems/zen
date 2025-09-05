"""
LLM Resource Cache Module

Provides caching functionality for LLM resources and responses.
Manages cache lifecycle and resource optimization.
"""

import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
import hashlib
import json
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self) -> None:
        """Update last accessed time and increment access count"""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache:
    """
    Least Recently Used cache implementation.
    
    Provides efficient caching with size limits and TTL support.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        logger.debug(f"LRUCache initialized: max_size={max_size}, default_ttl={default_ttl}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired:
            self.delete(key)
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.touch()
        
        return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in cache"""
        cache_ttl = ttl if ttl is not None else self.default_ttl
        
        if key in self._cache:
            # Update existing entry
            entry = self._cache[key]
            entry.value = value
            entry.created_at = time.time()
            entry.ttl = cache_ttl
            self._cache.move_to_end(key)
        else:
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=cache_ttl
            )
            self._cache[key] = entry
            
            # Evict if over capacity
            if len(self._cache) > self.max_size:
                self._evict_oldest()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest (least recently used) entry"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self._cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_access_count = sum(entry.access_count for entry in self._cache.values())
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hit_count': total_access_count,
            'utilization': len(self._cache) / self.max_size if self.max_size > 0 else 0,
            'oldest_entry_age': time.time() - min(
                (entry.created_at for entry in self._cache.values()),
                default=time.time()
            ) if self._cache else 0
        }


class LLMResourceCache:
    """
    Resource cache specifically for LLM operations.
    
    Provides caching for LLM responses, model metadata, and other resources
    with intelligent key generation and content-aware caching.
    """
    
    def __init__(self, 
                 max_size: int = 1000,
                 default_ttl: float = 3600.0,  # 1 hour
                 response_ttl: float = 1800.0):  # 30 minutes for responses
        self.cache = LRUCache(max_size, default_ttl)
        self.response_ttl = response_ttl
        logger.info(f"LLMResourceCache initialized: max_size={max_size}")
    
    def generate_key(self, prefix: str, data: Any) -> str:
        """
        Generate a cache key from data.
        
        Args:
            prefix: Key prefix (e.g., 'response', 'model_info')
            data: Data to generate key from
            
        Returns:
            Cache key string
        """
        if isinstance(data, dict):
            # Sort dict for consistent key generation
            sorted_data = json.dumps(data, sort_keys=True)
        else:
            sorted_data = str(data)
        
        # Generate hash
        key_hash = hashlib.md5(sorted_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def cache_response(self, 
                      model: str, 
                      messages: List[Dict[str, str]], 
                      response: str,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Cache an LLM response.
        
        Args:
            model: Model name
            messages: Input messages
            response: LLM response
            metadata: Additional metadata
            
        Returns:
            Cache key used
        """
        cache_data = {
            'model': model,
            'messages': messages,
            'metadata': metadata or {}
        }
        
        key = self.generate_key('response', cache_data)
        
        cache_value = {
            'response': response,
            'metadata': metadata,
            'model': model,
            'cached_at': time.time()
        }
        
        self.cache.put(key, cache_value, ttl=self.response_ttl)
        return key
    
    def get_cached_response(self, 
                           model: str, 
                           messages: List[Dict[str, str]],
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response.
        
        Args:
            model: Model name
            messages: Input messages
            metadata: Additional metadata
            
        Returns:
            Cached response data or None
        """
        cache_data = {
            'model': model,
            'messages': messages,
            'metadata': metadata or {}
        }
        
        key = self.generate_key('response', cache_data)
        return self.cache.get(key)
    
    def cache_model_info(self, model: str, info: Dict[str, Any]) -> str:
        """Cache model information"""
        key = self.generate_key('model_info', {'model': model})
        self.cache.put(key, info)
        return key
    
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get cached model information"""
        key = self.generate_key('model_info', {'model': model})
        return self.cache.get(key)
    
    def cache_resource(self, resource_type: str, resource_id: str, data: Any, ttl: Optional[float] = None) -> str:
        """Cache generic resource"""
        key = self.generate_key(resource_type, {'id': resource_id})
        self.cache.put(key, data, ttl=ttl)
        return key
    
    def get_resource(self, resource_type: str, resource_id: str) -> Optional[Any]:
        """Get cached generic resource"""
        key = self.generate_key(resource_type, {'id': resource_id})
        return self.cache.get(key)
    
    def invalidate_model(self, model: str) -> int:
        """Invalidate all cache entries for a specific model"""
        count = 0
        keys_to_delete = []
        
        # Find keys related to the model
        for key in self.cache._cache.keys():
            if f"model:{model}" in key or key.startswith(f"response:") or key.startswith(f"model_info:"):
                # Check if this entry is related to the model
                entry = self.cache._cache[key]
                if isinstance(entry.value, dict) and entry.value.get('model') == model:
                    keys_to_delete.append(key)
        
        # Delete found keys
        for key in keys_to_delete:
            self.cache.delete(key)
            count += 1
        
        if count > 0:
            logger.info(f"Invalidated {count} cache entries for model: {model}")
        
        return count
    
    def cleanup(self) -> Dict[str, int]:
        """Cleanup expired entries"""
        expired_count = self.cache.cleanup_expired()
        return {
            'expired_entries': expired_count
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        base_stats = self.cache.get_stats()
        
        # Count entries by type
        entry_types = {}
        for key in self.cache._cache.keys():
            entry_type = key.split(':')[0] if ':' in key else 'unknown'
            entry_types[entry_type] = entry_types.get(entry_type, 0) + 1
        
        return {
            **base_stats,
            'entry_types': entry_types,
            'response_ttl': self.response_ttl
        }
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("LLM resource cache cleared")


# Global cache instance
_llm_resource_cache = None


def get_llm_resource_cache() -> LLMResourceCache:
    """Get global LLM resource cache"""
    global _llm_resource_cache
    if _llm_resource_cache is None:
        _llm_resource_cache = LLMResourceCache()
    return _llm_resource_cache


def cache_llm_response(model: str, messages: List[Dict[str, str]], response: str, **kwargs) -> str:
    """Convenience function to cache LLM response"""
    return get_llm_resource_cache().cache_response(model, messages, response, **kwargs)


def get_cached_llm_response(model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
    """Convenience function to get cached LLM response"""
    return get_llm_resource_cache().get_cached_response(model, messages, **kwargs)


# Alias for backwards compatibility
LLMCacheManager = LLMResourceCache