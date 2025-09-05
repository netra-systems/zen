#!/usr/bin/env python3
"""
Start Backend in Resource-Aware Mode
This script starts the backend with minimal resource usage for local development.
"""

import os
import sys
import subprocess
from pathlib import Path

def start_backend():
    """Start the backend server with resource-aware settings."""
    
    # Set project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add project root and netra_backend to Python path
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / 'netra_backend'))
    
    # Set PYTHONPATH environment variable
    pythonpath_parts = [
        str(project_root),
        str(project_root / 'netra_backend'),
    ]
    os.environ['PYTHONPATH'] = os.pathsep.join(pythonpath_parts)
    
    # Resource-aware environment variables
    env_vars = {
        "ENVIRONMENT": "development",
        "BUILD_ENV": "development",
        "LOG_LEVEL": "INFO",
        "WORKERS": "1",
        "PORT": "8000",
        
        # Use SQLite for lightweight local development
        "USE_SQLITE": "true",
        "DATABASE_URL": "sqlite:///./netra_local.db",
        
        # Disable heavy features
        "ENABLE_MONITORING": "false",
        "ENABLE_TRACING": "false",
        "ENABLE_METRICS": "false",
        "ENABLE_WEBSOCKET_COMPRESSION": "true",
        
        # Memory optimization
        "MAX_CONNECTIONS": "10",
        "CONNECTION_POOL_SIZE": "5",
        "CACHE_SIZE": "100",
        
        # LLM settings (use local/mock for testing)
        "USE_MOCK_LLM": "false",
        "LLM_PROVIDER": "openai",
        "LLM_MAX_CONCURRENT": "1",
    }
    
    # Update environment
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("=" * 60)
    print("Starting Netra Backend in Resource-Aware Mode")
    print("=" * 60)
    print(f"Environment: {env_vars['ENVIRONMENT']}")
    print(f"Port: {env_vars['PORT']}")
    print(f"Workers: {env_vars['WORKERS']}")
    print(f"Database: SQLite (local file)")
    print("Features disabled: Monitoring, Tracing, Metrics")
    print("=" * 60)
    
    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "netra_backend.app.main:app",
        "--host", "0.0.0.0",
        "--port", env_vars["PORT"],
        "--workers", env_vars["WORKERS"],
        "--limit-concurrency", "10",
        "--limit-max-requests", "1000",
        "--log-level", env_vars["LOG_LEVEL"].lower(),
        "--reload"  # Enable auto-reload for development
    ]
    
    print(f"\nStarting server at http://localhost:{env_vars['PORT']}")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nBackend stopped.")
        sys.exit(0)

if __name__ == "__main__":
    start_backend()