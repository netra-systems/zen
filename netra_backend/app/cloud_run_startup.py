"""
Cloud Run startup wrapper for proper async context handling.
Ensures proper initialization in containerized environments.
"""
import asyncio
import sys
import os
import uvicorn
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def setup_cloud_run_environment():
    """Configure environment for Cloud Run."""
    # Ensure asyncio uses the default event loop policy
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    # Set environment variables for Cloud Run
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    
    # Disable interactive mode
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def get_port():
    """Get port from environment or default."""
    return int(os.environ.get("PORT", 8080))


def get_workers():
    """Get worker count from environment or default."""
    return int(os.environ.get("WORKERS", 1))


def get_timeout():
    """Get timeout from environment or default."""
    return int(os.environ.get("TIMEOUT", 120))


def run_server():
    """Run the uvicorn server with proper configuration."""
    setup_cloud_run_environment()
    config = _create_server_config()
    uvicorn.run(**config)


def _create_server_config() -> dict:
    """Create uvicorn server configuration."""
    return _build_server_config_dict()


def _build_server_config_dict() -> dict:
    """Build server configuration dictionary."""
    return {
        "app": "app.main:app", "host": "0.0.0.0", "port": get_port(),
        "loop": "asyncio", "log_level": "info",
        "access_log": True, "use_colors": False, "timeout_keep_alive": get_timeout()
    }


if __name__ == "__main__":
    run_server()