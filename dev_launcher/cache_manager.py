"""
Stub implementation for CacheManager to fix broken imports.
Functionality moved to cache_entry.py and cache_warmer.py.
"""

from typing import Any, Optional, Dict
from dev_launcher.cache_entry import CacheEntry
from dev_launcher.cache_warmer import CacheWarmer


class CacheManager:
    """Stub for backward compatibility - use CacheEntry and CacheWarmer directly."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cache_warmer = CacheWarmer()
        self.entries = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache entry."""
        entry = self.entries.get(key)
        return entry.value if entry else None
    
    def set(self, key: str, value: Any) -> None:
        """Set cache entry."""
        self.entries[key] = CacheEntry(key, value)
    
    def clear(self) -> None:
        """Clear cache."""
        self.entries.clear()
    
    async def warm_cache(self) -> None:
        """Warm cache - delegates to CacheWarmer."""
        await self.cache_warmer.warm()