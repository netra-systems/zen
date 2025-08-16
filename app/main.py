"""
Main FastAPI application module.
Entry point for the Netra AI Optimization Platform.
"""
import sys
import os
from pathlib import Path
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def _load_base_env_file(root_path: Path) -> None:
    """Load base .env file if it exists."""
    env_path = root_path / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"Loaded .env file from {env_path}")


def _load_development_env_file(root_path: Path) -> None:
    """Load development .env file if it exists."""
    env_dev_path = root_path / '.env.development'
    if env_dev_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_dev_path, override=True)
        print(f"Loaded .env.development file from {env_dev_path}")


def _load_local_development_env_file(root_path: Path) -> None:
    """Load local development .env file if it exists."""
    env_local_path = root_path / '.env.development.local'
    if env_local_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_local_path, override=True)
        print(f"Loaded .env.development.local file from {env_local_path}")


def _get_project_root() -> Path:
    """Get the project root path."""
    return Path(__file__).parent.parent


def _load_all_env_files(root_path: Path) -> None:
    """Load all environment files in order."""
    _load_base_env_file(root_path)
    _load_development_env_file(root_path)
    _load_local_development_env_file(root_path)


def _setup_environment_files() -> None:
    """Load environment files in the correct order of precedence."""
    try:
        root_path = _get_project_root()
        _load_all_env_files(root_path)
    except ImportError: pass


# Load environment files in the correct order
_setup_environment_files()

# Import unified logging first to ensure interceptor is set up
from app.logging_config import central_logger

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

from app.core.app_factory import create_app

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