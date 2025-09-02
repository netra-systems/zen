from shared.isolated_environment import get_env
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
        self._redis_builder = self._create_redis_builder()
    
    def _create_redis_builder(self):
        """Create Redis configuration builder for job manager."""
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
    
    async def initialize(self):
        """Initialize the job manager with Redis validation."""
        # Validate Redis configuration
        is_valid, error_msg = self._redis_builder.validate()
        if not is_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Job manager Redis configuration error: {error_msg}")
            raise RuntimeError(error_msg)
        
        self.initialized = True
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration for job manager."""
        return self._redis_builder.get_config_for_environment()
    
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
