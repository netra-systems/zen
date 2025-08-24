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
import os
import sys
from pathlib import Path

# Conditional import of environment management
try:
    from netra_backend.app.core.isolated_environment import get_env
    _env_available = True
except ImportError:
    # Fallback for production environments where dev_launcher might not be available
    def get_env():
        """Fallback environment manager for production."""
        class ProductionEnv:
            def get(self, key: str, default=None):
                return os.environ.get(key, default)
            def set(self, key: str, value: str, source: str = "production"):
                os.environ[key] = value
        return ProductionEnv()
    _env_available = False

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


def _get_project_root() -> Path:
    """Get the project root path."""
    # main.py is in netra_backend/app/, so project root is two levels up
    return Path(__file__).parent.parent.parent


def _load_all_env_files(root_path: Path) -> None:
    """Load all environment files in order."""
    _load_base_env_file(root_path)
    _load_development_env_file(root_path)
    _load_local_development_env_file(root_path)


def _setup_environment_files() -> None:
    """Load environment files ONLY if not already loaded by dev launcher."""
    env_manager = get_env()
    
    # Check if dev launcher already loaded environment variables
    # by looking for specific environment variables that dev launcher sets
    dev_launcher_indicators = [
        'DEV_LAUNCHER_ACTIVE',  # Explicit flag from dev launcher
        'CROSS_SERVICE_AUTH_TOKEN',  # Token set by dev launcher
    ]
    
    # If any dev launcher indicator is present, skip loading
    for indicator in dev_launcher_indicators:
        if env_manager.get(indicator):
            print(f"Dev launcher detected via {indicator} - skipping .env loading")
            return
    
    # Check if critical environment variables are already set
    # This handles cases where env vars are set directly without dev launcher
    critical_vars = ['LLM_MODE', 'DATABASE_URL', 'GEMINI_API_KEY']
    vars_already_set = sum(1 for var in critical_vars if env_manager.get(var))
    
    # If most critical vars are already set, assume external loading
    if vars_already_set >= len(critical_vars) // 2:
        print("Critical environment variables already set - skipping .env loading")
        return
    
    # Only load for direct uvicorn runs when environment is not pre-configured
    try:
        root_path = _get_project_root()
        print("Loading .env files for direct application run")
        _load_all_env_files(root_path)
    except ImportError: 
        print("python-dotenv not available - skipping .env loading")
        pass

# Load environment files only if needed
_setup_environment_files()

# Import unified logging first to ensure interceptor is set up
from netra_backend.app.logging_config import central_logger

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

from netra_backend.app.core.app_factory import create_app

app = create_app()


def _get_uvicorn_config() -> dict:
    """Get uvicorn server configuration."""
    return {
        "host": "0.0.0.0", "port": 8000, "reload": True,
        "reload_dirs": ["app"], "reload_excludes": ["*/tests/*", "*/.pytest_cache/*"]
    }


def _run_development_server() -> None:
    """Run the FastAPI development server with uvicorn."""
    import uvicorn
    config = _get_uvicorn_config()
    uvicorn.run("main:app", **config)


if __name__ == "__main__":
    _run_development_server()