"""PostgreSQL Database Client

Main resilient database client with circuit breaker protection.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.client_postgres_session import TransactionHandler
from netra_backend.app.client_postgres_executors import QueryExecutor, WriteExecutor, TransactionExecutor
from netra_backend.app.client_postgres_health import PostgresHealthChecker
from netra_backend.app.client_config import CircuitBreakerManager


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
        """Get read circuit breaker for database operations."""
        return await CircuitBreakerManager.get_read_circuit()
    
    async def _get_postgres_circuit(self):
        """Get postgres circuit breaker for database operations."""
        return await CircuitBreakerManager.get_postgres_circuit()

    async def _test_connection(self) -> Dict[str, Any]:
        """Test database connection for health checks."""
        return await PostgresHealthChecker.test_connection()

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check."""
        return await PostgresHealthChecker.health_check()