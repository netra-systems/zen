"""
Startup Coordinator Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a startup coordinator implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StartupPhase(Enum):
    """Startup phases."""
    INITIALIZATION = "initialization"
    DATABASE = "database"
    SERVICES = "services"
    ROUTES = "routes"
    HEALTH_CHECKS = "health_checks"
    FINALIZATION = "finalization"
    COMPLETED = "completed"


@dataclass
class StartupTask:
    """Startup task definition."""
    name: str
    phase: StartupPhase
    task_function: Callable
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 30.0
    critical: bool = True
    retries: int = 0


@dataclass
class StartupResult:
    """Result of a startup task."""
    task_name: str
    phase: StartupPhase
    success: bool
    duration: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class StartupCoordinator:
    """
    Simple startup coordinator for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self):
        """Initialize startup coordinator."""
        self.tasks: Dict[str, StartupTask] = {}
        self.results: Dict[str, StartupResult] = {}
        self.current_phase = None
        self.startup_complete = False
        self.startup_start_time = None

        logger.info("Startup coordinator initialized (test compatibility mode)")

    def register_task(self, task: StartupTask):
        """Register a startup task."""
        self.tasks[task.name] = task
        logger.debug(f"Startup task registered: {task.name} (phase: {task.phase.value})")

    def register_simple_task(self, name: str, phase: StartupPhase,
                           task_function: Callable, critical: bool = True):
        """Register a simple startup task."""
        task = StartupTask(
            name=name,
            phase=phase,
            task_function=task_function,
            critical=critical
        )
        self.register_task(task)

    async def execute_startup(self) -> bool:
        """Execute the complete startup sequence."""
        self.startup_start_time = time.time()
        logger.info("Starting application startup sequence")

        try:
            # Execute tasks phase by phase
            for phase in StartupPhase:
                if phase == StartupPhase.COMPLETED:
                    continue

                self.current_phase = phase
                success = await self._execute_phase(phase)

                if not success:
                    logger.error(f"Startup failed in phase: {phase.value}")
                    return False

            self.current_phase = StartupPhase.COMPLETED
            self.startup_complete = True

            total_duration = time.time() - self.startup_start_time
            logger.info(f"Application startup completed successfully in {total_duration:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Startup sequence failed: {e}")
            return False

    async def _execute_phase(self, phase: StartupPhase) -> bool:
        """Execute all tasks in a specific phase."""
        phase_tasks = [task for task in self.tasks.values() if task.phase == phase]

        if not phase_tasks:
            logger.debug(f"No tasks found for phase: {phase.value}")
            return True

        logger.info(f"Executing startup phase: {phase.value} ({len(phase_tasks)} tasks)")

        # Sort tasks by dependencies (simple topological sort)
        ordered_tasks = self._topological_sort_tasks(phase_tasks)

        for task in ordered_tasks:
            success = await self._execute_task(task)

            if not success and task.critical:
                logger.error(f"Critical task failed in phase {phase.value}: {task.name}")
                return False
            elif not success:
                logger.warning(f"Non-critical task failed in phase {phase.value}: {task.name}")

        return True

    def _topological_sort_tasks(self, tasks: List[StartupTask]) -> List[StartupTask]:
        """Simple topological sort for task dependencies."""
        # For simplicity, just return tasks as-is
        # In a real implementation, this would handle complex dependencies
        return sorted(tasks, key=lambda t: len(t.dependencies))

    async def _execute_task(self, task: StartupTask) -> bool:
        """Execute a single startup task."""
        logger.debug(f"Executing startup task: {task.name}")
        start_time = time.time()

        for attempt in range(task.retries + 1):
            try:
                # Execute the task with timeout
                if asyncio.iscoroutinefunction(task.task_function):
                    await asyncio.wait_for(task.task_function(), timeout=task.timeout)
                else:
                    # Run sync function in executor to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(None, task.task_function)

                duration = time.time() - start_time
                result = StartupResult(
                    task_name=task.name,
                    phase=task.phase,
                    success=True,
                    duration=duration
                )
                self.results[task.name] = result

                logger.debug(f"Task completed successfully: {task.name} ({duration:.3f}s)")
                return True

            except asyncio.TimeoutError:
                error_msg = f"Task timed out after {task.timeout}s"
                if attempt < task.retries:
                    logger.warning(f"Task {task.name} timed out, retrying... ({attempt + 1}/{task.retries})")
                    continue
                else:
                    logger.error(f"Task {task.name} failed: {error_msg}")
                    self._record_task_failure(task, error_msg, start_time)
                    return False

            except Exception as e:
                error_msg = str(e)
                if attempt < task.retries:
                    logger.warning(f"Task {task.name} failed, retrying... ({attempt + 1}/{task.retries}): {error_msg}")
                    continue
                else:
                    logger.error(f"Task {task.name} failed: {error_msg}")
                    self._record_task_failure(task, error_msg, start_time)
                    return False

        return False

    def _record_task_failure(self, task: StartupTask, error_msg: str, start_time: float):
        """Record task failure."""
        duration = time.time() - start_time
        result = StartupResult(
            task_name=task.name,
            phase=task.phase,
            success=False,
            duration=duration,
            error=error_msg
        )
        self.results[task.name] = result

    def get_startup_status(self) -> Dict[str, Any]:
        """Get startup status."""
        if not self.startup_start_time:
            return {"status": "not_started"}

        total_tasks = len(self.tasks)
        completed_tasks = len(self.results)
        successful_tasks = sum(1 for r in self.results.values() if r.success)
        failed_tasks = completed_tasks - successful_tasks

        return {
            "status": "completed" if self.startup_complete else "in_progress",
            "current_phase": self.current_phase.value if self.current_phase else None,
            "total_duration": time.time() - self.startup_start_time if self.startup_start_time else 0,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "progress_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }

    def get_task_results(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed task results."""
        return {
            name: {
                "phase": result.phase.value,
                "success": result.success,
                "duration": result.duration,
                "error": result.error,
                "timestamp": result.timestamp
            }
            for name, result in self.results.items()
        }

    def is_startup_complete(self) -> bool:
        """Check if startup is complete."""
        return self.startup_complete

    def reset(self):
        """Reset startup coordinator state."""
        self.results.clear()
        self.current_phase = None
        self.startup_complete = False
        self.startup_start_time = None
        logger.info("Startup coordinator reset")

    # Convenience methods for common startup tasks
    async def initialize_database(self):
        """Initialize database (placeholder)."""
        logger.info("Database initialization (simulated)")
        await asyncio.sleep(0.1)

    async def initialize_services(self):
        """Initialize services (placeholder)."""
        logger.info("Services initialization (simulated)")
        await asyncio.sleep(0.1)

    async def setup_routes(self):
        """Setup routes (placeholder)."""
        logger.info("Routes setup (simulated)")
        await asyncio.sleep(0.05)

    async def setup_health_checks(self):
        """Setup health checks (placeholder)."""
        logger.info("Health checks setup (simulated)")
        await asyncio.sleep(0.05)


# Global instance for compatibility
startup_coordinator = StartupCoordinator()

__all__ = [
    "StartupCoordinator",
    "StartupTask",
    "StartupResult",
    "StartupPhase",
    "startup_coordinator"
]