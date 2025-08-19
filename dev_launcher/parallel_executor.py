"""
Parallel execution engine for development launcher optimization.
"""

import os
import sys
import time
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future, as_completed
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

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
        """Initialize parallel executor with dynamic worker allocation."""
        self.max_cpu_workers = max_cpu_workers or self._get_cpu_workers()
        self.max_io_workers = max_io_workers or self._get_io_workers() 
        self._setup_executors()
        self._setup_state()
    
    def _get_cpu_workers(self) -> int:
        """Calculate optimal CPU worker count."""
        cpu_count = os.cpu_count() or 4
        return max(2, min(cpu_count, 8))
    
    def _get_io_workers(self) -> int:
        """Calculate optimal I/O worker count."""
        cpu_count = os.cpu_count() or 4
        return max(4, min(cpu_count * 4, 16))
    
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
        """Update dependency graph for task."""
        self.dependency_graph[task.task_id] = task.dependencies.copy()
    
    def execute_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """Execute all tasks respecting dependencies."""
        start_time = time.time()
        execution_order = self._resolve_dependencies()
        
        for batch in execution_order:
            self._execute_batch(batch)
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning("Execution timeout reached")
                break
        
        self._wait_for_completion()
        return self.completed
    
    def _resolve_dependencies(self) -> List[List[str]]:
        """Resolve task dependencies into execution batches."""
        batches = []
        remaining = set(self.tasks.keys())
        completed_in_this_run = set()
        
        while remaining:
            ready_tasks = self._find_ready_tasks(remaining, completed_in_this_run)
            if not ready_tasks:
                logger.error(f"Circular dependency detected, remaining: {remaining}")
                # Add remaining tasks to avoid infinite loop
                batches.append(list(remaining))
                break
            
            batches.append(sorted(ready_tasks, key=self._get_task_priority))
            completed_in_this_run.update(ready_tasks)
            remaining.difference_update(ready_tasks)
        
        return batches
    
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
        """Execute batch of independent tasks."""
        # Submit all tasks in batch
        for task_id in batch:
            self._submit_task(task_id)
        
        # Wait for this batch to complete before moving to next batch
        batch_futures = {task_id: future for task_id, future in self.pending.items() if task_id in batch}
        for task_id, future in batch_futures.items():
            try:
                result = future.result(timeout=30)
                self.completed[task_id] = result
            except Exception as e:
                logger.error(f"Batch task {task_id} failed: {e}")
                self.completed[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=e,
                    duration=0.0,
                    worker_type=""
                )
        
        # Remove completed tasks from pending
        for task_id in batch:
            self.pending.pop(task_id, None)
    
    def _submit_task(self, task_id: str):
        """Submit single task to appropriate executor."""
        task = self.tasks[task_id]
        executor = self._select_executor(task)
        
        if not executor:
            self._execute_synchronous(task)
            return
        
        future = executor.submit(self._execute_task, task)
        self.pending[task_id] = future
    
    def _select_executor(self, task: ParallelTask) -> Optional[Union[ProcessPoolExecutor, ThreadPoolExecutor]]:
        """Select appropriate executor for task."""
        # Use ThreadPoolExecutor for all tasks to avoid pickling issues
        # ProcessPoolExecutor has issues with local functions and complex objects
        return self.thread_executor
    
    def _execute_task(self, task: ParallelTask) -> TaskResult:
        """Execute single task with error handling."""
        start_time = time.time()
        
        try:
            result = task.func(*task.args, **task.kwargs)
            duration = time.time() - start_time
            
            return TaskResult(
                task_id=task.task_id,
                success=True, 
                result=result,
                duration=duration,
                worker_type=task.task_type.value
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Task {task.task_id} failed: {e}")
            
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=e,
                duration=duration,
                worker_type=task.task_type.value
            )
    
    def _execute_synchronous(self, task: ParallelTask):
        """Execute task synchronously as fallback."""
        result = self._execute_task(task)
        self.completed[task.task_id] = result
    
    def _wait_for_completion(self):
        """Wait for all pending tasks to complete."""
        for task_id, future in self.pending.items():
            try:
                result = future.result(timeout=30)
                self.completed[task_id] = result
            except Exception as e:
                logger.error(f"Task {task_id} completion failed: {e}")
                self.completed[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=e,
                    duration=0.0,
                    worker_type=""
                )
    
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
            "io_workers": self.max_io_workers
        }


def create_dependency_task(task_id: str, func: Callable, dependencies: List[str] = None,
                          task_type: TaskType = TaskType.IO_BOUND, **kwargs) -> ParallelTask:
    """Helper to create dependency-aware parallel task."""
    return ParallelTask(
        task_id=task_id,
        func=func,
        dependencies=dependencies or [],
        task_type=task_type,
        **kwargs
    )


def create_cpu_task(task_id: str, func: Callable, **kwargs) -> ParallelTask:
    """Helper to create CPU-bound parallel task."""
    return create_dependency_task(task_id, func, task_type=TaskType.CPU_BOUND, **kwargs)


def create_io_task(task_id: str, func: Callable, **kwargs) -> ParallelTask:
    """Helper to create I/O-bound parallel task."""
    return create_dependency_task(task_id, func, task_type=TaskType.IO_BOUND, **kwargs)