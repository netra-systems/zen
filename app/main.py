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

# Load environment files in the correct order
try:
    from dotenv import load_dotenv
    root_path = Path(__file__).parent.parent
    
    # Load in order of precedence (lowest to highest)
    # 1. Base .env file
    env_path = root_path / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env file from {env_path}")
    
    # 2. Development environment file
    env_dev_path = root_path / '.env.development'
    if env_dev_path.exists():
        load_dotenv(env_dev_path, override=True)
        print(f"Loaded .env.development file from {env_dev_path}")
    
    # 3. Local development file (Terraform-generated)
    env_local_path = root_path / '.env.development.local'
    if env_local_path.exists():
        load_dotenv(env_local_path, override=True)
        print(f"Loaded .env.development.local file from {env_local_path}")
except ImportError:
    # dotenv not installed, skip
    pass

# Import unified logging first to ensure interceptor is set up
from app.logging_config import central_logger

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

from app.core.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["*/tests/*", "*/.pytest_cache/*"]
    )