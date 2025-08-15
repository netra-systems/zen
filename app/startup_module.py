"""
Application startup management module.
Handles initialization of logging, database connections, services, and health checks.
"""
import time
import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Tuple, Optional
from fastapi import FastAPI

from app.logging_config import central_logger
from app.utils.multiprocessing_cleanup import setup_multiprocessing
from app.config import settings
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService
from app.llm.llm_manager import LLMManager
from app.background import BackgroundTaskManager
from app.redis_manager import redis_manager
from app.db.postgres import async_session_factory
from app.db.migration_utils import (
    get_sync_database_url, get_current_revision, get_head_revision,
    create_alembic_config, needs_migration, execute_migration,
    log_migration_status, should_continue_on_error, validate_database_url
)
from app.core.performance_optimization_manager import performance_manager
from app.monitoring.performance_monitor import performance_monitor
from app.db.index_optimizer import index_manager


async def _initialize_performance_optimizations(app: FastAPI, logger: logging.Logger) -> None:
    """Initialize performance optimization components."""
    try:
        # Initialize performance optimization manager
        await performance_manager.initialize()
        app.state.performance_manager = performance_manager
        
        # Run database index optimizations
        optimization_results = await index_manager.optimize_all_databases()
        logger.info(f"Database optimization completed: {optimization_results}")
        
        # Store optimization components in app state
        app.state.index_manager = index_manager
        
        logger.info("Performance optimizations initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize performance optimizations: {e}")
        # Don't fail startup, but log the error


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
    from app.services.database_env_service import validate_database_environment
    try:
        validate_database_environment()
    except ValueError as e:
        logger.critical(f"Database environment validation failed: {e}")
        os._exit(1)


def run_database_migrations(logger: logging.Logger) -> None:
    """Run database migrations if not in test mode."""
    if 'pytest' not in sys.modules:
        _execute_migrations(logger)


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


def setup_database_connections(app: FastAPI) -> None:
    """Setup PostgreSQL connection factory."""
    app.state.db_session_factory = async_session_factory


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
    """Initialize ClickHouse tables based on service mode."""
    clickhouse_mode = os.getenv('CLICKHOUSE_MODE', 'shared').lower()
    if 'pytest' not in sys.modules and clickhouse_mode not in ['disabled', 'mock']:
        await _setup_clickhouse_tables(logger, clickhouse_mode)
    else:
        _log_clickhouse_skip(logger, clickhouse_mode)


async def _setup_clickhouse_tables(logger: logging.Logger, mode: str) -> None:
    """Setup ClickHouse tables."""
    from app.db.clickhouse_init import initialize_clickhouse_tables
    try:
        logger.info(f"Initializing ClickHouse tables (mode: {mode})...")
        await initialize_clickhouse_tables()
        logger.info("ClickHouse tables initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")


def _log_clickhouse_skip(logger: logging.Logger, mode: str) -> None:
    """Log ClickHouse initialization skip."""
    if mode == 'disabled':
        logger.info("Skipping ClickHouse initialization (mode: disabled)")
    elif mode == 'mock':
        logger.info("Skipping ClickHouse initialization (mode: mock)")


def register_websocket_handlers(app: FastAPI) -> None:
    """Create tool registry and dispatcher."""
    from app.services.tool_registry import ToolRegistry
    from app.agents.tool_dispatcher import ToolDispatcher
    from app.agents.supervisor_consolidated import SupervisorAgent
    from app.services.agent_service import AgentService
    from app.ws_manager import manager as websocket_manager
    
    tool_registry = ToolRegistry(app.state.db_session_factory)
    app.state.tool_dispatcher = ToolDispatcher(tool_registry.get_tools([]))


def _create_agent_supervisor(app: FastAPI) -> None:
    """Create agent supervisor."""
    from app.agents.supervisor_consolidated import SupervisorAgent
    from app.services.agent_service import AgentService
    from app.ws_manager import manager as websocket_manager
    
    supervisor = SupervisorAgent(
        app.state.db_session_factory, 
        app.state.llm_manager, 
        websocket_manager, 
        app.state.tool_dispatcher
    )
    app.state.agent_supervisor = supervisor
    app.state.agent_service = AgentService(supervisor)


async def startup_health_checks(app: FastAPI, logger: logging.Logger) -> None:
    """Run application startup checks."""
    from app.startup_checks import run_startup_checks
    try:
        await run_startup_checks(app)
    except Exception as e:
        await _handle_startup_failure(logger, e)


async def _handle_startup_failure(logger: logging.Logger, error: Exception) -> None:
    """Handle startup check failures."""
    logger.critical(f"CRITICAL: Startup checks failed: {error}")
    logger.info("Application shutting down due to startup failure.")
    await _emergency_cleanup(logger)
    raise RuntimeError(f"Application startup failed: {error}")


async def _emergency_cleanup(logger: logging.Logger) -> None:
    """Perform emergency cleanup on startup failure."""
    from app.utils.multiprocessing_cleanup import cleanup_multiprocessing
    try:
        await redis_manager.disconnect()
        cleanup_multiprocessing()
        await central_logger.shutdown()
    except Exception as cleanup_error:
        logger.error(f"Error during cleanup: {cleanup_error}")


async def validate_schema(logger: logging.Logger) -> None:
    """Perform comprehensive schema validation."""
    from app.services.schema_validation_service import run_comprehensive_validation
    from app.db.postgres import async_engine
    if "pytest" not in sys.modules:
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
    """Start comprehensive performance monitoring."""
    if 'pytest' not in sys.modules:
        try:
            await _create_monitoring_task(app, logger)
            await _initialize_performance_optimizations(app, logger)
        except Exception as e:
            logger.error(f"Failed to start monitoring and optimizations: {e}")


async def _create_monitoring_task(app: FastAPI, logger: logging.Logger) -> None:
    """Create comprehensive monitoring tasks."""
    from app.services.database.connection_monitor import start_connection_monitoring
    
    # Start database connection monitoring
    app.state.monitoring_task = asyncio.create_task(start_connection_monitoring())
    
    # Start performance monitoring
    await performance_monitor.start_monitoring()
    app.state.performance_monitor = performance_monitor
    
    logger.info("Comprehensive monitoring started")


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
    setup_database_connections(app)  # Move database setup first
    key_manager = initialize_core_services(app, logger)
    setup_security_services(app, key_manager)
    await initialize_clickhouse(logger)


async def _run_startup_phase_three(app: FastAPI, logger: logging.Logger) -> None:
    """Run validation and setup phase."""
    await startup_health_checks(app, logger)
    await validate_schema(logger)
    register_websocket_handlers(app)
    _create_agent_supervisor(app)
    await start_monitoring(app, logger)


async def run_complete_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """Run complete startup sequence."""
    start_time, logger = await _run_startup_phase_one(app)
    await _run_startup_phase_two(app, logger)
    await _run_startup_phase_three(app, logger)
    log_startup_complete(start_time, logger)
    return start_time, logger