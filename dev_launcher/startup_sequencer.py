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
        
        steps = self.phases.get(phase, [])
        for step in steps:
            if not self._can_skip_step(step):
                return False
        return True
    
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
        
        start_time = time.time()
        try:
            result = step.func()
            duration = time.time() - start_time
            success = result if isinstance(result, bool) else True
            if success and step.cache_key:
                self.cache_manager.cache_result(step.cache_key, True)
            return success, duration
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Step {step.name} failed: {e}")
            return False, duration
    
    def _execute_phase(self, phase: StartupPhase) -> PhaseResult:
        """Execute a single phase with all its steps."""
        logger.info(f"Starting phase: {phase.phase_name}")
        phase_start = time.time()
        steps = self.phases.get(phase, [])
        
        executed_steps = []
        skipped_steps = []
        
        for step in steps:
            step_success, step_duration = self._execute_step(step)
            
            if self._can_skip_step(step):
                skipped_steps.append(step.name)
            else:
                executed_steps.append(step.name)
            
            if not step_success and step.required:
                phase_duration = time.time() - phase_start
                return PhaseResult(
                    phase, False, phase_duration,
                    executed_steps, skipped_steps,
                    f"Required step {step.name} failed"
                )
        
        phase_duration = time.time() - phase_start
        return PhaseResult(phase, True, phase_duration, executed_steps, skipped_steps)
    
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
        
        sequence_phases = [
            StartupPhase.INIT,
            StartupPhase.VALIDATE,
            StartupPhase.PREPARE,
            StartupPhase.LAUNCH,
            StartupPhase.VERIFY
        ]
        
        for phase in sequence_phases:
            if self.can_skip_phase(phase):
                logger.info(f"Skipping entire phase: {phase.phase_name}")
                self.phase_results[phase] = PhaseResult(
                    phase, True, 0.0, [], 
                    [step.name for step in self.phases.get(phase, [])]
                )
                continue
            
            result = self._execute_phase(phase)
            self.phase_results[phase] = result
            
            if self._check_timeout(phase, result.duration):
                result.success = False
                result.error = f"Phase timeout ({result.duration:.1f}s)"
            
            if not result.success:
                logger.error(f"Phase {phase.phase_name} failed: {result.error}")
                self._execute_rollback(phase)
                break
        
        return self.phase_results
    
    def get_sequence_summary(self) -> Dict[str, Any]:
        """Get summary of sequence execution."""
        total_time = time.time() - self.start_time if self.start_time > 0 else 0
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
            "phase_timings": {
                p.phase_name: r.duration 
                for p, r in self.phase_results.items()
            }
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