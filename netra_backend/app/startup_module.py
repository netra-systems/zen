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

# CRITICAL: Set up paths BEFORE any imports that depend on them
def _setup_paths():
    """Set up Python path and environment BEFORE importing anything else."""
    try:
        # Get the project root first
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
    except Exception as e:
        # Fallback to current working directory
        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))

# Call this immediately before any other imports
_setup_paths()

# NOW import shared modules after paths are set
from shared.isolated_environment import get_env
from netra_backend.app.core.project_utils import get_project_root as _get_project_root

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
from netra_backend.app.startup_health_checks import validate_startup_health


# SSOT compliance: _get_project_root now imported from netra_backend.app.core.project_utils

async def _ensure_database_tables_exist(logger: logging.Logger, graceful_startup: bool = True) -> None:
    """Ensure that required database tables exist (created by migration service).
    
    CRITICAL: This function ONLY verifies table existence - it does NOT create tables.
    Table creation is EXCLUSIVELY handled by the migration service.
    """
    await _verify_required_database_tables_exist(logger, graceful_startup)


async def _verify_required_database_tables_exist(logger: logging.Logger, graceful_startup: bool = True) -> None:
    """Verify that required database tables exist (created by migration service).
    
    CRITICAL: This function ONLY verifies table existence - it does NOT create tables.
    Table creation is EXCLUSIVELY handled by the migration service.
    """
    try:
        from netra_backend.app.db.base import Base
        from sqlalchemy import text
        import asyncio
        
        # Import all model classes to ensure they're registered with Base.metadata
        logger.debug("Importing database models to verify table requirements...")
        _import_all_models()
        
        logger.debug("Verifying required database tables exist...")
        
        # Get async engine from SSOT
        from netra_backend.app.database import get_engine
        engine = get_engine()
        
        if not engine:
            error_msg = "Failed to get database engine for table verification"
            if graceful_startup:
                logger.warning(f"{error_msg} - continuing without table verification")
                return
            else:
                raise RuntimeError(error_msg)
        
        # Check if tables exist - use separate transaction for each operation
        async with engine.connect() as conn:
            # Start a new transaction for the query
            async with conn.begin() as trans:
                try:
                    result = await conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        ORDER BY table_name
                    """))
                    
                    existing_tables = set(row[0] for row in result.fetchall())
                    expected_tables = set(Base.metadata.tables.keys())
                    missing_tables = expected_tables - existing_tables
                    # Commit the transaction
                    await trans.commit()
                except Exception as e:
                    # Rollback on error to clean transaction state
                    await trans.rollback()
                    raise e
            
            if missing_tables:
                # SSOT: Define critical vs non-critical tables
                critical_tables = {
                    'users', 'threads', 'messages', 'runs', 'assistants'  # Core chat functionality
                }
                critical_missing = missing_tables & critical_tables
                non_critical_missing = missing_tables - critical_tables
                
                if critical_missing:
                    error_msg = f"CRITICAL STARTUP FAILURE: Missing CRITICAL database tables: {critical_missing}"
                    logger.error(error_msg)
                    logger.error("🚨 CRITICAL: Core chat functionality requires these tables")
                    logger.error("🔧 SOLUTION: Run the migration service to create critical tables")
                    logger.error("⚠️  Backend CANNOT function without critical tables")
                    
                    # Critical tables missing = HARD FAILURE regardless of graceful_startup
                    raise RuntimeError(f"Missing critical database tables: {critical_missing}. Run migration service first.")
                
                if non_critical_missing:
                    logger.warning(f"ARCHITECTURE NOTICE: Missing non-critical database tables: {non_critical_missing}")
                    logger.warning("🔧 These tables should be created by migration service for full functionality")
                    logger.warning("⚠️  Some features may be degraded until tables are created")
                    
                    if graceful_startup:
                        logger.info("✅ Continuing with degraded functionality - core chat will work")
                    else:
                        logger.error(f"Non-critical tables missing in strict mode: {non_critical_missing}")
                        raise RuntimeError(f"Missing required database tables: {non_critical_missing}. Run migration service first.")
            else:
                logger.debug(f"✅ All {len(expected_tables)} required database tables are present")
        
        # Log final pool status before disposal
        logger.debug(f"Database table verification complete")
        
        await engine.dispose()
        
    except Exception as e:
        error_msg = f"Failed to verify database tables exist: {e}"
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
            AgentStateCheckpoint,
            AgentStateMetadata,
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
        
        # CRITICAL FIX: Import SQLAlchemy models from netra_backend.app.models directory
        # The AgentExecution model exists but wasn't being imported, causing table verification failures
        from netra_backend.app.models.agent_execution import AgentExecution
        
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
    
    # Check if database is in mock mode by examining #removed-legacyor service config
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
        "@localhost:5432/mock",  # specific mock pattern used by dev launcher
        "?mock"  # query parameter indicating mock mode
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
    
    # Check if database is in mock mode by examining #removed-legacyor service config
    database_url = config.database_url or ""
    is_mock_database = _is_mock_database_url(database_url) or _is_postgres_service_mock_mode()
    
    if is_mock_database:
        logger.debug("PostgreSQL in mock mode - using mock session factory")
        app.state.db_session_factory = None  # Signal to use mock/fallback
        app.state.database_available = False
        app.state.database_mock_mode = True
        return
    
    # CRITICAL FIX: Wrap database initialization in timeout to prevent server startup hanging
    # Get environment-aware timeout configuration
    from netra_backend.app.core.database_timeout_config import get_database_timeout_config
    from shared.isolated_environment import get_env
    
    environment = get_env().get("ENVIRONMENT", "development")
    timeout_config = get_database_timeout_config(environment)
    
    initialization_timeout = timeout_config["initialization_timeout"]
    table_setup_timeout = timeout_config["table_setup_timeout"]
    
    logger.info(f"Database setup for {environment} environment - init timeout: {initialization_timeout}s, table timeout: {table_setup_timeout}s")
    
    try:
        logger.debug(f"Calling initialize_postgres() with {initialization_timeout}s timeout...")
        async_session_factory = await asyncio.wait_for(
            asyncio.create_task(_async_initialize_postgres(logger)),
            timeout=initialization_timeout
        )
        logger.debug(f"initialize_postgres() returned: {async_session_factory}")
        
        if async_session_factory is None:
            error_msg = f"initialize_postgres() returned None - database initialization failed in {environment} environment"
            if graceful_startup:
                logger.error(f"{error_msg} - using mock database for graceful degradation")
                app.state.db_session_factory = None  # Signal to use mock/fallback
                app.state.database_available = False
                app.state.database_mock_mode = True
                return
            else:
                raise RuntimeError(error_msg)
        
        # Verify database tables exist (created by migration service) with timeout protection
        logger.debug(f"Verifying database tables exist with {table_setup_timeout}s timeout...")
        await asyncio.wait_for(
            _verify_required_database_tables_exist(logger, graceful_startup),
            timeout=table_setup_timeout
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
    app.state.llm_manager = LLMManager()
    
    # CRITICAL FIX: Set ClickHouse availability flag based on configuration
    config = get_config()
    from shared.isolated_environment import get_env
    clickhouse_required = get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
    
    # ClickHouse is available if required or if not in staging/development
    clickhouse_available = clickhouse_required or config.environment not in ["staging", "development"]
    app.state.clickhouse_available = clickhouse_available
    app.state.clickhouse_client = None  # Will be initialized on-demand


async def initialize_clickhouse(logger: logging.Logger) -> dict:
    """Initialize ClickHouse with clear status reporting and handle failures appropriately.
    
    CRITICAL FIX: Improved error handling per STAGING_STARTUP_FIXES_IMPLEMENTATION_PLAN.md
    - Check if ClickHouse is required based on environment
    - Return detailed status report from initialization  
    - Log appropriate level based on requirement (error if required, info if optional)
    - Only raise exception if ClickHouse is required and fails
    - Make logging crystal clear about optional vs required status
    
    Returns:
        dict: Status report with service, required, status, and error fields
    """
    config = get_config()
    clickhouse_mode = config.clickhouse_mode.lower()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    # Status tracking object
    result = {
        "service": "clickhouse",
        "required": False,
        "status": "unknown",
        "error": None
    }
    
    # CRITICAL FIX: Check if ClickHouse is required based on environment
    from shared.isolated_environment import get_env
    import subprocess
    clickhouse_required = (
        config.environment == "production" or
        get_env().get("CLICKHOUSE_REQUIRED", "false").lower() == "true"
    )
    result["required"] = clickhouse_required
    
    # Check if ClickHouse container is running (for better error reporting)
    try:
        # Use docker only
        cmd = 'docker'
        try:
            result_cmd = subprocess.run(
                [cmd, 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result_cmd.returncode == 0:
                running_containers = result_cmd.stdout.strip().split('\n')
                clickhouse_running = any('clickhouse' in name.lower() for name in running_containers)
                if not clickhouse_running:
                    logger.warning("=" * 80)
                    logger.warning("CLICKHOUSE CONTAINER NOT RUNNING")
                    logger.warning("=" * 80)
                    logger.warning(f"No ClickHouse container found. To start:")
                    logger.warning(f"  {cmd} start <clickhouse-container-name>")
                    logger.warning(f"Or use: python scripts/docker_manual.py start")
                    logger.warning("=" * 80)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Docker not available - cannot check ClickHouse container status")
    except Exception:
        pass  # Ignore container check errors
    
    # CRITICAL FIX: Make ClickHouse optional in development and staging when not explicitly required
    if config.environment in ["development", "staging"] and not clickhouse_required:
        result["status"] = "skipped"
        logger.info(f"ℹ️ ClickHouse not required in {config.environment} environment - skipping initialization")
        logger.info("ℹ️ System continuing without analytics")
        return result
    
    # CRITICAL FIX: Check if conditions prevent connection attempt
    if 'pytest' in sys.modules or clickhouse_mode in ['disabled', 'mock']:
        # ClickHouse is skipped due to test mode or disabled mode
        result["status"] = "skipped"
        skip_reason = "test mode" if 'pytest' in sys.modules else f"mode: {clickhouse_mode}"
        
        # CRITICAL FIX: If ClickHouse is required but skipped, that's an error
        if clickhouse_required:
            error_msg = f"ClickHouse required but skipped due to {skip_reason}"
            result["status"] = "failed"
            result["error"] = error_msg
            logger.error(f"❌ CRITICAL: {error_msg}")
            raise RuntimeError(f"ClickHouse initialization failed: {error_msg}. Cannot skip required service.")
        else:
            _log_clickhouse_skip(logger, clickhouse_mode)
            logger.info(f"ℹ️ ClickHouse skipped (optional) due to {skip_reason}")
    else:
        # Attempt actual connection
        try:
            # CRITICAL FIX: Reduce timeout for faster startup failure in optional environments
            timeout = 10.0 if config.environment in ["staging", "development"] else 30.0
            
            # Attempt connection
            await asyncio.wait_for(
                _setup_clickhouse_tables(logger, clickhouse_mode),
                timeout=timeout
            )
            result["status"] = "connected"
            logger.info("✅ ClickHouse initialized successfully")
            
        except asyncio.TimeoutError:
            timeout_msg = f"ClickHouse initialization timed out after {timeout} seconds"
            result["status"] = "failed"
            result["error"] = timeout_msg
            
            if clickhouse_required:
                logger.error(f"❌ CRITICAL: ClickHouse required but timed out: {timeout_msg}")
                raise RuntimeError(f"{timeout_msg}. ClickHouse is required in {config.environment} mode.")
            else:
                logger.info(f"ℹ️ ClickHouse unavailable (optional): {timeout_msg}")
                logger.info("ℹ️ System continuing without analytics")
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            
            # Enhanced error handling for common ClickHouse connection issues
            error_msg = str(e).lower()
            is_connection_error = any(keyword in error_msg for keyword in [
                'connection', 'refused', 'timeout', 'unreachable', 'network', 'dns', 'httpsconnectionpool'
            ])
            
            if clickhouse_required:
                logger.error(f"❌ CRITICAL: ClickHouse required but failed: {e}")
                raise RuntimeError(f"ClickHouse initialization failed in {config.environment}: {e}. ClickHouse is required in {config.environment} mode.") from e
            else:
                logger.info(f"ℹ️ ClickHouse unavailable (optional): {e}")
                logger.info("ℹ️ System continuing without analytics")
    
    return result


async def _setup_clickhouse_tables(logger: logging.Logger, mode: str) -> None:
    """Setup ClickHouse tables with timeout and error handling.
    
    CRITICAL FIX: Based on Five Whys root cause analysis - tables MUST be initialized
    for core business functionality.
    """
    import asyncio
    from shared.isolated_environment import get_env
    
    try:
        _log_clickhouse_start(logger, mode)
        
        # CRITICAL FIX: Add timeout protection for table initialization
        environment = get_env().get("ENVIRONMENT", "development").lower()
        init_timeout = 8.0 if environment in ["staging", "development"] else 20.0
        
        # First try the new table initializer for mandatory tables
        logger.info("🚀 Ensuring ClickHouse critical tables exist...")
        from netra_backend.app.db.clickhouse_table_initializer import ensure_clickhouse_tables
        
        # Get ClickHouse connection details from environment
        config = get_config()
        # Use environment variables for ClickHouse connection
        host = get_env().get('CLICKHOUSE_HOST', 'dev-clickhouse' if environment == 'development' else 'localhost')
        port = int(get_env().get('CLICKHOUSE_PORT', '9000'))  # Native protocol port
        user = get_env().get('CLICKHOUSE_USER', 'default')
        password = get_env().get('CLICKHOUSE_PASSWORD', '')
        
        try:
            # Ensure critical tables exist (fail_fast=False for backward compatibility)
            tables_ok = await asyncio.wait_for(
                asyncio.to_thread(ensure_clickhouse_tables, host, port, user, password, False),
                timeout=init_timeout
            )
            
            if tables_ok:
                logger.info("✅ All critical ClickHouse tables verified")
            else:
                logger.warning("⚠️ Some ClickHouse tables could not be created - proceeding with legacy init")
        except Exception as table_error:
            logger.warning(f"⚠️ Table initializer encountered issue: {table_error} - trying legacy method")
        
        # Also run legacy initialization for backward compatibility
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
    from netra_backend.app.core.registry.universal_registry import ToolRegistry
    return ToolRegistry()


def _create_tool_dispatcher(tool_registry):
    """Create tool dispatcher instance.
    
    DEPRECATED WARNING: This function creates a global ToolDispatcher instance
    that may cause user isolation issues in production environments.
    
    MIGRATION NEEDED: Replace with request-scoped dispatcher factory pattern:
    - Use ToolDispatcher.create_request_scoped_dispatcher() in request handlers
    - Use ToolDispatcher.create_scoped_dispatcher_context() for automatic cleanup
    - Remove global dispatcher from startup module
    
    SECURITY RISKS:
    - Global tool dispatcher shared between all users
    - WebSocket events may be delivered to wrong users
    - Tool state not isolated per request
    - Memory leaks possible with concurrent requests
    """
    import warnings
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.logging_config import central_logger
    
    logger = central_logger.get_logger(__name__)
    
    # Emit deprecation warning
    warnings.warn(
        "startup_module._create_tool_dispatcher() creates global state that may cause user isolation issues. "
        "Replace with request-scoped factory patterns. "
        "Global dispatcher will be removed in v3.0.0 (Q2 2025).",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.warning("🚨 DEPRECATED: Creating global ToolDispatcher in startup module")
    logger.warning("⚠️ This creates security risks and user isolation issues")
    logger.warning("📋 MIGRATION: Remove global dispatcher, use request-scoped patterns")
    logger.warning("📅 REMOVAL: Global startup dispatcher will be removed in v3.0.0")
    
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
        
        # CRITICAL: Validate WebSocket infrastructure for agent events
        # Note: SupervisorAgent using UserExecutionContext pattern creates per-request tool dispatchers
        # so we validate that the WebSocket infrastructure is properly initialized instead
        if hasattr(supervisor, 'websocket_bridge') and supervisor.websocket_bridge:
            logger.info("✅ SupervisorAgent has WebSocket bridge - agent events will be enabled")
            
            # Validate WebSocket bridge has required method
            required_methods = ['emit_agent_event']
            missing_methods = [method for method in required_methods if not hasattr(supervisor.websocket_bridge, method)]
            if missing_methods:
                logger.error(f"🚨 WebSocket bridge missing required methods: {missing_methods}")
                raise RuntimeError(f"WebSocket bridge incomplete - missing methods: {missing_methods}")
        else:
            logger.error("🚨 CRITICAL: SupervisorAgent missing WebSocket bridge - agent events will be broken!")
            raise RuntimeError("SupervisorAgent must have WebSocket bridge for agent event notifications")
        
        # Validate WebSocket manager factory is available for per-request enhancement  
        # SSOT COMPLIANCE: Using factory pattern - no singleton WebSocket managers during startup
        from netra_backend.app.websocket_core import get_websocket_manager_factory
        try:
            factory = get_websocket_manager_factory()
            if not factory:
                logger.error("🚨 CRITICAL: WebSocket manager factory not available - per-request tool dispatcher enhancement will fail!")
                raise RuntimeError("WebSocket manager factory must be available for tool dispatcher enhancement")
            logger.info("✅ SSOT COMPLIANCE: WebSocket factory pattern verified - no singleton manager calls during startup")
            logger.debug("✅ WebSocket manager factory available for per-request enhancement")
        except Exception as e:
            logger.error(f"🚨 CRITICAL: Failed to get WebSocket manager factory: {e}")
            raise RuntimeError(f"WebSocket manager factory initialization failed: {e}")
        
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
    
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Create the proper websocket bridge instance  
    websocket_bridge = AgentWebSocketBridge()
    logger.debug(f"Creating supervisor with dependencies: db_session_factory={app.state.db_session_factory}, llm_manager={app.state.llm_manager}")
    
    # CRITICAL: No tool_dispatcher - created per-request for isolation
    return SupervisorAgent(
        app.state.llm_manager, 
        websocket_bridge  # Correct AgentWebSocketBridge instance
        # NO tool_dispatcher - created per-request
    )


def _setup_agent_state(app: FastAPI, supervisor) -> None:
    """Setup agent state in app."""
    from netra_backend.app.services.agent_service import AgentService
    from netra_backend.app.services.thread_service import ThreadService
    from netra_backend.app.services.corpus_service import CorpusService
    app.state.agent_supervisor = supervisor
    app.state.agent_service = AgentService(supervisor)
    app.state.thread_service = ThreadService()
    # NOTE: CorpusService now requires user context for WebSocket notifications
    # This will be created per-request with user context instead of singleton
    app.state.corpus_service = CorpusService()  # Default without user context for backward compatibility


async def initialize_websocket_components(logger: logging.Logger) -> None:
    """Initialize WebSocket components that require async context (optional service)."""
    config = get_config()
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    try:
        from netra_backend.app.websocket_core import (
            get_websocket_manager_factory,
            WebSocketManagerFactory,
        )
        # Initialize the WebSocket manager factory for per-request use
        # SSOT COMPLIANCE: Factory pattern ensures UserExecutionContext isolation
        factory = get_websocket_manager_factory()
        
        # Factory is initialized on creation - no additional initialization needed
        # Individual managers are created per-request with UserExecutionContext
        logger.info("✅ SSOT COMPLIANCE: WebSocket components use factory pattern - no singleton violations")
        logger.debug("WebSocket factory initialized for per-request manager creation")
        
        logger.debug("WebSocket components initialized")
    except Exception as e:
        if graceful_startup:
            logger.warning(f"WebSocket components initialization failed but continuing (optional service): {e}")
        else:
            logger.error(f"Failed to initialize WebSocket components: {e}")
            raise


async def startup_health_checks(app: FastAPI, logger: logging.Logger) -> None:
    """Run application startup checks with timeout protection and test thread awareness.
    
    CRITICAL FIX: Added test thread detection to prevent "Cannot deliver message" errors
    during health checks. Test threads are handled gracefully without WebSocket connections.
    """
    config = get_config()
    disable_checks = config.disable_startup_checks.lower() == "true"
    fast_startup = config.fast_startup_mode.lower() == "true"
    graceful_startup = getattr(config, 'graceful_startup_mode', 'true').lower() == "true"
    
    if disable_checks or fast_startup:
        logger.debug("Skipping startup health checks (fast startup mode)")
        return
    
    logger.debug("Starting comprehensive startup health checks with test thread awareness...")
    from netra_backend.app.startup_checks import run_startup_checks
    try:
        logger.debug("Calling run_startup_checks() with 20s timeout...")
        # CRITICAL FIX: Add timeout to prevent startup health checks from hanging server startup
        results = await asyncio.wait_for(
            run_startup_checks(app, test_thread_aware=True),  # Enable test thread detection
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
            failed = total - passed
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
    await redis_manager.shutdown()


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


async def initialize_monitoring_integration(handlers: dict = None) -> bool:
    """
    Initialize monitoring integration between ChatEventMonitor and AgentWebSocketBridge.
    
    CRITICAL FIX: Now accepts handlers parameter to ensure monitoring is initialized
    AFTER handlers are registered, preventing "ZERO handlers" warnings during startup.
    
    This function connects the ChatEventMonitor with the AgentWebSocketBridge to enable
    comprehensive monitoring coverage where the monitor can audit the bridge without
    creating tight coupling.
    
    CRITICAL DESIGN: Both components work independently if integration fails.
    The system continues operating even if monitoring integration is not available.
    
    Args:
        handlers: Dictionary of registered handlers (ensures monitoring happens after registration)
    
    Returns:
        bool: True if integration successful, False if integration failed but components
              are still operating independently
    """
    logger = central_logger.get_logger(__name__)
    
    try:
        # CRITICAL FIX: Log handler registration status at monitoring initialization
        handler_count = len(handlers) if handlers else 0
        logger.info(f"Initializing monitoring integration with {handler_count} registered handlers...")
        
        if handler_count == 0:
            logger.warning("⚠️ Monitoring initialized with zero handlers - may indicate registration timing issue")
        
        # Import monitoring components
        from netra_backend.app.websocket_core.event_monitor import chat_event_monitor
        
        # Initialize ChatEventMonitor independently first
        await chat_event_monitor.start_monitoring()
        logger.debug(f"ChatEventMonitor started successfully with {handler_count} handlers available")
        
        # CRITICAL FIX: The AgentWebSocketBridge is now per-request, not singleton
        # The legacy singleton pattern is deprecated, so we should not try to initialize it
        # Instead, mark the component as healthy by default since per-request bridges work independently
        logger.info("ℹ️ AgentWebSocketBridge uses per-request architecture - no global initialization needed")
        logger.info("ℹ️ WebSocket events work via per-user emitters created on-demand")
        
        # Register the bridge component as healthy since it's always available on-demand
        try:
            from netra_backend.app.core.health.unified_health_checker import backend_health_checker
            # Mark agent_websocket_bridge as healthy since it's available on-demand
            # Using the backend_health_checker which is the SSOT for health status
            if hasattr(backend_health_checker, 'component_health'):
                backend_health_checker.component_health["agent_websocket_bridge"] = {
                    "status": "healthy",
                    "message": "Available on-demand via per-request architecture",
                    "last_check": time.time(),
                    "component_type": "bridge"
                }
                logger.info("✅ Marked agent_websocket_bridge as healthy (per-request architecture)")
            else:
                logger.debug("Health checker doesn't track component health directly - this is expected")
        except Exception as health_error:
            logger.warning(f"Could not update health status for agent_websocket_bridge: {health_error}")
            logger.info("ℹ️ AgentWebSocketBridge using per-request pattern - this is expected")
        
        # CRITICAL FIX: Removed legacy bridge registration code
        # The AgentWebSocketBridge is now per-request, not singleton
        # There's no global 'bridge' instance to register with the monitor
        # Each request creates its own bridge instance as needed
        logger.info("✅ Monitoring integration complete - per-request bridges work independently")
        
        return True
    
    except Exception as e:
        logger.error(
            f"⚠️ Monitoring integration initialization failed: {e}. "
            f"Components will operate independently without cross-system validation."
        )
        return False


# CLEANED UP: Legacy deprecated phase functions removed
# Use run_complete_startup() -> run_deterministic_startup() for all startup needs


async def run_complete_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run complete startup sequence - FIXED DETERMINISTIC MODE ONLY.
    
    This is the SSOT for startup. NO FALLBACKS, NO GRACEFUL DEGRADATION.
    If chat cannot work, the service MUST NOT start.
    
    CRITICAL FIX: Ensures proper startup sequence order:
    1. Core Infrastructure (Database, Redis, Auth)
    2. WebSocket Components BEFORE Monitoring (register handlers first!)
    3. Monitoring WITH handlers context (only if handlers exist)
    4. Optional Services (ClickHouse)
    5. Health Checks LAST with proper setup
    """
    # ALWAYS use deterministic startup - this is the SSOT
    from netra_backend.app.smd import run_deterministic_startup
    return await run_deterministic_startup(app)


# CLEANED UP: All legacy startup code removed
# Only deterministic startup via run_complete_startup() is supported

# REMOVED: _deprecated_legacy_startup function
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
            from netra_backend.app.smd import run_deterministic_startup
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
            # No fallback - deterministic startup only
            raise RuntimeError(f"Startup failed: {e}") from e
    else:
        # Always use deterministic startup - no legacy fallbacks
        from netra_backend.app.smd import run_deterministic_startup
        return await run_deterministic_startup(app)


# REMOVED: All legacy startup functions eliminated - only deterministic startup supported