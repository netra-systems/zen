"""PostgreSQL Session Management

Session and transaction lifecycle management for PostgreSQL client.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError

from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
from netra_backend.app.db.postgres import get_async_db, async_session_factory
from netra_backend.app.logging_config import central_logger
from netra_backend.app.client_config import CircuitBreakerManager

logger = central_logger.get_logger(__name__)


class SessionManager:
    """Manage database session lifecycle."""
    
    @staticmethod
    async def create_session_factory() -> AsyncSession:
        """Create database session via factory."""
        if async_session_factory is None:
            raise RuntimeError("Database not configured")
        return async_session_factory()

    @staticmethod
    async def commit_session(session: AsyncSession) -> None:
        """Commit session transaction."""
        await session.commit()

    @staticmethod
    async def rollback_session(session: AsyncSession, error: Exception) -> None:
        """Rollback session on error."""
        await session.rollback()
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