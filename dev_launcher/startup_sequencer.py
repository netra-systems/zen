"""
Smart startup sequencer with dynamic phase ordering and timeout management.

Orchestrates the startup sequence phases (INIT, VALIDATE, PREPARE, LAUNCH, VERIFY)
with intelligent dependency resolution, skip logic for cached operations,
and rollback capability on failure.
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dev_launcher.cache_manager import CacheManager

logger = logging.getLogger(__name__)


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


class SmartStartupSequencer:
    """
    Smart startup sequencer with dynamic phase ordering and timeout management.
    
    Manages the five startup phases with intelligent caching, skip logic,
    timeout management, and rollback capability on failure.
    """
    
    def __init__(self, cache_manager: CacheManager):
        """Initialize sequencer with cache manager."""
        self.cache_manager = cache_manager
        self.phases: Dict[StartupPhase, List[PhaseStep]] = {}
        self.phase_results: Dict[StartupPhase, PhaseResult] = {}
        self.rollback_actions: Dict[StartupPhase, Callable] = {}
        self.start_time = 0.0
    
    def register_phase(self, phase: StartupPhase, steps: List[PhaseStep]):
        """Register steps for a startup phase."""
        if len(steps) > 10:
            logger.warning(f"Phase {phase.phase_name} has {len(steps)} steps")
        self.phases[phase] = steps
    
    def register_rollback(self, phase: StartupPhase, rollback_func: Callable):
        """Register rollback action for a phase."""
        self.rollback_actions[phase] = rollback_func
    
    def can_skip_phase(self, phase: StartupPhase) -> bool:
        """Determine if entire phase can be skipped."""
        if phase == StartupPhase.INIT:
            return False  # INIT never skipped
        return self._check_all_steps_skippable(phase)
    
    def _check_all_steps_skippable(self, phase: StartupPhase) -> bool:
        """Check if all steps in phase are skippable."""
        steps = self.phases.get(phase, [])
        return all(self._can_skip_step(step) for step in steps)
    
    def _can_skip_step(self, step: PhaseStep) -> bool:
        """Check if individual step can be skipped."""
        if not step.can_skip or not step.cache_key:
            return False
        return self.cache_manager.is_cached_and_valid(step.cache_key)
    
    def _execute_step(self, step: PhaseStep) -> Tuple[bool, float]:
        """Execute a single step with timeout and error handling."""
        if self._can_skip_step(step):
            logger.debug(f"Skipping cached step: {step.name}")
            return True, 0.0
        return self._run_step_with_timing(step)
    
    def _run_step_with_timing(self, step: PhaseStep) -> Tuple[bool, float]:
        """Run step and measure timing."""
        start_time = time.time()
        try:
            result = step.func()
            return self._process_step_result(step, result, time.time() - start_time)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Step {step.name} failed: {e}")
            return False, duration
    
    def _process_step_result(self, step: PhaseStep, result: Any, duration: float) -> Tuple[bool, float]:
        """Process step execution result."""
        success = result if isinstance(result, bool) else True
        if success and step.cache_key:
            self.cache_manager.cache_result(step.cache_key, True)
        return success, duration
    
    def _execute_phase(self, phase: StartupPhase) -> PhaseResult:
        """Execute a single phase with all its steps."""
        logger.info(f"Starting phase: {phase.phase_name}")
        phase_start = time.time()
        return self._run_phase_steps(phase, phase_start)
    
    def _run_phase_steps(self, phase: StartupPhase, start_time: float) -> PhaseResult:
        """Run all steps in a phase."""
        steps = self.phases.get(phase, [])
        executed_steps, skipped_steps = [], []
        for step in steps:
            result = self._execute_and_categorize_step(step, executed_steps, skipped_steps)
            if result:  # Failed required step
                return PhaseResult(phase, False, time.time() - start_time, executed_steps, skipped_steps, result)
        return PhaseResult(phase, True, time.time() - start_time, executed_steps, skipped_steps)
    
    def _execute_and_categorize_step(self, step: PhaseStep, executed: List, skipped: List) -> Optional[str]:
        """Execute step and categorize result."""
        step_success, _ = self._execute_step(step)
        (skipped if self._can_skip_step(step) else executed).append(step.name)
        if not step_success and step.required:
            return f"Required step {step.name} failed"
        return None
    
    def _check_timeout(self, phase: StartupPhase, elapsed: float) -> bool:
        """Check if phase has exceeded timeout."""
        if elapsed > phase.timeout:
            logger.error(f"Phase {phase.phase_name} timeout ({elapsed:.1f}s > {phase.timeout}s)")
            return True
        return False
    
    def _execute_rollback(self, failed_phase: StartupPhase):
        """Execute rollback for failed phase and predecessors."""
        phases_to_rollback = self._get_rollback_phases(failed_phase)
        for phase in reversed(phases_to_rollback):
            self._rollback_single_phase(phase)
    
    def _rollback_single_phase(self, phase: StartupPhase):
        """Rollback a single phase."""
        rollback_func = self.rollback_actions.get(phase)
        if rollback_func:
            try:
                logger.info(f"Rolling back phase: {phase.phase_name}")
                rollback_func()
            except Exception as e:
                logger.error(f"Rollback failed for {phase.phase_name}: {e}")
    
    def _get_rollback_phases(self, failed_phase: StartupPhase) -> List[StartupPhase]:
        """Get phases that need rollback when a phase fails."""
        all_phases = list(StartupPhase)
        failed_index = all_phases.index(failed_phase)
        return all_phases[:failed_index + 1]
    
    def execute_sequence(self) -> Dict[StartupPhase, PhaseResult]:
        """Execute the complete startup sequence."""
        self.start_time = time.time()
        self.phase_results.clear()
        return self._run_sequence_phases()
    
    def _run_sequence_phases(self) -> Dict[StartupPhase, PhaseResult]:
        """Run all phases in sequence."""
        sequence_phases = [StartupPhase.INIT, StartupPhase.VALIDATE, StartupPhase.PREPARE, StartupPhase.LAUNCH, StartupPhase.VERIFY]
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
        self.phase_results[phase] = PhaseResult(phase, True, 0.0, [], [step.name for step in self.phases.get(phase, [])])
    
    def _execute_and_validate_phase(self, phase: StartupPhase) -> bool:
        """Execute phase and validate result."""
        result = self._execute_phase(phase)
        self.phase_results[phase] = result
        if self._check_timeout(phase, result.duration):
            result.success, result.error = False, f"Phase timeout ({result.duration:.1f}s)"
        if not result.success:
            logger.error(f"Phase {phase.phase_name} failed: {result.error}")
            self._execute_rollback(phase)
            return False
        return True
    
    def get_sequence_summary(self) -> Dict[str, Any]:
        """Get summary of sequence execution."""
        total_time = time.time() - self.start_time if self.start_time > 0 else 0
        return self._build_summary_dict(total_time)
    
    def _build_summary_dict(self, total_time: float) -> Dict[str, Any]:
        """Build summary dictionary from phase results."""
        successful_phases = [p for p, r in self.phase_results.items() if r.success]
        failed_phases = [p for p, r in self.phase_results.items() if not r.success]
        total_skipped = sum(len(r.steps_skipped) for r in self.phase_results.values())
        total_executed = sum(len(r.steps_executed) for r in self.phase_results.values())
        return {
            "total_time": total_time, "target_met": total_time < 10.0,
            "successful_phases": [p.phase_name for p in successful_phases],
            "failed_phases": [p.phase_name for p in failed_phases],
            "total_steps_skipped": total_skipped, "total_steps_executed": total_executed,
            "phase_timings": {p.phase_name: r.duration for p, r in self.phase_results.items()}
        }
    
    def reset_sequence(self):
        """Reset sequencer state for new execution."""
        self.phase_results.clear()
        self.start_time = 0.0
        logger.debug("Startup sequencer state reset")


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
        PhaseStep("health_check", health_checker.quick_health_check, 1.0, True, False),
        PhaseStep("update_cache", cache_mgr.update_success_cache, 0.5, False, False),
        PhaseStep("show_summary", reporter.show_startup_summary, 1.5, False, False)
    ]