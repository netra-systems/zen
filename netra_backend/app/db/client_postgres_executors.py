"""PostgreSQL Query Executors

Query execution components with circuit breaker protection.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
from netra_backend.app.db.client_config import CircuitBreakerManager
from netra_backend.app.db.client_postgres_session import TransactionHandler
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QueryExecutor:
    """Execute database queries with circuit breaker protection."""
    
    @staticmethod
    async def execute_query_on_session(session: AsyncSession, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute query on session and return results."""
        result = await session.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def execute_read_operation(query: str, params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute read operation on database session."""
        async with TransactionHandler.get_session() as session:
            return await QueryExecutor.execute_query_on_session(session, query, params or {})

    @staticmethod
    async def handle_read_circuit_open() -> List[Dict[str, Any]]:
        """Handle circuit breaker open for read queries."""
        logger.warning("Read query blocked - circuit breaker open")
        return []

    @staticmethod
    async def create_read_operation(query: str, params: Optional[Dict[str, Any]]):
        """Create read operation function for circuit breaker."""
        async def _read_operation():
            return await QueryExecutor.execute_read_operation(query, params)
        return _read_operation

    @staticmethod
    async def create_postgres_operation(query: str, params: Optional[Dict[str, Any]]):
        """Create postgres operation that handles connection and delegates to read circuit."""
        async def _postgres_operation():
            read_circuit = await CircuitBreakerManager.get_read_circuit()
            read_operation = await QueryExecutor.create_read_operation(query, params)
            return await read_circuit.call(read_operation)
        return _postgres_operation

    @staticmethod
    async def execute_read_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute read query with circuit breaker protection."""
        postgres_circuit = await CircuitBreakerManager.get_postgres_circuit()
        read_circuit = await CircuitBreakerManager.get_read_circuit()
        
        # Use postgres circuit for connection-level operations
        try:
            postgres_operation = await QueryExecutor.create_postgres_operation(query, params)
            return await postgres_circuit.call(postgres_operation)
        except CircuitBreakerOpenError:
            return await QueryExecutor.handle_read_circuit_open()


class WriteExecutor:
    """Execute write operations with circuit breaker protection."""
    
    @staticmethod
    async def execute_write_on_session(session: AsyncSession, query: str, params: Dict[str, Any]) -> int:
        """Execute write query on session."""
        result = await session.execute(text(query), params)
        return result.rowcount or 0

    @staticmethod
    async def execute_write_operation(query: str, params: Optional[Dict[str, Any]]) -> int:
        """Execute write operation on database session."""
        async with TransactionHandler.get_session() as session:
            return await WriteExecutor.execute_write_on_session(session, query, params or {})

    @staticmethod
    async def handle_write_circuit_open():
        """Handle circuit breaker open for write queries."""
        logger.error("Write query blocked - circuit breaker open")
        raise CircuitBreakerOpenError("Write circuit breaker is open")

    @staticmethod
    async def create_write_operation(query: str, params: Optional[Dict[str, Any]]):
        """Create write operation function for circuit breaker."""
        async def _write_operation():
            return await WriteExecutor.execute_write_operation(query, params)
        return _write_operation

    @staticmethod
    async def execute_write_query(query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Execute write query with circuit breaker protection."""
        write_circuit = await CircuitBreakerManager.get_write_circuit()
        try:
            write_operation = await WriteExecutor.create_write_operation(query, params)
            return await write_circuit.call(write_operation)
        except CircuitBreakerOpenError:
            await WriteExecutor.handle_write_circuit_open()


class TransactionExecutor:
    """Execute database transactions with circuit breaker protection."""
    
    @staticmethod
    async def execute_single_query_in_transaction(session: AsyncSession, query: str, params: Optional[Dict[str, Any]]) -> None:
        """Execute single query in transaction."""
        await session.execute(text(query), params or {})

    @staticmethod
    async def execute_transaction_queries(queries: List[tuple]) -> bool:
        """Execute transaction queries on database session."""
        async with TransactionHandler.get_session() as session:
            for query, params in queries:
                await TransactionExecutor.execute_single_query_in_transaction(session, query, params)
            return True

    @staticmethod
    async def handle_transaction_circuit_open() -> bool:
        """Handle circuit breaker open for transactions."""
        logger.error("Transaction blocked - circuit breaker open")
        return False

    @staticmethod
    async def create_transaction_operation(queries: List[tuple]):
        """Create transaction operation function for circuit breaker."""
        async def _transaction_operation():
            return await TransactionExecutor.execute_transaction_queries(queries)
        return _transaction_operation

    @staticmethod
    async def execute_transaction(queries: List[tuple]) -> bool:
        """Execute multiple queries in transaction with protection."""
        write_circuit = await CircuitBreakerManager.get_write_circuit()
        try:
            transaction_operation = await TransactionExecutor.create_transaction_operation(queries)
            return await write_circuit.call(transaction_operation)
        except CircuitBreakerOpenError:
            return await TransactionExecutor.handle_transaction_circuit_open()