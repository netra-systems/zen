"""Minimal dependencies for Auth Service - Uses Single Source of Truth.

Auth service specific dependencies without LLM imports.
CRITICAL: Uses single source of truth from netra_backend.app.database.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Import from SINGLE SOURCE OF TRUTH
from netra_backend.app.database import get_db, get_system_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.security_service import SecurityService

logger = central_logger.get_logger(__name__)


def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type."""
    from shared.database.session_validation import validate_db_session
    
    try:
        validate_db_session(session, "auth_dependencies_validation")
    except TypeError as e:
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(str(e))
    logger.debug(f"Dependency injected session type: {type(session).__name__}")


async def get_request_scoped_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped database session with validation.
    
    FastAPI-compatible async generator (no @asynccontextmanager decorator).
    Uses single source of truth from netra_backend.app.database.
    """
    async with get_db() as session:
        _validate_session_type(session)
        yield session

# Alias for backward compatibility
async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Use get_request_scoped_db_session instead.
    
    FastAPI-compatible async generator (no @asynccontextmanager decorator).
    Kept for backward compatibility.
    """
    logger.warning("Using deprecated get_db_dependency - consider get_request_scoped_db_session")
    async with get_db() as session:
        _validate_session_type(session)
        yield session

# LEGACY COMPATIBILITY: get_db_session for backward compatibility
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Legacy compatibility function for get_db_session.
    
    FastAPI-compatible async generator (no @asynccontextmanager decorator).
    Use get_db_dependency instead for new code.
    """
    async with get_db() as session:
        _validate_session_type(session)
        yield session


async def get_request_scoped_db_session_for_fastapi() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible wrapper for get_request_scoped_db_session.
    
    CRITICAL: This function properly wraps the async context manager to work with
    FastAPI's dependency injection system. It avoids the '_AsyncGeneratorContextManager'
    object has no attribute 'execute' error by properly yielding the session.
    """
    logger.debug("Creating FastAPI-compatible auth request-scoped database session")
    
    try:
        # Use async for since get_request_scoped_db_session is an async generator
        async for session in get_request_scoped_db_session():
            logger.debug(f"Yielding FastAPI-compatible auth session: {id(session)}")
            yield session
            logger.debug(f"FastAPI-compatible auth session {id(session)} completed")
    except Exception as e:
        logger.error(f"Failed to create FastAPI-compatible auth request-scoped database session: {e}")
        raise


async def get_security_service(
    request: Request,
    db: AsyncSession = Depends(get_request_scoped_db_session_for_fastapi)
) -> SecurityService:
    """Get security service instance."""
    return SecurityService(db)


async def get_system_db_session() -> AsyncGenerator[AsyncSession, None]:
    """System database session that bypasses authentication.
    
    CRITICAL: For internal system operations only.
    Never expose this to user-facing endpoints.
    
    Use cases:
    - Health checks
    - Background tasks
    - System initialization
    """
    async with get_system_db() as session:
        _validate_session_type(session)
        yield session