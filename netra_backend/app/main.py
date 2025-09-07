"""
Main FastAPI application module.
Entry point for the Netra AI Optimization Platform.

🔴 CRITICAL AUTH ARCHITECTURE:
- This is the MAIN BACKEND service, NOT the auth service
- Auth service runs SEPARATELY on port 8001 (see app/auth/auth_service.py)
- This backend ONLY uses auth_integration to connect to auth service
- NEVER implement authentication logic here
- All auth operations go through auth_client

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""
import logging
from pathlib import Path
from netra_backend.app.core.project_utils import get_project_root as _get_project_root

from shared.isolated_environment import get_env

# Add the project root to the Python path

def _load_base_env_file(root_path: Path) -> None:
    """Load base .env file if it exists."""
    env_path = root_path / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)


def _load_development_env_file(root_path: Path) -> None:
    """Load development .env file if it exists."""
    env_dev_path = root_path / '.env.development'
    if env_dev_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_dev_path, override=True)


def _load_local_development_env_file(root_path: Path) -> None:
    """Load local development .env file if it exists."""
    env_local_path = root_path / '.env.development.local'
    if env_local_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_local_path, override=True)



def _load_all_env_files(root_path: Path) -> None:
    """Load all environment files in order."""
    _load_base_env_file(root_path)
    _load_development_env_file(root_path)
    _load_local_development_env_file(root_path)


def _setup_environment_files() -> None:
    """Load environment files ONLY if not already loaded by dev launcher."""
    env_manager = get_env()
    
    # CRITICAL: Never load .env files in staging or production
    # All configuration comes from Cloud Run environment variables and Google Secret Manager
    environment = env_manager.get('ENVIRONMENT', '').lower()
    if environment in ['staging', 'production', 'prod']:
        # Running in production/staging - skipping all .env file loading (using GSM)
        return
    
    # Check if dev launcher already loaded environment variables
    # by looking for specific environment variables that dev launcher sets
    dev_launcher_indicators = [
        'DEV_LAUNCHER_ACTIVE',  # Explicit flag from dev launcher
        'CROSS_SERVICE_AUTH_TOKEN',  # Token set by dev launcher
    ]
    
    # If any dev launcher indicator is present, skip loading
    for indicator in dev_launcher_indicators:
        if env_manager.get(indicator):
            # Dev launcher detected - skipping .env loading
            return
    
    # Check if critical environment variables are already set
    # This handles cases where env vars are set directly without dev launcher
    critical_vars = ['LLM_MODE', 'POSTGRES_HOST', 'GEMINI_API_KEY']
    vars_already_set = sum(1 for var in critical_vars if env_manager.get(var))
    
    # If most critical vars are already set, assume external loading
    if vars_already_set >= len(critical_vars) // 2:
        # Critical environment variables already set - skipping .env loading
        return
    
    # Only load for direct uvicorn runs when environment is not pre-configured
    try:
        root_path = _get_project_root()
        # Loading .env files for direct application run
        _load_all_env_files(root_path)
    except ImportError: 
        # python-dotenv not available - skipping .env loading
        pass

# Load environment files only if needed
_setup_environment_files()

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
