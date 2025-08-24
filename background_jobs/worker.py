"""
Background Job Worker

Mock implementation for testing purposes.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, MagicMock


logger = logging.getLogger(__name__)


class JobWorker:
    """Mock job worker for testing background job processing."""
    
    def __init__(self, redis_config: Optional[Dict[str, Any]] = None, worker_id: Optional[str] = None):
        """Initialize job worker."""
        self.redis_config = redis_config or {}
        self.worker_id = worker_id or str(uuid.uuid4())
        self.handlers: Dict[str, Callable] = {}
        self.initialized = False
        self.running = False
        self.current_job: Optional[Dict[str, Any]] = None
    
    async def initialize(self):
        """Initialize the worker."""
        self.initialized = True
    
    async def stop(self):
        """Stop the worker."""
        self.running = False
        self.initialized = False
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler for a specific job type."""
        self.handlers[job_type] = handler
    
    async def start(self):
        """Start the worker (mock implementation)."""
        self.running = True
        
        # Mock worker loop - in real implementation, would pull from queue
        while self.running:
            await asyncio.sleep(0.1)  # Simulate work
            
            # Process any pending jobs (simplified for testing)
            if self.current_job and self.current_job["type"] in self.handlers:
                handler = self.handlers[self.current_job["type"]]
                try:
                    result = await handler(self.current_job)
                    self.current_job["status"] = "completed"
                    self.current_job["result"] = result
                except Exception as e:
                    self.current_job["status"] = "failed"
                    self.current_job["error"] = str(e)
                finally:
                    self.current_job = None
    
    async def update_job_progress(self, job_id: str, progress: int):
        """Update job progress."""
        if self.current_job and self.current_job.get("id") == job_id:
            self.current_job["progress"] = progress
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job (for testing)."""
        self.current_job = job_data
        
        job_type = job_data.get("type")
        if job_type in self.handlers:
            handler = self.handlers[job_type]
            try:
                result = await handler(job_data)
                return {
                    "status": "completed",
                    "result": result
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "status": "failed",
            "error": f"No handler for job type: {job_type}"
        }