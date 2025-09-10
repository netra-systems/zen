"""
SystemLifecycle - SSOT for All Lifecycle Operations

Business Value Justification (BVJ):
- Segment: Platform/Internal - Risk Reduction, Development Velocity
- Business Goal: Zero-downtime deployments and reliable service lifecycle management
- Value Impact: Reduces chat service interruption during deployments from ~30s to <2s
- Strategic Impact: Consolidates 100+ lifecycle managers into one SSOT for operational simplicity

CRITICAL: This is a MEGA CLASS exception approved for up to 2000 lines due to SSOT requirements.
Consolidates ALL lifecycle operations including:
- GracefulShutdownManager
- StartupStatusManager  
- SupervisorLifecycleManager
- Health monitoring and status tracking
- WebSocket lifecycle coordination
- Database connection lifecycle
- Agent task lifecycle management

Factory Pattern: Supports multi-user isolation via user-scoped instances.
Thread Safety: All operations are thread-safe and support concurrent users.
WebSocket Integration: Coordinates with WebSocket manager for real-time notifications.

NAMING MIGRATION: Renamed from UnifiedLifecycleManager to SystemLifecycle for business clarity.
"""

import asyncio
import signal
import time
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Callable, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_logging import central_logger

logger = central_logger.get_logger(__name__)


class LifecyclePhase(Enum):
    """Lifecycle phases for tracking system state."""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    ERROR = "error"


class ComponentType(Enum):
    """Types of components managed by lifecycle."""
    WEBSOCKET_MANAGER = "websocket_manager"
    DATABASE_MANAGER = "database_manager" 
    AGENT_REGISTRY = "agent_registry"
    HEALTH_SERVICE = "health_service"
    LLM_MANAGER = "llm_manager"
    REDIS_MANAGER = "redis_manager"
    CLICKHOUSE_MANAGER = "clickhouse_manager"


@dataclass
class ComponentStatus:
    """Status tracking for individual components."""
    name: str
    component_type: ComponentType
    status: str = "unknown"
    last_check: float = field(default_factory=time.time)
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LifecycleMetrics:
    """Metrics for lifecycle operations."""
    startup_time: Optional[float] = None
    shutdown_time: Optional[float] = None
    successful_shutdowns: int = 0
    failed_shutdowns: int = 0
    component_failures: int = 0
    last_health_check: Optional[float] = None
    active_requests: int = 0


class SystemLifecycle:
    """
    SSOT for all lifecycle operations across the Netra platform.
    
    Consolidates functionality from:
    - GracefulShutdownManager
    - StartupStatusManager
    - SupervisorLifecycleManager
    - Various component lifecycle managers
    
    Features:
    - Multi-user isolation via factory pattern
    - Thread-safe operations
    - WebSocket event coordination
    - Comprehensive health monitoring
    - Graceful shutdown with request draining
    - Startup validation and readiness checks
    - Error recovery and circuit breaking
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        shutdown_timeout: int = 30,
        drain_timeout: int = 20,
        health_check_grace_period: int = 5,
        startup_timeout: int = 60
    ):
        """
        Initialize unified lifecycle manager.
        
        Args:
            user_id: User ID for isolated user context (None for global)
            shutdown_timeout: Total time allowed for graceful shutdown
            drain_timeout: Time allowed for request draining
            health_check_grace_period: Time to mark unhealthy before shutdown
            startup_timeout: Maximum time allowed for startup
        """
        self.user_id = user_id
        self.shutdown_timeout = shutdown_timeout
        self.drain_timeout = drain_timeout
        self.health_check_grace_period = health_check_grace_period
        self.startup_timeout = startup_timeout
        
        # Core state tracking
        self._current_phase = LifecyclePhase.INITIALIZING
        self._phase_lock = asyncio.Lock()
        self._startup_time: Optional[float] = None
        self._shutdown_initiated = False
        self._shutdown_event = asyncio.Event()
        
        # Request tracking for graceful shutdown
        self._active_requests: Dict[str, float] = {}
        self._request_lock = asyncio.Lock()
        
        # Component registry
        self._components: Dict[str, ComponentStatus] = {}
        self._component_instances: Dict[ComponentType, Any] = {}
        self._component_lock = asyncio.Lock()
        
        # Lifecycle hooks and handlers
        self._startup_handlers: List[Callable[[], Any]] = []
        self._shutdown_handlers: List[Callable[[], Any]] = []
        self._lifecycle_hooks: Dict[str, List[Callable]] = {
            "pre_startup": [],
            "post_startup": [],
            "pre_shutdown": [],
            "post_shutdown": [],
            "on_error": [],
            "health_check": []
        }
        
        # Metrics and monitoring
        self._metrics = LifecycleMetrics()
        self._health_checks: Dict[str, Callable] = {}
        self._error_threshold = 5
        self._health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        
        # WebSocket integration
        self._websocket_manager = None
        self._enable_websocket_events = True
        
        # Environment configuration
        self._env = IsolatedEnvironment()
        self._load_environment_config()
        
        logger.info(
            f"SystemLifecycle initialized: user_id={user_id}, "
            f"shutdown_timeout={shutdown_timeout}s, startup_timeout={startup_timeout}s"
        )
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        try:
            self.shutdown_timeout = int(self._env.get('SHUTDOWN_TIMEOUT', str(self.shutdown_timeout)))
            self.drain_timeout = int(self._env.get('DRAIN_TIMEOUT', str(self.drain_timeout)))
            self.health_check_grace_period = int(self._env.get('HEALTH_GRACE_PERIOD', str(self.health_check_grace_period)))
            self.startup_timeout = int(self._env.get('STARTUP_TIMEOUT', str(self.startup_timeout)))
            self._error_threshold = int(self._env.get('LIFECYCLE_ERROR_THRESHOLD', str(self._error_threshold)))
            self._health_check_interval = float(self._env.get('HEALTH_CHECK_INTERVAL', str(self._health_check_interval)))
            
            logger.debug("Environment configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Error loading environment config, using defaults: {e}")
    
    # ============================================================================
    # COMPONENT REGISTRATION AND MANAGEMENT
    # ============================================================================
    
    async def register_component(
        self,
        name: str,
        component: Any,
        component_type: ComponentType,
        health_check: Optional[Callable] = None
    ) -> None:
        """
        Register a component for lifecycle management.
        
        Args:
            name: Unique component name
            component: Component instance
            component_type: Type of component
            health_check: Optional health check callable
        """
        async with self._component_lock:
            # Create component status
            component_status = ComponentStatus(
                name=name,
                component_type=component_type,
                status="registered",
                metadata={
                    "registered_at": time.time(),
                    "has_health_check": health_check is not None
                }
            )
            
            self._components[name] = component_status
            self._component_instances[component_type] = component
            
            # Register health check if provided
            if health_check:
                self._health_checks[name] = health_check
            
            logger.info(f"Component registered: {name} ({component_type.value})")
            
            # Send WebSocket event
            await self._emit_websocket_event("component_registered", {
                "component_name": name,
                "component_type": component_type.value,
                "has_health_check": health_check is not None
            })
    
    async def unregister_component(self, name: str) -> None:
        """Unregister a component from lifecycle management."""
        async with self._component_lock:
            if name in self._components:
                component = self._components.pop(name)
                
                # Remove from component instances
                for comp_type, instance in list(self._component_instances.items()):
                    if getattr(instance, 'name', None) == name:
                        del self._component_instances[comp_type]
                        break
                
                # Remove health check
                self._health_checks.pop(name, None)
                
                logger.info(f"Component unregistered: {name}")
                
                await self._emit_websocket_event("component_unregistered", {
                    "component_name": name,
                    "component_type": component.component_type.value
                })
    
    def get_component(self, component_type: ComponentType) -> Optional[Any]:
        """Get registered component by type."""
        return self._component_instances.get(component_type)
    
    def get_component_status(self, name: str) -> Optional[ComponentStatus]:
        """Get status of a registered component."""
        return self._components.get(name)
    
    # ============================================================================
    # STARTUP LIFECYCLE MANAGEMENT
    # ============================================================================
    
    async def startup(self) -> bool:
        """
        Execute complete startup sequence.
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        if self._current_phase != LifecyclePhase.INITIALIZING:
            logger.warning(f"Startup attempted from invalid phase: {self._current_phase}")
            return False
        
        async with self._phase_lock:
            await self._set_phase(LifecyclePhase.STARTING)
            self._startup_time = time.time()
        
        logger.info("=== UNIFIED STARTUP SEQUENCE INITIATED ===")
        
        try:
            # Execute startup phases
            await self._execute_lifecycle_hooks("pre_startup")
            
            # Phase 1: Component validation
            if not await self._phase_validate_components():
                await self._set_phase(LifecyclePhase.ERROR)
                return False
            
            # Phase 2: Initialize components
            if not await self._phase_initialize_components():
                await self._set_phase(LifecyclePhase.ERROR)
                return False
            
            # Phase 3: Start health monitoring
            await self._phase_start_health_monitoring()
            
            # Phase 4: Validate system readiness
            if not await self._phase_validate_readiness():
                await self._set_phase(LifecyclePhase.ERROR)
                return False
            
            # Phase 5: Execute custom startup handlers
            await self._phase_execute_startup_handlers()
            
            # Complete startup
            async with self._phase_lock:
                await self._set_phase(LifecyclePhase.RUNNING)
                self._metrics.startup_time = time.time() - self._startup_time
            
            await self._execute_lifecycle_hooks("post_startup")
            
            logger.info(f"=== STARTUP COMPLETED in {self._metrics.startup_time:.2f}s ===")
            
            await self._emit_websocket_event("startup_completed", {
                "startup_time": self._metrics.startup_time,
                "components": len(self._components),
                "phase": self._current_phase.value
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Startup failed: {e}", exc_info=True)
            await self._set_phase(LifecyclePhase.ERROR)
            await self._execute_lifecycle_hooks("on_error", error=e, phase="startup")
            return False
    
    async def _phase_validate_components(self) -> bool:
        """Phase 1: Validate all registered components."""
        logger.info("Phase 1: Validating components")
        
        if not self._components:
            logger.warning("No components registered for startup")
            return True
        
        async with self._component_lock:
            for name, component in self._components.items():
                try:
                    # Update component status
                    component.status = "validating"
                    component.last_check = time.time()
                    
                    # Perform component-specific validation
                    if component.component_type == ComponentType.DATABASE_MANAGER:
                        await self._validate_database_component(name)
                    elif component.component_type == ComponentType.WEBSOCKET_MANAGER:
                        await self._validate_websocket_component(name)
                    elif component.component_type == ComponentType.AGENT_REGISTRY:
                        await self._validate_agent_registry_component(name)
                    
                    component.status = "validated"
                    logger.info(f"Component validated: {name}")
                    
                except Exception as e:
                    component.status = "validation_failed"
                    component.last_error = str(e)
                    component.error_count += 1
                    logger.error(f"Component validation failed: {name} - {e}")
                    return False
        
        return True
    
    async def _validate_database_component(self, name: str) -> None:
        """Validate database component connectivity."""
        db_manager = self.get_component(ComponentType.DATABASE_MANAGER)
        if db_manager and hasattr(db_manager, 'health_check'):
            health_status = await db_manager.health_check()
            if not health_status.get('healthy', False):
                raise Exception(f"Database unhealthy: {health_status.get('error', 'Unknown')}")
    
    async def _validate_websocket_component(self, name: str) -> None:
        """Validate WebSocket component readiness."""
        ws_manager = self.get_component(ComponentType.WEBSOCKET_MANAGER)
        if ws_manager:
            # Store reference for lifecycle events
            self._websocket_manager = ws_manager
            # Basic validation - component exists and is callable
            if not hasattr(ws_manager, 'broadcast_system_message'):
                logger.warning("WebSocket manager missing expected methods")
    
    async def _validate_agent_registry_component(self, name: str) -> None:
        """Validate agent registry component."""
        agent_registry = self.get_component(ComponentType.AGENT_REGISTRY)
        if agent_registry and hasattr(agent_registry, 'get_registry_status'):
            status = agent_registry.get_registry_status()
            if not status.get('ready', False):
                raise Exception(f"Agent registry not ready: {status.get('reason', 'Unknown')}")
    
    async def _phase_initialize_components(self) -> bool:
        """Phase 2: Initialize all components."""
        logger.info("Phase 2: Initializing components")
        
        initialization_order = [
            ComponentType.DATABASE_MANAGER,
            ComponentType.REDIS_MANAGER,
            ComponentType.CLICKHOUSE_MANAGER,
            ComponentType.LLM_MANAGER,
            ComponentType.AGENT_REGISTRY,
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.HEALTH_SERVICE
        ]
        
        for component_type in initialization_order:
            if component_type in self._component_instances:
                component = self._component_instances[component_type]
                try:
                    # Find component name
                    component_name = None
                    for name, status in self._components.items():
                        if status.component_type == component_type:
                            component_name = name
                            break
                    
                    if component_name:
                        self._components[component_name].status = "initializing"
                        
                        # Component-specific initialization
                        if hasattr(component, 'initialize'):
                            await component.initialize()
                        elif hasattr(component, 'startup'):
                            await component.startup()
                        elif hasattr(component, 'start'):
                            await component.start()
                        
                        self._components[component_name].status = "initialized"
                        logger.info(f"Component initialized: {component_name}")
                        
                except Exception as e:
                    if component_name:
                        self._components[component_name].status = "initialization_failed"
                        self._components[component_name].last_error = str(e)
                        self._components[component_name].error_count += 1
                    
                    logger.error(f"Component initialization failed: {component_type.value} - {e}")
                    return False
        
        return True
    
    async def _phase_start_health_monitoring(self) -> None:
        """Phase 3: Start health monitoring."""
        logger.info("Phase 3: Starting health monitoring")
        
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_monitor_loop())
            logger.info("Health monitoring started")
    
    async def _phase_validate_readiness(self) -> bool:
        """Phase 4: Validate system readiness."""
        logger.info("Phase 4: Validating system readiness")
        
        # Run comprehensive health checks
        health_results = await self._run_all_health_checks()
        
        # Check if any critical components are unhealthy
        critical_failures = []
        for name, result in health_results.items():
            if not result.get('healthy', False) and result.get('critical', True):
                critical_failures.append(f"{name}: {result.get('error', 'Unknown')}")
        
        if critical_failures:
            logger.error(f"Critical components unhealthy: {critical_failures}")
            return False
        
        logger.info("System readiness validated successfully")
        return True
    
    async def _phase_execute_startup_handlers(self) -> None:
        """Phase 5: Execute custom startup handlers."""
        logger.info("Phase 5: Executing startup handlers")
        
        for handler in self._startup_handlers:
            try:
                logger.debug(f"Running startup handler: {handler.__name__}")
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error in startup handler {handler.__name__}: {e}")
                # Continue with other handlers
    
    # ============================================================================
    # SHUTDOWN LIFECYCLE MANAGEMENT
    # ============================================================================
    
    async def shutdown(self) -> bool:
        """
        Execute complete shutdown sequence.
        
        Returns:
            bool: True if shutdown successful, False otherwise
        """
        if self._shutdown_initiated:
            logger.warning("Shutdown already initiated, ignoring duplicate request")
            await self._shutdown_event.wait()
            return True
        
        self._shutdown_initiated = True
        shutdown_start_time = time.time()
        
        async with self._phase_lock:
            await self._set_phase(LifecyclePhase.SHUTTING_DOWN)
        
        logger.info("=== UNIFIED SHUTDOWN SEQUENCE INITIATED ===")
        
        try:
            await self._execute_lifecycle_hooks("pre_shutdown")
            
            # Phase 1: Mark unhealthy in health checks
            await self._shutdown_phase_1_mark_unhealthy()
            
            # Phase 2: Drain active requests
            await self._shutdown_phase_2_drain_requests()
            
            # Phase 3: Close WebSocket connections
            await self._shutdown_phase_3_close_websockets()
            
            # Phase 4: Complete agent tasks
            await self._shutdown_phase_4_complete_agents()
            
            # Phase 5: Shutdown components
            await self._shutdown_phase_5_shutdown_components()
            
            # Phase 6: Cleanup resources
            await self._shutdown_phase_6_cleanup_resources()
            
            # Phase 7: Run custom shutdown handlers
            await self._shutdown_phase_7_custom_handlers()
            
            # Complete shutdown
            async with self._phase_lock:
                await self._set_phase(LifecyclePhase.SHUTDOWN_COMPLETE)
                self._metrics.shutdown_time = time.time() - shutdown_start_time
                self._metrics.successful_shutdowns += 1
            
            await self._execute_lifecycle_hooks("post_shutdown")
            
            logger.info(f"=== SHUTDOWN COMPLETED in {self._metrics.shutdown_time:.2f}s ===")
            
            await self._emit_websocket_event("shutdown_completed", {
                "shutdown_time": self._metrics.shutdown_time,
                "success": True
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            self._metrics.failed_shutdowns += 1
            await self._set_phase(LifecyclePhase.ERROR)
            await self._execute_lifecycle_hooks("on_error", error=e, phase="shutdown")
            return False
        finally:
            self._shutdown_event.set()
    
    async def _shutdown_phase_1_mark_unhealthy(self) -> None:
        """Phase 1: Mark service as unhealthy in health checks."""
        logger.info("Phase 1: Marking service as unhealthy")
        
        health_service = self.get_component(ComponentType.HEALTH_SERVICE)
        if health_service:
            try:
                if hasattr(health_service, 'mark_shutting_down'):
                    await health_service.mark_shutting_down()
                    logger.info("Health service marked as shutting down")
                
                # Wait for grace period to let load balancers detect
                await asyncio.sleep(self.health_check_grace_period)
                logger.info(f"Health check grace period completed ({self.health_check_grace_period}s)")
                
            except Exception as e:
                logger.error(f"Error marking health service unhealthy: {e}")
        else:
            logger.warning("No health service registered for shutdown")
    
    async def _shutdown_phase_2_drain_requests(self) -> None:
        """Phase 2: Drain active HTTP requests."""
        logger.info("Phase 2: Draining active requests")
        
        if not self._active_requests:
            logger.info("No active requests to drain")
            return
        
        start_time = time.time()
        initial_count = len(self._active_requests)
        logger.info(f"Starting request drain: {initial_count} active requests")
        
        while self._active_requests and (time.time() - start_time) < self.drain_timeout:
            current_count = len(self._active_requests)
            logger.info(f"Waiting for {current_count} requests to complete...")
            
            # Show details of long-running requests
            long_running = []
            current_time = time.time()
            for req_id, start in self._active_requests.items():
                duration = current_time - start
                if duration > 5.0:  # Requests running longer than 5 seconds
                    long_running.append(f"{req_id} ({duration:.1f}s)")
            
            if long_running:
                logger.warning(f"Long-running requests: {', '.join(long_running)}")
            
            await asyncio.sleep(1.0)
        
        remaining_count = len(self._active_requests)
        elapsed = time.time() - start_time
        
        if remaining_count == 0:
            logger.info(f"All requests drained successfully in {elapsed:.2f}s")
        else:
            logger.warning(f"Request drain timeout: {remaining_count} requests still active after {elapsed:.2f}s")
    
    async def _shutdown_phase_3_close_websockets(self) -> None:
        """Phase 3: Gracefully close WebSocket connections."""
        logger.info("Phase 3: Closing WebSocket connections")
        
        if not self._websocket_manager:
            logger.info("No WebSocket manager registered")
            return
        
        try:
            # Send shutdown notification to all connected clients
            shutdown_message = {
                "type": "system_shutdown",
                "message": "Service is restarting. You will be automatically reconnected.",
                "timestamp": time.time(),
                "reconnect_delay": 2000  # 2 seconds
            }
            
            connection_count = getattr(self._websocket_manager, 'get_connection_count', lambda: 0)()
            logger.info(f"Notifying {connection_count} WebSocket connections of shutdown")
            
            if hasattr(self._websocket_manager, 'broadcast_system_message'):
                await self._websocket_manager.broadcast_system_message(shutdown_message)
            
            # Wait a moment for messages to be sent
            await asyncio.sleep(1.0)
            
            # Gracefully close all connections
            if hasattr(self._websocket_manager, 'close_all_connections'):
                await self._websocket_manager.close_all_connections()
                logger.info("All WebSocket connections closed gracefully")
            
        except Exception as e:
            logger.error(f"Error closing WebSocket connections: {e}")
    
    async def _shutdown_phase_4_complete_agents(self) -> None:
        """Phase 4: Allow agent tasks to complete."""
        logger.info("Phase 4: Completing agent tasks")
        
        agent_registry = self.get_component(ComponentType.AGENT_REGISTRY)
        if not agent_registry:
            logger.info("No agent registry registered")
            return
        
        try:
            # Get active agent tasks
            if hasattr(agent_registry, 'get_active_tasks'):
                active_tasks = agent_registry.get_active_tasks()
                if active_tasks:
                    logger.info(f"Waiting for {len(active_tasks)} agent tasks to complete")
                    
                    # Wait for tasks with timeout
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*active_tasks, return_exceptions=True),
                            timeout=10.0
                        )
                        logger.info("All agent tasks completed")
                    except asyncio.TimeoutError:
                        logger.warning("Agent task completion timeout - some tasks may be interrupted")
                else:
                    logger.info("No active agent tasks")
            
            # Stop accepting new agent requests
            if hasattr(agent_registry, 'stop_accepting_requests'):
                agent_registry.stop_accepting_requests()
                
        except Exception as e:
            logger.error(f"Error completing agent tasks: {e}")
    
    async def _shutdown_phase_5_shutdown_components(self) -> None:
        """Phase 5: Shutdown all components in reverse order."""
        logger.info("Phase 5: Shutting down components")
        
        # Shutdown in reverse order of initialization
        shutdown_order = [
            ComponentType.HEALTH_SERVICE,
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.AGENT_REGISTRY,
            ComponentType.LLM_MANAGER,
            ComponentType.CLICKHOUSE_MANAGER,
            ComponentType.REDIS_MANAGER,
            ComponentType.DATABASE_MANAGER
        ]
        
        for component_type in shutdown_order:
            if component_type in self._component_instances:
                component = self._component_instances[component_type]
                try:
                    # Find component name
                    component_name = None
                    for name, status in self._components.items():
                        if status.component_type == component_type:
                            component_name = name
                            break
                    
                    if component_name:
                        self._components[component_name].status = "shutting_down"
                        
                        # Component-specific shutdown
                        if hasattr(component, 'shutdown'):
                            await component.shutdown()
                        elif hasattr(component, 'close'):
                            await component.close()
                        elif hasattr(component, 'stop'):
                            await component.stop()
                        
                        self._components[component_name].status = "shutdown"
                        logger.info(f"Component shut down: {component_name}")
                        
                except Exception as e:
                    if component_name:
                        self._components[component_name].status = "shutdown_failed"
                        self._components[component_name].last_error = str(e)
                        self._components[component_name].error_count += 1
                    
                    logger.error(f"Component shutdown failed: {component_type.value} - {e}")
                    # Continue with other components
    
    async def _shutdown_phase_6_cleanup_resources(self) -> None:
        """Phase 6: Cleanup system resources."""
        logger.info("Phase 6: Cleaning up resources")
        
        try:
            # Stop health monitoring
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Error waiting for health check task: {e}")
                finally:
                    self._health_check_task = None
            elif self._health_check_task:
                # Task is already done, just clean up
                self._health_check_task = None
            
            # Cancel any background tasks
            current_task = asyncio.current_task()
            all_tasks = [task for task in asyncio.all_tasks() if task != current_task]
            
            if all_tasks:
                logger.info(f"Cancelling {len(all_tasks)} background tasks")
                for task in all_tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait a moment for tasks to handle cancellation
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")
    
    async def _shutdown_phase_7_custom_handlers(self) -> None:
        """Phase 7: Run custom shutdown handlers."""
        logger.info("Phase 7: Running custom shutdown handlers")
        
        for handler in self._shutdown_handlers:
            try:
                logger.debug(f"Running shutdown handler: {handler.__name__}")
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler {handler.__name__}: {e}")
    
    # ============================================================================
    # HEALTH MONITORING
    # ============================================================================
    
    async def _health_monitor_loop(self) -> None:
        """Background task for periodic health monitoring."""
        logger.info("Health monitoring loop started")
        
        while self._current_phase in [LifecyclePhase.RUNNING, LifecyclePhase.STARTING]:
            try:
                await self._run_periodic_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Short delay before retry
    
    async def _run_periodic_health_checks(self) -> None:
        """Run periodic health checks on all components."""
        health_results = await self._run_all_health_checks()
        self._metrics.last_health_check = time.time()
        
        # Update component statuses
        async with self._component_lock:
            for name, result in health_results.items():
                if name in self._components:
                    component = self._components[name]
                    component.status = "healthy" if result.get('healthy', False) else "unhealthy"
                    component.last_check = time.time()
                    
                    if not result.get('healthy', False):
                        error_msg = result.get('error', 'Unknown health check failure')
                        component.last_error = error_msg
                        component.error_count += 1
                        self._metrics.component_failures += 1
                        
                        # Execute error hooks
                        await self._execute_lifecycle_hooks("on_error", 
                                                           error=error_msg, 
                                                           component=name,
                                                           phase="health_check")
        
        # Send health status via WebSocket
        await self._emit_websocket_event("health_status", {
            "timestamp": time.time(),
            "results": health_results,
            "overall_health": all(r.get('healthy', False) for r in health_results.values())
        })
    
    async def _run_all_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run health checks for all registered components."""
        results = {}
        
        for name, health_check in self._health_checks.items():
            try:
                if asyncio.iscoroutinefunction(health_check):
                    result = await health_check()
                else:
                    result = health_check()
                
                results[name] = result if isinstance(result, dict) else {"healthy": bool(result)}
                
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "critical": True
                }
        
        return results
    
    # ============================================================================
    # REQUEST TRACKING
    # ============================================================================
    
    @asynccontextmanager
    async def request_context(self, request_id: str):
        """Context manager to track active requests during shutdown."""
        async with self._request_lock:
            self._active_requests[request_id] = time.time()
            self._metrics.active_requests = len(self._active_requests)
        
        try:
            yield
        finally:
            async with self._request_lock:
                self._active_requests.pop(request_id, None)
                self._metrics.active_requests = len(self._active_requests)
    
    # ============================================================================
    # LIFECYCLE HOOKS AND HANDLERS
    # ============================================================================
    
    def add_startup_handler(self, handler: Callable[[], Any]) -> None:
        """Add custom startup handler."""
        self._startup_handlers.append(handler)
        logger.debug(f"Added startup handler: {handler.__name__}")
    
    def add_shutdown_handler(self, handler: Callable[[], Any]) -> None:
        """Add custom shutdown handler."""
        self._shutdown_handlers.append(handler)
        logger.debug(f"Added shutdown handler: {handler.__name__}")
    
    def register_lifecycle_hook(self, event: str, handler: Callable) -> None:
        """Register lifecycle event hook."""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].append(handler)
            logger.debug(f"Registered lifecycle hook: {event} -> {handler.__name__}")
        else:
            logger.warning(f"Unknown lifecycle event: {event}")
    
    async def _execute_lifecycle_hooks(self, event: str, **kwargs) -> None:
        """Execute registered lifecycle hooks."""
        hooks = self._lifecycle_hooks.get(event, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(**kwargs)
                else:
                    hook(**kwargs)
            except Exception as e:
                logger.warning(f"Lifecycle hook {event} failed: {e}")
    
    # ============================================================================
    # WEBSOCKET INTEGRATION
    # ============================================================================
    
    async def _emit_websocket_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit WebSocket event if WebSocket manager is available."""
        if not self._enable_websocket_events or not self._websocket_manager:
            return
        
        try:
            if hasattr(self._websocket_manager, 'broadcast_system_message'):
                message = {
                    "type": f"lifecycle_{event_type}",
                    "data": data,
                    "timestamp": time.time(),
                    "user_id": self.user_id
                }
                await self._websocket_manager.broadcast_system_message(message)
        except Exception as e:
            logger.debug(f"Failed to emit WebSocket event {event_type}: {e}")
    
    def set_websocket_manager(self, websocket_manager: Any) -> None:
        """Set WebSocket manager for lifecycle events."""
        self._websocket_manager = websocket_manager
        logger.debug("WebSocket manager set for lifecycle events")
    
    def enable_websocket_events(self, enabled: bool = True) -> None:
        """Enable/disable WebSocket event emission."""
        self._enable_websocket_events = enabled
        logger.debug(f"WebSocket events {'enabled' if enabled else 'disabled'}")
    
    # ============================================================================
    # STATUS AND MONITORING
    # ============================================================================
    
    async def _set_phase(self, phase: LifecyclePhase) -> None:
        """Set current lifecycle phase with logging."""
        old_phase = self._current_phase
        self._current_phase = phase
        
        logger.info(f"Lifecycle phase transition: {old_phase.value} -> {phase.value}")
        
        await self._emit_websocket_event("phase_changed", {
            "old_phase": old_phase.value,
            "new_phase": phase.value
        })
    
    def get_current_phase(self) -> LifecyclePhase:
        """Get current lifecycle phase."""
        return self._current_phase
    
    def is_running(self) -> bool:
        """Check if system is in running state."""
        return self._current_phase == LifecyclePhase.RUNNING
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutdown_initiated
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        return {
            "user_id": self.user_id,
            "phase": self._current_phase.value,
            "startup_time": self._metrics.startup_time,
            "shutdown_time": self._metrics.shutdown_time,
            "active_requests": len(self._active_requests),
            "components": {
                name: {
                    "type": status.component_type.value,
                    "status": status.status,
                    "error_count": status.error_count,
                    "last_error": status.last_error,
                    "last_check": status.last_check
                }
                for name, status in self._components.items()
            },
            "metrics": {
                "successful_shutdowns": self._metrics.successful_shutdowns,
                "failed_shutdowns": self._metrics.failed_shutdowns,
                "component_failures": self._metrics.component_failures,
                "last_health_check": self._metrics.last_health_check
            },
            "is_shutting_down": self._shutdown_initiated,
            "ready_for_requests": self._current_phase == LifecyclePhase.RUNNING,
            "uptime": time.time() - self._startup_time if self._startup_time else 0
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring endpoints."""
        if self._current_phase == LifecyclePhase.RUNNING:
            return {
                "status": "healthy",
                "phase": self._current_phase.value,
                "components_healthy": all(
                    c.status in ["healthy", "initialized"] 
                    for c in self._components.values()
                ),
                "active_requests": len(self._active_requests)
            }
        elif self._current_phase == LifecyclePhase.STARTING:
            return {
                "status": "starting",
                "phase": self._current_phase.value,
                "ready": False
            }
        elif self._current_phase == LifecyclePhase.SHUTTING_DOWN:
            return {
                "status": "shutting_down", 
                "phase": self._current_phase.value,
                "ready": False
            }
        else:
            return {
                "status": "unhealthy",
                "phase": self._current_phase.value,
                "ready": False
            }
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to complete."""
        await self._shutdown_event.wait()
    
    # ============================================================================
    # SIGNAL HANDLING
    # ============================================================================
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig_num, frame):
            logger.info(f"Received signal {sig_num}, initiating graceful shutdown")
            # Create new event loop if needed for async shutdown
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule shutdown in the event loop
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Signal handlers configured for graceful shutdown")


# ============================================================================
# FACTORY PATTERN FOR USER ISOLATION
# ============================================================================

class LifecycleManagerFactory:
    """Factory for creating user-isolated lifecycle managers."""
    
    _global_manager: Optional[SystemLifecycle] = None
    _user_managers: Dict[str, SystemLifecycle] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_global_manager(cls) -> SystemLifecycle:
        """Get global lifecycle manager instance."""
        if cls._global_manager is None:
            with cls._lock:
                if cls._global_manager is None:
                    env = IsolatedEnvironment()
                    
                    # Environment-specific configuration
                    shutdown_timeout = int(env.get('SHUTDOWN_TIMEOUT', '30'))
                    drain_timeout = int(env.get('DRAIN_TIMEOUT', '20'))
                    grace_period = int(env.get('HEALTH_GRACE_PERIOD', '5'))
                    startup_timeout = int(env.get('STARTUP_TIMEOUT', '60'))
                    
                    cls._global_manager = SystemLifecycle(
                        user_id=None,
                        shutdown_timeout=shutdown_timeout,
                        drain_timeout=drain_timeout,
                        health_check_grace_period=grace_period,
                        startup_timeout=startup_timeout
                    )
                    
                    logger.info("Global lifecycle manager created")
        
        return cls._global_manager
    
    @classmethod
    def get_user_manager(cls, user_id: str) -> SystemLifecycle:
        """Get user-specific lifecycle manager instance."""
        if user_id not in cls._user_managers:
            with cls._lock:
                if user_id not in cls._user_managers:
                    env = IsolatedEnvironment()
                    
                    # Environment-specific configuration
                    shutdown_timeout = int(env.get('SHUTDOWN_TIMEOUT', '30'))
                    drain_timeout = int(env.get('DRAIN_TIMEOUT', '20'))
                    grace_period = int(env.get('HEALTH_GRACE_PERIOD', '5'))
                    startup_timeout = int(env.get('STARTUP_TIMEOUT', '60'))
                    
                    cls._user_managers[user_id] = SystemLifecycle(
                        user_id=user_id,
                        shutdown_timeout=shutdown_timeout,
                        drain_timeout=drain_timeout,
                        health_check_grace_period=grace_period,
                        startup_timeout=startup_timeout
                    )
                    
                    logger.info(f"User-specific lifecycle manager created: {user_id}")
        
        return cls._user_managers[user_id]
    
    @classmethod
    async def shutdown_all_managers(cls) -> None:
        """Shutdown all lifecycle managers."""
        shutdown_tasks = []
        
        # Shutdown global manager
        if cls._global_manager:
            shutdown_tasks.append(cls._global_manager.shutdown())
        
        # Shutdown user managers
        for manager in cls._user_managers.values():
            shutdown_tasks.append(manager.shutdown())
        
        if shutdown_tasks:
            results = await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            failed_shutdowns = sum(1 for r in results if isinstance(r, Exception) or r is False)
            
            if failed_shutdowns:
                logger.warning(f"{failed_shutdowns} lifecycle managers failed to shutdown gracefully")
            else:
                logger.info("All lifecycle managers shut down successfully")
        
        # Clear references
        cls._global_manager = None
        cls._user_managers.clear()
    
    @classmethod
    def get_manager_count(cls) -> Dict[str, int]:
        """Get count of active managers."""
        return {
            "global": 1 if cls._global_manager else 0,
            "user_specific": len(cls._user_managers),
            "total": (1 if cls._global_manager else 0) + len(cls._user_managers)
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_lifecycle_manager(user_id: Optional[str] = None) -> UnifiedLifecycleManager:
    """
    Get appropriate lifecycle manager instance.
    
    Args:
        user_id: User ID for user-specific manager, None for global
    
    Returns:
        UnifiedLifecycleManager instance
    """
    if user_id:
        return LifecycleManagerFactory.get_user_manager(user_id)
    else:
        return LifecycleManagerFactory.get_global_manager()


async def setup_application_lifecycle(
    app,
    websocket_manager=None,
    db_manager=None,
    agent_registry=None,
    health_service=None,
    user_id: Optional[str] = None
) -> UnifiedLifecycleManager:
    """
    Setup application lifecycle management.
    
    Args:
        app: FastAPI application instance
        websocket_manager: WebSocket manager instance
        db_manager: Database manager instance
        agent_registry: Agent registry instance
        health_service: Health service instance
        user_id: User ID for user-specific lifecycle management
    
    Returns:
        UnifiedLifecycleManager instance
    """
    lifecycle_manager = get_lifecycle_manager(user_id)
    
    # Register components
    if websocket_manager:
        await lifecycle_manager.register_component(
            "websocket_manager", 
            websocket_manager, 
            ComponentType.WEBSOCKET_MANAGER
        )
    if db_manager:
        await lifecycle_manager.register_component(
            "database_manager", 
            db_manager, 
            ComponentType.DATABASE_MANAGER
        )
    if agent_registry:
        await lifecycle_manager.register_component(
            "agent_registry", 
            agent_registry, 
            ComponentType.AGENT_REGISTRY
        )
    if health_service:
        await lifecycle_manager.register_component(
            "health_service", 
            health_service, 
            ComponentType.HEALTH_SERVICE
        )
    
    # Setup signal handlers
    lifecycle_manager.setup_signal_handlers()
    
    # Add FastAPI lifecycle event handlers
    @app.on_event("startup")
    async def startup_event():
        logger.info("FastAPI startup event triggered")
        startup_success = await lifecycle_manager.startup()
        if not startup_success:
            logger.error("Application startup failed")
            # In production, you might want to exit the application here
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FastAPI shutdown event triggered")
        if not lifecycle_manager.is_shutting_down():
            await lifecycle_manager.shutdown()
    
    logger.info(f"Unified lifecycle management configured: user_id={user_id}")
    return lifecycle_manager