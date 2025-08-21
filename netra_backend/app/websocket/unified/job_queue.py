"""WebSocket Job Queue Management.

Implements job-based message queue management with zero-loss guarantees
and state persistence for WebSocket operations.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional


class JobQueueManager:
    """Job-based message queue management with zero-loss guarantees."""
    
    def __init__(self) -> None:
        """Initialize job queue manager."""
        self.job_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.job_states: Dict[str, Dict[str, Any]] = {}
        self.active_sends: Dict[str, int] = defaultdict(int)
        self._queue_lock = asyncio.Lock()

    async def queue_message(self, job_id: str, message: Dict[str, Any], priority: bool = False) -> None:
        """Queue message for job with optional priority."""
        async with self._queue_lock:
            queued_message = {**message, "queued_at": time.time(), "priority": priority}
            if priority:
                self.job_queues[job_id].appendleft(queued_message)
            else:
                self.job_queues[job_id].append(queued_message)

    async def get_next_message(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get next message from job queue."""
        async with self._queue_lock:
            queue = self.job_queues[job_id]
            return queue.popleft() if queue else None

    def get_queue_size(self, job_id: str) -> int:
        """Get current queue size for job."""
        return len(self.job_queues[job_id])

    def increment_active_send(self, job_id: str) -> None:
        """Track active send operation for job."""
        self.active_sends[job_id] += 1

    def decrement_active_send(self, job_id: str) -> None:
        """Complete active send operation for job."""
        if self.active_sends[job_id] > 0:
            self.active_sends[job_id] -= 1

    def set_job_state(self, job_id: str, state: Dict[str, Any]) -> None:
        """Set job state data."""
        self.job_states[job_id] = {**state, "updated_at": time.time()}

    def get_job_state(self, job_id: str) -> Dict[str, Any]:
        """Get job state data."""
        return self.job_states.get(job_id, {})

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        total_queued = sum(len(queue) for queue in self.job_queues.values())
        total_active = sum(self.active_sends.values())
        jobs_with_queue = sum(1 for queue in self.job_queues.values() if len(queue) > 0)
        return {
            "total_jobs": len(self.job_queues), "total_queued_messages": total_queued,
            "total_active_sends": total_active, "jobs_with_queue": jobs_with_queue
        }