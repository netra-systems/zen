"""Background Task Manager - Minimal implementation.

This module provides background task management functionality.
Created as a minimal implementation to resolve missing module imports.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Enables background task management and shutdown procedures
- Strategic Impact: Foundation for asynchronous operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """Represents a background task."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    _task: Optional[asyncio.Task] = None


class BackgroundTaskManager:
    """Manages background tasks and their lifecycle."""
    
    # Default timeout for operations (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self._running = True
        logger.info("BackgroundTaskManager initialized")
    
    async def start_task(self, task_id: str, name: str, coro: Callable) -> BackgroundTask:
        """Start a background task."""
        if task_id in self.tasks:
            logger.warning(f"Task {task_id} already exists")
            return self.tasks[task_id]
        
        bg_task = BackgroundTask(task_id=task_id, name=name)
        self.tasks[task_id] = bg_task
        
        try:
            if asyncio.iscoroutinefunction(coro):
                bg_task._task = asyncio.create_task(coro())
            else:
                # Convert regular callable to coroutine
                async def wrapper():
                    return coro()
                bg_task._task = asyncio.create_task(wrapper())
            
            bg_task.status = TaskStatus.RUNNING
            logger.info(f"Started background task: {task_id} ({name})")
            
            # Set up completion callback
            bg_task._task.add_done_callback(
                lambda t: self._task_completed(task_id, t)
            )
            
        except Exception as e:
            bg_task.status = TaskStatus.FAILED
            bg_task.error = str(e)
            logger.error(f"Failed to start task {task_id}: {e}")
        
        return bg_task
    
    def _task_completed(self, task_id: str, task: asyncio.Task):
        """Handle task completion."""
        if task_id not in self.tasks:
            return
        
        bg_task = self.tasks[task_id]
        
        if task.cancelled():
            bg_task.status = TaskStatus.CANCELLED
            logger.info(f"Task {task_id} was cancelled")
        elif task.exception():
            bg_task.status = TaskStatus.FAILED
            bg_task.error = str(task.exception())
            logger.error(f"Task {task_id} failed: {bg_task.error}")
        else:
            bg_task.status = TaskStatus.COMPLETED
            bg_task.result = task.result()
            logger.info(f"Task {task_id} completed successfully")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a background task."""
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return False
        
        bg_task = self.tasks[task_id]
        if bg_task._task and not bg_task._task.done():
            bg_task._task.cancel()
            bg_task.status = TaskStatus.CANCELLED
            logger.info(f"Cancelled task {task_id}")
            return True
        
        return False
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = DEFAULT_TIMEOUT) -> Optional[Any]:
        """Wait for a task to complete."""
        if task_id not in self.tasks:
            return None
        
        bg_task = self.tasks[task_id]
        if not bg_task._task:
            return None
        
        try:
            if timeout:
                return await asyncio.wait_for(bg_task._task, timeout=timeout)
            else:
                return await bg_task._task
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error waiting for task {task_id}: {e}")
            return None
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[BackgroundTask]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[BackgroundTask]:
        """Get running tasks."""
        return [task for task in self.tasks.values() 
                if task.status == TaskStatus.RUNNING]
    
    async def shutdown(self, timeout: int = DEFAULT_TIMEOUT):
        """Shutdown task manager and cancel all running tasks."""
        logger.info("Shutting down BackgroundTaskManager")
        self._running = False
        
        running_tasks = self.get_running_tasks()
        if not running_tasks:
            logger.info("No running tasks to cancel")
            return
        
        logger.info(f"Cancelling {len(running_tasks)} running tasks")
        
        for task in running_tasks:
            if task._task and not task._task.done():
                task._task.cancel()
        
        # Wait for tasks to complete cancellation
        try:
            await asyncio.wait_for(
                asyncio.gather(*[
                    task._task for task in running_tasks 
                    if task._task and not task._task.done()
                ], return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Some tasks did not cancel within {timeout}s timeout")
        except Exception as e:
            logger.error(f"Error during task shutdown: {e}")
        
        logger.info("BackgroundTaskManager shutdown completed")
    
    @property
    def is_running(self) -> bool:
        """Check if task manager is running."""
        return self._running


# Global instance
background_task_manager = BackgroundTaskManager()


async def get_background_task_manager() -> BackgroundTaskManager:
    """Get background task manager instance."""
    return background_task_manager