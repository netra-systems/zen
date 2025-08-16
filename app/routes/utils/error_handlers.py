"""Error handling utilities for route handlers."""

from fastapi import HTTPException
from app.logging_config import central_logger
from typing import Any, NoReturn


logger = central_logger.get_logger(__name__)


def handle_service_error(e: Exception, service: str) -> NoReturn:
    """Handle service errors with logging."""
    logger.error(f"{service} error: {e}")
    raise HTTPException(status_code=500, detail=f"{service} unavailable")


def handle_not_found_error(resource: str, identifier: str) -> NoReturn:
    """Handle resource not found errors."""
    raise HTTPException(
        status_code=404, 
        detail=f"{resource} '{identifier}' not found"
    )


def handle_access_denied_error() -> NoReturn:
    """Handle access denied errors."""
    raise HTTPException(status_code=403, detail="Access denied")


def handle_validation_error(message: str) -> NoReturn:
    """Handle validation errors."""
    raise HTTPException(status_code=400, detail=message)


def handle_database_error(e: Exception) -> NoReturn:
    """Handle database errors."""
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=503, detail="Database unavailable")


def handle_auth_error(message: str) -> NoReturn:
    """Handle authentication errors."""
    logger.error(f"Authentication error: {message}")
    raise HTTPException(status_code=401, detail="Authentication failed")


def handle_circuit_breaker_error(e: Exception, operation: str) -> NoReturn:
    """Handle circuit breaker errors."""
    logger.error(f"Circuit breaker {operation} failed: {e}")
    raise HTTPException(status_code=500, detail=f"{operation} unavailable")


def handle_job_error(e: Exception, operation: str) -> NoReturn:
    """Handle job operation errors."""
    logger.error(f"Job {operation} failed: {e}")
    raise HTTPException(status_code=500, detail=f"Job {operation} failed")