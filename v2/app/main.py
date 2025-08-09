import logging
import time
import sys
import os
import asyncio
import alembic.config
import alembic.script
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.getLogger("faker").setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes.websockets import router as websockets_router
from app.db.postgres import async_session_factory
from app.config import settings
from app.logging_config import central_logger
from app.llm.llm_manager import LLMManager
from app.agents.supervisor import Supervisor
from app.services.agent_service import AgentService
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService
from app.background import BackgroundTaskManager
from app.ws_manager import manager as websocket_manager
from app.agents.tool_dispatcher import ToolDispatcher
from app.services.tool_registry import ToolRegistry
from app.redis_manager import redis_manager

def run_migrations(logger):
    """Run database migrations automatically on startup."""
    try:
        logger.info("Checking database migrations...")
        
        # Get the database URL
        database_url = settings.database_url
        if not database_url:
            logger.warning("No database URL configured, skipping migrations")
            return
            
        # Convert async URL to sync for Alembic
        if database_url.startswith("postgresql+asyncpg://"):
            sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            sync_database_url = database_url
            
        # Check current revision
        engine = create_engine(sync_database_url)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            logger.info(f"Current database revision: {current_rev}")
        
        # Run migrations
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_database_url)
        
        # Check if we need to upgrade
        script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        
        if current_rev != head_rev:
            logger.info(f"Migrating database from {current_rev} to {head_rev}...")
            alembic.config.main(argv=["--raiseerr", "upgrade", "head"])
            logger.info("Database migrations completed successfully")
        else:
            logger.info("Database is already up to date")
            
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        if settings.environment == "production":
            raise
        else:
            logger.warning("Continuing without migrations in development mode")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    start_time = time.time()
    logger = central_logger.get_logger(__name__)
    logger.info("Application startup...")
    if 'pytest' in sys.modules:
        logger.info(f"pytest in sys.modules")

    # Initialize services
    app.state.redis_manager = redis_manager
    app.state.background_task_manager = BackgroundTaskManager()
    logger.info("Loading key manager...")
    key_manager = KeyManager.load_from_settings(settings)
    logger.info("Key manager loaded.")
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)
    app.state.llm_manager = LLMManager(settings)

    # Run startup checks
    from app.startup_checks import run_startup_checks
    try:
        await run_startup_checks(app)
    except Exception as e:
        logger.critical(f"CRITICAL: Startup checks failed: {e}")
        logger.info("Application shutting down due to startup failure.")
        os._exit(1)

    # The ClickHouse client is now managed by the central_logger
    app.state.clickhouse_client = central_logger.clickhouse_db

    # Initialize Postgres
    app.state.db_session_factory = async_session_factory

    # Perform database self-check
    from app.services.db_check_service import check_db_schema
    if "pytest" not in sys.modules:
        async with app.state.db_session_factory() as session:
            if not await check_db_schema(session):
                # In a real application, you might want to raise an exception here
                # to prevent the application from starting with a bad schema.
                logger.error("Database schema validation failed. The application might not work as expected.")

    # Initialize the agent supervisor
    tool_registry = ToolRegistry(app.state.db_session_factory)
    app.state.tool_dispatcher = ToolDispatcher(tool_registry.get_tools([]))
    app.state.agent_supervisor = Supervisor(app.state.db_session_factory, app.state.llm_manager, websocket_manager, app.state.tool_dispatcher)
    app.state.agent_service = AgentService(app.state.agent_supervisor)
    
    elapsed_time = time.time() - start_time
    logger.info(f"System Ready (Took {elapsed_time:.2f}s).")

    try:
        yield
    finally:
        # Shutdown
        logger.info("Application shutdown initiated...")
        await asyncio.sleep(0.1)
        await app.state.background_task_manager.shutdown()
        await app.state.agent_supervisor.shutdown()
        await websocket_manager.shutdown()
        await redis_manager.disconnect()
        await central_logger.shutdown()
        logger.info("Application shutdown complete.")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = central_logger.get_logger("api")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f'{process_time:.2f}ms'
    
    logger.info(f"Request: {request.method} {request.url.path} | Status: {response.status_code} | Duration: {formatted_process_time}")
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax" if settings.environment != "development" else "none",
    https_only=settings.environment != "development",
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

from app.routes import supply, generation, admin, references, health, corpus, synthetic_data, config
from app.routes.auth import auth as auth_router

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(supply.router, prefix="/api/supply", tags=["supply"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(websockets_router, tags=["websockets"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(references.router, prefix="/api", tags=["references"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(corpus.router, prefix="/api/corpus", tags=["corpus"])
app.include_router(synthetic_data.router, prefix="/synthetic_data", tags=["synthetic_data"])
app.include_router(config.router, prefix="/api", tags=["config"])

@app.get("/")
def read_root():
    logger = central_logger.get_logger(__name__)
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API"}

@app.get("/test-error")
def test_error():
    logger = central_logger.get_logger(__name__)
    try:
        raise HTTPException(status_code=500, detail="This is a test error.")
    except HTTPException as e:
        logger.error(f"An HTTP exception occurred: {e.detail}", exc_info=True)
        raise e

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

if "pytest" in sys.modules:
    llm_manager = LLMManager(settings)
    app.state.llm_manager = llm_manager
    key_manager = KeyManager.load_from_settings(settings)
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)
    tool_registry = ToolRegistry(async_session_factory)
    tool_dispatcher = ToolDispatcher(tool_registry.get_tools([]))
    app.state.agent_supervisor = Supervisor(async_session_factory, llm_manager, websocket_manager, tool_dispatcher)

    from app.db.testing import override_get_db
    from app.dependencies import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db