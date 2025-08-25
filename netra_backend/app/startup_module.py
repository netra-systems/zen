from netra_backend.app.core.isolated_environment import get_env
"""
Application startup management module.
Handles initialization of logging, database connections, services, and health checks.
"""
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from fastapi import FastAPI

from netra_backend.app.agents.base.monitoring import performance_monitor
from netra_backend.app.services.background_task_manager import BackgroundTaskManager
from netra_backend.app.config import get_config, settings
from netra_backend.app.services.background_task_manager import background_task_manager
from netra_backend.app.services.startup_fixes_integration import startup_fixes
from netra_backend.app.core.performance_optimization_manager import performance_manager
from netra_backend.app.core.startup_manager import startup_manager
from netra_backend.app.db.index_optimizer import index_manager
from netra_backend.app.db.migration_utils import (
    create_alembic_config,
    execute_migration,
    get_current_revision,
    get_head_revision,
    get_sync_database_url,
    log_migration_status,
    needs_migration,
    should_continue_on_error,
    validate_database_url,
)
from netra_backend.app.db.postgres import initialize_postgres
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.key_manager import KeyManager
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.utils.multiprocessing_cleanup import setup_multiprocessing


async def _ensure_database_tables_exist(logger: logging.Logger, graceful_startup: bool = True) -> None:
    """Ensure all required database tables exist, creating them if necessary."""
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.db.base import Base
        from sqlalchemy import text
        import asyncio
        
        # Import all model classes to ensure they're registered with Base.metadata
        logger.info("Importing database models to register tables...")
        _import_all_models()
        
        logger.info("Checking if database tables exist...")
        
        # Create async engine for table creation
        engine = DatabaseManager.create_application_engine()
        
        # Test connection with retry logic to avoid pool exhaustion
        connection_ok = await DatabaseManager.test_connection_with_retry(engine)
        if not connection_ok:
            error_msg = "Failed to establish database connection for table verification"
            if graceful_startup:
                logger.warning(f"{error_msg} - continuing without table verification")
                return
            else:
                raise RuntimeError(error_msg)
        
        # Check if tables exist
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            existing_tables = set(row[0] for row in result.fetchall())
            expected_tables = set(Base.metadata.tables.keys())
            missing_tables = expected_tables - existing_tables
            
            if missing_tables:
                logger.warning(f"Missing {len(missing_tables)} database tables: {missing_tables}")
                logger.info("Creating missing database tables automatically...")
                
                # Create missing tables
                await conn.run_sync(Base.metadata.create_all)
                
                # Verify tables were created
                result = await conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """))
                
                new_existing_tables = set(row[0] for row in result.fetchall())
                still_missing = expected_tables - new_existing_tables
                
                if still_missing:
                    error_msg = f"Failed to create tables: {still_missing}"
                    if graceful_startup:
                        logger.error(f"{error_msg} - continuing with degraded functionality")
                    else:
                        raise RuntimeError(error_msg)
                else:
                    logger.info(f"Successfully created {len(missing_tables)} missing database tables")
            else:
                logger.info(f"All {len(expected_tables)} database tables are present")
        
        # Log final pool status before disposal
        pool_status = DatabaseManager.get_pool_status(engine)
        logger.debug(f"Database pool status before disposal: {pool_status}")
        
        await engine.dispose()
        
    except Exception as e:
        error_msg = f"Failed to ensure database tables exist: {e}"
        if graceful_startup:
            logger.warning(f"{error_msg} - continuing with potential database issues")
        else:
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def _import_all_models() -> None:
    """Import all model classes to register them with Base.metadata."""
    # Import all models to ensure they are registered
    try:
        # Agent models
        from netra_backend.app.db.models_agent import (
            ApexOptimizerAgentRun,
            ApexOptimizerAgentRunReport,
            Assistant,
            Message,
            Run,
            Step,
            Thread,
        )
        
        # Agent State models
        from netra_backend.app.db.models_agent_state import (
            AgentRecoveryLog,
            AgentStateSnapshot,
            AgentStateTransaction,
        )
        
        # Content models
        from netra_backend.app.db.models_content import (
            Analysis,
            AnalysisResult,
            Corpus,
            CorpusAuditLog,
            Reference,
        )
        
        # MCP Client models
        from netra_backend.app.db.models_mcp_client import (
            MCPExternalServer,
            MCPResourceAccess,
            MCPToolExecution,
        )
        
        # Supply models  
        from netra_backend.app.db.models_supply import (
            AISupplyItem,
            AvailabilityStatus,
            ResearchSession,
            ResearchSessionStatus,
            Supply,
            SupplyOption,
            SupplyUpdateLog,
        )
        
        # User models
        from netra_backend.app.db.models_user import Secret, ToolUsageLog, User
        
    except ImportError as e:
        # Some models might not be available in certain environments
        pass


async def _initialize_performance_optimizations(app: FastAPI, logger: logging.Logger) -> None:
    """Initialize performance optimization components."""
    try:
        await _setup_performance_manager(app)
        _setup_optimization_components(app)
        await _schedule_background_optimizations(app, logger)
        logger.info("Performance optimizations initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize performance optimizations: {e}")
        # Don't fail startup, but log the error


async def _setup_performance_manager(app: FastAPI) -> None:
    """Setup performance optimization manager."""
    await performance_manager.initialize()
    app.state.performance_manager = performance_manager


def _setup_optimization_components(app: FastAPI) -> None:
    """Setup optimization components in app state."""
    app.state.index_manager = index_manager


async def _schedule_background_optimizations(app: FastAPI, logger: logging.Logger) -> None:
    """Schedule index optimization as background task."""
    if hasattr(app.state, 'background_task_manager'):
        # Use partial to bind the logger argument to the coroutine function
        from functools import partial
        optimization_coro = partial(_run_index_optimization_background, logger)
        
        # Use create_task method with coroutine function
        task_id = await app.state.background_task_manager.create_task(
            coro=optimization_coro,
            name="database_index_optimization",
            timeout=120  # 2-minute timeout to prevent hanging
        )
        logger.info(f"Database index optimization scheduled as background task (ID: {task_id})")


async def _run_index_optimization_background(logger: logging.Logger) -> None:
    """Run database index optimization in background."""
    try:
        # Delay optimization to avoid startup bottleneck
        await asyncio.sleep(30)  # Wait 30 seconds after startup
        logger.info("Starting background database index optimization...")
        
        # Add timeout to prevent hanging indefinitely
        optimization_results = await asyncio.wait_for(
            index_manager.optimize_all_databases(), 
            timeout=120.0  # 2 minute timeout
        )
        logger.info(f"Background database optimization completed successfully: {optimization_results}")
    except asyncio.TimeoutError:
        logger.error("Background index optimization timed out after 2 minutes - continuing without optimization")
    except Exception as e:
        logger.error(f"Background index optimization failed: {e}")
        # Continue running - don't let this crash the application


def initialize_logging() -> Tuple[float, logging.Logger]:
    """Initialize startup logging and timing."""
    start_time = time.time()
    logger = central_logger.get_logger(__name__)
    logger.info("Application startup...")
    return start_time, logger


def setup_multiprocessing_env(logger: logging.Logger) -> None:
    """Setup multiprocessing environment."""
    setup_multiprocessing()
    if 'pytest' in sys.modules:
        logger.info("pytest detected in sys.modules")


def validate_database_environment(logger: logging.Logger) -> None:
    """Validate database environment separation."""
    if 'pytest' not in sys.modules:
        _perform_database_validation(logger)


def _perform_database_validation(logger: logging.Logger) -> None:
    """Perform database environment validation."""
    from netra_backend.app.services.database_env_service import (
        validate_database_environment,
    )
    try:
        validate_database_environment()
    except ValueError as e:
        logger.critical(f"Database environment validation failed: {e}")
        os._exit(1)


def run_database_migrations(logger: logging.Logger) -> None:
    """Run database migrations if not in test mode."""
    config = get_config()
    fast_startup = config.fast_startup_mode.lower() == "true"
    skip_migrations = config.skip_migrations.lower() == "true"
    
    # Check if database is in mock mode by examining DATABASE_URL or service config
    database_url = config.database_url or ""
    is_mock_database = _is_mock_database_url(database_url) or _is_postgres_service_mock_mode()
    
    if is_mock_database:
        logger.info("Skipping database migrations (PostgreSQL in mock mode)")
        return
    
    if 'pytest' not in sys.modules and not fast_startup and not skip_migrations:
        _execute_migrations(logger)
    elif fast_startup or skip_migrations:
        logger.info("Skipping database migrations (fast startup mode)")


def _is_mock_database_url(database_url: str) -> bool:
    """Check if database URL indicates mock mode."""
    if not database_url:
        return False
    
    # Check for common mock database URL patterns
    mock_patterns = [
        "postgresql://mock:mock@",
        "postgresql+asyncpg://mock:mock@",
        "/mock?",  # database name is "mock"
        "/mock$",  # database name is "mock" at end
        "@localhost:5432/mock"  # specific mock pattern used by dev launcher
    ]
    
    return any(pattern in database_url for pattern in mock_patterns)


def _is_postgres_service_mock_mode() -> bool:
    """Check if PostgreSQL service is configured in mock mode via dev launcher config."""
    import json
    import os
    from pathlib import Path
    
    try:
        # Check dev launcher service config
        config_path = Path.cwd() / ".dev_services.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                postgres_config = config.get("postgres", {})
                return postgres_config.get("mode") == "mock"
    except Exception:
        pass  # Ignore errors in config reading
    
    # Check configuration for postgres mode
    try:
        from netra_backend.app.core.configuration.base import get_unified_config
        config = get_unified_config()
        return getattr(config, 'postgres_mode', '').lower() == 'mock'
    except Exception:
        # Fallback for bootstrap
        return get_env().get("POSTGRES_MODE", "").lower() == "mock"


def _execute_migrations(logger: logging.Logger) -> None:
    """Execute database migrations."""
    try:
        _check_and_run_migrations(logger)
    except Exception as e:
        _handle_migration_error(logger, e)


def _check_and_run_migrations(logger: logging.Logger) -> None:
    """Check and run migrations if needed."""
    logger.info("Checking database migrations...")
    if not validate_database_url(settings.database_url, logger):
        return
    sync_url = get_sync_database_url(settings.database_url)
    _perform_migration(logger, sync_url)


def _perform_migration(logger: logging.Logger, sync_url: str) -> None:
    """Perform the actual migration."""
    current = get_current_revision(sync_url)
    logger.info(f"Current revision: {current}")
    cfg = create_alembic_config(sync_url)
    head = get_head_revision(cfg)
    _execute_if_needed(logger, current, head)


def _execute_if_needed(logger: logging.Logger, current: Optional[str], head: Optional[str]) -> None:
    """Execute migration if needed."""
    log_migration_status(logger, current, head)
    if needs_migration(current, head):
        execute_migration(logger)


def _handle_migration_error(logger: logging.Logger, error: Exception) -> None:
    """Handle migration errors based on environment."""
    logger.error(f"Failed to run migrations: {error}")
    if not should_continue_on_error(settings.environment):
        raise
    logger.warning("Continuing without migrations")


async def setup_database_connections(app: FastAPI) -> None:
    """Setup PostgreSQL connection factory (critical service)."""
    logger = central_logger.get_logger(__name__)
    logger.info("Setting up database connections...")
    config = get_config()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    # Check if database is in mock mode by examining DATABASE_URL or service config
    database_url = config.database_url or ""
    is_mock_database = _is_mock_database_url(database_url) or _is_postgres_service_mock_mode()
    
    if is_mock_database:
        logger.info("PostgreSQL in mock mode - using mock session factory")
        app.state.db_session_factory = None  # Signal to use mock/fallback
        app.state.database_available = False
        app.state.database_mock_mode = True
        return
    
    try:
        logger.debug("Calling initialize_postgres()...")
        async_session_factory = initialize_postgres()
        logger.debug(f"initialize_postgres() returned: {async_session_factory}")
        
        if async_session_factory is None:
            error_msg = "initialize_postgres() returned None - database initialization failed"
            if graceful_startup:
                logger.error(f"{error_msg} - using mock database for graceful degradation")
                app.state.db_session_factory = None  # Signal to use mock/fallback
                app.state.database_available = False
                return
            else:
                raise RuntimeError(error_msg)
        
        # Ensure database tables exist before proceeding
        await _ensure_database_tables_exist(logger, graceful_startup)
            
        app.state.db_session_factory = async_session_factory
        app.state.database_available = True
        logger.info("Database session factory successfully set on app.state")
        
        # Verify it's accessible
        if hasattr(app.state, 'db_session_factory') and app.state.db_session_factory is not None:
            logger.debug("Verified: app.state.db_session_factory is accessible and not None")
        else:
            logger.error("ERROR: app.state.db_session_factory is None after setting!")
            
    except Exception as e:
        if graceful_startup:
            logger.warning(f"Database initialization failed but continuing in graceful mode: {e}")
            app.state.db_session_factory = None
            app.state.database_available = False
        else:
            # Log the error and re-raise to fail startup early
            logger.critical(f"Failed to setup database connections: {e}")
            raise RuntimeError(f"Database initialization failed: {e}") from e


def initialize_core_services(app: FastAPI, logger: logging.Logger) -> KeyManager:
    """Initialize core application services."""
    app.state.redis_manager = redis_manager
    app.state.background_task_manager = BackgroundTaskManager()
    logger.info("Loading key manager...")
    key_manager = KeyManager.load_from_settings(settings)
    logger.info("Key manager loaded.")
    return key_manager


def setup_security_services(app: FastAPI, key_manager: KeyManager) -> None:
    """Setup security and LLM services."""
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)
    app.state.llm_manager = LLMManager(settings)
    app.state.clickhouse_client = None


async def initialize_clickhouse(logger: logging.Logger) -> None:
    """Initialize ClickHouse tables based on service mode (optional service)."""
    config = get_config()
    clickhouse_mode = config.clickhouse_mode.lower()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    if 'pytest' not in sys.modules and clickhouse_mode not in ['disabled', 'mock']:
        try:
            await _setup_clickhouse_tables(logger, clickhouse_mode)
        except Exception as e:
            if graceful_startup:
                logger.warning(f"ClickHouse initialization failed but continuing (optional service): {e}")
                # Set clickhouse to mock mode for graceful degradation
                config.clickhouse_mode = "mock"
            else:
                raise
    else:
        _log_clickhouse_skip(logger, clickhouse_mode)


async def _setup_clickhouse_tables(logger: logging.Logger, mode: str) -> None:
    """Setup ClickHouse tables."""
    from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
    try:
        _log_clickhouse_start(logger, mode)
        await initialize_clickhouse_tables()
        logger.info("ClickHouse tables initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")


def _log_clickhouse_start(logger: logging.Logger, mode: str) -> None:
    """Log ClickHouse initialization start."""
    logger.info(f"Initializing ClickHouse tables (mode: {mode})...")


def _log_clickhouse_skip(logger: logging.Logger, mode: str) -> None:
    """Log ClickHouse initialization skip."""
    if mode == 'disabled':
        logger.info("Skipping ClickHouse initialization (mode: disabled)")
    elif mode == 'mock':
        logger.info("Skipping ClickHouse initialization (mode: mock)")


def register_websocket_handlers(app: FastAPI) -> None:
    """Create tool registry and dispatcher."""
    tool_registry = _create_tool_registry(app)
    app.state.tool_dispatcher = _create_tool_dispatcher(tool_registry)


def _create_tool_registry(app: FastAPI):
    """Create tool registry instance."""
    from netra_backend.app.services.tool_registry import ToolRegistry
    return ToolRegistry(app.state.db_session_factory)


def _create_tool_dispatcher(tool_registry):
    """Create tool dispatcher instance."""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    return ToolDispatcher(tool_registry.get_tools([]))


def _create_agent_supervisor(app: FastAPI) -> None:
    """Create agent supervisor."""
    supervisor = _build_supervisor_agent(app)
    _setup_agent_state(app, supervisor)


def _build_supervisor_agent(app: FastAPI):
    """Build supervisor agent instance."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.websocket_core import get_unified_manager
    websocket_manager = get_unified_manager()
    return SupervisorAgent(
        app.state.db_session_factory, 
        app.state.llm_manager, 
        websocket_manager, 
        app.state.tool_dispatcher
    )


def _setup_agent_state(app: FastAPI, supervisor) -> None:
    """Setup agent state in app."""
    from netra_backend.app.services.agent_service import AgentService
    from netra_backend.app.services.thread_service import ThreadService
    from netra_backend.app.services.corpus_service import CorpusService
    app.state.agent_supervisor = supervisor
    app.state.agent_service = AgentService(supervisor)
    app.state.thread_service = ThreadService()
    app.state.corpus_service = CorpusService()


async def initialize_websocket_components(logger: logging.Logger) -> None:
    """Initialize WebSocket components that require async context (optional service)."""
    config = get_config()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    try:
        from netra_backend.app.websocket_core import (
            get_websocket_manager,
            WebSocketManager,
        )
        # Get the consolidated WebSocket manager instance
        manager = get_websocket_manager()
        
        # Initialize if the manager has an initialize method
        if hasattr(manager, 'initialize'):
            await manager.initialize()
        
        logger.info("WebSocket components initialized")
    except Exception as e:
        if graceful_startup:
            logger.warning(f"WebSocket components initialization failed but continuing (optional service): {e}")
        else:
            logger.error(f"Failed to initialize WebSocket components: {e}")
            raise


async def startup_health_checks(app: FastAPI, logger: logging.Logger) -> None:
    """Run application startup checks (graceful failure handling)."""
    config = get_config()
    disable_checks = config.disable_startup_checks.lower() == "true"
    fast_startup = config.fast_startup_mode.lower() == "true"
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    if disable_checks or fast_startup:
        logger.info("Skipping startup health checks (fast startup mode)")
        return
    
    logger.info("Starting comprehensive startup health checks...")
    from netra_backend.app.startup_checks import run_startup_checks
    try:
        logger.debug("Calling run_startup_checks...")
        results = await run_startup_checks(app)
        passed = results.get('passed', 0)
        total = results.get('total_checks', 0)
        logger.info(f"Startup checks completed: {passed}/{total} passed")
        
        # In graceful mode, continue even if some non-critical checks fail
        if graceful_startup and passed < total:
            failed = total - passed
            logger.warning(f"Some startup checks failed ({failed}), but continuing in graceful mode")
        elif passed < total:
            raise RuntimeError(f"Critical startup checks failed: {failed} of {total}")
            
    except Exception as e:
        if graceful_startup:
            logger.warning(f"Startup health checks had issues but continuing in graceful mode: {e}")
        else:
            logger.error(f"Startup health checks failed with exception: {e}")
            await _handle_startup_failure(logger, e)


async def _handle_startup_failure(logger: logging.Logger, error: Exception) -> None:
    """Handle startup check failures."""
    logger.critical(f"CRITICAL: Startup checks failed: {error}")
    logger.info("Application shutting down due to startup failure.")
    await _emergency_cleanup(logger)
    raise RuntimeError(f"Application startup failed: {error}")


async def _emergency_cleanup(logger: logging.Logger) -> None:
    """Perform emergency cleanup on startup failure."""
    from netra_backend.app.utils.multiprocessing_cleanup import cleanup_multiprocessing
    try:
        await _cleanup_connections()
        cleanup_multiprocessing()
        await central_logger.shutdown()
    except Exception as cleanup_error:
        logger.error(f"Error during cleanup: {cleanup_error}")


async def _cleanup_connections() -> None:
    """Cleanup Redis connections."""
    await redis_manager.disconnect()


async def validate_schema(logger: logging.Logger) -> None:
    """Perform comprehensive schema validation."""
    from netra_backend.app.db.postgres import initialize_postgres
    from netra_backend.app.db.postgres_core import async_engine
    from netra_backend.app.services.schema_validation_service import (
        run_comprehensive_validation,
    )
    if "pytest" not in sys.modules:
        # Ensure database is initialized before validation
        initialize_postgres()
        if async_engine is None:
            logger.warning("Database engine not initialized, skipping schema validation")
            return
        validation_passed = await run_comprehensive_validation(async_engine)
        _handle_schema_validation_result(logger, validation_passed)


def _handle_schema_validation_result(logger: logging.Logger, passed: bool) -> None:
    """Handle schema validation results."""
    if not passed:
        if settings.environment == "production":
            logger.critical("Schema validation failed in production. Shutting down.")
            os._exit(1)
        else:
            logger.error("Schema validation failed. The application might not work as expected.")


async def start_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Start comprehensive performance monitoring (optional service)."""
    config = get_config()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    if 'pytest' not in sys.modules:
        try:
            await _create_monitoring_task(app, logger)
            await _initialize_performance_optimizations(app, logger)
        except Exception as e:
            if graceful_startup:
                logger.warning(f"Monitoring and optimizations failed to start but continuing (optional service): {e}")
            else:
                logger.error(f"Failed to start monitoring and optimizations: {e}")
                raise


async def _create_monitoring_task(app: FastAPI, logger: logging.Logger) -> None:
    """Create comprehensive monitoring tasks."""
    await _start_connection_monitoring(app)
    await _start_performance_monitoring(app)
    logger.info("Comprehensive monitoring started")


async def _start_connection_monitoring(app: FastAPI) -> None:
    """Start database connection monitoring."""
    from netra_backend.app.services.database.connection_monitor import (
        start_connection_monitoring,
    )
    await start_connection_monitoring()
    # Monitoring task is now created internally in health_checker


async def _start_performance_monitoring(app: FastAPI) -> None:
    """Start performance monitoring."""
    await performance_monitor.start_monitoring()
    app.state.performance_monitor = performance_monitor


def log_startup_complete(start_time: float, logger: logging.Logger) -> None:
    """Log startup completion with timing."""
    elapsed_time = time.time() - start_time
    logger.info(f"System Ready (Took {elapsed_time:.2f}s).")


async def _run_startup_phase_one(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run initial startup phase."""
    start_time, logger = initialize_logging()
    setup_multiprocessing_env(logger)
    validate_database_environment(logger)
    run_database_migrations(logger)
    return start_time, logger


async def _run_startup_phase_two(app: FastAPI, logger: logging.Logger) -> None:
    """Run service initialization phase."""
    await setup_database_connections(app)  # Move database setup first
    key_manager = initialize_core_services(app, logger)
    setup_security_services(app, key_manager)
    await initialize_clickhouse(logger)
    
    # FIX: Initialize background task manager to prevent 4-minute crash
    logger.info("Initializing background task manager with 2-minute timeout...")
    app.state.background_task_manager = background_task_manager
    logger.info("Background task manager initialized successfully")
    
    # FIX: Apply all startup fixes for critical cold start issues
    logger.info("Applying startup fixes for critical cold start issues...")
    try:
        fix_results = await startup_fixes.run_comprehensive_verification()
        applied_fixes = fix_results.get('total_fixes', 0)
        logger.info(f"Startup fixes applied: {applied_fixes}/5 fixes")
        
        if applied_fixes < 5:
            logger.warning("Some startup fixes could not be applied - check system configuration")
            logger.info(startup_fixes.get_fix_status_summary())
        else:
            logger.info("All critical startup fixes successfully applied")
            
    except Exception as e:
        logger.error(f"Error applying startup fixes: {e}")
        logger.warning("Continuing startup despite fix application errors")


async def _run_startup_phase_three(app: FastAPI, logger: logging.Logger) -> None:
    """Run validation and setup phase."""
    await startup_health_checks(app, logger)
    await validate_schema(logger)
    register_websocket_handlers(app)
    await initialize_websocket_components(logger)
    _create_agent_supervisor(app)
    await start_monitoring(app, logger)


async def run_complete_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run complete startup sequence with improved initialization handling."""
    # Use the global startup manager instance
    
    # Check if we should use the new robust startup system
    config = get_config()
    use_robust_startup = getattr(config, 'use_robust_startup', 'true').lower() == 'true'
    
    if use_robust_startup:
        # Use the new robust startup system with dependency resolution
        logger = central_logger.get_logger(__name__)
        logger.info("Using robust startup manager with dependency resolution...")
        
        try:
            # Set startup in progress flags at the beginning
            start_time = time.time()
            app.state.startup_complete = False
            app.state.startup_in_progress = True
            app.state.startup_failed = False
            app.state.startup_error = None
            app.state.startup_start_time = start_time
            logger.info("Startup in progress flags set - health endpoint will report startup in progress")
            
            # Initialize the startup manager and run the startup sequence
            success = await startup_manager.initialize_system(app)
            
            if not success:
                logger.error("Startup manager reported initialization failure")
                # Set startup failure flags
                app.state.startup_complete = False
                app.state.startup_in_progress = False
                app.state.startup_failed = True
                app.state.startup_error = "Robust startup manager initialization failed"
                # Fall back to legacy startup if robust startup fails
                logger.warning("Falling back to legacy startup sequence...")
                return await _run_legacy_startup(app)
            
            # Store the startup manager in app state for health monitoring
            app.state.startup_manager = startup_manager
            
            # CRITICAL: Set startup_complete flag for health endpoint
            app.state.startup_complete = True
            app.state.startup_in_progress = False
            app.state.startup_failed = False
            app.state.startup_error = None
            logger.info("Startup completion flags set - health endpoint will report healthy")
            
            log_startup_complete(start_time, logger)
            return start_time, logger
            
        except Exception as e:
            logger.error(f"Error in robust startup: {e}")
            # Set startup failure flags
            app.state.startup_complete = False
            app.state.startup_in_progress = False
            app.state.startup_failed = True
            app.state.startup_error = f"Robust startup exception: {str(e)}"
            logger.warning("Falling back to legacy startup sequence...")
            return await _run_legacy_startup(app)
    else:
        # Use the legacy startup sequence
        return await _run_legacy_startup(app)


async def _run_legacy_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run legacy startup sequence (fallback)."""
    start_time, logger = await _run_startup_phase_one(app)
    
    # Set startup in progress flags if not already set
    if not hasattr(app.state, 'startup_in_progress') or not app.state.startup_in_progress:
        app.state.startup_complete = False
        app.state.startup_in_progress = True
        app.state.startup_failed = False
        app.state.startup_error = None
        app.state.startup_start_time = start_time
        logger.info("Legacy startup in progress flags set")
    await _run_startup_phase_two(app, logger)
    await _run_startup_phase_three(app, logger)
    
    # CRITICAL: Set startup_complete flag for health endpoint
    app.state.startup_complete = True
    app.state.startup_in_progress = False
    app.state.startup_failed = False
    app.state.startup_error = None
    logger.info("Legacy startup completion flags set - health endpoint will report healthy")
    
    log_startup_complete(start_time, logger)
    return start_time, logger