"""
Parallel execution engine for development launcher optimization.
"""

import asyncio
import logging
import os
import sys
import time
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task execution type classification."""
    CPU_BOUND = "cpu_bound"
    IO_BOUND = "io_bound" 
    NETWORK_BOUND = "network_bound"
    MIXED = "mixed"


@dataclass
class ParallelTask:
    """Task definition for parallel execution."""
    task_id: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    task_type: TaskType = TaskType.IO_BOUND
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    priority: int = 0
    retry_count: int = 0


@dataclass  
class TaskResult:
    """Result of parallel task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    worker_type: str = ""


class ParallelExecutor:
    """
    Parallel execution engine with dependency management.
    
    Supports both process and thread pools with intelligent
    task routing based on workload characteristics.
    """
    
    def __init__(self, max_cpu_workers: Optional[int] = None,
                 max_io_workers: Optional[int] = None):
        """Initialize parallel executor with dynamic worker allocation and performance monitoring."""
        self.max_cpu_workers = max_cpu_workers or self._get_cpu_workers()
        self.max_io_workers = max_io_workers or self._get_io_workers() 
        self._setup_executors()
        self._setup_state()
        self._setup_performance_tracking()
        
    def _setup_performance_tracking(self):
        """Setup performance monitoring for concurrent tasks."""
        self.performance_metrics = {
            'task_start_times': {},
            'batch_processing_times': [],
            'concurrent_task_count': 0,
            'max_concurrent_tasks': 0,
            'retry_attempts': {},
            'timeout_events': 0
        }
    
    def _get_cpu_workers(self) -> int:
        """Calculate optimal CPU worker count."""
        cpu_count = os.cpu_count() or 4
        return max(2, min(cpu_count, 8))
    
    def _get_io_workers(self) -> int:
        """Calculate optimal I/O worker count with performance optimization."""
        cpu_count = os.cpu_count() or 4
        # Increase worker count for better concurrent performance
        return max(6, min(cpu_count * 6, 24))  # Increased from 4*4,16 to 6*6,24
    
    def _setup_executors(self):
        """Setup process and thread pool executors."""
        try:
            self.process_executor = ProcessPoolExecutor(
                max_workers=self.max_cpu_workers
            )
            self.thread_executor = ThreadPoolExecutor(
                max_workers=self.max_io_workers
            )
        except Exception as e:
            logger.warning(f"Executor setup failed: {e}")
            self._setup_fallback_executors()
    
    def _setup_fallback_executors(self):
        """Setup fallback executors on error."""
        self.process_executor = None
        self.thread_executor = ThreadPoolExecutor(max_workers=4)
    
    def _setup_state(self):
        """Setup execution state tracking."""
        self.tasks: Dict[str, ParallelTask] = {}
        self.completed: Dict[str, TaskResult] = {}
        self.pending: Dict[str, Future] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
    
    def add_task(self, task: ParallelTask) -> bool:
        """Add task to execution queue."""
        if task.task_id in self.tasks:
            logger.warning(f"Task {task.task_id} already exists")
            return False
        
        self.tasks[task.task_id] = task
        self._update_dependency_graph(task)
        return True
    
    def _update_dependency_graph(self, task: ParallelTask):
        """Update dependency graph for task with validation."""
        # Validate dependencies exist
        for dep in task.dependencies:
            if dep not in self.tasks and dep not in self.dependency_graph:
                logger.warning(f"Task {task.task_id} depends on unknown task {dep}")
        
        self.dependency_graph[task.task_id] = task.dependencies.copy()
        
        # Detect potential circular dependencies early
        if self._has_circular_dependency(task.task_id):
            logger.warning(f"Potential circular dependency detected for task {task.task_id}")
    
    def execute_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """Execute all tasks respecting dependencies with improved error handling."""
        start_time = time.time()
        execution_order = self._resolve_dependencies()
        
        for batch_index, batch in enumerate(execution_order):
            # Check global timeout before each batch
            if timeout:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Global execution timeout reached after {elapsed:.1f}s")
                    # Mark remaining tasks as failed
                    remaining_tasks = set(self.tasks.keys()) - set(self.completed.keys())
                    for task_id in remaining_tasks:
                        self.completed[task_id] = TaskResult(
                            task_id=task_id,
                            success=False,
                            error=TimeoutError(f"Global timeout exceeded"),
                            duration=0.0,
                            worker_type="timeout"
                        )
                    break
            
            logger.debug(f"Executing batch {batch_index + 1}/{len(execution_order)}: {batch}")
            try:
                self._execute_batch(batch)
            except Exception as e:
                logger.error(f"Batch {batch_index + 1} execution failed: {e}")
                # Continue with next batch instead of failing completely
                
        self._wait_for_completion()
        return self.completed
    
    def _resolve_dependencies(self) -> List[List[str]]:
        """Resolve task dependencies into execution batches with cycle detection."""
        batches = []
        remaining = set(self.tasks.keys())
        completed_in_this_run = set()
        max_iterations = len(self.tasks) + 5  # Prevent infinite loops
        iteration_count = 0
        
        while remaining and iteration_count < max_iterations:
            iteration_count += 1
            ready_tasks = self._find_ready_tasks(remaining, completed_in_this_run)
            
            if not ready_tasks:
                logger.error(f"Circular dependency detected after {iteration_count} iterations, remaining: {remaining}")
                # Try to break circular dependencies by finding tasks with fewest unresolved deps
                fallback_tasks = self._find_fallback_tasks(remaining, completed_in_this_run)
                if fallback_tasks:
                    logger.warning(f"Breaking circular dependency by executing: {fallback_tasks}")
                    batches.append(fallback_tasks)
                    completed_in_this_run.update(fallback_tasks)
                    remaining.difference_update(fallback_tasks)
                else:
                    # Last resort: add remaining tasks to avoid infinite loop
                    logger.error(f"Adding remaining tasks without dependency resolution: {remaining}")
                    batches.append(list(remaining))
                    break
            else:
                # Sort by priority and dependency count for optimal execution order
                sorted_tasks = sorted(ready_tasks, key=lambda t: (self._get_task_priority(t), len(self.dependency_graph.get(t, []))))
                batches.append(sorted_tasks)
                completed_in_this_run.update(ready_tasks)
                remaining.difference_update(ready_tasks)
        
        if iteration_count >= max_iterations:
            logger.error(f"Dependency resolution exceeded maximum iterations ({max_iterations})")
        
        return batches
    
    def _wait_for_dependencies(self, batch: List[str]):
        """Wait for dependencies of batch tasks to complete."""
        for task_id in batch:
            task = self.tasks[task_id]
            for dep_id in task.dependencies:
                if dep_id not in self.completed:
                    logger.debug(f"Waiting for dependency {dep_id} of task {task_id}")
                    # Dependencies should already be completed by batch ordering
                    # This is a safety check
                    max_wait_time = 30
                    wait_start = time.time()
                    while dep_id not in self.completed and (time.time() - wait_start) < max_wait_time:
                        time.sleep(0.1)
                    
                    if dep_id not in self.completed:
                        logger.error(f"Dependency {dep_id} of task {task_id} not completed within timeout")
    
    def _has_circular_dependency(self, task_id: str, visited: set = None, path: set = None) -> bool:
        """Check for circular dependencies using DFS."""
        if visited is None:
            visited = set()
        if path is None:
            path = set()
            
        if task_id in path:
            return True
            
        if task_id in visited:
            return False
            
        visited.add(task_id)
        path.add(task_id)
        
        for dep_id in self.dependency_graph.get(task_id, []):
            if self._has_circular_dependency(dep_id, visited, path):
                return True
                
        path.remove(task_id)
        return False
    
    def _find_fallback_tasks(self, remaining: set, completed_in_this_run: set) -> List[str]:
        """Find tasks with fewest unresolved dependencies to break circular deps."""
        all_completed = self.completed.keys() | completed_in_this_run
        fallback_candidates = []
        
        for task_id in remaining:
            deps = self.dependency_graph.get(task_id, [])
            unresolved_deps = [dep for dep in deps if dep not in all_completed]
            fallback_candidates.append((task_id, len(unresolved_deps)))
        
        # Sort by fewest unresolved dependencies
        fallback_candidates.sort(key=lambda x: x[1])
        
        # Return tasks with minimum unresolved dependencies
        if fallback_candidates:
            min_deps = fallback_candidates[0][1]
            return [task_id for task_id, deps_count in fallback_candidates if deps_count == min_deps]
        
        return []
    
    def _find_ready_tasks(self, remaining: set, completed_in_this_run: set = None) -> List[str]:
        """Find tasks ready for execution."""
        if completed_in_this_run is None:
            completed_in_this_run = set()
        
        ready = []
        all_completed = self.completed.keys() | completed_in_this_run
        
        for task_id in remaining:
            deps = self.dependency_graph.get(task_id, [])
            if all(dep in all_completed for dep in deps):
                ready.append(task_id)
        return ready
    
    def _get_task_priority(self, task_id: str) -> int:
        """Get task priority for sorting."""
        return -self.tasks[task_id].priority
    
    def _execute_batch(self, batch: List[str]):
        """Execute batch of independent tasks with dependency-aware timing."""
        # Ensure dependencies are completed before starting batch
        self._wait_for_dependencies(batch)
        
        # Submit all tasks in batch
        for task_id in batch:
            self._submit_task(task_id)
        
        # Wait for this batch to complete before moving to next batch
        batch_futures = {task_id: future for task_id, future in self.pending.items() if task_id in batch}
        for task_id, future in batch_futures.items():
            task = self.tasks[task_id]
            # Use task-specific timeout or default
            task_timeout = task.timeout if task.timeout else 30
            
            try:
                result = future.result(timeout=task_timeout)
                self.completed[task_id] = result
                # Update performance tracking
                self.performance_metrics['concurrent_task_count'] -= 1
            except Exception as e:
                logger.error(f"Batch task {task_id} failed: {e}")
                self.completed[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=e,
                    duration=0.0,
                    worker_type=""
                )
                self.performance_metrics['concurrent_task_count'] -= 1
                
                # Track timeout events
                if isinstance(e, TimeoutError):
                    self.performance_metrics['timeout_events'] += 1
        
        # Remove completed tasks from pending
        for task_id in batch:
            self.pending.pop(task_id, None)
    
    def _submit_task(self, task_id: str):
        """Submit single task to appropriate executor with performance tracking."""
        task = self.tasks[task_id]
        executor = self._select_executor(task)
        
        # Track performance metrics
        self.performance_metrics['task_start_times'][task_id] = time.time()
        self.performance_metrics['concurrent_task_count'] += 1
        self.performance_metrics['max_concurrent_tasks'] = max(
            self.performance_metrics['max_concurrent_tasks'],
            self.performance_metrics['concurrent_task_count']
        )
        
        if not executor:
            self._execute_synchronous(task)
            self.performance_metrics['concurrent_task_count'] -= 1
            return
        
        future = executor.submit(self._execute_task, task)
        self.pending[task_id] = future
    
    def _select_executor(self, task: ParallelTask) -> Optional[Union[ProcessPoolExecutor, ThreadPoolExecutor]]:
        """Select appropriate executor for task."""
        # Use ThreadPoolExecutor for all tasks to avoid pickling issues
        # ProcessPoolExecutor has issues with local functions and complex objects
        return self.thread_executor
    
    def _execute_task(self, task: ParallelTask) -> TaskResult:
        """Execute single task with error handling and retry logic with timeout enforcement."""
        start_time = time.time()
        last_exception = None
        
        # Attempt execution with retries
        for attempt in range(task.retry_count + 1):  # +1 for initial attempt
            attempt_start_time = time.time()
            try:
                if attempt > 0:
                    logger.info(f"Retrying task {task.task_id}, attempt {attempt + 1}/{task.retry_count + 1}")
                    # Brief delay before retry to allow transient issues to resolve
                    time.sleep(0.1 * attempt)  # Reduced delay for faster retries
                
                # Check timeout before each attempt
                if task.timeout:
                    elapsed = time.time() - start_time
                    if elapsed >= task.timeout:
                        raise TimeoutError(f"Task {task.task_id} timed out after {elapsed:.1f}s (limit: {task.timeout}s)")
                    
                    # Calculate remaining time for this attempt
                    remaining_time = task.timeout - elapsed
                    if remaining_time <= 0:
                        raise TimeoutError(f"Task {task.task_id} no time remaining for attempt {attempt + 1}")
                
                # Execute with timeout monitoring
                result = task.func(*task.args, **task.kwargs)
                
                # Check if we exceeded timeout during execution
                attempt_duration = time.time() - attempt_start_time
                total_elapsed = time.time() - start_time
                if task.timeout and total_elapsed > task.timeout:
                    raise TimeoutError(f"Task {task.task_id} exceeded timeout during execution ({total_elapsed:.1f}s > {task.timeout}s)")
                
                duration = time.time() - start_time
                
                if attempt > 0:
                    logger.info(f"Task {task.task_id} succeeded on retry {attempt}")
                
                return TaskResult(
                    task_id=task.task_id,
                    success=True, 
                    result=result,
                    duration=duration,
                    worker_type=task.task_type.value
                )
            except TimeoutError as e:
                last_exception = e
                logger.error(f"Task {task.task_id} timed out on attempt {attempt + 1}: {e}")
                break  # Don't retry timeout errors
            except Exception as e:
                last_exception = e
                if attempt < task.retry_count:
                    # Check if we have time for another retry
                    if task.timeout:
                        elapsed = time.time() - start_time
                        if elapsed >= task.timeout * 0.8:  # Use 80% of timeout for retries
                            logger.warning(f"Task {task.task_id} skipping retry due to timeout approaching")
                            break
                    logger.warning(f"Task {task.task_id} failed on attempt {attempt + 1}: {e}")
                else:
                    logger.error(f"Task {task.task_id} failed after {task.retry_count + 1} attempts: {e}")
        
        # All attempts failed
        duration = time.time() - start_time
        return TaskResult(
            task_id=task.task_id,
            success=False,
            error=last_exception,
            duration=duration,
            worker_type=task.task_type.value
        )
    
    def _execute_synchronous(self, task: ParallelTask):
        """Execute task synchronously as fallback."""
        result = self._execute_task(task)
        self.completed[task.task_id] = result
    
    def _wait_for_completion(self):
        """Wait for all pending tasks to complete with improved error handling."""
        if not self.pending:
            return
            
        # Use as_completed for better performance with many concurrent tasks
        try:
            for task_id, future in self.pending.items():
                task = self.tasks.get(task_id)
                task_timeout = task.timeout if task and task.timeout else 30
                
                try:
                    result = future.result(timeout=task_timeout)
                    if task_id not in self.completed:  # Avoid duplicate completion
                        self.completed[task_id] = result
                except Exception as e:
                    if task_id not in self.completed:  # Only log if not already completed
                        logger.error(f"Task {task_id} completion failed: {e}")
                        self.completed[task_id] = TaskResult(
                            task_id=task_id,
                            success=False,
                            error=e,
                            duration=0.0,
                            worker_type=task.task_type.value if task else ""
                        )
        except Exception as e:
            logger.error(f"Wait for completion failed: {e}")
    
    def cleanup(self):
        """Cleanup executors and resources."""
        try:
            if self.thread_executor:
                self.thread_executor.shutdown(wait=True)
            if self.process_executor:
                self.process_executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Executor cleanup failed: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get execution performance statistics."""
        total_tasks = len(self.completed)
        successful_tasks = sum(1 for r in self.completed.values() if r.success)
        total_duration = sum(r.duration for r in self.completed.values())
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": total_tasks - successful_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / total_tasks if total_tasks > 0 else 0,
            "cpu_workers": self.max_cpu_workers,
            "io_workers": self.max_io_workers,
            "concurrent_tasks": len(self.pending),
            "timeout_failures": sum(1 for r in self.completed.values() 
                                   if r.error and isinstance(r.error, TimeoutError)),
            "retry_successes": sum(1 for r in self.completed.values() 
                                 if r.success and "retry" in str(r.result or "").lower())
        }


def create_dependency_task(task_id: str, func: Callable, dependencies: List[str] = None,
                          task_type: TaskType = TaskType.IO_BOUND, retry_count: int = 0, **kwargs) -> ParallelTask:
    """Helper to create dependency-aware parallel task."""
    return ParallelTask(
        task_id=task_id,
        func=func,
        dependencies=dependencies or [],
        task_type=task_type,
        retry_count=retry_count,
        **kwargs
    )


def create_cpu_task(task_id: str, func: Callable, **kwargs) -> ParallelTask:
    """Helper to create CPU-bound parallel task."""
    return create_dependency_task(task_id, func, task_type=TaskType.CPU_BOUND, **kwargs)


def create_io_task(task_id: str, func: Callable, **kwargs) -> ParallelTask:
    """Helper to create I/O-bound parallel task."""
    return create_dependency_task(task_id, func, task_type=TaskType.IO_BOUND, **kwargs)