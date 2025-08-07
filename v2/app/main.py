import logging
import time
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.getLogger("faker").setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, supply, generation, websocket, admin, references, agent_route, health
from app.auth import google_oauth
from app.db.postgres import async_session_factory
from app.config import settings
from app.logging_config import central_logger
from app.llm.llm_manager import LLMManager
from app.services.deepagents.overall_supervisor import OverallSupervisor
from app.services.agent_service import AgentService
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService
from app.websocket import manager as websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    start_time = time.time()
    logger = central_logger.get_logger(__name__)
    logger.info("Application startup...")

    key_manager = KeyManager.load_from_settings(settings)
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)

    # Initialize LLMManager
    app.state.llm_manager = LLMManager(settings)

    # The ClickHouse client is now managed by the central_logger
    app.state.clickhouse_client = central_logger.clickhouse_db

    # Initialize Postgres
    app.state.db_session_factory = async_session_factory

    # Initialize the agent supervisor
    app.state.agent_supervisor = OverallSupervisor(app.state.db_session_factory, app.state.llm_manager, websocket_manager)
    app.state.agent_service = AgentService(app.state.agent_supervisor)
    
    elapsed_time = time.time() - start_time
    logger.info(f"System Ready (Took {elapsed_time:.2f}s).")

    yield
    
    # Shutdown
    logger.info("Application shutdown...")
    await app.state.agent_supervisor.shutdown()
    central_logger.shutdown()



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


app.include_router(auth.router, prefix="/api/v3/auth", tags=["auth"])
app.include_router(supply.router, prefix="/api/v3/supply", tags=["supply"])
app.include_router(generation.router, prefix="/api/v3/generation", tags=["generation"])

app.include_router(agent_route.router, prefix="/api/v3/agent/chat", tags=["agent"])
app.include_router(websocket.router, prefix="/ws", tags=["websockets"])
app.include_router(admin.router, prefix="/api/v3", tags=["admin"])
app.include_router(references.router, prefix="/api/v3", tags=["references"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(google_oauth.router, prefix="/api/v3/auth", tags=["auth"])


@app.get("/")
def read_root():
    logger = central_logger.get_logger(__name__)
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}

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
    uvicorn.run(app, host="0.0.0.0", port=8000)

if "pytest" in sys.modules:
    from app.db.postgres import async_session_factory
    from app.llm.llm_manager import LLMManager
    from app.services.deepagents.overall_supervisor import OverallSupervisor
    from app.websocket import manager as websocket_manager

    llm_manager = LLMManager(settings)
    app.state.agent_supervisor = OverallSupervisor(async_session_factory, llm_manager, websocket_manager)