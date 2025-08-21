"""PostgreSQL operations manager for transactions.

Manages PostgreSQL database operations within distributed transactions.
"""

from typing import Dict, Any

from netra_backend.app.db.postgres import get_postgres_session
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PostgresOperationManager:
    """Manages PostgreSQL operations within transactions."""
    
    def __init__(self):
        """Initialize PostgreSQL operation manager."""
        self.active_sessions: Dict[str, Any] = {}
    
    async def begin_operation(self, transaction_id: str, operation_id: str) -> None:
        """Begin a new PostgreSQL operation."""
        if not self._has_active_session(transaction_id):
            await self._create_new_session(transaction_id)
    
    def _has_active_session(self, transaction_id: str) -> bool:
        """Check if transaction has active session."""
        return transaction_id in self.active_sessions
    
    async def _create_new_session(self, transaction_id: str) -> None:
        """Create new PostgreSQL session for transaction."""
        session = await get_postgres_session()
        await session.begin()
        self.active_sessions[transaction_id] = session
        logger.debug(f"Started PostgreSQL transaction: {transaction_id}")
    
    async def commit_operation(self, transaction_id: str) -> None:
        """Commit PostgreSQL transaction."""
        if self._has_active_session(transaction_id):
            await self._execute_commit(transaction_id)
    
    async def _execute_commit(self, transaction_id: str) -> None:
        """Execute commit and cleanup."""
        session = self.active_sessions[transaction_id]
        await session.commit()
        await self._close_and_cleanup(transaction_id, session)
        logger.debug(f"Committed PostgreSQL transaction: {transaction_id}")
    
    async def rollback_operation(self, transaction_id: str) -> None:
        """Rollback PostgreSQL transaction."""
        if self._has_active_session(transaction_id):
            await self._execute_rollback(transaction_id)
    
    async def _execute_rollback(self, transaction_id: str) -> None:
        """Execute rollback and cleanup."""
        session = self.active_sessions[transaction_id]
        await session.rollback()
        await self._close_and_cleanup(transaction_id, session)
        logger.debug(f"Rolled back PostgreSQL transaction: {transaction_id}")
    
    async def _close_and_cleanup(self, transaction_id: str, session) -> None:
        """Close session and cleanup resources."""
        await session.close()
        del self.active_sessions[transaction_id]