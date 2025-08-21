"""Minimal FastAPI application entry point for reduced resource usage.

This lightweight main module provides essential API endpoints and health checks
while excluding heavy components like full WebSocket management, database migrations,
and complex agent systems. Ideal for development environments with limited resources
or when debugging specific components in isolation.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

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
    pass

# Minimal lifespan handler for resource management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan handler."""
    print("Starting minimal app...")
    yield
    print("Shutting down minimal app...")

# Create minimal app
app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Minimal Netra API"}

@app.get("/health/live")
def health_live():
    return {"status": "alive"}

@app.get("/health/ready")
def health_ready():
    return {"status": "ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        lifespan="on"
    )