"""Cache strategies for API Gateway."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class CacheStrategy(ABC):
    """Abstract base class for cache strategies."""
    
    @abstractmethod
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Determine if item should be cached."""
        pass
    
    @abstractmethod
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Get time-to-live for cache entry in seconds."""
        pass
    
    @abstractmethod
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """Get cache priority (higher = more important)."""
        pass


class DefaultCacheStrategy(CacheStrategy):
    """Default caching strategy."""
    
    def __init__(self, default_ttl: int = 300, default_priority: int = 1):
        self.default_ttl = default_ttl
        self.default_priority = default_priority
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Cache everything by default."""
        return True
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Return default TTL."""
        return self.default_ttl
    
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """Return default priority."""
        return self.default_priority


class SizeBasedCacheStrategy(CacheStrategy):
    """Cache strategy based on response size."""
    
    def __init__(self, max_size_bytes: int = 1024 * 1024, ttl: int = 600):
        self.max_size_bytes = max_size_bytes
        self.ttl = ttl
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Cache only if size is within limits."""
        size_estimate = len(str(value))
        return size_estimate <= self.max_size_bytes
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Return TTL based on size."""
        size_estimate = len(str(value))
        # Smaller responses get longer TTL
        if size_estimate < 1024:  # 1KB
            return self.ttl * 2
        elif size_estimate < 10240:  # 10KB
            return self.ttl
        else:
            return self.ttl // 2
    
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """Smaller responses get higher priority."""
        size_estimate = len(str(value))
        if size_estimate < 1024:
            return 3
        elif size_estimate < 10240:
            return 2
        else:
            return 1


class FrequencyBasedCacheStrategy(CacheStrategy):
    """Cache strategy based on request frequency."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.access_counts: Dict[str, int] = {}
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Always cache initially."""
        return True
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Higher frequency gets longer TTL."""
        access_count = self.access_counts.get(key, 0)
        self.access_counts[key] = access_count + 1
        
        if access_count > 10:
            return self.ttl * 3
        elif access_count > 5:
            return self.ttl * 2
        else:
            return self.ttl
    
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """More frequent requests get higher priority."""
        access_count = self.access_counts.get(key, 0)
        if access_count > 10:
            return 3
        elif access_count > 5:
            return 2
        else:
            return 1


class TimeBasedCacheStrategy(CacheStrategy):
    """Cache strategy with time-based rules."""
    
    def __init__(self):
        # Different TTLs for different times of day
        self.time_based_ttl = {
            "peak": 900,    # 15 minutes during peak hours
            "normal": 1800, # 30 minutes during normal hours
            "off_peak": 3600 # 1 hour during off-peak
        }
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Cache based on time patterns."""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        # Cache more aggressively during off-peak hours
        if current_hour < 6 or current_hour > 22:  # Off-peak
            return True
        elif 9 <= current_hour <= 17:  # Peak business hours
            # More selective during peak hours
            return metadata.get("cache_priority", 1) >= 2
        else:  # Normal hours
            return True
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Return TTL based on time of day."""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        if current_hour < 6 or current_hour > 22:
            return self.time_based_ttl["off_peak"]
        elif 9 <= current_hour <= 17:
            return self.time_based_ttl["peak"]
        else:
            return self.time_based_ttl["normal"]
    
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """Priority based on metadata."""
        return metadata.get("cache_priority", 1)


class CompositeStrategy(CacheStrategy):
    """Composite strategy that combines multiple strategies."""
    
    def __init__(self, strategies: list[CacheStrategy]):
        self.strategies = strategies
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """All strategies must agree to cache."""
        return all(strategy.should_cache(key, value, metadata) 
                  for strategy in self.strategies)
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Use minimum TTL from all strategies."""
        ttls = [strategy.get_ttl(key, value, metadata) for strategy in self.strategies]
        valid_ttls = [ttl for ttl in ttls if ttl is not None]
        
        if not valid_ttls:
            return None
        
        return min(valid_ttls)
    
    def get_priority(self, key: str, value: Any, metadata: Dict[str, Any]) -> int:
        """Use maximum priority from all strategies."""
        priorities = [strategy.get_priority(key, value, metadata) for strategy in self.strategies]
        return max(priorities) if priorities else 1
