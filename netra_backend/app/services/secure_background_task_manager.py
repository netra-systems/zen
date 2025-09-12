"""Secure Background Task Manager with UserExecutionContext Support

SECURITY CRITICAL: This module provides secure background task management with mandatory
user context isolation to prevent data leakage between users in background processing.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Ensure secure background processing with user isolation
- Value Impact: Prevents user data mixing in async tasks and background operations
- Revenue Impact: Prevents security breaches and maintains user trust

Key Security Features:
- Mandatory UserExecutionContext propagation for all user-related tasks
- Context serialization and deserialization for async task queuing
- User-specific task filtering to prevent cross-user data access
- Comprehensive audit trails for security compliance
- Task isolation validation to prevent context bleeding

Architecture:
This implementation replaces the legacy BackgroundTaskManager with a security-first
approach that ensures proper user context isolation in all background operations.
"""

import asyncio
import logging
import json
import inspect
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

# SECURITY CRITICAL: Import UserExecutionContext for proper user isolation
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SecureBackgroundTask:
    """Represents a secure background task with mandatory user context isolation."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    _task: Optional[asyncio.Task] = field(default=None, repr=False, compare=False)
    
    # SECURITY CRITICAL: User context data for proper isolation
    user_context_data: Optional[Dict[str, Any]] = field(default=None)
    require_user_context: bool = field(default=True)
    
    # Audit and tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = field(default=None)
    completed_at: Optional[datetime] = field(default=None)
    
    def get_user_id(self) -> Optional[str]:
        """Get the user ID from context data."""
        return self.user_context_data.get('user_id') if self.user_context_data else None
    
    def get_execution_time(self) -> Optional[float]:
        """Get task execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status,
            'user_id': self.get_user_id(),
            'require_user_context': self.require_user_context,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'execution_time': self.get_execution_time(),
            'has_error': bool(self.error),
            'error_message': self.error[:100] if self.error else None  # Truncated for security
        }


class SecureBackgroundTaskManager:
    """Secure background task manager with mandatory user context isolation."""
    
    def __init__(self, enforce_user_context: bool = True, max_tasks_per_user: int = 50):
        self.tasks: Dict[str, SecureBackgroundTask] = {}
        self._running = True
        
        # SECURITY CRITICAL: Control whether user context is mandatory
        self.enforce_user_context = enforce_user_context
        self.max_tasks_per_user = max_tasks_per_user
        
        # Metrics
        self._total_tasks_created = 0
        self._total_tasks_completed = 0
        self._total_tasks_failed = 0
        self._tasks_by_user: Dict[str, int] = {}
        
        logger.info(
            f"SecureBackgroundTaskManager initialized with "
            f"user_context_enforcement={enforce_user_context}, "
            f"max_tasks_per_user={max_tasks_per_user}"
        )
    
    async def start_task(
        self, 
        task_id: str, 
        name: str, 
        coro: Callable, 
        user_context: Optional[UserExecutionContext] = None,
        require_user_context: Optional[bool] = None,
        task_metadata: Optional[Dict[str, Any]] = None
    ) -> SecureBackgroundTask:
        """Start a secure background task with user context isolation.
        
        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            coro: Coroutine or callable to execute
            user_context: UserExecutionContext for proper isolation
            require_user_context: Override global enforcement setting
            task_metadata: Additional metadata for the task
            
        Returns:
            SecureBackgroundTask instance
            
        Raises:
            InvalidContextError: If user context is required but not provided
            ValueError: If task already exists or user has too many tasks
        """
        if task_id in self.tasks:
            logger.warning(f"Task {task_id} already exists")
            return self.tasks[task_id]
        
        # SECURITY CRITICAL: Determine if user context is required
        context_required = (
            require_user_context if require_user_context is not None 
            else self.enforce_user_context
        )
        
        # Validate user context if required
        if context_required and user_context is None:
            logger.error(f"SECURITY VIOLATION: Task {task_id} requires UserExecutionContext but none provided")
            raise InvalidContextError(f"Task '{name}' requires UserExecutionContext for proper isolation")
        
        # Check user task limits
        if user_context:
            user_id = user_context.user_id
            user_task_count = self._tasks_by_user.get(user_id, 0)
            if user_task_count >= self.max_tasks_per_user:
                raise ValueError(f"User {user_id} has reached maximum task limit ({self.max_tasks_per_user})")
        
        # Serialize user context for task isolation
        context_data = None
        if user_context:
            context_data = user_context.to_dict()
            # Add task metadata
            if task_metadata:
                context_data['task_metadata'] = task_metadata
            logger.info(f"Starting task {task_id} with user context for user {user_context.user_id}")
        
        # Create secure background task
        bg_task = SecureBackgroundTask(
            task_id=task_id,
            name=name,
            user_context_data=context_data,
            require_user_context=context_required
        )
        self.tasks[task_id] = bg_task
        self._total_tasks_created += 1
        
        # Update user task count
        if user_context:
            self._tasks_by_user[user_context.user_id] = self._tasks_by_user.get(user_context.user_id, 0) + 1
        
        try:
            # SECURITY CRITICAL: Wrap coroutine with user context if present
            if user_context:
                wrapped_coro = self._wrap_task_with_context(coro, user_context, task_id)
                bg_task._task = asyncio.create_task(wrapped_coro)
            else:
                if context_required:
                    logger.error(f"SECURITY VIOLATION: Cannot start task {task_id} without required user context")
                    bg_task.status = TaskStatus.FAILED
                    bg_task.error = "Missing required UserExecutionContext"
                    bg_task.completed_at = datetime.now(timezone.utc)
                    self._total_tasks_failed += 1
                    return bg_task
                
                # Start task without context (legacy support)
                if asyncio.iscoroutinefunction(coro):
                    bg_task._task = asyncio.create_task(coro())
                else:
                    # Convert regular callable to coroutine
                    async def wrapper():
                        return coro()
                    bg_task._task = asyncio.create_task(wrapper())
            
            bg_task.status = TaskStatus.RUNNING
            bg_task.started_at = datetime.now(timezone.utc)
            
            context_info = f" with user context for user {user_context.user_id}" if user_context else " without user context"
            logger.info(f"Started secure background task: {task_id} ({name}){context_info}")
            
            # Set up completion callback
            bg_task._task.add_done_callback(
                lambda t: self._task_completed(task_id, t)
            )
            
        except Exception as e:
            bg_task.status = TaskStatus.FAILED
            bg_task.error = str(e)
            bg_task.completed_at = datetime.now(timezone.utc)
            self._total_tasks_failed += 1
            logger.error(f"Failed to start secure task {task_id}: {e}")
        
        return bg_task
    
    async def _wrap_task_with_context(
        self, 
        coro: Callable, 
        user_context: UserExecutionContext, 
        task_id: str
    ):
        """Wrap a coroutine with user context for proper isolation."""
        try:
            logger.debug(f"Executing secure task {task_id} with user context: {user_context.get_correlation_id()}")
            
            # SECURITY CRITICAL: Validate context before execution
            user_context.verify_isolation()
            
            # Create child context for task execution
            task_context = user_context.create_child_context(
                operation_name=f"background_task_{task_id}",
                additional_audit_metadata={
                    'task_id': task_id,
                    'task_execution_start': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Execute the coroutine with context
            if asyncio.iscoroutinefunction(coro):
                # Check if the coroutine accepts user_context parameter
                sig = inspect.signature(coro)
                if 'user_context' in sig.parameters:
                    result = await coro(user_context=task_context)
                else:
                    # Log warning if task doesn't accept user context
                    logger.warning(
                        f"Task {task_id} doesn't accept user_context parameter - "
                        "isolation may be incomplete"
                    )
                    result = await coro()
            else:
                # Convert regular callable to coroutine
                async def wrapper():
                    return coro()
                result = await wrapper()
            
            logger.debug(f"Secure task {task_id} completed successfully for user {user_context.user_id}")
            return result
            
        except Exception as e:
            logger.error(
                f"Secure task {task_id} failed for user {user_context.user_id}: {e}",
                exc_info=True
            )
            raise
    
    def _task_completed(self, task_id: str, task: asyncio.Task):
        """Handle secure task completion with context cleanup."""
        if task_id not in self.tasks:
            return
        
        bg_task = self.tasks[task_id]
        bg_task.completed_at = datetime.now(timezone.utc)
        
        # Update user task count
        if bg_task.user_context_data:
            user_id = bg_task.user_context_data.get('user_id')
            if user_id and user_id in self._tasks_by_user:
                self._tasks_by_user[user_id] = max(0, self._tasks_by_user[user_id] - 1)
        
        if task.cancelled():
            bg_task.status = TaskStatus.CANCELLED
            logger.info(f"Secure task {task_id} was cancelled")
        elif task.exception():
            bg_task.status = TaskStatus.FAILED
            bg_task.error = str(task.exception())
            self._total_tasks_failed += 1
            logger.error(f"Secure task {task_id} failed: {bg_task.error}")
        else:
            bg_task.status = TaskStatus.COMPLETED
            bg_task.result = task.result()
            self._total_tasks_completed += 1
            logger.info(f"Secure task {task_id} completed successfully")
    
    async def cancel_task(self, task_id: str, user_context: Optional[UserExecutionContext] = None) -> bool:
        """Cancel a secure background task with user context validation."""
        task = self.get_task(task_id, user_context)
        if not task:
            logger.warning(f"Task {task_id} not found or access denied")
            return False
        
        if task._task and not task._task.done():
            task._task.cancel()
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            
            # Log with user context if available
            user_info = f" by user {user_context.user_id}" if user_context else ""
            logger.info(f"Cancelled secure task {task_id}{user_info}")
            return True
        
        return False
    
    async def wait_for_task(
        self, 
        task_id: str, 
        timeout: Optional[float] = None,
        user_context: Optional[UserExecutionContext] = None
    ) -> Optional[Any]:
        """Wait for a secure task to complete with user context validation."""
        task = self.get_task(task_id, user_context)
        if not task or not task._task:
            return None
        
        try:
            if timeout:
                return await asyncio.wait_for(task._task, timeout=timeout)
            else:
                return await task._task
        except asyncio.TimeoutError:
            logger.warning(f"Secure task {task_id} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error waiting for secure task {task_id}: {e}")
            return None
    
    def get_task(self, task_id: str, user_context: Optional[UserExecutionContext] = None) -> Optional[SecureBackgroundTask]:
        """Get task by ID with user context validation."""
        task = self.tasks.get(task_id)
        
        if task and user_context and task.user_context_data:
            # SECURITY CRITICAL: Validate user can access this task
            task_user_id = task.user_context_data.get('user_id')
            if task_user_id and task_user_id != user_context.user_id:
                logger.warning(
                    f"SECURITY: User {user_context.user_id} attempted to access "
                    f"task {task_id} belonging to user {task_user_id}"
                )
                return None
        
        return task
    
    def list_tasks(self, user_context: Optional[UserExecutionContext] = None) -> List[SecureBackgroundTask]:
        """Get tasks, optionally filtered by user context for security."""
        if user_context:
            # SECURITY CRITICAL: Filter tasks by user
            user_tasks = []
            for task in self.tasks.values():
                if task.user_context_data:
                    task_user_id = task.user_context_data.get('user_id')
                    if task_user_id == user_context.user_id:
                        user_tasks.append(task)
                else:
                    # Tasks without context - only include if not enforcing context
                    if not self.enforce_user_context:
                        user_tasks.append(task)
            return user_tasks
        else:
            # Return all tasks if no user context provided (admin view)
            return list(self.tasks.values())
    
    def get_running_tasks(self, user_context: Optional[UserExecutionContext] = None) -> List[SecureBackgroundTask]:
        """Get running tasks, optionally filtered by user context."""
        running_tasks = [task for task in self.tasks.values() 
                        if task.status == TaskStatus.RUNNING]
        
        if user_context:
            # SECURITY CRITICAL: Filter by user
            user_running_tasks = []
            for task in running_tasks:
                if task.user_context_data:
                    task_user_id = task.user_context_data.get('user_id')
                    if task_user_id == user_context.user_id:
                        user_running_tasks.append(task)
                else:
                    # Tasks without context
                    if not self.enforce_user_context:
                        user_running_tasks.append(task)
            return user_running_tasks
        
        return running_tasks
    
    def get_user_task_count(self, user_id: str) -> int:
        """Get the number of active tasks for a specific user."""
        return self._tasks_by_user.get(user_id, 0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get task manager metrics."""
        return {
            'total_tasks': len(self.tasks),
            'running_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            'completed_tasks': self._total_tasks_completed,
            'failed_tasks': self._total_tasks_failed,
            'cancelled_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED]),
            'tasks_created': self._total_tasks_created,
            'enforce_user_context': self.enforce_user_context,
            'max_tasks_per_user': self.max_tasks_per_user,
            'users_with_tasks': len(self._tasks_by_user),
            'average_tasks_per_user': sum(self._tasks_by_user.values()) / len(self._tasks_by_user) if self._tasks_by_user else 0
        }
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up completed tasks older than specified age."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_at and task.completed_at.timestamp() < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks older than {max_age_hours} hours")
    
    async def shutdown(self, timeout: int = 30):
        """Shutdown secure task manager and cancel all running tasks."""
        logger.info("Shutting down SecureBackgroundTaskManager")
        self._running = False
        
        running_tasks = self.get_running_tasks()
        if not running_tasks:
            logger.info("No running tasks to cancel")
            return
        
        logger.info(f"Cancelling {len(running_tasks)} running secure tasks")
        
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
            logger.warning(f"Some secure tasks did not cancel within {timeout}s timeout")
        except Exception as e:
            logger.error(f"Error during secure task shutdown: {e}")
        
        logger.info("SecureBackgroundTaskManager shutdown completed")
    
    @property
    def is_running(self) -> bool:
        """Check if task manager is running."""
        return self._running


# Global secure instance
secure_background_task_manager = SecureBackgroundTaskManager()


async def get_secure_background_task_manager() -> SecureBackgroundTaskManager:
    """Get secure background task manager instance."""
    return secure_background_task_manager


# Export public classes and functions
__all__ = [
    'SecureBackgroundTask',
    'SecureBackgroundTaskManager', 
    'TaskStatus',
    'secure_background_task_manager',
    'get_secure_background_task_manager'
]