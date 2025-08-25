"""
Mock implementations for StagedHealthMonitor and related classes.

These are placeholder implementations that provide the expected interface
for testing purposes. The actual StagedHealthMonitor implementation should
be created in dev_launcher/staged_health_monitor.py per SPEC/startup_coverage.xml.

IMPORTANT: This is a temporary mock to allow tests to run. The actual
implementation needs to be created separately.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, Mock


class HealthStage(Enum):
    """Health check stages during service lifecycle."""
    INITIALIZATION = "initialization"
    STARTUP = "startup"
    WARMING = "warming"
    OPERATIONAL = "operational"


class ServiceState(Enum):
    """Service state during startup and monitoring."""
    STARTING = "starting"
    GRACE_PERIOD = "grace_period"
    READY = "ready"
    MONITORING = "monitoring"
    FAILED = "failed"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    is_healthy: bool
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    stage: Optional[HealthStage] = None
    
    
@dataclass
class StageConfig:
    """Configuration for a specific health check stage."""
    name: str
    check_interval: float
    failure_threshold: int
    timeout: float


@dataclass
class ServiceConfig:
    """Configuration for a service being monitored."""
    name: str
    process_check: Optional[Callable[[], bool]] = None
    basic_health_check: Optional[Callable[[], bool]] = None
    ready_check: Optional[Callable[[], bool]] = None
    full_health_check: Optional[Callable[[], bool]] = None


@dataclass
class ServiceStateObject:
    """State object for a service being monitored."""
    name: str
    state: ServiceState = ServiceState.STARTING
    start_time: Optional[datetime] = None
    current_stage: HealthStage = HealthStage.INITIALIZATION
    failure_count: int = 0
    last_check: Optional[datetime] = None
    check_history: List[HealthCheckResult] = field(default_factory=list)
    grace_multiplier: float = 1.0
    
    def __post_init__(self):
        """Initialize default start_time if not provided."""
        if self.start_time is None:
            self.start_time = datetime.now()


class StagedHealthMonitor:
    """
    Mock implementation of StagedHealthMonitor for testing.
    
    This provides the expected interface but with minimal functionality
    to support unit testing of the test logic itself.
    """
    
    def __init__(self) -> None:
        """Initialize the mock health monitor."""
        self._services: Dict[str, ServiceConfig] = {}
        self._states: Dict[str, ServiceStateObject] = {}
        self._monitoring_tasks: Dict[str, Any] = {}
        self._running: bool = False
        
        # Mock stage configurations
        self._stage_configs = {
            HealthStage.INITIALIZATION: StageConfig("initialization", 2.0, 999, 30.0),
            HealthStage.STARTUP: StageConfig("startup", 5.0, 10, 60.0),
            HealthStage.WARMING: StageConfig("warming", 10.0, 5, 90.0),
            HealthStage.OPERATIONAL: StageConfig("operational", 30.0, 3, 120.0),
        }
    
    def register_service(self, service_config: ServiceConfig) -> None:
        """Register a service for monitoring."""
        self._services[service_config.name] = service_config
        self._states[service_config.name] = ServiceStateObject(name=service_config.name)
    
    def unregister_service(self, service_name: str) -> None:
        """Unregister a service from monitoring."""
        # Cancel monitoring task if exists
        if service_name in self._monitoring_tasks:
            task = self._monitoring_tasks[service_name]
            if hasattr(task, 'cancel'):
                task.cancel()
            del self._monitoring_tasks[service_name]
        
        # Remove from tracking
        self._services.pop(service_name, None)
        self._states.pop(service_name, None)
    
    async def start_monitoring(self, service_name: str) -> None:
        """Start monitoring a service."""
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        self._running = True
        # Create a mock task
        mock_task = Mock()
        self._monitoring_tasks[service_name] = mock_task
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring tasks."""
        self._running = False
    
    async def apply_adaptive_rules(self, service_name: str) -> None:
        """Apply adaptive rules to a service (mock implementation)."""
        if service_name not in self._states:
            return
        
        state = self._states[service_name]
        
        # Always set to test if method is being called
        state.grace_multiplier = 99.9  # Test value
        
        # Mock adaptive rule: if service has been initializing for > 60 seconds, increase grace_multiplier  
        if (state.current_stage == HealthStage.INITIALIZATION and 
            state.start_time and 
            (datetime.now() - state.start_time).total_seconds() > 60):
            state.grace_multiplier = 1.5
    
    async def check_service_health(self, service_name: str, stage: HealthStage) -> HealthCheckResult:
        """Check the health of a service at a specific stage."""
        if service_name not in self._services:
            return HealthCheckResult(
                is_healthy=False,
                message=f"Service {service_name} not registered",
                stage=stage
            )
        
        service_config = self._services[service_name]
        
        # Mock health check based on stage
        if stage == HealthStage.INITIALIZATION and service_config.process_check:
            is_healthy = service_config.process_check()
        elif stage == HealthStage.STARTUP and service_config.basic_health_check:
            is_healthy = service_config.basic_health_check()
        elif stage == HealthStage.WARMING and service_config.ready_check:
            is_healthy = service_config.ready_check()
        elif stage == HealthStage.OPERATIONAL and service_config.full_health_check:
            is_healthy = service_config.full_health_check()
        else:
            is_healthy = True  # Default to healthy if no check defined
        
        return HealthCheckResult(
            is_healthy=is_healthy,
            message="Health check completed" if is_healthy else "Health check failed",
            stage=stage
        )
    
    async def process_check_result(self, service_name: str, result: HealthCheckResult) -> None:
        """Process the result of a health check."""
        # Mock processing - just update state based on result
        if result.is_healthy:
            # Reset failure count on success (mock behavior)
            pass
        else:
            # Handle failure (mock behavior)
            await self.handle_failure(service_name, result)
    
    async def handle_failure(self, service_name: str, result: HealthCheckResult) -> None:
        """Handle a health check failure."""
        # Mock failure handling - could update state to FAILED
        if service_name in self._states:
            # Mock: after too many failures, mark as failed
            self._states[service_name] = ServiceState.FAILED
    
    async def update_service_stage(self, service_name: str, new_stage: HealthStage) -> None:
        """Update the monitoring stage for a service."""
        # Mock stage update
        pass
    
    def calculate_stage(self, service_name: str) -> HealthStage:
        """Calculate the current health check stage for a service."""
        # Mock stage calculation based on service state
        state = self._states.get(service_name, ServiceState.STARTING)
        
        if state == ServiceState.STARTING:
            return HealthStage.INITIALIZATION
        elif state == ServiceState.GRACE_PERIOD:
            return HealthStage.STARTUP
        elif state == ServiceState.READY:
            return HealthStage.WARMING
        else:
            return HealthStage.OPERATIONAL
    
    async def apply_adaptive_rules(self, service_name: str) -> None:
        """Apply adaptive monitoring rules."""
        # Mock adaptive rules
        pass
    
    def count_recent_failures(self, service_name: str, window_minutes: int = 5) -> int:
        """Count recent failures for a service."""
        # Mock failure counting
        return 0
    
    def get_check_interval(self, service_name: str) -> float:
        """Get the current check interval for a service."""
        stage = self.calculate_stage(service_name)
        return self._stage_configs[stage].check_interval
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a service."""
        if service_name not in self._services:
            return None
        
        return {
            "name": service_name,
            "state": self._states.get(service_name, ServiceState.STARTING).value,
            "stage": self.calculate_stage(service_name).value,
            "monitoring": service_name in self._monitoring_tasks
        }


def create_process_health_check(process_name: str) -> Callable[[], bool]:
    """Create a process-based health check function."""
    def check() -> bool:
        # Mock process check - always return True for testing
        return True
    return check


def create_url_health_check(url: str, timeout: float = 5.0) -> Callable[[], bool]:
    """Create a URL-based health check function."""
    def check() -> bool:
        # Mock URL check - always return True for testing
        return True
    return check