"""Session Cache - Minimal implementation for integration tests.

This module provides session caching functionality.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SessionCache:
    """Minimal session cache implementation for integration tests."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        logger.info("SessionCache initialized")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            self._cache[key] = value
            return True
        except Exception as e:
            logger.error(f"Failed to set cache value: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache value: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()