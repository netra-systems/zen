"""
Staged Health Monitor for progressive service health checking.

Addresses GAP-007: Implements 4-stage health monitoring with adaptive rules
to prevent false positives during service initialization.
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class HealthStage(str, Enum):
    """Health monitoring stages based on service lifecycle."""
    INITIALIZATION = "initialization"
    STARTUP = "startup"
    WARMING = "warming"
    OPERATIONAL = "operational"


class ServiceConfig(BaseModel):
    """Configuration for a monitored service."""
    name: str
    process_check: Optional[Callable[[], bool]] = None
    basic_health_check: Optional[Callable[[], bool]] = None
    ready_check: Optional[Callable[[], bool]] = None
    full_health_check: Optional[Callable[[], bool]] = None


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""
    timestamp: datetime = Field(default_factory=datetime.now)
    stage: HealthStage
    success: bool
    error_message: Optional[str] = None
    check_duration_ms: int = 0


@dataclass
class StageConfig:
    """Configuration for a specific health stage."""
    duration_seconds: int
    check_interval: int
    max_failures: Optional[int]
    check_function_name: str


@dataclass
class ServiceState:
    """Current state of a monitored service."""
    start_time: datetime
    current_stage: HealthStage = HealthStage.INITIALIZATION
    failure_count: int = 0
    last_check: Optional[datetime] = None
    check_history: List[HealthCheckResult] = field(default_factory=list)
    grace_multiplier: float = 1.0


class StagedHealthMonitor:
    """Progressive health monitoring with stage-based checks."""

    def __init__(self):
        """Initialize the staged health monitor."""
        self._services: Dict[str, ServiceConfig] = {}
        self._states: Dict[str, ServiceState] = {}
        self._stage_configs = self._init_stage_configs()
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    def _init_stage_configs(self) -> Dict[HealthStage, StageConfig]:
        """Initialize stage configurations."""
        return {
            HealthStage.INITIALIZATION: StageConfig(30, 2, None, "process_check"),
            HealthStage.STARTUP: StageConfig(60, 5, 10, "basic_health_check"),
            HealthStage.WARMING: StageConfig(90, 10, 5, "ready_check"),
            HealthStage.OPERATIONAL: StageConfig(-1, 30, 3, "full_health_check"),
        }

    def register_service(self, config: ServiceConfig) -> None:
        """Register a service for staged monitoring."""
        self._services[config.name] = config
        self._states[config.name] = ServiceState(start_time=datetime.now())
        logger.info(f"Registered staged monitoring for {config.name}")

    def unregister_service(self, name: str) -> None:
        """Unregister a service from monitoring."""
        if name in self._monitoring_tasks:
            self._monitoring_tasks[name].cancel()
            del self._monitoring_tasks[name]
        self._services.pop(name, None)
        self._states.pop(name, None)

    async def start_monitoring(self, service_name: str) -> None:
        """Start monitoring a specific service."""
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        self._running = True
        task = asyncio.create_task(self._monitor_service(service_name))
        self._monitoring_tasks[service_name] = task

    async def _monitor_service(self, service_name: str) -> None:
        """Monitor a single service through all stages."""
        while self._running:
            try:
                await self._check_service_health(service_name)
                await self._update_service_stage(service_name)
                await self._apply_adaptive_rules(service_name)
                interval = self._get_check_interval(service_name)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error monitoring {service_name}: {e}")
                await asyncio.sleep(5)

    async def _check_service_health(self, service_name: str) -> None:
        """Perform health check for current stage."""
        service = self._services[service_name]
        state = self._states[service_name]
        stage_config = self._stage_configs[state.current_stage]
        
        check_func = getattr(service, stage_config.check_function_name)
        if not check_func:
            return
        
        start_time = time.time()
        try:
            success = check_func()
            duration_ms = int((time.time() - start_time) * 1000)
            result = HealthCheckResult(
                stage=state.current_stage,
                success=success,
                check_duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = HealthCheckResult(
                stage=state.current_stage,
                success=False,
                error_message=str(e),
                check_duration_ms=duration_ms
            )
        
        await self._process_check_result(service_name, result)

    async def _process_check_result(self, service_name: str, result: HealthCheckResult) -> None:
        """Process health check result and update state."""
        state = self._states[service_name]
        state.check_history.append(result)
        state.last_check = result.timestamp
        
        if result.success:
            state.failure_count = 0
        else:
            state.failure_count += 1
            await self._handle_failure(service_name, result)

    async def _handle_failure(self, service_name: str, result: HealthCheckResult) -> None:
        """Handle health check failure."""
        state = self._states[service_name]
        stage_config = self._stage_configs[state.current_stage]
        
        logger.warning(
            f"Health check failed for {service_name} in {state.current_stage} "
            f"(failure {state.failure_count})"
        )
        
        if stage_config.max_failures and state.failure_count >= stage_config.max_failures:
            logger.error(f"Service {service_name} exceeded failure threshold")

    async def _update_service_stage(self, service_name: str) -> None:
        """Update service stage based on elapsed time."""
        state = self._states[service_name]
        elapsed = (datetime.now() - state.start_time).total_seconds()
        elapsed_adjusted = elapsed / state.grace_multiplier
        
        new_stage = self._calculate_stage(elapsed_adjusted)
        if new_stage != state.current_stage:
            state.current_stage = new_stage
            state.failure_count = 0
            logger.info(f"Service {service_name} advanced to {new_stage}")

    def _calculate_stage(self, elapsed_seconds: float) -> HealthStage:
        """Calculate appropriate stage based on elapsed time."""
        if elapsed_seconds < 30:
            return HealthStage.INITIALIZATION
        elif elapsed_seconds < 90:
            return HealthStage.STARTUP
        elif elapsed_seconds < 180:
            return HealthStage.WARMING
        else:
            return HealthStage.OPERATIONAL

    async def _apply_adaptive_rules(self, service_name: str) -> None:
        """Apply adaptive monitoring rules."""
        state = self._states[service_name]
        elapsed = (datetime.now() - state.start_time).total_seconds()
        
        # Slow startup rule
        if elapsed > 60 and state.current_stage == HealthStage.INITIALIZATION:
            state.grace_multiplier = 1.5
        
        # Frequent failures rule
        recent_failures = self._count_recent_failures(service_name, minutes=5)
        if recent_failures >= 3:
            # Increase check interval handled in _get_check_interval
            pass

    def _count_recent_failures(self, service_name: str, minutes: int) -> int:
        """Count failures in recent time window."""
        state = self._states[service_name]
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return sum(1 for check in state.check_history 
                  if check.timestamp > cutoff and not check.success)

    def _get_check_interval(self, service_name: str) -> int:
        """Get check interval with adaptive adjustments."""
        state = self._states[service_name]
        base_interval = self._stage_configs[state.current_stage].check_interval
        
        # Adjust for frequent failures
        recent_failures = self._count_recent_failures(service_name, 5)
        if recent_failures >= 3:
            return base_interval * 2
        
        # Adjust for stable operation
        recent_failures_30min = self._count_recent_failures(service_name, 30)
        if recent_failures_30min == 0 and state.current_stage == HealthStage.OPERATIONAL:
            return base_interval * 2
        
        return base_interval

    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get current status of a service."""
        if service_name not in self._states:
            return None
        
        state = self._states[service_name]
        return {
            "stage": state.current_stage,
            "failure_count": state.failure_count,
            "last_check": state.last_check,
            "uptime_seconds": (datetime.now() - state.start_time).total_seconds(),
            "grace_multiplier": state.grace_multiplier,
            "recent_checks": len(state.check_history[-10:])
        }

    async def stop_monitoring(self) -> None:
        """Stop all monitoring tasks."""
        self._running = False
        for task in self._monitoring_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)
        
        self._monitoring_tasks.clear()


def create_process_health_check(process) -> Callable[[], bool]:
    """Create health check for process existence."""
    def check() -> bool:
        return process.poll() is None
    return check


def create_url_health_check(url: str, timeout: int = 5) -> Callable[[], bool]:
    """Create health check for URL endpoint."""
    import requests
    
    def check() -> bool:
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False
    
    return check