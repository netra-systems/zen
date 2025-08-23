"""Background Task Manager with Timeout Handling

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Reliability
- Value Impact: Prevents service crashes from long-running background tasks
- Strategic Impact: Eliminates 4-minute crash scenario, ensures system resilience

This module provides centralized background task management with proper timeout
handling to prevent service crashes from runaway tasks.

FIX: Addresses Test 7.3 - 4-minute crash from background tasks without timeout.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Centralized manager for background tasks with timeout and error handling."""
    
    def __init__(self, default_timeout: int = 120):
        """Initialize task manager with default 2-minute timeout.
        
        Args:
            default_timeout: Default timeout in seconds (2 minutes to prevent 4-minute crash)
        """
        self.default_timeout = default_timeout
        self.active_tasks: Dict[UUID, asyncio.Task] = {}
        self.task_metadata: Dict[UUID, Dict[str, Any]] = {}
        self.completed_tasks: List[UUID] = []
        self.failed_tasks: List[UUID] = []
        self._shutdown = False
        
        logger.info(f"BackgroundTaskManager initialized with {default_timeout}s default timeout")
    
    async def create_task(
        self,
        coro: Callable,
        name: str,
        timeout: Optional[int] = None,
        retry_count: int = 0,
        critical: bool = False
    ) -> UUID:
        """Create and manage a background task with timeout.
        
        Args:
            coro: Coroutine to execute
            name: Human-readable task name
            timeout: Task timeout in seconds (uses default if None)
            retry_count: Number of retries on failure
            critical: Whether task failure should be logged as error
            
        Returns:
            Task UUID for tracking
        """
        if self._shutdown:
            logger.warning(f"Cannot create task '{name}' - manager is shutting down")
            return None
        
        task_id = uuid4()
        task_timeout = timeout or self.default_timeout
        
        # Create metadata
        self.task_metadata[task_id] = {
            "name": name,
            "created_at": datetime.now(),
            "timeout": task_timeout,
            "retry_count": retry_count,
            "retries_left": retry_count,
            "critical": critical,
            "status": "running"
        }
        
        # Create the actual task with timeout wrapper
        task = asyncio.create_task(
            self._execute_with_timeout(coro, task_id, task_timeout)
        )
        task.add_done_callback(lambda t: self._task_completed(task_id, t))
        
        self.active_tasks[task_id] = task
        
        logger.info(f"Created background task '{name}' (ID: {task_id}) with {task_timeout}s timeout")
        return task_id
    
    async def _execute_with_timeout(self, coro: Callable, task_id: UUID, timeout: int):
        """Execute coroutine with timeout handling."""
        metadata = self.task_metadata[task_id]
        
        try:
            # Handle both coroutine functions and coroutine objects
            if asyncio.iscoroutinefunction(coro):
                # It's a coroutine function, call it to get the coroutine
                coroutine_obj = coro()
            elif asyncio.iscoroutine(coro):
                # It's already a coroutine object
                coroutine_obj = coro
            else:
                # It might be a regular async callable, try calling it
                coroutine_obj = coro()
            
            # Execute with timeout
            result = await asyncio.wait_for(coroutine_obj, timeout=timeout)
            metadata["status"] = "completed"
            metadata["completed_at"] = datetime.now()
            metadata["result"] = result
            return result
            
        except asyncio.TimeoutError:
            metadata["status"] = "timeout"
            metadata["error"] = f"Task timed out after {timeout} seconds"
            error_msg = f"Background task '{metadata['name']}' timed out after {timeout}s"
            
            if metadata["critical"]:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
            
            raise asyncio.TimeoutError(error_msg)
            
        except Exception as e:
            metadata["status"] = "failed"
            metadata["error"] = str(e)
            error_msg = f"Background task '{metadata['name']}' failed: {e}"
            
            if metadata["critical"]:
                logger.error(error_msg, exc_info=True)
            else:
                logger.warning(error_msg)
            
            # Handle retries
            if metadata["retries_left"] > 0:
                metadata["retries_left"] -= 1
                logger.info(f"Retrying task '{metadata['name']}' ({metadata['retries_left']} retries left)")
                await asyncio.sleep(1)  # Brief delay before retry
                return await self._execute_with_timeout(coro, task_id, timeout)
            
            raise
    
    def _task_completed(self, task_id: UUID, task: asyncio.Task):
        """Handle task completion cleanup."""
        metadata = self.task_metadata.get(task_id, {})
        
        # Remove from active tasks
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        # Categorize completion
        if task.cancelled():
            metadata["status"] = "cancelled"
            logger.debug(f"Task '{metadata.get('name', task_id)}' was cancelled")
        elif task.exception():
            self.failed_tasks.append(task_id)
            logger.debug(f"Task '{metadata.get('name', task_id)}' failed")
        else:
            self.completed_tasks.append(task_id)
            logger.debug(f"Task '{metadata.get('name', task_id)}' completed successfully")
    
    async def wait_for_task(self, task_id: UUID, timeout: Optional[int] = None) -> Any:
        """Wait for a specific task to complete.
        
        Args:
            task_id: Task UUID to wait for
            timeout: Maximum time to wait (uses task's timeout if None)
            
        Returns:
            Task result
        """
        if task_id not in self.active_tasks:
            metadata = self.task_metadata.get(task_id, {})
            if metadata.get("status") == "completed":
                return metadata.get("result")
            else:
                raise ValueError(f"Task {task_id} not found or not active")
        
        task = self.active_tasks[task_id]
        wait_timeout = timeout or self.task_metadata[task_id]["timeout"]
        
        try:
            return await asyncio.wait_for(task, timeout=wait_timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timed out waiting for task {task_id}")
            raise
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a specific background task.
        
        Args:
            task_id: Task UUID to cancel
            
        Returns:
            True if task was cancelled, False if not found
        """
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.cancel()
        
        metadata = self.task_metadata.get(task_id, {})
        logger.info(f"Cancelled background task '{metadata.get('name', task_id)}'")
        
        return True
    
    async def cancel_all_tasks(self):
        """Cancel all active background tasks."""
        if not self.active_tasks:
            return
        
        logger.info(f"Cancelling {len(self.active_tasks)} active background tasks")
        
        # Cancel all tasks
        for task_id, task in list(self.active_tasks.items()):
            if not task.done():
                task.cancel()
        
        # Wait briefly for cancellation to complete
        if self.active_tasks:
            await asyncio.sleep(0.1)
        
        logger.info("All background tasks cancelled")
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get information about all active tasks."""
        active_info = []
        
        for task_id, task in self.active_tasks.items():
            metadata = self.task_metadata.get(task_id, {})
            info = {
                "id": str(task_id),
                "name": metadata.get("name", "Unknown"),
                "status": metadata.get("status", "unknown"),
                "created_at": metadata.get("created_at"),
                "timeout": metadata.get("timeout"),
                "critical": metadata.get("critical", False)
            }
            
            # Add runtime information
            if info["created_at"]:
                runtime = datetime.now() - info["created_at"]
                info["runtime_seconds"] = runtime.total_seconds()
                info["timeout_remaining"] = max(0, info["timeout"] - runtime.total_seconds())
            
            active_info.append(info)
        
        return active_info
    
    def get_task_statistics(self) -> Dict[str, int]:
        """Get task execution statistics."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "total_tasks": len(self.completed_tasks) + len(self.failed_tasks) + len(self.active_tasks)
        }
    
    async def cleanup_old_metadata(self, max_age_hours: int = 24):
        """Clean up old task metadata to prevent memory leaks."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        # Clean up completed and failed task metadata
        for task_list in [self.completed_tasks, self.failed_tasks]:
            for task_id in list(task_list):
                metadata = self.task_metadata.get(task_id, {})
                created_at = metadata.get("created_at")
                
                if created_at and created_at < cutoff_time:
                    if task_id in self.task_metadata:
                        del self.task_metadata[task_id]
                    task_list.remove(task_id)
                    removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old task metadata records")
    
    async def shutdown(self):
        """Shutdown the task manager and clean up resources."""
        logger.info("Shutting down BackgroundTaskManager...")
        self._shutdown = True
        
        # Cancel all active tasks
        await self.cancel_all_tasks()
        
        # Clear all data structures
        self.active_tasks.clear()
        self.task_metadata.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        
        logger.info("BackgroundTaskManager shutdown complete")


# Global instance for application use
background_task_manager = BackgroundTaskManager(default_timeout=120)  # 2-minute default timeout


# Convenience functions for common usage patterns
async def run_background_task(
    coro: Callable,
    name: str,
    timeout: Optional[int] = None,
    critical: bool = False
) -> UUID:
    """Convenience function to run a background task with timeout.
    
    Args:
        coro: Coroutine to execute
        name: Human-readable task name
        timeout: Task timeout in seconds (default: 2 minutes)
        critical: Whether task failure should be logged as error
        
    Returns:
        Task UUID for tracking
    """
    return await background_task_manager.create_task(
        coro=coro,
        name=name,
        timeout=timeout,
        critical=critical
    )


async def cleanup_background_tasks():
    """Clean up all background tasks - call during application shutdown."""
    await background_task_manager.shutdown()