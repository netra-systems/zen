"""State Cache Manager Module - PRIMARY Redis State Storage

Handles Redis as the PRIMARY storage for active agent states.
Redis is now the authoritative source for active states, not a cache.
Follows 450-line limit with 25-line function limit.

Architecture:
- Redis: PRIMARY active state storage (hot data)
- ClickHouse: Historical analytics (completed runs)
- PostgreSQL: Metadata and recovery checkpoints only
"""

import json
import time
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.state_serialization import DateTimeEncoder

logger = central_logger.get_logger(__name__)


class StateCacheManager:
    """Manages Redis as PRIMARY storage for active agent states.
    
    Redis is no longer just a cache - it's the authoritative source for active states.
    This provides optimal performance for high-frequency state updates.
    """
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.active_state_ttl = 86400  # 24 hours for active states
        self.completed_state_ttl = 3600  # 1 hour for completed states before ClickHouse
        self.checkpoint_ttl = 604800  # 1 week for recovery checkpoints
    
    async def save_primary_state(self, request) -> bool:
        """Save state data to Redis as PRIMARY storage.
        
        Returns:
            bool: Success status
        """
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            logger.error("Redis client unavailable for primary state storage")
            return False
        
        success = await self._save_agent_state_primary(redis_client, request)
        if success:
            await self._update_thread_context(redis_client, request)
        return success
    
    async def _save_agent_state_primary(self, redis_client, request) -> bool:
        """Save agent state to Redis as primary storage."""
        try:
            redis_key = f"agent_state:{request.run_id}"
            
            # Create comprehensive state record
            state_record = self._build_state_record(request)
            state_json = json.dumps(state_record, cls=DateTimeEncoder)
            
            # Use appropriate TTL based on state status
            ttl = self._get_state_ttl(request)
            
            # Atomic save with metadata
            await redis_client.set(redis_key, state_json, ex=ttl)
            
            # Track state version for optimistic locking
            version_key = f"agent_state_version:{request.run_id}"
            await redis_client.incr(version_key)
            await redis_client.expire(version_key, ttl)
            
            logger.debug(f"Saved primary state for run {request.run_id} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to save primary state for run {request.run_id}: {e}")
            return False
    
    async def _update_thread_context(self, redis_client, request) -> None:
        """Update thread context with current run information."""
        try:
            thread_key = f"thread_context:{request.thread_id}"
            checkpoint_value = self.extract_value(request.checkpoint_type)
            
            thread_context = {
                "current_run_id": request.run_id,
                "user_id": request.user_id,
                "last_updated": time.time(),
                "checkpoint_type": checkpoint_value,
                "agent_phase": self.extract_value(request.agent_phase) if request.agent_phase else None,
                "step_count": getattr(request, 'step_count', 0),
                "state_version": await redis_client.get(f"agent_state_version:{request.run_id}")
            }
            
            await redis_client.set(thread_key, json.dumps(thread_context), ex=self.active_state_ttl)
        except Exception as e:
            logger.warning(f"Failed to update thread context for {request.thread_id}: {e}")
    
    async def load_primary_state(self, run_id: str) -> Optional[DeepAgentState]:
        """Load state from Redis primary storage.
        
        Args:
            run_id: Agent run identifier
            
        Returns:
            DeepAgentState if found, None otherwise
        """
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            logger.warning(f"Redis unavailable for loading state {run_id}")
            return None
            
        redis_key = f"agent_state:{run_id}"
        state_json = await redis_client.get(redis_key)
        
        if state_json:
            state_record = json.loads(state_json)
            
            # Extract actual state data from the record
            state_data = state_record.get('state_data', state_record)
            
            # Log metadata for debugging
            if 'metadata' in state_record:
                metadata = state_record['metadata']
                logger.debug(f"Loaded primary state for run {run_id} - Phase: {metadata.get('agent_phase')}, Steps: {metadata.get('step_count')}")
            else:
                logger.info(f"Loaded primary state for run {run_id} from Redis")
            
            return DeepAgentState(**state_data)
        
        logger.debug(f"No primary state found in Redis for run {run_id}")
        return None
    
    async def cache_legacy_state(self, run_id: str, state_data: Dict[str, Any]) -> None:
        """Cache state loaded from legacy PostgreSQL storage (backward compatibility).
        
        This method is used when migrating from PostgreSQL-primary to Redis-primary.
        """
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return
            
        try:
            redis_key = f"agent_state:{run_id}"
            
            # Wrap legacy data in new format
            state_record = {
                'state_data': state_data,
                'metadata': {
                    'source': 'legacy_postgresql',
                    'migrated_at': time.time(),
                    'agent_phase': state_data.get('current_phase'),
                    'step_count': state_data.get('steps', 0)
                }
            }
            
            state_json = json.dumps(state_record, cls=DateTimeEncoder)
            await redis_client.set(redis_key, state_json, ex=self.active_state_ttl)
            logger.debug(f"Cached legacy state for run {run_id} in Redis")
        except Exception as e:
            logger.error(f"Failed to cache legacy state for run {run_id}: {e}")
    
    def _build_state_record(self, request) -> dict:
        """Build comprehensive state record for primary Redis storage."""
        return {
            'state_data': request.state_data,
            'metadata': {
                'run_id': request.run_id,
                'thread_id': request.thread_id,
                'user_id': request.user_id,
                'agent_phase': self.extract_value(request.agent_phase) if request.agent_phase else None,
                'checkpoint_type': self.extract_value(request.checkpoint_type),
                'step_count': getattr(request.state_data, 'steps', 0) if hasattr(request.state_data, 'steps') else 0,
                'is_recovery_point': getattr(request, 'is_recovery_point', False),
                'saved_at': time.time(),
                'source': 'primary_redis'
            }
        }
    
    def _get_state_ttl(self, request) -> int:
        """Get appropriate TTL based on state status."""
        # If it's a recovery point, keep longer
        if getattr(request, 'is_recovery_point', False):
            return self.checkpoint_ttl
        
        # Check if run is completed (would need metadata lookup)
        # For now, use active state TTL
        return self.active_state_ttl
    
    async def mark_state_completed(self, run_id: str) -> bool:
        """Mark a state as completed and reduce TTL before ClickHouse migration."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return False
            
        try:
            redis_key = f"agent_state:{run_id}"
            
            # Update TTL for completed state
            await redis_client.expire(redis_key, self.completed_state_ttl)
            
            # Update thread context
            thread_context_keys = await redis_client.keys(f"thread_context:*")
            for key in thread_context_keys:
                context_data = await redis_client.get(key)
                if context_data:
                    context = json.loads(context_data)
                    if context.get('current_run_id') == run_id:
                        context['run_status'] = 'completed'
                        context['completed_at'] = time.time()
                        await redis_client.set(key, json.dumps(context), ex=self.completed_state_ttl)
            
            logger.info(f"Marked state {run_id} as completed with reduced TTL")
            return True
        except Exception as e:
            logger.error(f"Failed to mark state {run_id} as completed: {e}")
            return False
    
    async def get_active_runs(self, thread_id: Optional[str] = None) -> List[str]:
        """Get list of active run IDs, optionally filtered by thread."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return []
            
        try:
            if thread_id:
                # Get runs for specific thread
                thread_key = f"thread_context:{thread_id}"
                context_data = await redis_client.get(thread_key)
                if context_data:
                    context = json.loads(context_data)
                    current_run = context.get('current_run_id')
                    return [current_run] if current_run else []
                return []
            else:
                # Get all active states
                state_keys = await redis_client.keys("agent_state:*")
                return [key.split(":", 1)[1] for key in state_keys]
        except Exception as e:
            logger.error(f"Failed to get active runs: {e}")
            return []
    
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states and return count."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return 0
            
        try:
            # Redis handles TTL expiration automatically
            # This method can be used for custom cleanup logic if needed
            state_keys = await redis_client.keys("agent_state:*")
            
            cleaned_count = 0
            for key in state_keys:
                ttl = await redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    # Set default expiration for states without TTL
                    await redis_client.expire(key, self.active_state_ttl)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Set TTL for {cleaned_count} states without expiration")
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0
    
    def extract_value(self, obj) -> str:
        """Extract value from enum or return as-is."""
        return obj.value if hasattr(obj, 'value') else obj

    # Backward compatibility methods (deprecated)
    async def cache_state_in_redis(self, request) -> None:
        """DEPRECATED: Use save_primary_state instead."""
        logger.warning("cache_state_in_redis is deprecated, use save_primary_state")
        await self.save_primary_state(request)
    
    async def load_from_redis_cache(self, run_id: str) -> Optional[DeepAgentState]:
        """DEPRECATED: Use load_primary_state instead."""
        logger.warning("load_from_redis_cache is deprecated, use load_primary_state")
        return await self.load_primary_state(run_id)
    
    async def cache_deserialized_state(self, run_id: str, state_data: Dict[str, Any]) -> None:
        """DEPRECATED: Use cache_legacy_state instead."""
        logger.warning("cache_deserialized_state is deprecated, use cache_legacy_state")
        await self.cache_legacy_state(run_id, state_data)

# Global instance
state_cache_manager = StateCacheManager()