"""
Startup Integration for Service Lifecycle Management

This module provides integration between the ServiceLifecycleManager and
the existing service startup processes. It demonstrates how to implement
the Level 3-5 fixes in the existing codebase.

CRITICAL: This shows how to migrate from race-condition-prone startup
to lifecycle-managed startup with proper dependency ordering.
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from contextlib import asynccontextmanager

from shared.lifecycle.service_lifecycle_manager import (
    ServiceLifecycleManager,
    ServiceRegistration,
    ServiceDependency,
    ReadinessContract,
    InitializationPhase,
    ServiceState,
    get_lifecycle_manager
)
from shared.configuration.central_config_validator import get_central_validator
from shared.logging.unified_logger_factory import get_logger

logger = get_logger(__name__)


class StartupIntegration:
    """
    Integration layer between lifecycle management and existing startup code.
    
    This class demonstrates how to migrate from the race-condition-prone 
    startup sequence to proper lifecycle management.
    """
    
    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self.lifecycle_manager = get_lifecycle_manager()
        self.startup_handlers: Dict[str, Callable] = {}
        
    def register_core_services(self) -> None:
        """
        Register core services with the lifecycle manager.
        
        LEVEL 3-5 FIX: This replaces the ad-hoc startup sequence with
        properly managed service initialization.
        """
        
        # PHASE 1: BOOTSTRAP - Environment and configuration
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="environment_validation",
            phase=InitializationPhase.BOOTSTRAP,
            initializer=self._initialize_environment_validation,
            readiness_contract=ReadinessContract(
                service_name="environment_validation",
                custom_validator=self._validate_environment_readiness,
                timeout_seconds=10.0,
                retry_count=3,
                retry_delay=0.5
            ),
            is_critical=True,
            timeout_seconds=30.0
        ))
        
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="logging_system",
            phase=InitializationPhase.BOOTSTRAP,
            initializer=self._initialize_logging,
            is_critical=True,
            timeout_seconds=10.0
        ))
        
        # PHASE 2: DEPENDENCIES - Auth, secrets, core services
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="auth_validation",
            phase=InitializationPhase.DEPENDENCIES,
            dependencies=[
                ServiceDependency(
                    service_name="environment_validation",
                    required_state=ServiceState.READY,
                    is_critical=True,
                    timeout_seconds=30.0,
                    description="Auth validation requires environment to be ready first"
                )
            ],
            initializer=self._initialize_auth_validation,
            readiness_contract=ReadinessContract(
                service_name="auth_validation",
                custom_validator=self._validate_auth_readiness,
                timeout_seconds=30.0,
                retry_count=5,  # More retries for auth due to complexity
                retry_delay=1.0
            ),
            is_critical=True,
            timeout_seconds=60.0
        ))
        
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="key_manager",
            phase=InitializationPhase.DEPENDENCIES,
            dependencies=[
                ServiceDependency(
                    service_name="auth_validation",
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            initializer=self._initialize_key_manager,
            is_critical=True,
            timeout_seconds=30.0
        ))
        
        # PHASE 3: DATABASE - Database connections
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="database_connection",
            phase=InitializationPhase.DATABASE,
            dependencies=[
                ServiceDependency(
                    service_name="key_manager",
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            initializer=self._initialize_database,
            readiness_contract=ReadinessContract(
                service_name="database_connection",
                custom_validator=self._validate_database_connectivity,
                timeout_seconds=45.0,
                retry_count=5,
                retry_delay=2.0
            ),
            is_critical=True,
            timeout_seconds=120.0  # Database init can take time
        ))
        
        # PHASE 4: CACHE - Redis and caching
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="redis_connection",
            phase=InitializationPhase.CACHE,
            dependencies=[
                ServiceDependency(
                    service_name="key_manager",
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            initializer=self._initialize_redis,
            readiness_contract=ReadinessContract(
                service_name="redis_connection", 
                custom_validator=self._validate_redis_connectivity,
                timeout_seconds=30.0,
                retry_count=3,
                retry_delay=1.0
            ),
            is_critical=True,
            timeout_seconds=60.0
        ))
        
        # PHASE 5: SERVICES - Business logic services
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="agent_supervisor",
            phase=InitializationPhase.SERVICES,
            dependencies=[
                ServiceDependency(
                    service_name="database_connection",
                    required_state=ServiceState.READY,
                    is_critical=True
                ),
                ServiceDependency(
                    service_name="redis_connection", 
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            initializer=self._initialize_agent_supervisor,
            is_critical=True,
            timeout_seconds=60.0
        ))
        
        # PHASE 6: INTEGRATION - WebSocket and external integrations
        self.lifecycle_manager.register_service(ServiceRegistration(
            name="websocket_manager",
            phase=InitializationPhase.INTEGRATION,
            dependencies=[
                ServiceDependency(
                    service_name="agent_supervisor",
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            initializer=self._initialize_websocket_manager,
            readiness_contract=ReadinessContract(
                service_name="websocket_manager",
                custom_validator=self._validate_websocket_readiness,
                timeout_seconds=20.0,
                retry_count=3,
                retry_delay=1.0
            ),
            is_critical=True,
            timeout_seconds=60.0
        ))
    
    async def _initialize_environment_validation(self) -> None:
        """Initialize environment validation with race condition protection."""
        logger.info("Initializing environment validation with race condition protection...")
        
        validator = get_central_validator()
        
        # LEVEL 1-2 FIX: Use the race-condition-protected validation
        # Wait for environment readiness before proceeding
        if not validator.force_readiness_check():
            raise RuntimeError("Environment readiness check failed - race condition detected")
        
        # Run the protected validation
        validator.validate_all_requirements()
        
        logger.info("Environment validation completed successfully")
    
    async def _validate_environment_readiness(self) -> bool:
        """Validate that environment system is ready."""
        try:
            validator = get_central_validator()
            return validator.is_ready() or validator.force_readiness_check()
        except Exception as e:
            logger.warning(f"Environment readiness validation failed: {e}")
            return False
    
    async def _initialize_logging(self) -> None:
        """Initialize logging system."""
        logger.info("Initializing logging system...")
        # Logging is already initialized by the time we get here
        # This is a placeholder for any additional logging setup
    
    async def _initialize_auth_validation(self) -> None:
        """Initialize auth validation system."""
        logger.info("Initializing auth validation...")
        
        try:
            # Import and run auth validation
            from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
            await validate_auth_at_startup()
            
            if self.app:
                # Store validation success on app state
                self.app.state.auth_validation_complete = True
            
            logger.info("Auth validation completed successfully")
            
        except Exception as e:
            logger.error(f"Auth validation failed: {e}")
            raise RuntimeError(f"Auth validation failure: {e}")
    
    async def _validate_auth_readiness(self) -> bool:
        """Validate that auth system is ready."""
        try:
            if self.app and hasattr(self.app.state, 'auth_validation_complete'):
                return self.app.state.auth_validation_complete
            
            # If we don't have app state, try to validate directly
            from netra_backend.app.core.auth_startup_validator import AuthStartupValidator
            validator = AuthStartupValidator()
            success, _ = await validator.validate_all()
            return success
            
        except Exception as e:
            logger.warning(f"Auth readiness validation failed: {e}")
            return False
    
    async def _initialize_key_manager(self) -> None:
        """Initialize key management system."""
        logger.info("Initializing key manager...")
        
        if not self.app:
            logger.warning("No app instance provided - key manager initialization skipped")
            return
        
        try:
            # Initialize key manager (this would be the actual implementation)
            from netra_backend.app.services.key_manager import KeyManager
            key_manager = KeyManager()
            await key_manager.initialize()
            
            self.app.state.key_manager = key_manager
            logger.info("Key manager initialized successfully")
            
        except ImportError:
            logger.warning("KeyManager not available - using mock")
            self.app.state.key_manager = "mock_key_manager"
        except Exception as e:
            logger.error(f"Key manager initialization failed: {e}")
            raise
    
    async def _initialize_database(self) -> None:
        """Initialize database connections."""
        logger.info("Initializing database connections...")
        
        if not self.app:
            logger.warning("No app instance provided - database initialization skipped")
            return
        
        try:
            # This would call the actual database initialization
            from netra_backend.app.db.postgres import initialize_postgres
            
            session_factory = await initialize_postgres()
            self.app.state.db_session_factory = session_factory
            
            logger.info("Database connections initialized successfully")
            
        except ImportError:
            logger.warning("Database module not available - using mock")
            self.app.state.db_session_factory = "mock_db"
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _validate_database_connectivity(self) -> bool:
        """Validate database connectivity."""
        try:
            if self.app and hasattr(self.app.state, 'db_session_factory'):
                # Could test actual database connection here
                return self.app.state.db_session_factory is not None
            return False
        except Exception as e:
            logger.warning(f"Database connectivity validation failed: {e}")
            return False
    
    async def _initialize_redis(self) -> None:
        """Initialize Redis connections.""" 
        logger.info("Initializing Redis connections...")
        
        if not self.app:
            logger.warning("No app instance provided - Redis initialization skipped")
            return
        
        try:
            # This would call the actual Redis initialization
            from netra_backend.app.db.redis import initialize_redis
            
            redis_manager = await initialize_redis()
            self.app.state.redis_manager = redis_manager
            
            logger.info("Redis connections initialized successfully")
            
        except ImportError:
            logger.warning("Redis module not available - using mock")
            self.app.state.redis_manager = "mock_redis"
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            raise
    
    async def _validate_redis_connectivity(self) -> bool:
        """Validate Redis connectivity."""
        try:
            if self.app and hasattr(self.app.state, 'redis_manager'):
                return self.app.state.redis_manager is not None
            return False
        except Exception as e:
            logger.warning(f"Redis connectivity validation failed: {e}")
            return False
    
    async def _initialize_agent_supervisor(self) -> None:
        """Initialize agent supervisor."""
        logger.info("Initializing agent supervisor...")
        
        if not self.app:
            logger.warning("No app instance provided - agent supervisor initialization skipped")
            return
        
        # Mock implementation - replace with actual agent supervisor initialization
        self.app.state.agent_supervisor = "mock_agent_supervisor"
        self.app.state.thread_service = "mock_thread_service"
        
        logger.info("Agent supervisor initialized successfully")
    
    async def _initialize_websocket_manager(self) -> None:
        """Initialize WebSocket manager."""
        logger.info("Initializing WebSocket manager...")
        
        if not self.app:
            logger.warning("No app instance provided - WebSocket initialization skipped")
            return
        
        # Mock implementation - replace with actual WebSocket initialization
        self.app.state.websocket_manager = "mock_websocket_manager"
        self.app.state.agent_websocket_bridge = "mock_websocket_bridge"
        
        logger.info("WebSocket manager initialized successfully")
    
    async def _validate_websocket_readiness(self) -> bool:
        """Validate WebSocket system readiness."""
        try:
            if self.app and hasattr(self.app.state, 'websocket_manager'):
                return self.app.state.websocket_manager is not None
            return False
        except Exception as e:
            logger.warning(f"WebSocket readiness validation failed: {e}")
            return False
    
    @asynccontextmanager
    async def lifecycle_managed_startup(self, app: Any = None):
        """
        Context manager for lifecycle-managed application startup.
        
        This replaces the existing startup sequence with proper lifecycle management.
        
        Usage:
            async with startup_integration.lifecycle_managed_startup(app):
                # App is now fully initialized with proper dependency ordering
                # No race conditions during startup
                yield app
        """
        if app:
            self.app = app
        
        try:
            logger.info("Starting lifecycle-managed application startup...")
            
            # Register all core services
            self.register_core_services()
            
            # Add state change callback for debugging
            def log_state_change(service_name: str, old_state: ServiceState, new_state: ServiceState):
                logger.debug(f"Service {service_name}: {old_state.value} -> {new_state.value}")
            
            self.lifecycle_manager.add_state_change_callback(log_state_change)
            
            # Initialize all services with proper ordering
            success = await self.lifecycle_manager.initialize_all_services()
            
            if not success:
                failed_services = self.lifecycle_manager.get_failed_services()
                raise RuntimeError(f"Critical services failed to initialize: {failed_services}")
            
            logger.info("Lifecycle-managed startup completed successfully")
            
            # Provide the initialized app
            yield self.app
            
        except Exception as e:
            logger.error(f"Lifecycle-managed startup failed: {e}")
            raise
        
        finally:
            # Cleanup
            logger.info("Shutting down lifecycle-managed services...")
            try:
                await self.lifecycle_manager.shutdown()
                logger.info("Lifecycle-managed shutdown completed")
            except Exception as e:
                logger.error(f"Shutdown error: {e}")


# Convenience function for integration
async def initialize_with_lifecycle_management(app: Any) -> bool:
    """
    Initialize application using lifecycle management.
    
    This function provides a drop-in replacement for existing startup sequences.
    
    Args:
        app: FastAPI or other app instance
        
    Returns:
        bool: True if initialization successful
        
    Example:
        # Replace existing startup with:
        success = await initialize_with_lifecycle_management(app)
        if not success:
            raise RuntimeError("Application startup failed")
    """
    integration = StartupIntegration(app)
    
    try:
        integration.register_core_services()
        return await integration.lifecycle_manager.initialize_all_services()
    except Exception as e:
        logger.error(f"Lifecycle initialization failed: {e}")
        return False


# Function to migrate existing startup code
def create_migration_plan(existing_startup_function: Callable) -> Dict[str, Any]:
    """
    Analyze existing startup function and create migration plan.
    
    This helps identify how to migrate existing startup code to lifecycle management.
    
    Args:
        existing_startup_function: The existing startup function to analyze
        
    Returns:
        Migration plan with recommendations
    """
    import inspect
    
    # Analyze the function
    source = inspect.getsource(existing_startup_function)
    
    migration_plan = {
        "function_name": existing_startup_function.__name__,
        "recommendations": [],
        "identified_services": [],
        "potential_race_conditions": []
    }
    
    # Simple analysis (in practice, this would be more sophisticated)
    if "auth" in source.lower():
        migration_plan["identified_services"].append("auth_validation")
        migration_plan["recommendations"].append("Move auth validation to DEPENDENCIES phase")
    
    if "database" in source.lower() or "db" in source.lower():
        migration_plan["identified_services"].append("database_connection") 
        migration_plan["recommendations"].append("Move database init to DATABASE phase")
    
    if "redis" in source.lower():
        migration_plan["identified_services"].append("redis_connection")
        migration_plan["recommendations"].append("Move Redis init to CACHE phase")
    
    if "websocket" in source.lower():
        migration_plan["identified_services"].append("websocket_manager")
        migration_plan["recommendations"].append("Move WebSocket init to INTEGRATION phase")
    
    # Look for potential race conditions
    if "thread" in source.lower() and "start" in source.lower():
        migration_plan["potential_race_conditions"].append("Threading without synchronization")
    
    if "async" in source and "await" not in source:
        migration_plan["potential_race_conditions"].append("Async function not properly awaited")
    
    return migration_plan