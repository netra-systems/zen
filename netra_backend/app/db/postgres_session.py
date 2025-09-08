"""PostgreSQL session management and validation module.

Handles session validation, error handling, and async session context management.
Now enhanced with resilience patterns for pragmatic rigor and degraded operation.
Focused module adhering to 25-line function limit and modular architecture.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.exc import DatabaseError, DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger

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
    from netra_backend.app.db.postgres_core import async_session_factory
    if async_session_factory is None:
        logger.error("async_session_factory is not initialized.")
        raise RuntimeError("Database unavailable (session factory initialization failed - check database URL and connectivity)")


def _validate_async_session(session):
    """Validate async session type and raise error if invalid."""
    if not validate_session(session):
        error_msg = get_session_validation_error(session)
        logger.error(f"Invalid session type: {error_msg}")
        raise RuntimeError(f"Database session error: {error_msg}")


async def _handle_async_transaction_error(session: AsyncSession, e: Exception):
    """Handle async transaction error with rollback and resilience tracking."""
    # Only rollback if session is in valid state with active transaction
    if (hasattr(session, 'is_active') and session.is_active and
        hasattr(session, 'in_transaction') and session.in_transaction()):
        try:
            await session.rollback()
        except Exception:
            # If rollback fails, let context manager handle cleanup
            pass
    
    # Track connection health for resilience manager
    if isinstance(e, (OperationalError, DatabaseError, DisconnectionError)):
        try:
            from netra_backend.app.db.postgres_resilience import postgres_resilience
            postgres_resilience.set_connection_health(False)
            logger.warning(f"PostgreSQL connection marked unhealthy due to: {e}")
        except ImportError:
            pass  # Resilience module not available
    
    logger.error(f"Async DB session error: {e}", exc_info=True)
    raise


def _log_session_creation(session: AsyncSession):
    """Log async session creation for debugging."""
    logger.debug(f"Created async session: {type(session).__name__}")


async def _commit_session_transaction(session: AsyncSession):
    """Commit session transaction and yield session."""
    await session.commit()


def _setup_session_for_transaction():
    """Setup and validate session for transaction.
    
    DEPRECATED: This function creates sessions without proper lifecycle management.
    Should not be used directly - use get_async_db() or DatabaseManager.get_async_session().
    """
    from netra_backend.app.db.postgres_core import async_session_factory
    _validate_async_session_factory()
    # WARNING: Direct factory call without context management - will leak connections
    return async_session_factory()

async def _yield_session_with_validation(session: AsyncSession):
    """Validate and yield session for transaction."""
    _validate_async_session(session)
    _log_session_creation(session)
    yield session

async def _execute_session_transaction(session: AsyncSession):
    """Execute session transaction with proper handling."""
    try:
        async for validated_session in _yield_session_with_validation(session):
            yield validated_session
        await _commit_session_transaction(session)
    except Exception as e:
        await _handle_async_transaction_error(session, e)

@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Use netra_backend.app.database.get_db() for SSOT compliance.
    
    This function delegates to DatabaseManager to eliminate SSOT violations.
    All new code should import from netra_backend.app.database directly.
    """
    import warnings
    warnings.warn(
        "postgres_session.get_async_db() is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Delegate to DatabaseManager via the single source of truth
    from netra_backend.app.database import get_db
    # FIX: get_db() is now properly an async context manager after adding @asynccontextmanager decorator
    async with get_db() as session:
        try:
            # Mark connection as healthy on successful completion
            try:
                from netra_backend.app.db.postgres_resilience import postgres_resilience
                postgres_resilience.set_connection_health(True)
            except ImportError:
                pass  # Resilience module not available
                
            yield session
                
        except Exception as e:
            # Track connection health for resilience manager
            if isinstance(e, (OperationalError, DatabaseError, DisconnectionError)):
                try:
                    from netra_backend.app.db.postgres_resilience import postgres_resilience
                    postgres_resilience.set_connection_health(False)
                    logger.warning(f"PostgreSQL connection marked unhealthy due to: {e}")
                except ImportError:
                    pass  # Resilience module not available
            
            logger.error(f"Async DB session error: {e}")
            raise


@asynccontextmanager
async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Use netra_backend.app.database.get_db() for SSOT compliance.
    
    This function delegates to DatabaseManager to eliminate SSOT violations.
    All new code should import from netra_backend.app.database directly.
    """
    import warnings
    warnings.warn(
        "postgres_session.get_postgres_session() is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    async with get_async_db() as session:
        yield session