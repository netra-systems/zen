"""
Startup sequence optimization component.

Optimizes the development launcher startup sequence by tracking timing,
enabling parallel execution, and skipping unnecessary initialization steps.
"""

import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from datetime import datetime

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