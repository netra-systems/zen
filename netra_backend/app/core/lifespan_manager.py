"""
Application lifespan management module.
Manages FastAPI application startup and shutdown lifecycle.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from netra_backend.app.shutdown import run_complete_shutdown
from netra_backend.app.startup_module import run_complete_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's startup and shutdown events."""
    start_time, logger = await run_complete_startup(app)
    try:
        yield
    finally:
        await run_complete_shutdown(app, logger)