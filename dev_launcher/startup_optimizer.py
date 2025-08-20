"""
Startup sequence optimization component.

Optimizes the development launcher startup sequence by tracking timing,
enabling parallel execution, and skipping unnecessary initialization steps.
"""

import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from dev_launcher.cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class StartupStep:
    """Represents a single startup step with timing and dependencies."""
    name: str
    func: Callable
    dependencies: List[str]
    parallel: bool = True
    timeout: int = 30
    required: bool = True
    cache_key: Optional[str] = None


@dataclass
class StepResult:
    """Result of a startup step execution."""
    name: str
    success: bool
    duration: float
    error: Optional[str] = None
    cached: bool = False


class StartupPhase(Enum):
    """Startup phases with defined timeouts."""
    INIT = ("INIT", 2.0)
    VALIDATE = ("VALIDATE", 3.0)
    PREPARE = ("PREPARE", 5.0)
    LAUNCH = ("LAUNCH", 5.0)
    VERIFY = ("VERIFY", 3.0)
    
    def __init__(self, phase_name: str, timeout: float):
        self.phase_name = phase_name
        self.timeout = timeout


@dataclass
class PhaseStep:
    """Individual step within a startup phase."""
    name: str
    func: Callable
    timeout: float
    required: bool = True
    can_skip: bool = True
    cache_key: Optional[str] = None


@dataclass
class PhaseResult:
    """Result of a phase execution."""
    phase: StartupPhase
    success: bool
    duration: float
    steps_executed: List[str]
    steps_skipped: List[str]
    error: Optional[str] = None


class StartupOptimizer:
    """
    Optimizes startup sequence and skips unnecessary steps.
    
    Manages parallel execution, dependency tracking, and intelligent
    caching to achieve sub-10 second startup times for cached runs.
    """
    
    def __init__(self, cache_manager: CacheManager, max_workers: int = 4):
        """Initialize startup optimizer."""
        self.cache_manager = cache_manager
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.steps: Dict[str, StartupStep] = {}
        self.step_results: Dict[str, StepResult] = {}
        self.step_futures: Dict[str, Future] = {}
        self.startup_start_time = 0.0
        self.timing_data: Dict[str, float] = {}
    
    def register_step(self, step: StartupStep):
        """Register a startup step."""
        self.steps[step.name] = step
    
    def register_steps(self, steps: List[StartupStep]):
        """Register multiple startup steps."""
        for step in steps:
            self.register_step(step)
    
    def can_skip_step(self, step_name: str) -> bool:
        """Check if a step can be skipped based on cache."""
        step = self.steps.get(step_name)
        if not step or not step.cache_key:
            return False
        
        # Check specific cache conditions
        if step_name == "environment_check":
            return not self.cache_manager.has_environment_changed()
        elif step_name == "migration_check":
            return not self.cache_manager.has_migration_files_changed()
        elif step_name in ["backend_deps", "frontend_deps", "auth_deps"]:
            service_name = step_name.replace("_deps", "")
            return not self.cache_manager.has_dependencies_changed(service_name)
        
        return False
    
    def start_timing(self):
        """Start timing the overall startup process."""
        self.startup_start_time = time.time()
        self.timing_data.clear()
        self.step_results.clear()
        self.step_futures.clear()
    
    def get_total_startup_time(self) -> float:
        """Get total startup time since start_timing was called."""
        if self.startup_start_time == 0:
            return 0.0
        return time.time() - self.startup_start_time
    
    def execute_step(self, step_name: str, *args, **kwargs) -> StepResult:
        """Execute a single step with timing and error handling."""
        step = self.steps.get(step_name)
        if not step:
            return StepResult(step_name, False, 0.0, f"Step '{step_name}' not registered")
        
        # Check if step can be skipped
        if self.can_skip_step(step_name):
            logger.info(f"Skipping {step_name} (cached)")
            return StepResult(step_name, True, 0.0, cached=True)
        
        start_time = time.time()
        try:
            result = step.func(*args, **kwargs)
            duration = time.time() - start_time
            self.timing_data[step_name] = duration
            
            success = result if isinstance(result, bool) else True
            return StepResult(step_name, success, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Step {step_name} failed: {error_msg}")
            return StepResult(step_name, False, duration, error_msg)
    
    def execute_parallel(self, step_names: List[str], *args, **kwargs) -> Dict[str, StepResult]:
        """Execute multiple steps in parallel."""
        futures = {}
        
        for step_name in step_names:
            step = self.steps.get(step_name)
            if step and step.parallel:
                future = self.executor.submit(self.execute_step, step_name, *args, **kwargs)
                futures[step_name] = future
                self.step_futures[step_name] = future
            else:
                # Execute non-parallel steps immediately
                result = self.execute_step(step_name, *args, **kwargs)
                self.step_results[step_name] = result
        
        # Wait for parallel steps to complete
        results = {}
        for step_name, future in futures.items():
            try:
                step = self.steps[step_name]
                result = future.result(timeout=step.timeout)
                results[step_name] = result
                self.step_results[step_name] = result
            except Exception as e:
                error_msg = f"Parallel execution failed: {str(e)}"
                result = StepResult(step_name, False, 0.0, error_msg)
                results[step_name] = result
                self.step_results[step_name] = result
        
        return results
    
    def execute_sequence(self, step_names: List[str], *args, **kwargs) -> Dict[str, StepResult]:
        """Execute steps in sequence, respecting dependencies."""
        results = {}
        
        for step_name in step_names:
            # Check dependencies
            step = self.steps.get(step_name)
            if step:
                for dep in step.dependencies:
                    if dep not in results or not results[dep].success:
                        if step.required:
                            error_msg = f"Dependency {dep} failed or not executed"
                            result = StepResult(step_name, False, 0.0, error_msg)
                            results[step_name] = result
                            self.step_results[step_name] = result
                            continue
            
            result = self.execute_step(step_name, *args, **kwargs)
            results[step_name] = result
            
            # Stop on required step failure
            if step and step.required and not result.success:
                logger.error(f"Required step {step_name} failed, stopping sequence")
                break
        
        return results
    
    def optimize_startup_sequence(self, step_names: List[str]) -> List[List[str]]:
        """Optimize startup sequence for parallel execution."""
        # Group steps by dependency level
        dependency_levels = []
        remaining_steps = set(step_names)
        completed_steps = set()
        
        while remaining_steps:
            current_level = []
            
            for step_name in list(remaining_steps):
                step = self.steps.get(step_name)
                if not step:
                    continue
                
                # Check if all dependencies are completed
                deps_satisfied = all(dep in completed_steps for dep in step.dependencies)
                
                if deps_satisfied:
                    current_level.append(step_name)
            
            if not current_level:
                # Circular dependency or missing step, add remaining
                current_level.extend(remaining_steps)
                logger.warning(f"Potential circular dependency in: {remaining_steps}")
            
            dependency_levels.append(current_level)
            for step_name in current_level:
                remaining_steps.discard(step_name)
                completed_steps.add(step_name)
        
        return dependency_levels
    
    def execute_optimized_sequence(self, step_names: List[str], *args, **kwargs) -> Dict[str, StepResult]:
        """Execute an optimized startup sequence with parallel execution."""
        self.start_timing()
        
        # Optimize the sequence
        dependency_levels = self.optimize_startup_sequence(step_names)
        logger.info(f"Optimized sequence: {dependency_levels}")
        
        all_results = {}
        
        for level_steps in dependency_levels:
            # Separate parallel and sequential steps
            parallel_steps = [name for name in level_steps 
                            if self.steps.get(name, StartupStep("", lambda: None, [])).parallel]
            sequential_steps = [name for name in level_steps 
                              if name not in parallel_steps]
            
            # Execute parallel steps
            if parallel_steps:
                parallel_results = self.execute_parallel(parallel_steps, *args, **kwargs)
                all_results.update(parallel_results)
            
            # Execute sequential steps
            if sequential_steps:
                sequential_results = self.execute_sequence(sequential_steps, *args, **kwargs)
                all_results.update(sequential_results)
            
            # Check for critical failures
            level_failures = [name for name, result in all_results.items() 
                            if name in level_steps and not result.success 
                            and self.steps.get(name, StartupStep("", lambda: None, [], required=True)).required]
            
            if level_failures:
                logger.error(f"Critical failures in level {level_steps}: {level_failures}")
                break
        
        total_time = self.get_total_startup_time()
        self.cache_manager.mark_successful_startup(total_time)
        
        return all_results
    
    def get_timing_report(self) -> Dict[str, Any]:
        """Get detailed timing report for optimization analysis."""
        total_time = self.get_total_startup_time()
        
        return {
            "total_startup_time": total_time,
            "step_timings": self.timing_data,
            "step_results": {name: {
                "success": result.success,
                "duration": result.duration,
                "cached": result.cached,
                "error": result.error
            } for name, result in self.step_results.items()},
            "cached_steps": [name for name, result in self.step_results.items() if result.cached],
            "failed_steps": [name for name, result in self.step_results.items() if not result.success],
            "slowest_steps": sorted(self.timing_data.items(), key=lambda x: x[1], reverse=True)[:5],
            "target_met": total_time < 10.0 if total_time > 0 else False
        }
    
    def cleanup(self):
        """Cleanup resources."""
        # Cancel any pending futures
        for future in self.step_futures.values():
            if not future.done():
                future.cancel()
        
        # Shutdown executor
        self.executor.shutdown(wait=False)
        
        logger.info("StartupOptimizer cleanup completed")
    
    def enable_async_mode(self) -> None:
        """Enable async mode for parallel I/O operations."""
        self._async_mode = True
        logger.info("Async mode enabled for startup optimization")
    
    async def execute_step_async(self, step_name: str, *args, **kwargs) -> StepResult:
        """Execute a single step asynchronously."""
        step = self.steps.get(step_name)
        if not step:
            return StepResult(step_name, False, 0.0, f"Step '{step_name}' not registered")
        
        # Check if step can be skipped
        if self.can_skip_step(step_name):
            logger.info(f"Skipping {step_name} (cached)")
            return StepResult(step_name, True, 0.0, cached=True)
        
        start_time = time.time()
        try:
            # Run in executor for CPU-bound tasks
            if asyncio.iscoroutinefunction(step.func):
                result = await step.func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.executor, step.func, *args, **kwargs)
            
            duration = time.time() - start_time
            self.timing_data[step_name] = duration
            
            success = result if isinstance(result, bool) else True
            return StepResult(step_name, success, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Async step {step_name} failed: {error_msg}")
            return StepResult(step_name, False, duration, error_msg)
    
    async def execute_parallel_async(self, step_names: List[str], *args, **kwargs) -> Dict[str, StepResult]:
        """Execute multiple steps in parallel using async/await."""
        if not self._async_mode:
            return self.execute_parallel(step_names, *args, **kwargs)
        
        # Create tasks for parallel execution
        tasks = []
        for step_name in step_names:
            task = asyncio.create_task(self.execute_step_async(step_name, *args, **kwargs))
            tasks.append((step_name, task))
        
        # Wait for all tasks to complete
        results = {}
        for step_name, task in tasks:
            try:
                result = await task
                results[step_name] = result
                self.step_results[step_name] = result
            except Exception as e:
                error_msg = f"Async parallel execution failed: {str(e)}"
                result = StepResult(step_name, False, 0.0, error_msg)
                results[step_name] = result
                self.step_results[step_name] = result
        
        return results
    
    async def execute_optimized_sequence_async(self, step_names: List[str], *args, **kwargs) -> Dict[str, StepResult]:
        """Execute an optimized startup sequence with async parallelization."""
        if not self._async_mode:
            return self.execute_optimized_sequence(step_names, *args, **kwargs)
        
        self.start_timing()
        
        # Optimize the sequence
        dependency_levels = self.optimize_startup_sequence(step_names)
        logger.info(f"Async optimized sequence: {dependency_levels}")
        
        all_results = {}
        
        for level_steps in dependency_levels:
            # Execute all steps in this level in parallel
            level_results = await self.execute_parallel_async(level_steps, *args, **kwargs)
            all_results.update(level_results)
            
            # Check for critical failures
            level_failures = [name for name, result in level_results.items() 
                            if not result.success 
                            and self.steps.get(name, StartupStep("", lambda: None, [], required=True)).required]
            
            if level_failures:
                logger.error(f"Critical async failures in level {level_steps}: {level_failures}")
                break
        
        total_time = self.get_total_startup_time()
        self.cache_manager.mark_successful_startup(total_time)
        
        return all_results
    
    # Phase-based execution methods (consolidated from startup_sequencer.py)
    def register_phase(self, phase: StartupPhase, steps: List[PhaseStep]):
        """Register steps for a startup phase."""
        if not hasattr(self, 'phases'):
            self.phases: Dict[StartupPhase, List[PhaseStep]] = {}
            self.phase_results: Dict[StartupPhase, PhaseResult] = {}
            self.rollback_actions: Dict[StartupPhase, Callable] = {}
        
        if len(steps) > 10:
            logger.warning(f"Phase {phase.phase_name} has {len(steps)} steps")
        self.phases[phase] = steps
    
    def register_rollback(self, phase: StartupPhase, rollback_func: Callable):
        """Register rollback action for a phase."""
        if not hasattr(self, 'rollback_actions'):
            self.rollback_actions: Dict[StartupPhase, Callable] = {}
        self.rollback_actions[phase] = rollback_func
    
    def can_skip_phase(self, phase: StartupPhase) -> bool:
        """Determine if entire phase can be skipped."""
        if phase == StartupPhase.INIT:
            return False  # INIT never skipped
        return self._check_all_steps_skippable(phase)
    
    def _check_all_steps_skippable(self, phase: StartupPhase) -> bool:
        """Check if all steps in phase are skippable."""
        if not hasattr(self, 'phases'):
            return False
        steps = self.phases.get(phase, [])
        return all(self._can_skip_phase_step(step) for step in steps)
    
    def _can_skip_phase_step(self, step: PhaseStep) -> bool:
        """Check if individual phase step can be skipped."""
        if not step.can_skip or not step.cache_key:
            return False
        return self.cache_manager.is_cached_and_valid(step.cache_key)
    
    def execute_phase_sequence(self) -> Dict[StartupPhase, PhaseResult]:
        """Execute the complete phase-based startup sequence."""
        if not hasattr(self, 'phases'):
            logger.error("No phases registered. Use register_phase() first.")
            return {}
        
        self.start_timing()
        if not hasattr(self, 'phase_results'):
            self.phase_results: Dict[StartupPhase, PhaseResult] = {}
        self.phase_results.clear()
        
        sequence_phases = [StartupPhase.INIT, StartupPhase.VALIDATE, 
                          StartupPhase.PREPARE, StartupPhase.LAUNCH, StartupPhase.VERIFY]
        
        for phase in sequence_phases:
            if not self._process_single_sequence_phase(phase):
                break  # Failed phase, stop execution
        
        return self.phase_results
    
    def _process_single_sequence_phase(self, phase: StartupPhase) -> bool:
        """Process a single phase in the sequence."""
        if self.can_skip_phase(phase):
            self._record_skipped_phase(phase)
            return True
        return self._execute_and_validate_phase(phase)
    
    def _record_skipped_phase(self, phase: StartupPhase):
        """Record a skipped phase result."""
        logger.info(f"Skipping entire phase: {phase.phase_name}")
        steps = self.phases.get(phase, [])
        self.phase_results[phase] = PhaseResult(
            phase, True, 0.0, [], [step.name for step in steps]
        )
    
    def _execute_and_validate_phase(self, phase: StartupPhase) -> bool:
        """Execute phase and validate result."""
        result = self._execute_phase(phase)
        self.phase_results[phase] = result
        
        # Check timeout (goal, not failure)
        if result.duration > phase.timeout:
            logger.warning(f"Phase {phase.phase_name} exceeded goal time ({result.duration:.1f}s > {phase.timeout}s goal)")
        
        if not result.success:
            logger.error(f"Phase {phase.phase_name} failed: {result.error}")
            self._execute_rollback(phase)
            return False
        return True
    
    def _execute_phase(self, phase: StartupPhase) -> PhaseResult:
        """Execute a single phase with all its steps."""
        logger.info(f"Starting phase: {phase.phase_name}")
        phase_start = time.time()
        
        steps = self.phases.get(phase, [])
        executed_steps, skipped_steps = [], []
        
        for step in steps:
            if self._can_skip_phase_step(step):
                logger.debug(f"Skipping cached step: {step.name}")
                skipped_steps.append(step.name)
                continue
            
            step_success, error_msg = self._execute_phase_step(step)
            executed_steps.append(step.name)
            
            if not step_success and step.required:
                error = error_msg or f"Required step {step.name} failed"
                return PhaseResult(phase, False, time.time() - phase_start, 
                                 executed_steps, skipped_steps, error)
        
        return PhaseResult(phase, True, time.time() - phase_start, 
                          executed_steps, skipped_steps)
    
    def _execute_phase_step(self, step: PhaseStep) -> Tuple[bool, Optional[str]]:
        """Execute a single phase step with timeout and error handling."""
        start_time = time.time()
        try:
            result = step.func()
            duration = time.time() - start_time
            success = result if isinstance(result, bool) else True
            
            if success and step.cache_key:
                self.cache_manager.cache_result(step.cache_key, True)
            
            logger.debug(f"Step {step.name}: {'success' if success else 'failed'} in {duration:.2f}s")
            return success, None
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Step {step.name} failed: {error_msg}")
            return False, error_msg
    
    def _execute_rollback(self, failed_phase: StartupPhase):
        """Execute rollback for failed phase and predecessors."""
        if not hasattr(self, 'rollback_actions'):
            return
        
        all_phases = list(StartupPhase)
        failed_index = all_phases.index(failed_phase)
        phases_to_rollback = all_phases[:failed_index + 1]
        
        for phase in reversed(phases_to_rollback):
            rollback_func = self.rollback_actions.get(phase)
            if rollback_func:
                try:
                    logger.info(f"Rolling back phase: {phase.phase_name}")
                    rollback_func()
                except Exception as e:
                    logger.error(f"Rollback failed for {phase.phase_name}: {e}")
    
    def get_phase_sequence_summary(self) -> Dict[str, Any]:
        """Get summary of phase sequence execution."""
        if not hasattr(self, 'phase_results'):
            return {"error": "No phase results available"}
        
        total_time = self.get_total_startup_time()
        successful_phases = [p for p, r in self.phase_results.items() if r.success]
        failed_phases = [p for p, r in self.phase_results.items() if not r.success]
        total_skipped = sum(len(r.steps_skipped) for r in self.phase_results.values())
        total_executed = sum(len(r.steps_executed) for r in self.phase_results.values())
        
        return {
            "total_time": total_time,
            "target_met": total_time < 10.0,
            "successful_phases": [p.phase_name for p in successful_phases],
            "failed_phases": [p.phase_name for p in failed_phases],
            "total_steps_skipped": total_skipped,
            "total_steps_executed": total_executed,
            "phase_timings": {p.phase_name: r.duration for p, r in self.phase_results.items()}
        }


# Factory functions for creating common phase configurations
def create_init_phase_steps(env_checker, secret_loader) -> List[PhaseStep]:
    """Create standard INIT phase steps."""
    return [
        PhaseStep("load_cache", lambda: True, 0.5, True, True, "cache_state"),
        PhaseStep("check_validity", lambda: True, 0.5, True, True, "cache_validity"),
        PhaseStep("load_env", env_checker.load_env_files, 1.0, True, True, "env_files")
    ]


def create_validate_phase_steps(cache_mgr, env_checker, port_checker) -> List[PhaseStep]:
    """Create standard VALIDATE phase steps."""
    return [
        PhaseStep("hash_check", cache_mgr.check_file_hashes, 1.0, True, True, "file_hashes"),
        PhaseStep("env_validate", env_checker.validate_environment, 1.5, True, True, "env_validation"),
        PhaseStep("port_check", port_checker.check_availability, 0.5, True, True, "port_availability")
    ]


def create_prepare_phase_steps(dep_installer, migrator, cache_warmer) -> List[PhaseStep]:
    """Create standard PREPARE phase steps."""
    return [
        PhaseStep("install_deps", dep_installer.install_if_needed, 3.0, False, True, "dependencies"),
        PhaseStep("run_migrations", migrator.migrate_if_needed, 1.5, False, True, "migrations"),
        PhaseStep("warm_cache", cache_warmer.warm_caches, 0.5, False, True, "cache_warming")
    ]


def create_launch_phase_steps(service_starter) -> List[PhaseStep]:
    """Create standard LAUNCH phase steps."""
    return [
        PhaseStep("start_auth", service_starter.start_auth, 2.0, False, False),
        PhaseStep("start_backend", service_starter.start_backend, 2.0, True, False),
        PhaseStep("start_frontend", service_starter.start_frontend, 2.0, True, False)
    ]


def create_verify_phase_steps(health_checker, cache_mgr, reporter) -> List[PhaseStep]:
    """Create standard VERIFY phase steps."""
    return [
        PhaseStep("health_check", health_checker.run_quick_checks, 1.0, True, False),
        PhaseStep("update_cache", cache_mgr.update_success_cache, 0.5, False, False),
        PhaseStep("show_summary", reporter.show_startup_summary, 1.5, False, False)
    ]