"""
Background Job Manager

Mock implementation for testing purposes.
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class JobManager:
    """Mock job manager for testing background job processing."""
    
    def __init__(self, redis_config: Optional[Dict[str, Any]] = None):
        """Initialize job manager with Redis configuration."""
        self.redis_config = redis_config or {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize the job manager."""
        self.initialized = True
    
    async def cleanup(self):
        """Clean up job manager resources."""
        self.jobs.clear()
        self.initialized = False
    
    async def enqueue_job(
        self, 
        job_type: str, 
        payload: Dict[str, Any], 
        priority: int = 1,
        retry_policy: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enqueue a job for processing."""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "priority": priority,
            "retry_policy": retry_policy or {},
            "status": "pending",
            "created_at": asyncio.get_event_loop().time()
        }
        
        self.jobs[job_id] = job_data
        return job_id
    
    async def schedule_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        scheduled_at: float,
        priority: int = 1
    ) -> str:
        """Schedule a job for future execution."""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "priority": priority,
            "status": "scheduled",
            "scheduled_at": scheduled_at,
            "created_at": asyncio.get_event_loop().time()
        }
        
        self.jobs[job_id] = job_data
        return job_id
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status by ID."""
        job = self.jobs.get(job_id)
        if job:
            return {
                "status": job["status"],
                "progress": job.get("progress", 0),
                "result": job.get("result")
            }
        return {"status": "not_found"}
    
    async def get_dead_letter_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that have permanently failed."""
        return [
            job for job in self.jobs.values() 
            if job.get("status") == "failed"
        ]