from shared.isolated_environment import get_env
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
from netra_backend.app.core.project_utils import get_project_root as _get_project_root
from typing import Optional, Tuple

from fastapi import FastAPI

from netra_backend.app.agents.base.monitoring import performance_monitor
from netra_backend.app.services.background_task_manager import BackgroundTaskManager
from netra_backend.app.config import get_config, settings
from netra_backend.app.services.background_task_manager import background_task_manager
from netra_backend.app.services.startup_fixes_integration import startup_fixes
from netra_backend.app.core.performance_optimization_manager import performance_manager
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


# SSOT compliance: _get_project_root now imported from netra_backend.app.core.project_utils

async def _ensure_database_tables_exist(logger: logging.Logger, graceful_startup: bool = True) -> None:
    """Ensure all required database tables exist, creating them if necessary."""
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.db.base import Base
        from sqlalchemy import text
        import asyncio
        
        # Import all model classes to ensure they're registered with Base.metadata
        logger.debug("Importing database models to register tables...")
        _import_all_models()
        
        logger.debug("Checking if database tables exist...")
        
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
                logger.debug("Creating missing database tables automatically...")
                
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
                    logger.debug(f"Successfully created {len(missing_tables)} missing database tables")
            else:
                logger.debug(f"All {len(expected_tables)} database tables are present")
        
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
        logger.debug("Performance optimizations initialized successfully")
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
    from shared.isolated_environment import get_env
    
    # Check if background tasks are disabled for testing
    if get_env().get("DISABLE_BACKGROUND_TASKS", "false").lower() == "true":
        logger.debug("Background tasks disabled for testing environment")
        return
    
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
        logger.debug(f"Database index optimization scheduled as background task (ID: {task_id})")


async def _run_index_optimization_background(logger: logging.Logger) -> None:
    """Run database index optimization in background."""
    try:
        # Extended delay to minimize startup performance impact
        await asyncio.sleep(60)  # Wait 60 seconds after startup for better performance
        logger.debug("Starting background database index optimization...")
        
        # Reduced timeout for faster failure detection
        optimization_results = await asyncio.wait_for(
            index_manager.optimize_all_databases(), 
            timeout=90.0  # 90 second timeout for better performance
        )
        logger.debug(f"Background database optimization completed successfully: {optimization_results}")
    except asyncio.TimeoutError:
        logger.warning("Background index optimization timed out after 90 seconds - will retry later")
        # Schedule retry after additional delay
        await asyncio.sleep(300)  # Wait 5 minutes before potential retry
        try:
            logger.debug("Retrying background database optimization...")
            optimization_results = await asyncio.wait_for(
                index_manager.optimize_all_databases(),
                timeout=60.0  # Shorter timeout for retry
            )
            logger.debug(f"Background database optimization retry succeeded: {optimization_results}")
        except Exception as retry_error:
            logger.error(f"Background index optimization retry failed: {retry_error}")
    except Exception as e:
        logger.error(f"Background index optimization failed: {e}")
        # Continue running - don't let this crash the application


def initialize_logging() -> Tuple[float, logging.Logger]:
    """Initialize startup logging and timing."""
    start_time = time.time()
    logger = central_logger.get_logger(__name__)
    logger.info("Starting Netra Backend...")
    return start_time, logger


def setup_multiprocessing_env(logger: logging.Logger) -> None:
    """Setup multiprocessing environment."""
    setup_multiprocessing()
    if 'pytest' in sys.modules:
        logger.debug("pytest detected in sys.modules")


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
        logger.debug("Skipping database migrations (PostgreSQL in mock mode)")
        return
    
    if 'pytest' not in sys.modules and not fast_startup and not skip_migrations:
        _execute_migrations(logger)
    elif fast_startup or skip_migrations:
        logger.debug("Skipping database migrations (fast startup mode)")


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
    logger.debug("Checking database migrations...")
    if not validate_database_url(settings.database_url, logger):
        return
    sync_url = get_sync_database_url(settings.database_url)
    _perform_migration(logger, sync_url)


def _perform_migration(logger: logging.Logger, sync_url: str) -> None:
    """Perform the actual migration."""
    current = get_current_revision(sync_url)
    logger.debug(f"Current revision: {current}")
    cfg = create_alembic_config(sync_url)
    head = get_head_revision(cfg)
    _execute_if_needed(logger, current, head)


def _execute_if_needed(logger: logging.Logger, current: Optional[str], head: Optional[str]) -> None:
    """Execute migration if needed with idempotent handling."""
    log_migration_status(logger, current, head)
    if needs_migration(current, head):
        try:
            execute_migration(logger)
        except Exception as e:
            # CRITICAL FIX: Handle DuplicateTable errors gracefully for idempotent migrations
            error_msg = str(e)
            if any(keyword in error_msg.lower() for keyword in ['already exists', 'duplicatetable', 'relation']):
                logger.warning(f"Tables already exist during migration: {e}")
                logger.debug("Attempting to stamp database to current head revision...")
                
                # Try to stamp the database to the current head
                try:
                    import alembic.config
                    
                    config = get_config()
                    sync_url = get_sync_database_url(config.database_url)
                    alembic_ini_path = Path(__file__).parent.parent.parent.parent / "config" / "alembic.ini"
                    
                    alembic.config.main(argv=["-c", str(alembic_ini_path), "--raiseerr", "stamp", "head"])
                    logger.debug("Successfully stamped database to current head revision")
                except Exception as stamp_error:
                    logger.error(f"Failed to stamp database: {stamp_error}")
                    if should_continue_on_error(settings.environment):
                        logger.warning("Continuing despite migration/stamp failure")
                    else:
                        raise stamp_error
            else:
                # Re-raise non-table-existence errors
                raise e


def _handle_migration_error(logger: logging.Logger, error: Exception) -> None:
    """Handle migration errors based on environment."""
    logger.error(f"Failed to run migrations: {error}")
    if not should_continue_on_error(settings.environment):
        raise
    logger.warning("Continuing without migrations")


async def _async_initialize_postgres(logger: logging.Logger):
    """Async wrapper for postgres initialization to enable timeout protection."""
    try:
        # Run postgres initialization in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        async_session_factory = await loop.run_in_executor(
            None,
            initialize_postgres
        )
        return async_session_factory
    except Exception as e:
        logger.error(f"Error in async postgres initialization: {e}")
        return None


async def setup_database_connections(app: FastAPI) -> None:
    """Setup PostgreSQL connection factory (critical service) with timeout protection."""
    logger = central_logger.get_logger(__name__)
    logger.debug("Setting up database connections...")
    config = get_config()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    # Check if database is in mock mode by examining DATABASE_URL or service config
    database_url = config.database_url or ""
    is_mock_database = _is_mock_database_url(database_url) or _is_postgres_service_mock_mode()
    
    if is_mock_database:
        logger.debug("PostgreSQL in mock mode - using mock session factory")
        app.state.db_session_factory = None  # Signal to use mock/fallback
        app.state.database_available = False
        app.state.database_mock_mode = True
        return
    
    # CRITICAL FIX: Wrap database initialization in timeout to prevent server startup hanging
    try:
        logger.debug("Calling initialize_postgres() with 15s timeout...")
        async_session_factory = await asyncio.wait_for(
            asyncio.create_task(_async_initialize_postgres(logger)),
            timeout=15.0
        )
        logger.debug(f"initialize_postgres() returned: {async_session_factory}")
        
        if async_session_factory is None:
            error_msg = "initialize_postgres() returned None - database initialization failed"
            if graceful_startup:
                logger.error(f"{error_msg} - using mock database for graceful degradation")
                app.state.db_session_factory = None  # Signal to use mock/fallback
                app.state.database_available = False
                app.state.database_mock_mode = True
                return
            else:
                raise RuntimeError(error_msg)
        
        # Ensure database tables exist with timeout protection
        logger.debug("Ensuring database tables exist with 10s timeout...")
        await asyncio.wait_for(
            _ensure_database_tables_exist(logger, graceful_startup),
            timeout=10.0
        )
            
        app.state.db_session_factory = async_session_factory
        app.state.database_available = True
        logger.debug("Database session factory successfully set on app.state")
        
        # Verify it's accessible
        if hasattr(app.state, 'db_session_factory') and app.state.db_session_factory is not None:
            logger.debug("Verified: app.state.db_session_factory is accessible and not None")
        else:
            logger.error("ERROR: app.state.db_session_factory is None after setting!")
            
    except asyncio.TimeoutError:
        # CRITICAL FIX: Handle database timeout gracefully to prevent server startup hanging
        timeout_msg = "Database initialization timed out - continuing in graceful mode"
        logger.error(timeout_msg)
        if graceful_startup:
            logger.warning("Database timeout - using mock mode for graceful degradation")
            app.state.db_session_factory = None
            app.state.database_available = False
            app.state.database_mock_mode = True
        else:
            raise RuntimeError("Database initialization timed out and graceful mode disabled") from None
            
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
    logger.debug("Loading key manager...")
    key_manager = KeyManager.load_from_settings(settings)
    logger.debug("Key manager loaded.")
    return key_manager


def setup_security_services(app: FastAPI, key_manager: KeyManager) -> None:
    """Setup security and LLM services."""
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)
    app.state.llm_manager = LLMManager(settings)
    
    # CRITICAL FIX: Set ClickHouse availability flag based on configuration
    config = get_config()
    from shared.isolated_environment import get_env
    clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
    
    # ClickHouse is available if required or if not in staging/development
    clickhouse_available = clickhouse_required or config.environment not in ["staging", "development"]
    app.state.clickhouse_available = clickhouse_available
    app.state.clickhouse_client = None  # Will be initialized on-demand


async def initialize_clickhouse(logger: logging.Logger) -> None:
    """Initialize ClickHouse tables based on service mode (optional service)."""
    config = get_config()
    clickhouse_mode = config.clickhouse_mode.lower()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    # CRITICAL FIX: Check if ClickHouse is explicitly required
    from shared.isolated_environment import get_env
    clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
    
    # CRITICAL FIX: Make ClickHouse optional in development when not explicitly required
    if config.environment == "development" and not clickhouse_required:
        logger.debug(f"ClickHouse not required in {config.environment} environment - skipping initialization")
        return
    elif config.environment == "staging":
        logger.debug(f"ClickHouse initialization required in {config.environment} environment")
        # Proceed with real connection for staging
    
    if 'pytest' not in sys.modules and clickhouse_mode not in ['disabled', 'mock']:
        try:
            # CRITICAL FIX: Reduce timeout for faster startup failure in optional environments
            timeout = 10.0 if config.environment in ["staging", "development"] else 30.0
            
            await asyncio.wait_for(
                _setup_clickhouse_tables(logger, clickhouse_mode),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            timeout_msg = f"ClickHouse initialization timed out after {timeout} seconds"
            logger.error(timeout_msg)
            
            # NO MOCKS IN DEV/STAGING - fail fast
            if config.environment in ["development", "staging"]:
                raise RuntimeError(f"{timeout_msg}. ClickHouse is required in {config.environment} mode.")
            elif graceful_startup or not clickhouse_required:
                logger.warning(f"{timeout_msg} - continuing without ClickHouse (optional service)")
                # Only allow mock in test environment, not dev
                if config.environment == "testing":
                    config.clickhouse_mode = "mock"
            else:
                raise RuntimeError(timeout_msg)
                
        except Exception as e:
            # Enhanced error handling for common ClickHouse connection issues
            error_msg = str(e).lower()
            is_connection_error = any(keyword in error_msg for keyword in [
                'connection', 'refused', 'timeout', 'unreachable', 'network', 'dns', 'httpsconnectionpool'
            ])
            
            # NO MOCKS IN DEV/STAGING - fail fast
            if config.environment in ["development", "staging"]:
                raise RuntimeError(f"ClickHouse initialization failed in {config.environment}: {e}. ClickHouse is required in {config.environment} mode.") from e
            elif (is_connection_error or graceful_startup) and not clickhouse_required:
                logger.warning(f"ClickHouse connection/initialization failed but continuing (optional service): {e}")
                # Only allow mock in test environment, not dev
                if config.environment == "testing":
                    config.clickhouse_mode = "mock"
            elif graceful_startup and not clickhouse_required:
                logger.warning(f"ClickHouse initialization failed but continuing (optional service): {e}")
                # Only allow mock in test environment, not dev
                if config.environment == "testing":
                    config.clickhouse_mode = "mock"
            else:
                raise RuntimeError(f"ClickHouse initialization failed: {e}") from e
    else:
        _log_clickhouse_skip(logger, clickhouse_mode)


async def _setup_clickhouse_tables(logger: logging.Logger, mode: str) -> None:
    """Setup ClickHouse tables with timeout and error handling."""
    import asyncio
    from shared.isolated_environment import get_env
    
    try:
        _log_clickhouse_start(logger, mode)
        
        # CRITICAL FIX: Add timeout protection for table initialization
        environment = get_env().get("ENVIRONMENT", "development").lower()
        init_timeout = 8.0 if environment in ["staging", "development"] else 20.0
        
        from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
        
        await asyncio.wait_for(
            initialize_clickhouse_tables(), 
            timeout=init_timeout
        )
        
        logger.debug("ClickHouse tables initialization complete")
        
    except asyncio.TimeoutError as e:
        logger.error(f"ClickHouse table initialization timed out after {init_timeout}s")
        raise ConnectionError(f"ClickHouse table initialization timeout") from e
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")
        raise


def _log_clickhouse_start(logger: logging.Logger, mode: str) -> None:
    """Log ClickHouse initialization start."""
    logger.debug(f"Initializing ClickHouse tables (mode: {mode})...")


def _log_clickhouse_skip(logger: logging.Logger, mode: str) -> None:
    """Log ClickHouse initialization skip."""
    if mode == 'disabled':
        logger.debug("Skipping ClickHouse initialization (mode: disabled)")
    elif mode == 'mock':
        logger.debug("Skipping ClickHouse initialization (mode: mock)")


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
    """Create agent supervisor - CRITICAL for chat functionality."""
    from netra_backend.app.logging_config import central_logger
    from shared.isolated_environment import get_env
    logger = central_logger.get_logger(__name__)
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    
    try:
        logger.debug(f"Creating agent supervisor for {environment} environment...")
        supervisor = _build_supervisor_agent(app)
        
        # Verify supervisor was created properly
        if supervisor is None:
            raise RuntimeError("Supervisor creation returned None")
        
        # CRITICAL: Ensure WebSocket enhancement for agent events
        if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'tool_dispatcher'):
            if not getattr(supervisor.registry.tool_dispatcher, '_websocket_enhanced', False):
                logger.warning("Tool dispatcher not enhanced with WebSocket - attempting enhancement")
                # Try to enhance it now
                from netra_backend.app.websocket_core import get_websocket_manager
                ws_manager = get_websocket_manager()
                if ws_manager:
                    supervisor.registry.set_websocket_manager(ws_manager)
                    if not getattr(supervisor.registry.tool_dispatcher, '_websocket_enhanced', False):
                        raise RuntimeError("Failed to enhance tool dispatcher with WebSocket notifications")
        
        _setup_agent_state(app, supervisor)
        
        # Final verification
        if not hasattr(app.state, 'agent_supervisor') or app.state.agent_supervisor is None:
            raise RuntimeError("Agent supervisor not set on app.state after setup")
        
        if not hasattr(app.state, 'thread_service') or app.state.thread_service is None:
            raise RuntimeError("Thread service not set on app.state after setup")
        
        logger.debug(f"Agent supervisor created successfully for {environment}")
        logger.debug(f"WebSocket enhancement status: {getattr(supervisor.registry.tool_dispatcher, '_websocket_enhanced', False) if hasattr(supervisor, 'registry') else 'N/A'}")
        
    except Exception as e:
        error_msg = f"Failed to create agent supervisor in {environment}: {e}"
        logger.error(error_msg, exc_info=True)
        
        # CRITICAL FIX: Agent supervisor is REQUIRED for chat functionality
        # Chat is king - we MUST fail fast if agent services cannot be initialized
        if environment in ["staging", "production"]:
            logger.critical(f"CRITICAL: Agent supervisor failed in {environment} - chat functionality broken!")
            logger.critical("Chat delivers 90% of value - failing startup to prevent broken user experience")
            # Re-raise to fail startup - chat MUST work
            raise RuntimeError(f"Agent supervisor initialization failed in {environment} - chat is broken") from e
        else:
            # In development/testing, still try to continue for debugging
            app.state.agent_supervisor = None
            app.state.thread_service = None
            logger.warning(f"Agent supervisor set to None for {environment} after failure - chat will not work!")
            # Don't raise in dev to allow debugging


def _build_supervisor_agent(app: FastAPI):
    """Build supervisor agent instance."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.websocket_core import get_websocket_manager
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    # Log current app.state attributes for debugging
    logger.debug("Checking supervisor dependencies in app.state...")
    app_state_attrs = [attr for attr in dir(app.state) if not attr.startswith('_')]
    logger.debug(f"Current app.state attributes: {app_state_attrs}")
    
    # Check required dependencies
    required_attrs = ['db_session_factory', 'llm_manager', 'tool_dispatcher']
    missing = [attr for attr in required_attrs if not hasattr(app.state, attr)]
    
    if missing:
        logger.error(f"Missing required app state attributes for supervisor: {missing}")
        # Log detailed state of each required attribute
        for attr in required_attrs:
            if hasattr(app.state, attr):
                value = getattr(app.state, attr)
                logger.debug(f"  {attr}: {value is not None} (type: {type(value).__name__})")
            else:
                logger.error(f"  {attr}: NOT SET")
        raise RuntimeError(f"Cannot create supervisor - missing dependencies: {missing}")
    
    websocket_manager = get_websocket_manager()
    logger.debug(f"Creating supervisor with dependencies: db_session_factory={app.state.db_session_factory}, llm_manager={app.state.llm_manager}, tool_dispatcher={app.state.tool_dispatcher}")
    
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
        
        logger.debug("WebSocket components initialized")
    except Exception as e:
        if graceful_startup:
            logger.warning(f"WebSocket components initialization failed but continuing (optional service): {e}")
        else:
            logger.error(f"Failed to initialize WebSocket components: {e}")
            raise


async def startup_health_checks(app: FastAPI, logger: logging.Logger) -> None:
    """Run application startup checks with timeout protection (graceful failure handling)."""
    config = get_config()
    disable_checks = config.disable_startup_checks.lower() == "true"
    fast_startup = config.fast_startup_mode.lower() == "true"
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    if disable_checks or fast_startup:
        logger.debug("Skipping startup health checks (fast startup mode)")
        return
    
    logger.debug("Starting comprehensive startup health checks...")
    from netra_backend.app.startup_checks import run_startup_checks
    try:
        logger.debug("Calling run_startup_checks() with 20s timeout...")
        # CRITICAL FIX: Add timeout to prevent startup health checks from hanging server startup
        results = await asyncio.wait_for(
            run_startup_checks(app),
            timeout=20.0
        )
        passed = results.get('passed', 0)
        total = results.get('total_checks', 0)
        logger.debug(f"Startup checks completed: {passed}/{total} passed")
        
        # In graceful mode, continue even if some non-critical checks fail
        if graceful_startup and passed < total:
            failed = total - passed
            logger.warning(f"Some startup checks failed ({failed}), but continuing in graceful mode")
        elif passed < total:
            raise RuntimeError(f"Critical startup checks failed: {failed} of {total}")
            
    except asyncio.TimeoutError:
        # CRITICAL FIX: Handle startup check timeout gracefully
        timeout_msg = "Startup health checks timed out after 20s"
        logger.error(timeout_msg)
        if graceful_startup:
            logger.warning("Startup checks timeout - continuing in graceful mode")
        else:
            logger.error("Startup checks timeout and graceful mode disabled")
            await _handle_startup_failure(logger, RuntimeError(timeout_msg))
            
    except Exception as e:
        if graceful_startup:
            logger.warning(f"Startup health checks had issues but continuing in graceful mode: {e}")
        else:
            logger.error(f"Startup health checks failed with exception: {e}")
            await _handle_startup_failure(logger, e)


async def _handle_startup_failure(logger: logging.Logger, error: Exception) -> None:
    """Handle startup check failures."""
    logger.critical(f"CRITICAL: Startup checks failed: {error}")
    logger.error("Application shutting down due to startup failure.")
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
    from shared.isolated_environment import get_env
    
    # Check if monitoring is disabled for testing
    if get_env().get("DISABLE_MONITORING", "false").lower() == "true":
        logger.debug("Monitoring disabled for testing environment")
        return
    
    await _start_connection_monitoring(app)
    await _start_performance_monitoring(app)
    logger.debug("Comprehensive monitoring started")


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
    logger.info(f"✓ Netra Backend Ready ({elapsed_time:.2f}s)")


async def _deprecated_run_startup_phase_one(app: FastAPI) -> Tuple[float, logging.Logger]:
    """DEPRECATED - Run initial startup phase."""
    start_time, logger = initialize_logging()
    setup_multiprocessing_env(logger)
    validate_database_environment(logger)
    run_database_migrations(logger)
    return start_time, logger


async def _deprecated_run_startup_phase_two(app: FastAPI, logger: logging.Logger) -> None:
    """DEPRECATED - Run service initialization phase."""
    logger.debug("Starting Phase 2: Service initialization")
    
    try:
        logger.debug("Setting up database connections...")
        await setup_database_connections(app)  # Move database setup first
        logger.debug("Database connections established successfully")
    except Exception as e:
        logger.error(f"Failed to setup database connections: {e}", exc_info=True)
        raise
    
    try:
        logger.debug("Initializing core services...")
        key_manager = initialize_core_services(app, logger)
        logger.debug("Core services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize core services: {e}", exc_info=True)
        raise
    
    try:
        logger.debug("Setting up security services and LLM manager...")
        setup_security_services(app, key_manager)
        logger.debug(f"Security services initialized - LLM manager: {app.state.llm_manager is not None}")
    except Exception as e:
        logger.error(f"Failed to setup security services: {e}", exc_info=True)
        raise
    
    try:
        logger.debug("Initializing ClickHouse...")
        await initialize_clickhouse(logger)
        logger.debug("ClickHouse initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse: {e}", exc_info=True)
        # ClickHouse failures are non-critical in some environments
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        if environment not in ["staging", "production"]:
            logger.warning(f"Continuing without ClickHouse in {environment}")
        else:
            raise
    
    # FIX: Initialize background task manager to prevent 4-minute crash
    logger.debug("Initializing background task manager...")
    app.state.background_task_manager = background_task_manager
    logger.debug("Background task manager initialized")
    
    # FIX: Apply all startup fixes for critical cold start issues
    logger.debug("Applying startup fixes...")
    try:
        fix_results = await startup_fixes.run_comprehensive_verification()
        applied_fixes = fix_results.get('total_fixes', 0)
        logger.debug(f"Startup fixes applied: {applied_fixes}/5 fixes")
        
        if applied_fixes < 5:
            logger.warning("Some startup fixes could not be applied - check system configuration")
            logger.debug(startup_fixes.get_fix_status_summary())
        else:
            logger.debug("All critical startup fixes successfully applied")
            
    except Exception as e:
        logger.error(f"Error applying startup fixes: {e}")
        logger.warning("Continuing startup despite fix application errors")


async def _deprecated_run_startup_phase_three(app: FastAPI, logger: logging.Logger) -> None:
    """DEPRECATED - Run validation and setup phase."""
    await startup_health_checks(app, logger)
    await validate_schema(logger)
    register_websocket_handlers(app)
    await initialize_websocket_components(logger)
    _create_agent_supervisor(app)
    await start_monitoring(app, logger)


async def run_complete_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run complete startup sequence - DETERMINISTIC MODE ONLY.
    
    This is the SSOT for startup. NO FALLBACKS, NO GRACEFUL DEGRADATION.
    If chat cannot work, the service MUST NOT start.
    """
    # ALWAYS use deterministic startup - this is the SSOT
    from netra_backend.app.startup_module_deterministic import run_deterministic_startup
    return await run_deterministic_startup(app)


# LEGACY CODE BELOW - DEPRECATED AND WILL BE REMOVED
# Only kept temporarily for reference during transition
# DO NOT USE - ALWAYS USE run_complete_startup() ABOVE

async def _deprecated_legacy_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """DEPRECATED - Legacy startup code. DO NOT USE."""
    # Initialize logger FIRST - before any logic to ensure it's always available in all scopes
    logger = None
    try:
        logger = central_logger.get_logger(__name__)
    except Exception as e:
        # Fallback logger initialization if central_logger fails
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize central logger, using fallback: {e}")
    
    # CRITICAL: Validate environment configuration FIRST before any other initialization
    # This ensures test flags never leak into production/staging
    try:
        from netra_backend.app.core.environment_validator import validate_environment_at_startup
        logger.debug("Validating environment configuration...")
        validate_environment_at_startup()
        logger.debug("Environment validation passed")
    except EnvironmentError as e:
        # Critical environment violation - fail fast
        logger.critical(f"Environment validation failed: {e}")
        # Set failure state before raising
        app.state.startup_complete = False
        app.state.startup_in_progress = False
        app.state.startup_failed = True
        app.state.startup_error = str(e)
        raise  # Re-raise to stop startup
    except Exception as e:
        # Non-critical validation error - log but continue
        logger.warning(f"Environment validation warning: {e}")
    
    # Check if we should use the new robust startup system
    config = get_config()
    use_robust_startup = getattr(config, 'use_robust_startup', 'true').lower() == 'true'
    
    if use_robust_startup:
        # Use the new robust startup system with dependency resolution
        logger.debug("Using robust startup manager with dependency resolution...")
        
        try:
            # Set startup in progress flags at the beginning
            start_time = time.time()
            app.state.startup_complete = False
            app.state.startup_in_progress = True
            app.state.startup_failed = False
            app.state.startup_error = None
            app.state.startup_start_time = start_time
            logger.debug("Startup in progress flags set")
            
            # DEPRECATED - Robust startup manager removed - use deterministic only
            logger.error("Robust startup manager has been removed - using deterministic startup")
            from netra_backend.app.startup_module_deterministic import run_deterministic_startup
            return await run_deterministic_startup(app)
            
            # CRITICAL: Set startup_complete flag for health endpoint
            app.state.startup_complete = True
            app.state.startup_in_progress = False
            app.state.startup_failed = False
            app.state.startup_error = None
            logger.debug("Startup completion flags set")
            
            log_startup_complete(start_time, logger)
            return start_time, logger
            
        except Exception as e:
            # Use central_logger directly in exception handler to avoid scope issues
            error_logger = central_logger.get_logger(__name__)
            error_logger.error(f"Error in robust startup: {e}")
            # Set startup failure flags
            app.state.startup_complete = False
            app.state.startup_in_progress = False
            app.state.startup_failed = True
            app.state.startup_error = f"Robust startup exception: {str(e)}"
            error_logger.warning("Falling back to legacy startup sequence...")
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
        logger.debug("Legacy startup in progress flags set")
    
    try:
        await _run_startup_phase_two(app, logger)
        logger.debug("Phase 2 completed - core services initialized")
    except Exception as e:
        error_msg = f"Phase 2 (service initialization) failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Check environment for critical failure handling
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        if environment in ["staging", "production"]:
            # In staging/production, Phase 2 failure is critical
            app.state.startup_complete = False
            app.state.startup_in_progress = False
            app.state.startup_failed = True
            app.state.startup_error = error_msg
            raise RuntimeError(error_msg) from e
        else:
            # In development, log but continue with degraded functionality
            logger.warning(f"Continuing with degraded functionality in {environment} after Phase 2 failure")
            # Set minimal state to prevent complete failure
            if not hasattr(app.state, 'llm_manager'):
                app.state.llm_manager = None
            if not hasattr(app.state, 'db_session_factory'):
                app.state.db_session_factory = None
    
    try:
        await _run_startup_phase_three(app, logger)
        logger.debug("Phase 3 completed - agent supervisor initialized")
    except Exception as e:
        error_msg = f"Phase 3 (agent supervisor) failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Check environment for critical failure handling
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        if environment in ["staging", "production"]:
            # CRITICAL FIX: Phase 3 failure is CRITICAL - chat is broken
            # Chat delivers 90% of value - we cannot run without it
            logger.critical(f"CRITICAL: Phase 3 failure in {environment} - CHAT IS BROKEN!")
            logger.critical("Cannot continue without agent supervisor - chat delivers 90% of value")
            # Mark as failed and re-raise
            app.state.startup_complete = False
            app.state.startup_in_progress = False
            app.state.startup_failed = True
            app.state.startup_error = error_msg
            # Re-raise to fail startup - chat MUST work
            raise RuntimeError(f"Phase 3 critical failure in {environment} - chat is broken") from e
        else:
            # In development, log but continue for debugging
            logger.warning(f"Continuing with broken chat in {environment} after Phase 3 failure - FOR DEBUGGING ONLY")
    
    # CRITICAL: Set startup_complete flag for health endpoint
    app.state.startup_complete = True
    app.state.startup_in_progress = False
    app.state.startup_failed = False
    app.state.startup_error = None
    logger.debug("Legacy startup completion flags set")
    
    log_startup_complete(start_time, logger)
    return start_time, logger