"""PostgreSQL Database Client

PostgreSQL-specific database client with circuit breaker protection.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.db.postgres import get_async_db, async_session_factory
from app.logging_config import central_logger
from .client_config import CircuitBreakerManager, HealthAssessment

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
    async def handle_session_transaction(session: AsyncSession):
        """Handle session transaction with commit/rollback."""
        try:
            yield session
            await SessionManager.commit_session(session)
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
    async def execute_read_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute read query with circuit breaker protection."""
        read_circuit = await CircuitBreakerManager.get_read_circuit()
        try:
            read_operation = await QueryExecutor.create_read_operation(query, params)
            return await read_circuit.call(read_operation)
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


class PostgresHealthChecker:
    """Health checking for PostgreSQL connections."""
    
    @staticmethod
    async def execute_connection_test() -> Dict[str, Any]:
        """Execute connection test query."""
        result = await QueryExecutor.execute_read_query("SELECT 1 as test")
        return {"status": "healthy", "test_query": len(result) == 1}

    @staticmethod
    async def handle_connection_error(error: Exception) -> Dict[str, Any]:
        """Handle connection test error."""
        return {"status": "unhealthy", "error": str(error)}

    @staticmethod
    async def test_connection() -> Dict[str, Any]:
        """Test database connection."""
        try:
            return await PostgresHealthChecker.execute_connection_test()
        except Exception as e:
            return await PostgresHealthChecker.handle_connection_error(e)

    @staticmethod
    def add_circuit_status(status: Dict[str, Dict[str, Any]], name: str, circuit) -> None:
        """Add circuit status to status dict."""
        if circuit:
            status[name] = circuit.get_status()

    @staticmethod
    async def get_circuits_status() -> Dict[str, Dict[str, Any]]:
        """Get status of all database circuits."""
        status = {}
        postgres_circuit = await CircuitBreakerManager.get_postgres_circuit()
        read_circuit = await CircuitBreakerManager.get_read_circuit()
        write_circuit = await CircuitBreakerManager.get_write_circuit()
        
        PostgresHealthChecker.add_circuit_status(status, "postgres", postgres_circuit)
        PostgresHealthChecker.add_circuit_status(status, "read", read_circuit)
        PostgresHealthChecker.add_circuit_status(status, "write", write_circuit)
        return status

    @staticmethod
    async def perform_health_checks() -> tuple:
        """Perform connection and circuit health checks."""
        connection_status = await PostgresHealthChecker.test_connection()
        circuits_status = await PostgresHealthChecker.get_circuits_status()
        return connection_status, circuits_status

    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """Comprehensive database health check."""
        try:
            connection_status, circuits_status = await PostgresHealthChecker.perform_health_checks()
            return HealthAssessment.build_health_response(connection_status, circuits_status)
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"error": str(e), "overall_health": "unhealthy"}


class ResilientDatabaseClient:
    """Database client with circuit breaker protection."""
    
    def __init__(self) -> None:
        pass

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with circuit breaker protection."""
        async with TransactionHandler.get_session() as session:
            yield session

    async def execute_read_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute read query with circuit breaker protection."""
        return await QueryExecutor.execute_read_query(query, params)

    async def execute_write_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Execute write query with circuit breaker protection."""
        return await WriteExecutor.execute_write_query(query, params)

    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in transaction with protection."""
        return await TransactionExecutor.execute_transaction(queries)

    async def _get_read_circuit(self):
        """Get read circuit breaker for testing."""
        return await CircuitBreakerManager.get_read_circuit()

    async def _test_connection(self) -> Dict[str, Any]:
        """Test database connection for health checks."""
        return await PostgresHealthChecker.test_connection()

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check."""
        return await PostgresHealthChecker.health_check()