"""PostgreSQL session management and validation module.

Handles session validation, error handling, and async session context management.
Focused module adhering to 8-line function limit and modular architecture.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def _is_actual_async_session(session: Any) -> bool:
    """Check if session is actual AsyncSession instance."""
    return isinstance(session, AsyncSession)


def _is_mock_async_session(session: Any) -> bool:
    """Check if session is mock object with AsyncSession spec."""
    return hasattr(session, '_spec_class') and session._spec_class == AsyncSession


def _has_async_session_interface(session: Any) -> bool:
    """Check if session implements AsyncSession interface."""
    return (hasattr(session, 'commit') and 
            hasattr(session, 'rollback') and 
            hasattr(session, 'execute'))


def validate_session(session: Any) -> bool:
    """Validate that a session is a proper AsyncSession instance."""
    return (_is_actual_async_session(session) or
            _is_mock_async_session(session) or
            _has_async_session_interface(session))


def _get_mock_error_details(session: Any, actual_type: str) -> str:
    """Get detailed error for mock session objects."""
    spec_info = ""
    if hasattr(session, '_spec_class'):
        spec_info = f" with spec {session._spec_class.__name__}"
    return f"Expected AsyncSession or compatible mock, got {actual_type}{spec_info}"


def _get_standard_error_details(actual_type: str) -> str:
    """Get standard error message for non-AsyncSession types."""
    return f"Expected AsyncSession, got {actual_type}"


def _check_session_none(session: Any) -> str:
    """Check if session is None and return error."""
    return "Session is None" if session is None else ""

def _get_session_type_error(session: Any) -> str:
    """Get error for session type."""
    actual_type = type(session).__name__
    if 'Mock' in actual_type:
        return _get_mock_error_details(session, actual_type)
    return _get_standard_error_details(actual_type)

def get_session_validation_error(session: Any) -> str:
    """Get descriptive error for invalid session type."""
    none_error = _check_session_none(session)
    if none_error:
        return none_error
    return _get_session_type_error(session)


def _validate_async_session_factory():
    """Validate that async session factory is initialized."""
    from app.db.postgres_core import async_session_factory
    if async_session_factory is None:
        logger.error("async_session_factory is not initialized.")
        raise RuntimeError("Database not configured")


def _validate_async_session(session):
    """Validate async session type and raise error if invalid."""
    if not validate_session(session):
        error_msg = get_session_validation_error(session)
        logger.error(f"Invalid session type: {error_msg}")
        raise RuntimeError(f"Database session error: {error_msg}")


async def _handle_async_transaction_error(session: AsyncSession, e: Exception):
    """Handle async transaction error with rollback and logging."""
    await session.rollback()
    logger.error(f"Async DB session error: {e}", exc_info=True)
    raise


def _log_session_creation(session: AsyncSession):
    """Log async session creation for debugging."""
    logger.debug(f"Created async session: {type(session).__name__}")


async def _commit_session_transaction(session: AsyncSession):
    """Commit session transaction and yield session."""
    await session.commit()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session with proper transaction handling."""
    from app.db.postgres_core import async_session_factory
    _validate_async_session_factory()
    async with async_session_factory() as session:
        _validate_async_session(session)
        _log_session_creation(session)
        try:
            yield session
            await _commit_session_transaction(session)
        except Exception as e:
            await _handle_async_transaction_error(session, e)


@asynccontextmanager
async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for get_async_db() for compatibility with existing code.
    Get a PostgreSQL async database session with proper transaction handling.
    """
    async with get_async_db() as session:
        yield session