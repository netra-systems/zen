"""Minimal dependencies for Auth Service.

Auth service specific dependencies without LLM imports.
"""
from typing import AsyncGenerator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import get_async_db as _get_async_db
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type."""
    if not isinstance(session, AsyncSession):
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(f"Expected AsyncSession, got {type(session)}")
    logger.debug(f"Dependency injected session type: {type(session).__name__}")


async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Wrapper for database dependency with validation."""
    async with _get_async_db() as session:
        _validate_session_type(session)
        yield session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for auth routes."""
    async for session in get_db_dependency():
        yield session


async def get_security_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> SecurityService:
    """Get security service instance."""
    return SecurityService(db)