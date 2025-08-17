"""State Cache Manager Module

Handles Redis caching operations for state persistence.
Follows 300-line limit with 8-line function limit.
"""

import json
import time
from typing import Any, Dict, Optional
from app.redis_manager import redis_manager
from app.services.state_serialization import DateTimeEncoder
from app.logging_config import central_logger
from app.agents.state import DeepAgentState

logger = central_logger.get_logger(__name__)


class StateCacheManager:
    """Manages Redis caching for agent state data."""
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.redis_ttl = 3600  # 1 hour TTL for Redis cache
    
    async def cache_state_in_redis(self, request) -> None:
        """Cache state data in Redis for fast access."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return
        await self.cache_agent_state(redis_client, request)
        await self.cache_thread_context(redis_client, request)
    
    async def cache_agent_state(self, redis_client, request) -> None:
        """Cache agent state in Redis."""
        redis_key = f"agent_state:{request.run_id}"
        state_json = json.dumps(request.state_data, cls=DateTimeEncoder)
        await redis_client.set(redis_key, state_json, ex=self.redis_ttl)
    
    async def cache_thread_context(self, redis_client, request) -> None:
        """Cache thread context in Redis."""
        thread_key = f"thread_context:{request.thread_id}"
        checkpoint_value = self.extract_value(request.checkpoint_type)
        thread_context = {
            "current_run_id": request.run_id, "user_id": request.user_id,
            "last_updated": time.time(), "checkpoint_type": checkpoint_value}
        await redis_client.set(thread_key, json.dumps(thread_context), ex=self.redis_ttl * 24)
    
    async def load_from_redis_cache(self, run_id: str) -> Optional[DeepAgentState]:
        """Load state from Redis cache."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return None
        redis_key = f"agent_state:{run_id}"
        state_json = await redis_client.get(redis_key)
        if state_json:
            state_dict = json.loads(state_json)
            logger.info(f"Loaded state for run {run_id} from Redis cache")
            return DeepAgentState(**state_dict)
        return None
    
    async def cache_deserialized_state(self, run_id: str, state_data: Dict[str, Any]) -> None:
        """Cache deserialized state in Redis."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return
        redis_key = f"agent_state:{run_id}"
        state_json = json.dumps(state_data, cls=DateTimeEncoder)
        await redis_client.set(redis_key, state_json, ex=self.redis_ttl)
    
    def extract_value(self, obj) -> str:
        """Extract value from enum or return as-is."""
        return obj.value if hasattr(obj, 'value') else obj

# Global instance
state_cache_manager = StateCacheManager()