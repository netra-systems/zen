"""Minimal dependencies for Auth Service - Uses Single Source of Truth.

Auth service specific dependencies without LLM imports.
CRITICAL: Uses single source of truth from netra_backend.app.database.
"""
from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Import from SINGLE SOURCE OF TRUTH
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.security_service import SecurityService

logger = central_logger.get_logger(__name__)


def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type."""
    if not isinstance(session, AsyncSession):
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(f"Expected AsyncSession, got {type(session)}")
    logger.debug(f"Dependency injected session type: {type(session).__name__}")


async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Wrapper for database dependency with validation.
    
    Uses single source of truth from netra_backend.app.database.
    """
    async for session in get_db():
        _validate_session_type(session)
        yield session

# LEGACY COMPATIBILITY: get_db_session for backward compatibility
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Legacy compatibility function for get_db_session.
    
    Use get_db_dependency instead for new code.
    """
    async for session in get_db_dependency():
        yield session


async def get_security_service(
    request: Request,
    db: AsyncSession = Depends(get_db_dependency)
) -> SecurityService:
    """Get security service instance."""
    return SecurityService(db)