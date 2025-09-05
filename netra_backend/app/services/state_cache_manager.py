"""State Cache Manager - Minimal implementation for legacy compatibility.

This module provides state caching functionality for removed legacy dependencies.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability
- Value Impact: Ensures backward compatibility during migration
- Strategic Impact: Enables gradual refactoring without breaking changes
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StateCacheManager:
    """Minimal state cache manager for backward compatibility."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        logger.info("StateCacheManager initialized")
    
    async def save_primary_state(self, request: Any) -> bool:
        """Save primary state to cache."""
        try:
            if hasattr(request, 'run_id') and hasattr(request, 'state_data'):
                self._cache[request.run_id] = request.state_data
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save primary state: {e}")
            return False
    
    async def cache_state_in_redis(self, request: Any) -> bool:
        """Cache state in Redis (stub)."""
        return await self.save_primary_state(request)
    
    async def load_primary_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load primary state from cache."""
        return self._cache.get(run_id)
    
    async def load_from_redis_cache(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load state from Redis cache (stub)."""
        return await self.load_primary_state(run_id)
    
    async def cache_deserialized_state(self, run_id: str, state_data: Any) -> bool:
        """Cache deserialized state."""
        try:
            self._cache[run_id] = state_data
            return True
        except Exception as e:
            logger.error(f"Failed to cache deserialized state: {e}")
            return False
    
    async def mark_state_completed(self, run_id: str) -> bool:
        """Mark state as completed."""
        if run_id in self._cache:
            if isinstance(self._cache[run_id], dict):
                self._cache[run_id]['_completed'] = True
            return True
        return False
    
    async def cache_legacy_state(self, run_id: str, state_data: Any) -> bool:
        """Cache legacy state format."""
        return await self.cache_deserialized_state(run_id, state_data)


# Global instance for backward compatibility
state_cache_manager = StateCacheManager()