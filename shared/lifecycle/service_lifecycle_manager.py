"""
Service Lifecycle Manager - LEVEL 3-5 FIXES

This module implements comprehensive service lifecycle management to prevent 
race conditions and ensure proper initialization ordering. Addresses root causes
identified in the Five Whys analysis.

CRITICAL: This is the architectural solution for service initialization race conditions.

Implemented Levels:
- Level 3: Initialization sequence management with proper phases
- Level 4: Service dependency management with readiness contracts  
- Level 5: Full ServiceLifecycleManager architecture pattern

Business Value: Platform/Internal - System Stability & Startup Reliability
Prevents cascade failures during service initialization by ensuring proper ordering.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any, TypeVar, Generic
from collections import defaultdict

from shared.logging.unified_logger_factory import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ServiceState(Enum):
    """Service lifecycle states."""
    UNINITIALIZED = "uninitialized"
    CONFIGURING = "configuring" 
    VALIDATING = "validating"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class InitializationPhase(Enum):
    """System-wide initialization phases."""
    BOOTSTRAP = "bootstrap"           # Environment, logging, config validation
    DEPENDENCIES = "dependencies"     # Core dependencies, secrets, auth
    DATABASE = "database"            # Database connections and schema  
    CACHE = "cache"                  # Redis and caching systems
    SERVICES = "services"            # Business logic services
    INTEGRATION = "integration"      # WebSocket, messaging, APIs
    VALIDATION = "validation"        # Health checks and final validation
    READY = "ready"                  # System fully operational


@dataclass
class ServiceDependency:
    """Defines a dependency relationship between services."""
    service_name: str
    required_state: ServiceState
    timeout_seconds: float = 30.0
    is_critical: bool = True
    description: str = ""


@dataclass 
class ReadinessContract:
    """Defines what constitutes "ready" for a service."""
    service_name: str
    required_checks: List[str] = field(default_factory=list)
    health_check_url: Optional[str] = None
    custom_validator: Optional[Callable[[], bool]] = None
    timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class ServiceRegistration:
    """Service registration with lifecycle management."""
    name: str
    phase: InitializationPhase
    dependencies: List[ServiceDependency] = field(default_factory=list)
    readiness_contract: Optional[ReadinessContract] = None
    initializer: Optional[Callable] = None
    health_checker: Optional[Callable] = None
    cleanup_handler: Optional[Callable] = None
    timeout_seconds: float = 60.0
    is_critical: bool = True
    
    # State tracking
    current_state: ServiceState = ServiceState.UNINITIALIZED
    last_state_change: Optional[datetime] = None
    initialization_attempts: int = 0
    last_error: Optional[str] = None


class ServiceLifecycleManager:
    """
    LEVEL 3-5 FIX: Comprehensive service lifecycle management.
    
    This manager ensures:
    1. Proper initialization sequence ordering (LEVEL 3)
    2. Service dependency resolution and validation (LEVEL 4)  
    3. Complete service lifecycle architecture (LEVEL 5)
    
    ROOT CAUSE ADDRESSED: Absence of explicit service lifecycle management
    that was causing initialization race conditions.
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceRegistration] = {}
        self._phase_order: List[InitializationPhase] = list(InitializationPhase)
        self._current_phase = InitializationPhase.BOOTSTRAP
        self._state_lock = threading.RLock()
        self._initialization_complete = False
        self._failed_services: Set[str] = set()
        self._initialization_start_time: Optional[datetime] = None
        
        # Event callbacks
        self._state_change_callbacks: List[Callable[[str, ServiceState, ServiceState], None]] = []
        self._phase_change_callbacks: List[Callable[[InitializationPhase, InitializationPhase], None]] = []
        
        # Health monitoring
        self._health_check_interval = 30.0  # seconds
        self._health_monitor_task: Optional[asyncio.Task] = None
        
        logger.info("ServiceLifecycleManager initialized")
    
    def register_service(self, registration: ServiceRegistration) -> None:
        """Register a service with the lifecycle manager."""
        with self._state_lock:
            if registration.name in self._services:
                raise ValueError(f"Service {registration.name} already registered")
            
            registration.last_state_change = datetime.now()
            self._services[registration.name] = registration
            
            logger.info(f"Registered service '{registration.name}' for phase {registration.phase.value}")
    
    def add_dependency(self, service_name: str, dependency: ServiceDependency) -> None:
        """Add a dependency to a registered service."""
        with self._state_lock:
            if service_name not in self._services:
                raise ValueError(f"Service {service_name} not registered")
            
            self._services[service_name].dependencies.append(dependency)
            logger.debug(f"Added dependency {dependency.service_name} -> {service_name}")
    
    def set_readiness_contract(self, service_name: str, contract: ReadinessContract) -> None:
        """Set readiness contract for a service."""
        with self._state_lock:
            if service_name not in self._services:
                raise ValueError(f"Service {service_name} not registered")
            
            self._services[service_name].readiness_contract = contract
            logger.debug(f"Set readiness contract for {service_name}")
    
    async def initialize_all_services(self) -> bool:
        """
        LEVEL 3 FIX: Initialize all services in proper phase order.
        
        Returns:
            bool: True if all critical services initialized successfully
        """
        with self._state_lock:
            if self._initialization_complete:
                logger.warning("Services already initialized")
                return True
            
            self._initialization_start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("SERVICE LIFECYCLE INITIALIZATION STARTING")
        logger.info(f"Total services registered: {len(self._services)}")
        logger.info("=" * 60)
        
        try:
            # Initialize services phase by phase
            for phase in self._phase_order:
                if not await self._initialize_phase(phase):
                    logger.error(f"Phase {phase.value} initialization failed")
                    return False
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            with self._state_lock:
                self._initialization_complete = True
            
            total_time = datetime.now() - self._initialization_start_time
            logger.info("=" * 60) 
            logger.info(f"SERVICE LIFECYCLE INITIALIZATION COMPLETE ({total_time.total_seconds():.2f}s)")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            return False
    
    async def _initialize_phase(self, phase: InitializationPhase) -> bool:
        """Initialize all services in a specific phase."""
        services_in_phase = [s for s in self._services.values() if s.phase == phase]
        
        if not services_in_phase:
            logger.debug(f"Phase {phase.value}: No services to initialize")
            return True
        
        logger.info(f"Phase {phase.value}: Initializing {len(services_in_phase)} services")
        
        # Notify phase change
        old_phase = self._current_phase
        self._current_phase = phase
        for callback in self._phase_change_callbacks:
            try:
                callback(old_phase, phase)
            except Exception as e:
                logger.warning(f"Phase change callback failed: {e}")
        
        # Sort by dependencies (dependency resolution)
        sorted_services = self._resolve_dependencies_in_phase(services_in_phase)
        
        for service in sorted_services:
            if not await self._initialize_single_service(service):
                if service.is_critical:
                    logger.error(f"Critical service {service.name} failed in phase {phase.value}")
                    return False
                else:
                    logger.warning(f"Optional service {service.name} failed in phase {phase.value}")
        
        logger.info(f"Phase {phase.value}: Complete")
        return True
    
    def _resolve_dependencies_in_phase(self, services: List[ServiceRegistration]) -> List[ServiceRegistration]:
        """
        LEVEL 4 FIX: Resolve service dependencies within a phase.
        
        Uses topological sort to ensure proper initialization order.
        """
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        service_map = {s.name: s for s in services}
        
        # Initialize in_degree for all services
        for service in services:
            in_degree[service.name] = 0
        
        # Build graph edges
        for service in services:
            for dep in service.dependencies:
                if dep.service_name in service_map:
                    # Only consider dependencies within this phase
                    graph[dep.service_name].append(service.name)
                    in_degree[service.name] += 1
        
        # Topological sort
        queue = [s for s in services if in_degree[s.name] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current.name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    # Find the service object
                    neighbor_service = next(s for s in services if s.name == neighbor)
                    queue.append(neighbor_service)
        
        # Check for circular dependencies
        if len(result) != len(services):
            remaining = [s for s in services if s not in result]
            logger.warning(f"Circular dependency detected in services: {[s.name for s in remaining]}")
            # Add remaining services (best effort)
            result.extend(remaining)
        
        return result
    
    async def _initialize_single_service(self, service: ServiceRegistration) -> bool:
        """
        Initialize a single service with full lifecycle management.
        
        LEVEL 4 FIX: Includes dependency checking and readiness contracts.
        """
        logger.info(f"  Initializing service: {service.name}")
        
        try:
            # Update state
            await self._update_service_state(service, ServiceState.CONFIGURING)
            
            # Check dependencies first (LEVEL 4 FIX)
            if not await self._check_service_dependencies(service):
                await self._update_service_state(service, ServiceState.FAILED)
                return False
            
            # Run initializer if provided
            await self._update_service_state(service, ServiceState.STARTING)
            
            if service.initializer:
                if asyncio.iscoroutinefunction(service.initializer):
                    await asyncio.wait_for(service.initializer(), timeout=service.timeout_seconds)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, service.initializer
                    )
            
            # Validate readiness contract (LEVEL 4 FIX)
            if not await self._validate_readiness_contract(service):
                await self._update_service_state(service, ServiceState.FAILED) 
                return False
            
            # Success
            await self._update_service_state(service, ServiceState.READY)
            logger.info(f"  ✅ Service {service.name} initialized successfully")
            return True
            
        except asyncio.TimeoutError:
            service.last_error = f"Initialization timeout after {service.timeout_seconds}s"
            await self._update_service_state(service, ServiceState.FAILED)
            logger.error(f"  ❌ Service {service.name} initialization timeout")
            return False
            
        except Exception as e:
            service.last_error = str(e)
            await self._update_service_state(service, ServiceState.FAILED)
            logger.error(f"  ❌ Service {service.name} initialization failed: {e}")
            return False
    
    async def _check_service_dependencies(self, service: ServiceRegistration) -> bool:
        """
        LEVEL 4 FIX: Check that all service dependencies are satisfied.
        """
        for dep in service.dependencies:
            if dep.service_name not in self._services:
                logger.error(f"Service {service.name} depends on unregistered service {dep.service_name}")
                return False
            
            dep_service = self._services[dep.service_name]
            
            # Check if dependency is in required state
            if dep_service.current_state != dep.required_state:
                if dep.is_critical:
                    logger.error(f"Critical dependency {dep.service_name} not ready for {service.name}")
                    return False
                else:
                    logger.warning(f"Optional dependency {dep.service_name} not ready for {service.name}")
        
        return True
    
    async def _validate_readiness_contract(self, service: ServiceRegistration) -> bool:
        """
        LEVEL 4 FIX: Validate service readiness contract.
        """
        contract = service.readiness_contract
        if not contract:
            return True  # No contract means always ready
        
        for attempt in range(contract.retry_count):
            try:
                # Custom validator takes precedence
                if contract.custom_validator:
                    if await self._run_custom_validator(contract.custom_validator):
                        return True
                
                # Run required checks
                all_passed = True
                for check_name in contract.required_checks:
                    if not await self._run_readiness_check(service, check_name):
                        all_passed = False
                        break
                
                if all_passed:
                    return True
                    
            except Exception as e:
                logger.warning(f"Readiness check attempt {attempt + 1} failed for {service.name}: {e}")
            
            if attempt < contract.retry_count - 1:
                await asyncio.sleep(contract.retry_delay)
        
        logger.error(f"Service {service.name} failed readiness validation after {contract.retry_count} attempts")
        return False
    
    async def _run_custom_validator(self, validator: Callable) -> bool:
        """Run a custom readiness validator."""
        try:
            if asyncio.iscoroutinefunction(validator):
                return await validator()
            else:
                return await asyncio.get_event_loop().run_in_executor(None, validator)
        except Exception as e:
            logger.warning(f"Custom validator failed: {e}")
            return False
    
    async def _run_readiness_check(self, service: ServiceRegistration, check_name: str) -> bool:
        """Run a specific readiness check."""
        # This is a placeholder - in practice, you'd implement specific checks
        # like database connectivity, API responsiveness, etc.
        logger.debug(f"Running readiness check '{check_name}' for {service.name}")
        return True
    
    async def _update_service_state(self, service: ServiceRegistration, new_state: ServiceState) -> None:
        """Update service state and notify callbacks."""
        old_state = service.current_state
        service.current_state = new_state
        service.last_state_change = datetime.now()
        
        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(service.name, old_state, new_state)
            except Exception as e:
                logger.warning(f"State change callback failed: {e}")
    
    async def _start_health_monitoring(self) -> None:
        """Start continuous health monitoring of services."""
        if self._health_monitor_task:
            return
        
        async def health_monitor():
            while True:
                try:
                    await self._run_health_checks()
                    await asyncio.sleep(self._health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(self._health_check_interval)
        
        self._health_monitor_task = asyncio.create_task(health_monitor())
        logger.info("Health monitoring started")
    
    async def _run_health_checks(self) -> None:
        """Run health checks on all services."""
        for service in self._services.values():
            if service.current_state == ServiceState.READY and service.health_checker:
                try:
                    if asyncio.iscoroutinefunction(service.health_checker):
                        healthy = await service.health_checker()
                    else:
                        healthy = await asyncio.get_event_loop().run_in_executor(
                            None, service.health_checker
                        )
                    
                    if not healthy and service.current_state == ServiceState.READY:
                        await self._update_service_state(service, ServiceState.DEGRADED)
                        logger.warning(f"Service {service.name} health check failed - marked as degraded")
                        
                except Exception as e:
                    logger.warning(f"Health check failed for {service.name}: {e}")
                    if service.current_state == ServiceState.READY:
                        await self._update_service_state(service, ServiceState.DEGRADED)
    
    def get_service_state(self, service_name: str) -> Optional[ServiceState]:
        """Get current state of a service."""
        service = self._services.get(service_name)
        return service.current_state if service else None
    
    def get_failed_services(self) -> List[str]:
        """Get list of failed service names."""
        return list(self._failed_services)
    
    def is_initialization_complete(self) -> bool:
        """Check if initialization is complete."""
        return self._initialization_complete
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Get detailed initialization status."""
        with self._state_lock:
            return {
                "complete": self._initialization_complete,
                "current_phase": self._current_phase.value,
                "total_services": len(self._services),
                "ready_services": len([s for s in self._services.values() if s.current_state == ServiceState.READY]),
                "failed_services": len(self._failed_services),
                "start_time": self._initialization_start_time.isoformat() if self._initialization_start_time else None,
                "services": {
                    name: {
                        "state": service.current_state.value,
                        "phase": service.phase.value,
                        "last_error": service.last_error,
                        "attempts": service.initialization_attempts
                    }
                    for name, service in self._services.items()
                }
            }
    
    def add_state_change_callback(self, callback: Callable[[str, ServiceState, ServiceState], None]) -> None:
        """Add callback for service state changes."""
        self._state_change_callbacks.append(callback)
    
    def add_phase_change_callback(self, callback: Callable[[InitializationPhase, InitializationPhase], None]) -> None:
        """Add callback for phase changes."""
        self._phase_change_callbacks.append(callback)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down ServiceLifecycleManager")
        
        # Cancel health monitoring
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown services in reverse order
        shutdown_order = list(reversed(self._phase_order))
        
        for phase in shutdown_order:
            services_in_phase = [s for s in self._services.values() if s.phase == phase]
            
            for service in reversed(services_in_phase):  # Reverse within phase too
                if service.cleanup_handler:
                    try:
                        await self._update_service_state(service, ServiceState.STOPPING)
                        
                        if asyncio.iscoroutinefunction(service.cleanup_handler):
                            await service.cleanup_handler()
                        else:
                            await asyncio.get_event_loop().run_in_executor(
                                None, service.cleanup_handler
                            )
                        
                        await self._update_service_state(service, ServiceState.STOPPED)
                        logger.info(f"Service {service.name} shut down cleanly")
                        
                    except Exception as e:
                        logger.error(f"Error shutting down service {service.name}: {e}")


# Global singleton instance
_lifecycle_manager: Optional[ServiceLifecycleManager] = None
_manager_lock = threading.RLock()


def get_lifecycle_manager() -> ServiceLifecycleManager:
    """Get the global ServiceLifecycleManager singleton."""
    global _lifecycle_manager
    
    if _lifecycle_manager is None:
        with _manager_lock:
            if _lifecycle_manager is None:
                _lifecycle_manager = ServiceLifecycleManager()
    
    return _lifecycle_manager


def register_service(
    name: str,
    phase: InitializationPhase,
    is_critical: bool = True,
    dependencies: Optional[List[ServiceDependency]] = None,
    readiness_contract: Optional[ReadinessContract] = None,
    initializer: Optional[Callable] = None,
    health_checker: Optional[Callable] = None,
    cleanup_handler: Optional[Callable] = None,
    timeout_seconds: float = 60.0
) -> None:
    """Convenience function to register a service."""
    registration = ServiceRegistration(
        name=name,
        phase=phase,
        dependencies=dependencies or [],
        readiness_contract=readiness_contract,
        initializer=initializer,
        health_checker=health_checker, 
        cleanup_handler=cleanup_handler,
        timeout_seconds=timeout_seconds,
        is_critical=is_critical
    )
    
    get_lifecycle_manager().register_service(registration)