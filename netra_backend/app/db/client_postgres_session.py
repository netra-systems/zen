"""PostgreSQL Session Management

Session and transaction lifecycle management for PostgreSQL client.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
from netra_backend.app.db.client_config import CircuitBreakerManager
from netra_backend.app.db.postgres import async_session_factory, get_async_db
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SessionManager:
    """Manage database session lifecycle."""
    
    @staticmethod
    async def create_session_factory() -> AsyncSession:
        """Create database session via factory.
        
        CRITICAL: This method should NOT be called directly!
        Sessions must be managed through proper context managers.
        Use TransactionHandler.get_session() instead.
        """
        if async_session_factory is None:
            raise RuntimeError("Database not configured")
        # WARNING: Direct factory call - caller MUST manage session lifecycle
        return async_session_factory()

    @staticmethod
    async def commit_session(session: AsyncSession) -> None:
        """Commit session transaction."""
        # Only commit if session is active and has a transaction
        if hasattr(session, 'is_active') and session.is_active:
            if hasattr(session, 'in_transaction') and session.in_transaction():
                await session.commit()

    @staticmethod
    async def rollback_session(session: AsyncSession, error: Exception) -> None:
        """Rollback session on error."""
        # Only rollback if session is in valid state with active transaction
        if (hasattr(session, 'is_active') and session.is_active and
            hasattr(session, 'in_transaction') and session.in_transaction()):
            try:
                await session.rollback()
            except Exception:
                # If rollback fails, let context manager handle cleanup
                pass
        logger.error(f"Database session error: {error}")
        raise

    @staticmethod
    async def close_session(session: AsyncSession) -> None:
        """Close session safely."""
        await session.close()


class TransactionHandler:
    """Handle database transactions with proper lifecycle management."""
    
    @staticmethod
    async def _yield_session_and_commit(session: AsyncSession):
        """Yield session and commit if successful."""
        yield session
        await SessionManager.commit_session(session)

    @staticmethod
    async def handle_session_transaction(session: AsyncSession):
        """Handle session transaction with commit/rollback."""
        try:
            async for s in TransactionHandler._yield_session_and_commit(session):
                yield s
        except Exception as e:
            await SessionManager.rollback_session(session, e)
        finally:
            await SessionManager.close_session(session)

    @staticmethod
    async def create_protected_session() -> AsyncSession:
        """Create session through circuit breaker."""
        postgres_circuit = await CircuitBreakerManager.get_postgres_circuit()
        return await postgres_circuit.call(SessionManager.create_session_factory)

    @staticmethod
    async def handle_circuit_breaker_error() -> None:
        """Handle circuit breaker open error."""
        logger.error("Database session blocked - circuit breaker open")
        raise CircuitBreakerOpenError("Database circuit breaker is open")

    @staticmethod
    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """Get database session with circuit breaker protection."""
        try:
            session = await TransactionHandler.create_protected_session()
            async for s in TransactionHandler.handle_session_transaction(session):
                yield s
        except CircuitBreakerOpenError:
            await TransactionHandler.handle_circuit_breaker_error()