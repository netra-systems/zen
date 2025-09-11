"""State Cache Manager - Enhanced implementation for persistence testing.

This module provides state caching functionality for removed legacy dependencies.
Enhanced with Redis integration for persistence testing.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability
- Value Impact: Ensures backward compatibility during migration
- Strategic Impact: Enables gradual refactoring without breaking changes
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from netra_backend.app.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class StateCacheManager:
    """Enhanced state cache manager with Redis integration for persistence testing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._versions: Dict[str, int] = {}
        logger.info("StateCacheManager initialized")
        
    def _serialize_state_data(self, data: Any) -> str:
        """Serialize state data to JSON, handling datetime objects."""
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        return json.dumps(data, default=json_serializer, sort_keys=True)
    
    async def save_primary_state(self, request: Any) -> bool:
        """Save primary state to cache and Redis."""
        try:
            if hasattr(request, 'run_id') and hasattr(request, 'state_data'):
                run_id = request.run_id
                
                # Save to local cache
                self._cache[run_id] = request.state_data
                
                # Update version tracking
                current_version = self._versions.get(run_id, 0)
                self._versions[run_id] = current_version + 1
                
                # Save to Redis if available
                try:
                    redis_client = await redis_manager.get_client()
                    if redis_client:
                        # Save serialized state
                        serialized_data = self._serialize_state_data(request.state_data)
                        await redis_client.set(f"agent_state:{run_id}", serialized_data, ex=3600)
                        
                        # Save version
                        await redis_client.set(f"agent_state_version:{run_id}", str(self._versions[run_id]), ex=3600)
                        
                        # Update thread context if available
                        if hasattr(request, 'thread_id') and hasattr(request, 'user_id'):
                            thread_context = {
                                "current_run_id": run_id,
                                "user_id": request.user_id
                            }
                            await redis_client.set(
                                f"thread_context:{request.thread_id}", 
                                json.dumps(thread_context), 
                                ex=3600
                            )
                except Exception as e:
                    logger.warning(f"Redis save failed, using local cache only: {e}")
                
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save primary state: {e}")
            return False
    
    async def cache_state_in_redis(self, request: Any) -> bool:
        """Cache state in Redis (stub)."""
        return await self.save_primary_state(request)
    
    async def load_primary_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load primary state from cache or Redis."""
        # Try local cache first
        if run_id in self._cache:
            return self._cache[run_id]
            
        # Try Redis if available
        try:
            redis_client = await redis_manager.get_client()
            if redis_client:
                serialized_data = await redis_client.get(f"agent_state:{run_id}")
                if serialized_data:
                    data = json.loads(serialized_data)
                    # Cache locally for faster access
                    self._cache[run_id] = data
                    return data
        except Exception as e:
            logger.warning(f"Redis load failed: {e}")
            
        return None
        
    async def delete_primary_state(self, run_id: str) -> bool:
        """Delete primary state from cache and Redis."""
        try:
            # Remove from local cache
            self._cache.pop(run_id, None)
            self._versions.pop(run_id, None)
            
            # Remove from Redis if available
            try:
                redis_client = await redis_manager.get_client()
                if redis_client:
                    await redis_client.delete(f"agent_state:{run_id}")
                    await redis_client.delete(f"agent_state_version:{run_id}")
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Failed to delete primary state: {e}")
            return False
    
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