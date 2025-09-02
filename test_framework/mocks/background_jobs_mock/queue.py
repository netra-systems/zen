from shared.isolated_environment import get_env
"""
Background Job Queue

Mock implementation for testing purposes.
"""

import asyncio
import heapq
import json
import uuid
from typing import Any, Dict, List, Optional


class RedisQueue:
    """Mock Redis queue for testing background job processing."""
    
    def __init__(self, queue_name: str, redis_config: Optional[Dict[str, Any]] = None):
        """Initialize Redis queue."""
        self.queue_name = queue_name
        self.redis_config = redis_config or {}
        self.queue: List[tuple] = []  # Priority queue using heapq
        self.initialized = False
    
    async def initialize(self):
        """Initialize the queue."""
        self.initialized = True
    
    async def cleanup(self):
        """Clean up queue resources."""
        self.queue.clear()
        self.initialized = False
    
    async def enqueue(self, job_data: Dict[str, Any]) -> str:
        """Enqueue a job with priority."""
        job_id = str(uuid.uuid4())
        
        # Add job ID to data
        job_data["id"] = job_id
        
        # Use negative priority for max-heap behavior (higher priority first)
        priority = -job_data.get("priority", 1)
        
        # Add to priority queue
        heapq.heappush(self.queue, (priority, job_id, job_data))
        
        return job_id
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Dequeue a job based on priority."""
        if not self.queue:
            return None
        
        # Get highest priority job
        priority, job_id, job_data = heapq.heappop(self.queue)
        
        return job_data
    
    async def size(self) -> int:
        """Get queue size."""
        return len(self.queue)
    
    async def clear(self):
        """Clear the queue."""
        self.queue.clear()


class JobQueue(RedisQueue):
    """Job Queue with Redis Configuration Builder integration."""
    
    def __init__(self, queue_name: str, redis_config: Optional[Dict[str, Any]] = None):
        """Initialize job queue with Redis configuration."""
        super().__init__(queue_name, redis_config)
        self._redis_builder = self._create_redis_builder()
    
    def _create_redis_builder(self):
        """Create Redis configuration builder for job queue."""
        import os
        from shared.redis_config_builder import RedisConfigurationBuilder
        
        # Build environment variables dict for Redis builder
        env_vars = {
            "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
            "NETRA_ENVIRONMENT": os.environ.get("NETRA_ENVIRONMENT"),
            "K_SERVICE": os.environ.get("K_SERVICE"),
            "GCP_PROJECT_ID": os.environ.get("GCP_PROJECT_ID"),
            "REDIS_URL": os.environ.get("REDIS_URL"),
            "REDIS_HOST": os.environ.get("REDIS_HOST"),
            "REDIS_PORT": os.environ.get("REDIS_PORT"),
            "REDIS_DB": os.environ.get("REDIS_DB"),
            "REDIS_PASSWORD": os.environ.get("REDIS_PASSWORD"),
            "REDIS_USERNAME": os.environ.get("REDIS_USERNAME"),
            "REDIS_SSL": os.environ.get("REDIS_SSL"),
            "REDIS_FALLBACK_ENABLED": os.environ.get("REDIS_FALLBACK_ENABLED"),
            "REDIS_REQUIRED": os.environ.get("REDIS_REQUIRED"),
        }
        
        return RedisConfigurationBuilder(env_vars)
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration for job queue."""
        return self._redis_builder.get_config_for_environment()
    
    async def initialize(self):
        """Initialize the job queue with Redis validation."""
        # Validate Redis configuration
        is_valid, error_msg = self._redis_builder.validate()
        if not is_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Job queue Redis configuration error: {error_msg}")
            raise RuntimeError(error_msg)
        
        await super().initialize()
