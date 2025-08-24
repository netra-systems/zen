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