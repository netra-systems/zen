"""
Cache Models and Configuration
Defines data models, enums, and configurations for caching
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    ttl: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if not self.ttl:
            return False
        
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl
    
    def update_access(self) -> None:
        """Update access statistics"""
        self.accessed_at = datetime.now(timezone.utc)
        self.access_count += 1