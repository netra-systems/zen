import time
import sys
import os
from pathlib import Path
from typing import Any, Callable, Optional, Tuple
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

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import ValidationError

from app.config import settings
from app.startup import run_complete_startup
from app.shutdown import run_complete_shutdown

# Import new error handling components
from app.core.exceptions_base import NetraException
from app.core.error_handlers import (
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.core.error_context import ErrorContext


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's startup and shutdown events."""
    start_time, logger = await run_complete_startup(app)
    try:
        yield
    finally:
        await run_complete_shutdown(app, logger)


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


def _should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    return isinstance(response, RedirectResponse) and settings.environment != "production"


def _add_cors_headers_to_response(response: Any, origin: str) -> None:
    """Add CORS headers to response."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID"


def _process_cors_if_needed(request: Request, response: Any) -> None:
    """Process CORS headers if needed."""
    if _should_add_cors_headers(response):
        origin = request.headers.get("origin")
        if origin:
            _add_cors_headers_to_response(response, origin)


@app.middleware("http")
async def cors_redirect_middleware(request: Request, call_next: Callable) -> Any:
    """Handle CORS for redirects (e.g., trailing slash redirects)."""
    response = await call_next(request)
    _process_cors_if_needed(request, response)
    return response


def _generate_context_ids(request: Request) -> Tuple[str, Optional[str]]:
    """Generate trace and request IDs."""
    trace_id = ErrorContext.generate_trace_id()
    request_id = request.headers.get("x-request-id")
    return trace_id, request_id


def _set_error_context(request_id: Optional[str]) -> None:
    """Set error context if request ID available."""
    if request_id:
        ErrorContext.set_request_id(request_id)


def _store_context_in_state(request: Request, trace_id: str, request_id: Optional[str]) -> None:
    """Store context in request state."""
    request.state.trace_id = trace_id
    request.state.request_id = request_id


def _setup_request_context(request: Request) -> Tuple[str, Optional[str]]:
    """Setup request context with trace and request IDs."""
    trace_id, request_id = _generate_context_ids(request)
    _set_error_context(request_id)
    _store_context_in_state(request, trace_id, request_id)
    return trace_id, request_id


def _add_context_headers(response: Any, trace_id: str, request_id: Optional[str]) -> None:
    """Add context headers to response."""
    response.headers["x-trace-id"] = trace_id
    if request_id:
        response.headers["x-request-id"] = request_id


@app.middleware("http")
async def error_context_middleware(request: Request, call_next: Callable) -> Any:
    """Middleware to set up error context for each request."""
    trace_id, request_id = _setup_request_context(request)
    response = await call_next(request)
    _add_context_headers(response, trace_id, request_id)
    return response


def _calculate_request_duration(start_time: float) -> str:
    """Calculate and format request duration."""
    process_time = (time.time() - start_time) * 1000
    return f'{process_time:.2f}ms'


def _log_request_details(logger: logging.Logger, request: Request, response: Any, duration: str) -> None:
    """Log request details with timing information."""
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    logger.info(f"Request: {request.method} {request.url.path} | Status: {response.status_code} | Duration: {duration} | Trace: {trace_id}")


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Any:
    """Log request details with timing."""
    logger = central_logger.get_logger("api")
    start_time = time.time()
    response = await call_next(request)
    duration = _calculate_request_duration(start_time)
    _log_request_details(logger, request, response, duration)
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
from app.routes.websockets import router as websockets_router

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