"""
Centralized Startup Manager for Robust System Initialization

Handles startup orchestration with dependency resolution, timeout handling,
retry logic, graceful degradation, and circuit breaker patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Platform Stability
- Value Impact: Ensures reliable service startup preventing 100% downtime
- Revenue Impact: Protects entire revenue stream from initialization failures
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Status of startup components"""
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


class ComponentPriority(Enum):
    """Priority levels for startup components"""
    CRITICAL = 1  # Must succeed for system to start
    HIGH = 2      # Should succeed, but system can run in degraded mode
    MEDIUM = 3    # Nice to have, system functions without it
    LOW = 4       # Optional enhancement


@dataclass
class StartupComponent:
    """Represents a component that needs initialization during startup"""
    name: str
    init_func: Callable
    cleanup_func: Optional[Callable] = None
    priority: ComponentPriority = ComponentPriority.HIGH
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_base: float = 1.0
    retry_delay_max: float = 30.0
    status: ComponentStatus = ComponentStatus.NOT_STARTED
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_count: int = 0


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for component initialization"""
    failure_count: int = 0
    failure_threshold: int = 3
    last_failure_time: Optional[float] = None
    recovery_timeout: float = 30.0
    is_open: bool = False


class StartupManager:
    """
    Manages system startup with dependency resolution, retries, and graceful degradation
    """
    
    def __init__(
        self,
        global_timeout: float = 300.0,  # 5 minutes default
        enable_circuit_breaker: bool = True,
        enable_metrics: bool = True
    ):
        self.components: Dict[str, StartupComponent] = {}
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.global_timeout = global_timeout
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_metrics = enable_metrics
        self.startup_metrics: Dict[str, Any] = defaultdict(dict)
        self.is_initialized = False
        self._shutdown_event = asyncio.Event()
        self._startup_task: Optional[asyncio.Task] = None
        
    def register_component(
        self,
        name: str,
        init_func: Callable,
        cleanup_func: Optional[Callable] = None,
        priority: ComponentPriority = ComponentPriority.HIGH,
        dependencies: Optional[List[str]] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3
    ) -> None:
        """Register a component for startup initialization"""
        component = StartupComponent(
            name=name,
            init_func=init_func,
            cleanup_func=cleanup_func,
            priority=priority,
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )
        self.components[name] = component
        self.circuit_breakers[name] = CircuitBreakerState()
        logger.info(f"Registered startup component: {name} (priority={priority.name})")
    
    def _check_circuit_breaker(self, name: str) -> bool:
        """Check if circuit breaker allows initialization attempt"""
        if not self.enable_circuit_breaker:
            return True
            
        cb = self.circuit_breakers.get(name)
        if not cb:
            return True
            
        if cb.is_open:
            if cb.last_failure_time:
                elapsed = time.time() - cb.last_failure_time
                if elapsed >= cb.recovery_timeout:
                    logger.info(f"Circuit breaker for {name} recovering after {elapsed:.1f}s")
                    cb.is_open = False
                    cb.failure_count = 0
                else:
                    logger.warning(f"Circuit breaker for {name} is open, skipping")
                    return False
        
        return True
    
    def _trip_circuit_breaker(self, name: str) -> None:
        """Trip the circuit breaker after failure threshold"""
        if not self.enable_circuit_breaker:
            return
            
        cb = self.circuit_breakers.get(name)
        if not cb:
            return
            
        cb.failure_count += 1
        cb.last_failure_time = time.time()
        
        if cb.failure_count >= cb.failure_threshold:
            cb.is_open = True
            logger.error(f"Circuit breaker tripped for {name} after {cb.failure_count} failures")
    
    def _get_initialization_order(self) -> List[str]:
        """
        Resolve dependencies and return initialization order using topological sort
        """
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for name, component in self.components.items():
            for dep in component.dependencies:
                if dep not in self.components:
                    logger.warning(f"Component {name} depends on unknown component {dep}")
                    continue
                graph[dep].append(name)
                in_degree[name] += 1
        
        # Topological sort with priority consideration
        queue = []
        for name in self.components:
            if in_degree[name] == 0:
                priority = self.components[name].priority.value
                queue.append((priority, name))
        
        queue.sort()  # Sort by priority
        result = []
        
        while queue:
            _, name = queue.pop(0)
            result.append(name)
            
            for neighbor in graph[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    priority = self.components[neighbor].priority.value
                    queue.append((priority, neighbor))
                    queue.sort()
        
        # Check for cycles
        if len(result) != len(self.components):
            unresolved = set(self.components.keys()) - set(result)
            logger.error(f"Circular dependency detected among: {unresolved}")
            # Add remaining components anyway (they might work)
            for name in unresolved:
                result.append(name)
        
        return result
    
    async def _initialize_component(self, name: str) -> bool:
        """
        Initialize a single component with retry logic
        """
        component = self.components[name]
        
        # Check circuit breaker
        if not self._check_circuit_breaker(name):
            component.status = ComponentStatus.FAILED
            return False
        
        component.status = ComponentStatus.STARTING
        component.start_time = time.time()
        
        for attempt in range(component.max_retries):
            component.retry_count = attempt
            
            try:
                logger.info(f"Initializing {name} (attempt {attempt + 1}/{component.max_retries})")
                
                # Execute initialization with timeout
                await asyncio.wait_for(
                    component.init_func(),
                    timeout=component.timeout_seconds
                )
                
                component.status = ComponentStatus.RUNNING
                component.end_time = time.time()
                component.error = None
                
                duration = component.end_time - component.start_time
                logger.info(f"Successfully initialized {name} in {duration:.2f}s")
                
                if self.enable_metrics:
                    self.startup_metrics[name]["duration"] = duration
                    self.startup_metrics[name]["retries"] = attempt
                
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout initializing {name} after {component.timeout_seconds}s")
                component.error = TimeoutError(f"Initialization timeout: {component.timeout_seconds}s")
                
            except Exception as e:
                logger.error(f"Error initializing {name}: {e}")
                component.error = e
            
            # Retry with exponential backoff
            if attempt < component.max_retries - 1:
                delay = min(
                    component.retry_delay_base * (2 ** attempt),
                    component.retry_delay_max
                )
                logger.info(f"Retrying {name} in {delay:.1f}s")
                await asyncio.sleep(delay)
        
        # All retries failed
        component.status = ComponentStatus.FAILED
        component.end_time = time.time()
        self._trip_circuit_breaker(name)
        
        if self.enable_metrics:
            duration = component.end_time - component.start_time
            self.startup_metrics[name]["duration"] = duration
            self.startup_metrics[name]["retries"] = component.max_retries
            self.startup_metrics[name]["failed"] = True
        
        return False
    
    async def startup(self) -> bool:
        """
        Execute startup sequence with dependency resolution
        """
        logger.info("Starting system initialization")
        start_time = time.time()
        
        try:
            # Get initialization order
            init_order = self._get_initialization_order()
            logger.info(f"Initialization order: {init_order}")
            
            # Group by priority for potential parallel initialization
            priority_groups: Dict[ComponentPriority, List[str]] = defaultdict(list)
            for name in init_order:
                priority_groups[self.components[name].priority].append(name)
            
            # Initialize components by priority
            failed_critical = False
            
            for priority in sorted(ComponentPriority, key=lambda p: p.value):
                if priority not in priority_groups:
                    continue
                    
                components = priority_groups[priority]
                logger.info(f"Initializing {priority.name} priority components: {components}")
                
                # Initialize components in this priority group
                # Critical components are sequential, others can be parallel
                if priority == ComponentPriority.CRITICAL:
                    for name in components:
                        success = await self._initialize_component(name)
                        if not success:
                            failed_critical = True
                            logger.error(f"Critical component {name} failed to initialize")
                            break
                else:
                    # Non-critical can be initialized in parallel
                    tasks = [self._initialize_component(name) for name in components]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for name, result in zip(components, results):
                        if isinstance(result, Exception):
                            logger.error(f"Component {name} initialization failed: {result}")
                        elif not result:
                            logger.warning(f"Component {name} failed but is non-critical")
            
            # Check if we can proceed
            if failed_critical:
                logger.error("Critical component failed, cannot start system")
                return False
            
            # Calculate success metrics
            total_components = len(self.components)
            successful = sum(1 for c in self.components.values() 
                           if c.status == ComponentStatus.RUNNING)
            degraded = sum(1 for c in self.components.values() 
                          if c.status == ComponentStatus.DEGRADED)
            failed = sum(1 for c in self.components.values() 
                        if c.status == ComponentStatus.FAILED)
            
            elapsed = time.time() - start_time
            
            logger.info(f"Startup completed in {elapsed:.2f}s: "
                       f"{successful}/{total_components} successful, "
                       f"{degraded} degraded, {failed} failed")
            
            if self.enable_metrics:
                self.startup_metrics["global"]["total_duration"] = elapsed
                self.startup_metrics["global"]["successful_components"] = successful
                self.startup_metrics["global"]["degraded_components"] = degraded
                self.startup_metrics["global"]["failed_components"] = failed
            
            self.is_initialized = True
            return successful > 0
            
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return False
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown all components in reverse order
        """
        logger.info("Starting system shutdown")
        self._shutdown_event.set()
        
        # Get shutdown order (reverse of initialization)
        shutdown_order = list(reversed(self._get_initialization_order()))
        
        for name in shutdown_order:
            component = self.components[name]
            
            if component.status not in [ComponentStatus.RUNNING, ComponentStatus.DEGRADED]:
                continue
                
            if component.cleanup_func:
                try:
                    logger.info(f"Shutting down {name}")
                    await asyncio.wait_for(
                        component.cleanup_func(),
                        timeout=10.0  # Shorter timeout for shutdown
                    )
                    component.status = ComponentStatus.STOPPED
                except Exception as e:
                    logger.error(f"Error shutting down {name}: {e}")
        
        logger.info("System shutdown complete")
        self.is_initialized = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all components"""
        status = {
            "initialized": self.is_initialized,
            "components": {}
        }
        
        for name, component in self.components.items():
            status["components"][name] = {
                "status": component.status.value,
                "priority": component.priority.name,
                "retry_count": component.retry_count,
                "error": str(component.error) if component.error else None
            }
            
            if component.start_time and component.end_time:
                status["components"][name]["duration"] = component.end_time - component.start_time
        
        if self.enable_metrics:
            status["metrics"] = dict(self.startup_metrics)
        
        return status
    
    async def health_check(self) -> Tuple[bool, Dict[str, Any]]:
        """Check health of all components"""
        healthy = True
        details = {}
        
        for name, component in self.components.items():
            if component.priority == ComponentPriority.CRITICAL:
                if component.status != ComponentStatus.RUNNING:
                    healthy = False
                    
            details[name] = {
                "healthy": component.status == ComponentStatus.RUNNING,
                "status": component.status.value,
                "priority": component.priority.name
            }
        
        return healthy, details


# Global instance
startup_manager = StartupManager()


async def initialize_system() -> bool:
    """Main entry point for system initialization"""
    return await startup_manager.startup()


async def shutdown_system() -> None:
    """Main entry point for system shutdown"""
    await startup_manager.shutdown()