"""
Cache Statistics and Metrics
Handles performance tracking and statistics for cache operations
"""

from typing import Any, Dict


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