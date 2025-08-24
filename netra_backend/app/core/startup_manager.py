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

    async def initialize_system(self, app) -> bool:
        """
        Initialize system with all startup components registered and executed in proper order.
        
        This method registers all startup components based on priority configuration,
        integrates with DatabaseInitializer, and executes the complete startup sequence.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        try:
            # Import required modules for initialization
            from fastapi import FastAPI
            from netra_backend.app.startup_module import (
                initialize_logging, setup_multiprocessing_env, validate_database_environment,
                run_database_migrations, setup_database_connections, initialize_core_services,
                setup_security_services, initialize_clickhouse, initialize_websocket_components,
                startup_health_checks, validate_schema, register_websocket_handlers,
                start_monitoring
            )
            from netra_backend.app.services.startup_fixes_integration import startup_fixes
            from netra_backend.app.services.background_task_manager import background_task_manager
            from netra_backend.app.db.database_initializer import DatabaseInitializer
            from netra_backend.app.core.startup_config import StartupConfig
            
            # Clear any existing components to ensure clean initialization
            self.components.clear()
            self.circuit_breakers.clear()
            
            # Register database as CRITICAL priority - must succeed
            self.register_component(
                name="database",
                init_func=lambda: self._initialize_database(app),
                priority=ComponentPriority.CRITICAL,
                timeout_seconds=60.0,
                max_retries=3
            )
            
            # Register redis as HIGH priority
            self.register_component(
                name="redis", 
                init_func=lambda: self._initialize_redis(app),
                priority=ComponentPriority.HIGH,
                dependencies=["database"],
                timeout_seconds=30.0,
                max_retries=2
            )
            
            # Register auth_service as HIGH priority
            self.register_component(
                name="auth_service",
                init_func=lambda: self._initialize_auth_service(app),
                priority=ComponentPriority.HIGH,
                dependencies=["database"],
                timeout_seconds=30.0,
                max_retries=2
            )
            
            # Register websocket as HIGH priority
            self.register_component(
                name="websocket",
                init_func=lambda: self._initialize_websocket(app),
                priority=ComponentPriority.HIGH,
                dependencies=["database", "redis"],
                timeout_seconds=30.0,
                max_retries=2
            )
            
            # Register clickhouse as MEDIUM priority
            self.register_component(
                name="clickhouse",
                init_func=lambda: self._initialize_clickhouse_wrapper(),
                priority=ComponentPriority.MEDIUM,
                timeout_seconds=45.0,
                max_retries=2
            )
            
            # Register monitoring as MEDIUM priority
            self.register_component(
                name="monitoring",
                init_func=lambda: self._initialize_monitoring_wrapper(app),
                priority=ComponentPriority.MEDIUM,
                dependencies=["database"],
                timeout_seconds=20.0,
                max_retries=1
            )
            
            # Register background_tasks as MEDIUM priority
            self.register_component(
                name="background_tasks",
                init_func=lambda: self._initialize_background_tasks(app),
                priority=ComponentPriority.MEDIUM,
                dependencies=["database"],
                timeout_seconds=20.0,
                max_retries=1
            )
            
            # Register metrics as LOW priority
            self.register_component(
                name="metrics",
                init_func=lambda: self._initialize_metrics(app),
                priority=ComponentPriority.LOW,
                timeout_seconds=15.0,
                max_retries=1
            )
            
            # Register tracing as LOW priority
            self.register_component(
                name="tracing", 
                init_func=lambda: self._initialize_tracing(app),
                priority=ComponentPriority.LOW,
                timeout_seconds=15.0,
                max_retries=1
            )
            
            # Register agent_supervisor as HIGH priority - required for WebSocket agent communication
            self.register_component(
                name="agent_supervisor",
                init_func=lambda: self._initialize_agent_supervisor(app),
                priority=ComponentPriority.HIGH,
                dependencies=["database", "websocket"],
                timeout_seconds=30.0,
                max_retries=2
            )
            
            # Initialize logging first (synchronous, required for other components)
            start_time, logger = initialize_logging()
            logger.info("Starting robust system initialization...")
            
            # Execute the startup sequence
            success = await self.startup()
            
            if success:
                logger.info("Robust system initialization completed successfully")
                # Store components in app state for monitoring
                app.state.startup_manager = self
                return True
            else:
                logger.error("Robust system initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"Error in initialize_system: {e}")
            return False

    async def _initialize_database(self, app) -> None:
        """Initialize PostgreSQL database with DatabaseInitializer integration"""
        from netra_backend.app.startup_module import (
            setup_multiprocessing_env, validate_database_environment,
            run_database_migrations, setup_database_connections
        )
        from netra_backend.app.db.database_initializer import DatabaseInitializer
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Setup multiprocessing environment
        setup_multiprocessing_env(logger)
        
        # Validate database environment
        validate_database_environment(logger)
        
        # Run migrations
        run_database_migrations(logger)
        
        # Initialize database connections using DatabaseInitializer
        db_initializer = DatabaseInitializer()
        await db_initializer.initialize_postgresql()
        
        # Setup database connections in FastAPI app
        await setup_database_connections(app)
        
        logger.info("Database initialization completed successfully")

    async def _initialize_redis(self, app) -> None:
        """Initialize Redis connection and services"""
        from netra_backend.app.redis_manager import redis_manager
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Initialize Redis manager
        await redis_manager.initialize()
        
        # Store in app state
        app.state.redis_manager = redis_manager
        
        logger.info("Redis initialization completed successfully")

    async def _initialize_auth_service(self, app) -> None:
        """Initialize authentication and security services"""
        from netra_backend.app.startup_module import initialize_core_services, setup_security_services
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Initialize core services including KeyManager
        key_manager = initialize_core_services(app, logger)
        
        # Setup security services
        setup_security_services(app, key_manager)
        
        logger.info("Auth service initialization completed successfully")

    async def _initialize_websocket(self, app) -> None:
        """Initialize WebSocket components and handlers"""
        from netra_backend.app.startup_module import initialize_websocket_components, register_websocket_handlers
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Register WebSocket handlers
        register_websocket_handlers(app)
        
        # Initialize WebSocket components
        await initialize_websocket_components(logger)
        
        logger.info("WebSocket initialization completed successfully")

    async def _initialize_background_tasks(self, app) -> None:
        """Initialize background task management"""
        from netra_backend.app.services.background_task_manager import background_task_manager
        from netra_backend.app.services.startup_fixes_integration import startup_fixes
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Initialize background task manager
        app.state.background_task_manager = background_task_manager
        logger.info("Background task manager initialized")
        
        # Apply startup fixes
        try:
            fix_results = await startup_fixes.run_comprehensive_verification()
            applied_fixes = fix_results.get('total_fixes', 0)
            logger.info(f"Applied {applied_fixes}/5 startup fixes")
        except Exception as e:
            logger.warning(f"Error applying startup fixes: {e}")
        
        logger.info("Background tasks initialization completed successfully")

    async def _initialize_metrics(self, app) -> None:
        """Initialize metrics collection and reporting"""
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Initialize metrics collection (placeholder for metrics setup)
        # This would integrate with actual metrics collection system
        app.state.metrics_enabled = True
        
        logger.info("Metrics initialization completed successfully")

    async def _initialize_tracing(self, app) -> None:
        """Initialize distributed tracing"""
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Initialize tracing (placeholder for tracing setup)
        # This would integrate with actual tracing system like OpenTelemetry
        app.state.tracing_enabled = True
        
        logger.info("Tracing initialization completed successfully")

    async def _initialize_clickhouse_wrapper(self) -> None:
        """Wrapper for ClickHouse initialization with proper logger access"""
        from netra_backend.app.startup_module import initialize_clickhouse
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        await initialize_clickhouse(logger)

    async def _initialize_monitoring_wrapper(self, app) -> None:
        """Wrapper for monitoring initialization with proper logger access"""
        from netra_backend.app.startup_module import start_monitoring
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        await start_monitoring(app, logger)

    async def _initialize_agent_supervisor(self, app) -> None:
        """Initialize agent supervisor for WebSocket agent communication"""
        from netra_backend.app.startup_module import _create_agent_supervisor
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # Create agent supervisor and set up agent services
        _create_agent_supervisor(app)
        
        # Verify agent supervisor was created
        if not hasattr(app.state, 'agent_supervisor') or app.state.agent_supervisor is None:
            raise RuntimeError("Failed to create agent supervisor - app.state.agent_supervisor is None")
        
        logger.info("Agent supervisor initialization completed successfully")


# Global instance
startup_manager = StartupManager()


async def initialize_system_components() -> bool:
    """Main entry point for system initialization (deprecated - use initialize_system)"""
    return await startup_manager.startup()


async def shutdown_system() -> None:
    """Main entry point for system shutdown"""
    await startup_manager.shutdown()