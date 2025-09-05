#!/usr/bin/env python3
"""
Lightweight Backend Startup Script
Runs backend directly without Docker, using SQLite for minimal resource usage.
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Set up environment for lightweight backend operation."""
    
    # Set project root
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    # Add to Python path
    sys.path.insert(0, str(project_root))
    
    # Minimal environment setup
    env_vars = {
        # Core settings
        "ENVIRONMENT": "development",
        "BUILD_ENV": "development",
        "LOG_LEVEL": "INFO",
        
        # Database - use SQLite for lightweight operation
        "DATABASE_URL": "sqlite:///./netra_local.db",
        "USE_SQLITE": "true",
        
        # Disable resource-intensive features
        "ENABLE_MONITORING": "false",
        "ENABLE_TRACING": "false",
        "ENABLE_METRICS": "false",
        "ENABLE_WEBSOCKET": "true",
        "ENABLE_WEBSOCKET_COMPRESSION": "true",
        
        # Redis - disable for lite mode
        "REDIS_URL": "",
        "USE_REDIS": "false",
        
        # Auth service - simplified
        "AUTH_SERVICE_URL": "http://localhost:8081",
        "BYPASS_AUTH": "true",  # For development only
        
        # LLM settings
        "LLM_PROVIDER": "openai",
        "USE_MOCK_LLM": "false",
        
        # Performance settings
        "MAX_CONNECTIONS": "10",
        "CONNECTION_POOL_SIZE": "5",
        "CACHE_SIZE": "100",
        
        # Server settings
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "WORKERS": "1",
        "RELOAD": "true",
    }
    
    # Apply environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    return project_root, env_vars

def check_dependencies():
    """Check if required Python packages are installed."""
    required = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"WARNING: Missing packages: {', '.join(missing)}")
        print("Installing missing packages...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True)
        print("OK: Packages installed")
    
    return True

def start_backend(project_root, env_vars):
    """Start the backend server."""
    
    print("=" * 60)
    print("NETRA Backend - Lightweight Mode")
    print("=" * 60)
    print(f"Project: {project_root}")
    print(f"Server: http://localhost:{env_vars['PORT']}")
    print(f"Database: SQLite (local file)")
    print(f"Features: Minimal resource usage mode")
    print("=" * 60)
    print()
    
    # Build uvicorn command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "netra_backend.app.main:app",
        "--host", env_vars["HOST"],
        "--port", env_vars["PORT"],
        "--reload",
        "--log-level", env_vars["LOG_LEVEL"].lower(),
        "--limit-concurrency", "10",
        "--limit-max-requests", "1000"
    ]
    
    print("Starting server...")
    print(f"Command: {' '.join(cmd)}")
    print("\nPress Ctrl+C to stop\n")
    
    # Set PYTHONPATH
    os.environ["PYTHONPATH"] = str(project_root)
    
    try:
        result = subprocess.run(cmd, env=os.environ.copy())
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n\nBackend stopped")
        return True
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def main():
    """Main entry point."""
    try:
        # Setup environment
        project_root, env_vars = setup_environment()
        
        # Check dependencies
        if not check_dependencies():
            print("ERROR: Failed to install dependencies")
            sys.exit(1)
        
        # Start backend
        if not start_backend(project_root, env_vars):
            print("ERROR: Backend failed to start")
            sys.exit(1)
            
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()