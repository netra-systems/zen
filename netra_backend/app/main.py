"""
Main FastAPI application module.
Entry point for the Netra AI Optimization Platform.

[U+1F534] CRITICAL AUTH ARCHITECTURE:
- This is the MAIN BACKEND service, NOT the auth service
- Auth service runs SEPARATELY on port 8001 (see app/auth/auth_service.py)
- This backend ONLY uses auth_integration to connect to auth service
- NEVER implement authentication logic here
- All auth operations go through auth_client

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""
import logging
from pathlib import Path
from shared.isolated_environment import get_env
from shared.environment_loading_ssot import StartupEnvironmentManager, BACKEND_CONFIG

# Load environment files using SSOT implementation
env_manager = get_env()
startup_manager = StartupEnvironmentManager(env_manager)
startup_manager.setup_service_environment(BACKEND_CONFIG)

# Configure logging for Cloud Run compatibility (prevents ANSI codes)
from netra_backend.app.core.logging_config import configure_cloud_run_logging, setup_exception_handler
configure_cloud_run_logging()
setup_exception_handler()

# Import unified logging first to ensure interceptor is set up
from netra_backend.app.logging_config import central_logger

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

from netra_backend.app.core.app_factory import create_app

app = create_app()


def _get_uvicorn_config() -> dict:
    """Get uvicorn server configuration with modern WebSocket support."""
    env_manager = get_env()
    host = env_manager.get("HOST", "0.0.0.0")
    port = int(env_manager.get("PORT", "8000"))
    
    # Modern uvicorn configuration that avoids deprecated WebSocket implementations
    config = {
        "host": host, 
        "port": port, 
        "reload": True,
        "reload_dirs": ["app"], 
        "reload_excludes": ["*/tests/*", "*/.pytest_cache/*"],
        # WebSocket configuration to avoid deprecated implementations
        "ws_ping_interval": 20.0,
        "ws_ping_timeout": 20.0,
        "ws_max_size": 16 * 1024 * 1024,  # 16MB
        # Use modern HTTP/WebSocket handling
        "http": "httptools",
        "loop": "auto",
        # Disable legacy WebSocket implementations
        "interface": "asgi3"
    }
    
    return config


def _run_development_server() -> None:
    """Run the FastAPI development server with uvicorn."""
    import uvicorn
    config = _get_uvicorn_config()
    uvicorn.run("main:app", **config)


if __name__ == "__main__":
    _run_development_server()
