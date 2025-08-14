import time
import sys
import os
import asyncio
import multiprocessing
import alembic.config
import alembic.script
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from pathlib import Path
from typing import Any, Callable, Optional
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env file from {env_path}")
except ImportError:
    # dotenv not installed, skip
    pass

# Import unified logging first to ensure interceptor is set up
from app.logging_config import central_logger
from app.utils.multiprocessing_cleanup import setup_multiprocessing, cleanup_multiprocessing

# Configure loggers after unified logging is initialized
import logging
logging.getLogger("faker").setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import ValidationError

from app.routes.websockets import router as websockets_router
from app.db.postgres import async_session_factory
from app.config import settings
from app.llm.llm_manager import LLMManager
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.services.agent_service import AgentService
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService
from app.background import BackgroundTaskManager
from app.ws_manager import manager as websocket_manager
from app.agents.tool_dispatcher import ToolDispatcher
from app.services.tool_registry import ToolRegistry
from app.redis_manager import redis_manager
from app.db.clickhouse_init import initialize_clickhouse_tables
from app.db.migration_utils import (
    get_sync_database_url, get_current_revision, get_head_revision,
    create_alembic_config, needs_migration, execute_migration,
    log_migration_status, should_continue_on_error, validate_database_url
)

# Import new error handling components
from app.core.exceptions import NetraException
from app.core.error_handlers import (
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.core.error_context import ErrorContext

def run_migrations(logger: logging.Logger) -> None:
    """Run database migrations automatically on startup."""
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    start_time = time.time()
    logger = central_logger.get_logger(__name__)
    logger.info("Application startup...")
    
    # Set up multiprocessing properly to avoid semaphore leaks
    setup_multiprocessing()
    if 'pytest' in sys.modules:
        logger.info(f"pytest in sys.modules")

    # Validate database environment separation
    if 'pytest' not in sys.modules:  # Skip during testing
        from app.services.database_env_service import validate_database_environment
        try:
            validate_database_environment()
        except ValueError as e:
            logger.critical(f"Database environment validation failed: {e}")
            os._exit(1)
    
    # Run database migrations first (before initializing services that depend on DB)
    if 'pytest' not in sys.modules:  # Skip migrations during testing
        run_migrations(logger)
    
    # Initialize services
    app.state.redis_manager = redis_manager
    app.state.background_task_manager = BackgroundTaskManager()
    logger.info("Loading key manager...")
    key_manager = KeyManager.load_from_settings(settings)
    logger.info("Key manager loaded.")
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)
    app.state.llm_manager = LLMManager(settings)

    # ClickHouse client managed by central_logger
    app.state.clickhouse_client = None
    
    # Initialize ClickHouse tables based on service mode
    clickhouse_mode = os.getenv('CLICKHOUSE_MODE', 'shared').lower()
    if 'pytest' not in sys.modules and clickhouse_mode not in ['disabled', 'mock']:
        try:
            logger.info(f"Initializing ClickHouse tables (mode: {clickhouse_mode})...")
            await initialize_clickhouse_tables()
            logger.info("ClickHouse tables initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse tables: {e}")
            # Don't fail startup, the app can still work with PostgreSQL
    elif clickhouse_mode == 'disabled':
        logger.info("Skipping ClickHouse initialization (mode: disabled)")
    elif clickhouse_mode == 'mock':
        logger.info("Skipping ClickHouse initialization (mode: mock)")

    # Initialize Postgres - must be done before startup checks
    app.state.db_session_factory = async_session_factory

    # Run startup checks
    from app.startup_checks import run_startup_checks
    try:
        await run_startup_checks(app)
    except Exception as e:
        logger.critical(f"CRITICAL: Startup checks failed: {e}")
        logger.info("Application shutting down due to startup failure.")
        # Clean up resources before exit
        try:
            await redis_manager.disconnect()
            cleanup_multiprocessing()
            await central_logger.shutdown()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
        # Use sys.exit instead of os._exit to allow proper cleanup
        sys.exit(1)

    # Perform comprehensive schema validation
    from app.services.schema_validation_service import run_comprehensive_validation
    from app.db.postgres import async_engine
    if "pytest" not in sys.modules:
        validation_passed = await run_comprehensive_validation(async_engine)
        if not validation_passed:
            if settings.environment == "production":
                logger.critical("Schema validation failed in production. Shutting down.")
                os._exit(1)
            else:
                logger.error("Schema validation failed. The application might not work as expected.")

    # Initialize the agent supervisor
    tool_registry = ToolRegistry(app.state.db_session_factory)
    app.state.tool_dispatcher = ToolDispatcher(tool_registry.get_tools([]))
    app.state.agent_supervisor = Supervisor(app.state.db_session_factory, app.state.llm_manager, websocket_manager, app.state.tool_dispatcher)
    app.state.agent_service = AgentService(app.state.agent_supervisor)
    
    # Start database connection monitoring
    if 'pytest' not in sys.modules:  # Skip during testing
        try:
            from app.services.database.connection_monitor import start_connection_monitoring
            app.state.monitoring_task = asyncio.create_task(start_connection_monitoring())
            logger.info("Database connection monitoring started")
        except Exception as e:
            logger.error(f"Failed to start database monitoring: {e}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"System Ready (Took {elapsed_time:.2f}s).")

    try:
        yield
    finally:
        # Shutdown
        logger.info("Application shutdown initiated...")
        
        # Clean up multiprocessing resources
        cleanup_multiprocessing()
        
        # Stop database monitoring
        if hasattr(app.state, 'monitoring_task'):
            try:
                from app.services.database.connection_monitor import stop_connection_monitoring
                stop_connection_monitoring()
                app.state.monitoring_task.cancel()
                try:
                    await app.state.monitoring_task
                except asyncio.CancelledError:
                    pass
                logger.info("Database monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping database monitoring: {e}")
        
        await asyncio.sleep(0.1)
        await app.state.background_task_manager.shutdown()
        await app.state.agent_supervisor.shutdown()
        await websocket_manager.shutdown()
        await redis_manager.disconnect()
        await central_logger.shutdown()
        logger.info("Application shutdown complete.")

from fastapi.middleware.cors import CORSMiddleware
from app.auth.auth import oauth_client
from starlette.responses import RedirectResponse

app = FastAPI(lifespan=lifespan)

# Configure CORS first (before other middleware and routes)
allowed_origins = []
if settings.environment == "production":
    # In production, only allow specific origins from env or default
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    allowed_origins = cors_origins_env.split(",") if cors_origins_env else ["https://netra.ai"]
else:
    # In development, allow all origins with wildcard
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if cors_origins_env:
        # Use specific origins if configured
        allowed_origins = cors_origins_env.split(",")
    else:
        # Use wildcard to allow all origins in development
        allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID"],
    expose_headers=["X-Trace-ID", "X-Request-ID"],  # Expose custom headers to frontend
)

# Initialize OAuth
oauth_client.init_app(app)

@app.middleware("http")
async def cors_redirect_middleware(request: Request, call_next: Callable) -> Any:
    """Handle CORS for redirects (e.g., trailing slash redirects)."""
    response = await call_next(request)
    
    # If it's a redirect and we're in development, add CORS headers
    if isinstance(response, RedirectResponse) and settings.environment != "production":
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID"
    
    return response

@app.middleware("http")
async def error_context_middleware(request: Request, call_next: Callable) -> Any:
    """Middleware to set up error context for each request."""
    # Generate trace ID for the request
    trace_id = ErrorContext.generate_trace_id()
    
    # Set request ID if available in headers
    request_id = request.headers.get("x-request-id")
    if request_id:
        ErrorContext.set_request_id(request_id)
    
    # Store in request state for access in handlers
    request.state.trace_id = trace_id
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    # Add trace ID to response headers
    response.headers["x-trace-id"] = trace_id
    if request_id:
        response.headers["x-request-id"] = request_id
    
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Any:
    logger = central_logger.get_logger("api")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f'{process_time:.2f}ms'
    
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    logger.info(f"Request: {request.method} {request.url.path} | Status: {response.status_code} | Duration: {formatted_process_time} | Trace: {trace_id}")
    
    return response

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=(settings.environment == "production"),  # Enable HTTPS-only cookies in production
)

# Register error handlers
app.add_exception_handler(NetraException, netra_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

from app.routes import supply, generation, admin, references, health, corpus, synthetic_data, config, demo, unified_tools
from app.routes.auth import auth as auth_router
from app.routes.agent_route import router as agent_router
from app.routes.llm_cache import router as llm_cache_router
from app.routes.threads_route import router as threads_router
from app.routes.health_extended import router as health_extended_router
from app.routes.monitoring import router as monitoring_router

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(agent_router, prefix="/api/agent", tags=["agent"])
app.include_router(threads_router, tags=["threads"])
app.include_router(llm_cache_router, prefix="/api/llm-cache", tags=["llm-cache"])
app.include_router(supply.router, prefix="/api/supply", tags=["supply"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(websockets_router, tags=["websockets"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(references.router, prefix="/api", tags=["references"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(health_extended_router, tags=["monitoring"])
app.include_router(monitoring_router, prefix="/api", tags=["database-monitoring"])
app.include_router(corpus.router, prefix="/api/corpus", tags=["corpus"])
app.include_router(synthetic_data.router, tags=["synthetic_data"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(demo.router, tags=["demo"])
app.include_router(unified_tools.router, prefix="/api/tools", tags=["unified-tools"])

@app.get("/")
def read_root():
    logger = central_logger.get_logger(__name__)
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["*/tests/*", "*/.pytest_cache/*"],
        lifespan="on"
    )