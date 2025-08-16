"""Circuit breaker-enabled database client for reliable data operations.

This module provides database clients with circuit breaker protection,
connection pooling, and comprehensive error handling for production environments.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError

from app.core.circuit_breaker import (
    CircuitBreaker, CircuitConfig, CircuitBreakerOpenError, circuit_registry
)
from app.db.postgres import get_async_db, async_session_factory
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseClientConfig:
    """Configuration for database circuit breakers."""
    
    # PostgreSQL circuit breaker config
    POSTGRES_CONFIG = CircuitConfig(
        name="postgres",
        failure_threshold=5,
        recovery_timeout=30.0,
        timeout_seconds=15.0,
        half_open_max_calls=2
    )
    
    # ClickHouse circuit breaker config
    CLICKHOUSE_CONFIG = CircuitConfig(
        name="clickhouse",
        failure_threshold=3,
        recovery_timeout=45.0,
        timeout_seconds=20.0,
        half_open_max_calls=1
    )
    
    # Read-only operations (more lenient)
    READ_CONFIG = CircuitConfig(
        name="db_read",
        failure_threshold=7,
        recovery_timeout=20.0,
        timeout_seconds=10.0
    )
    
    # Write operations (stricter)
    WRITE_CONFIG = CircuitConfig(
        name="db_write",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout_seconds=15.0
    )


class ResilientDatabaseClient:
    """Database client with circuit breaker protection."""
    
    def __init__(self) -> None:
        self._postgres_circuit: Optional[CircuitBreaker] = None
        self._read_circuit: Optional[CircuitBreaker] = None
        self._write_circuit: Optional[CircuitBreaker] = None
    
    async def _get_postgres_circuit(self) -> CircuitBreaker:
        """Get PostgreSQL circuit breaker."""
        if not self._postgres_circuit:
            self._postgres_circuit = await circuit_registry.get_circuit(
                "postgres", DatabaseClientConfig.POSTGRES_CONFIG
            )
        return self._postgres_circuit
    
    async def _get_read_circuit(self) -> CircuitBreaker:
        """Get read operations circuit breaker."""
        if not self._read_circuit:
            self._read_circuit = await circuit_registry.get_circuit(
                "db_read", DatabaseClientConfig.READ_CONFIG
            )
        return self._read_circuit
    
    async def _get_write_circuit(self) -> CircuitBreaker:
        """Get write operations circuit breaker."""
        if not self._write_circuit:
            self._write_circuit = await circuit_registry.get_circuit(
                "db_write", DatabaseClientConfig.WRITE_CONFIG
            )
        return self._write_circuit
    
    async def _create_session_factory(self) -> AsyncSession:
        """Create database session via factory."""
        if async_session_factory is None:
            raise RuntimeError("Database not configured")
        return async_session_factory()
    
    async def _handle_session_transaction(self, session: AsyncSession):
        """Handle session transaction with commit/rollback."""
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with circuit breaker protection."""
        postgres_circuit = await self._get_postgres_circuit()
        try:
            session = await postgres_circuit.call(self._create_session_factory)
            async for s in self._handle_session_transaction(session):
                yield s
        except CircuitBreakerOpenError:
            logger.error("Database session blocked - circuit breaker open")
            raise
    
    async def _execute_read_operation(self, query: str, params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute read operation on database session."""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def _handle_read_circuit_open(self) -> List[Dict[str, Any]]:
        """Handle circuit breaker open for read queries."""
        logger.warning("Read query blocked - circuit breaker open")
        return []
    
    async def execute_read_query(self, 
                                query: str, 
                                params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute read query with circuit breaker protection."""
        read_circuit = await self._get_read_circuit()
        try:
            async def _read_operation():
                return await self._execute_read_operation(query, params)
            return await read_circuit.call(_read_operation)
        except CircuitBreakerOpenError:
            return await self._handle_read_circuit_open()
    
    async def _execute_write_operation(self, query: str, params: Optional[Dict[str, Any]]) -> int:
        """Execute write operation on database session."""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return result.rowcount or 0
    
    async def _handle_write_circuit_open(self):
        """Handle circuit breaker open for write queries."""
        logger.error("Write query blocked - circuit breaker open")
        raise CircuitBreakerOpenError("Write circuit breaker is open")
    
    async def execute_write_query(self, 
                                 query: str, 
                                 params: Optional[Dict[str, Any]] = None) -> int:
        """Execute write query with circuit breaker protection."""
        write_circuit = await self._get_write_circuit()
        try:
            async def _write_operation():
                return await self._execute_write_operation(query, params)
            return await write_circuit.call(_write_operation)
        except CircuitBreakerOpenError:
            await self._handle_write_circuit_open()
    
    async def _execute_transaction_queries(self, queries: List[tuple]) -> bool:
        """Execute transaction queries on database session."""
        async with self.get_session() as session:
            for query, params in queries:
                await session.execute(text(query), params or {})
            return True
    
    async def _handle_transaction_circuit_open(self) -> bool:
        """Handle circuit breaker open for transactions."""
        logger.error("Transaction blocked - circuit breaker open")
        return False
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in transaction with protection."""
        write_circuit = await self._get_write_circuit()
        try:
            async def _transaction_operation():
                return await self._execute_transaction_queries(queries)
            return await write_circuit.call(_transaction_operation)
        except CircuitBreakerOpenError:
            return await self._handle_transaction_circuit_open()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check."""
        try:
            # Test basic connectivity
            connection_status = await self._test_connection()
            
            # Get circuit statuses
            circuits_status = await self._get_circuits_status()
            
            return {
                "connection": connection_status,
                "circuits": circuits_status,
                "overall_health": self._assess_health(connection_status, circuits_status)
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "error": str(e),
                "overall_health": "unhealthy"
            }
    
    async def _test_connection(self) -> Dict[str, Any]:
        """Test database connection."""
        try:
            result = await self.execute_read_query("SELECT 1 as test")
            return {
                "status": "healthy",
                "test_query": len(result) == 1
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _get_circuits_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all database circuits."""
        status = {}
        
        if self._postgres_circuit:
            status["postgres"] = self._postgres_circuit.get_status()
        if self._read_circuit:
            status["read"] = self._read_circuit.get_status()
        if self._write_circuit:
            status["write"] = self._write_circuit.get_status()
        
        return status
    
    def _assess_health(self, 
                      connection_status: Dict[str, Any], 
                      circuits_status: Dict[str, Dict[str, Any]]) -> str:
        """Assess overall database health."""
        if connection_status.get("status") != "healthy":
            return "unhealthy"
        
        circuit_states = [c.get("health", "unknown") for c in circuits_status.values()]
        
        if "unhealthy" in circuit_states:
            return "degraded"
        elif "recovering" in circuit_states:
            return "recovering"
        else:
            return "healthy"


class ClickHouseDatabaseClient:
    """ClickHouse client with circuit breaker protection."""
    
    def __init__(self) -> None:
        self._circuit: Optional[CircuitBreaker] = None
    
    async def _get_circuit(self) -> CircuitBreaker:
        """Get ClickHouse circuit breaker."""
        if not self._circuit:
            self._circuit = await circuit_registry.get_circuit(
                "clickhouse", DatabaseClientConfig.CLICKHOUSE_CONFIG
            )
        return self._circuit
    
    async def execute_query(self, 
                           query: str, 
                           params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with circuit breaker."""
        circuit = await self._get_circuit()
        
        async def _execute_ch_query() -> List[Dict[str, Any]]:
            """Execute ClickHouse query using configured client."""
            from app.db.clickhouse import get_clickhouse_client
            
            async with get_clickhouse_client() as ch_client:
                return await ch_client.execute_query(query, params)
        
        try:
            return await circuit.call(_execute_ch_query)
        except CircuitBreakerOpenError:
            logger.warning("ClickHouse query blocked - circuit breaker open")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """ClickHouse health check."""
        try:
            circuit = await self._get_circuit()
            circuit_status = circuit.get_status()
            
            # Test basic connectivity
            await self.execute_query("SELECT 1")
            
            return {
                "status": "healthy",
                "circuit": circuit_status
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


class DatabaseClientManager:
    """Manager for all database clients."""
    
    def __init__(self) -> None:
        self.postgres_client = ResilientDatabaseClient()
        self.clickhouse_client = ClickHouseDatabaseClient()
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check for all database clients."""
        return {
            "postgres": await self.postgres_client.health_check(),
            "clickhouse": await self.clickhouse_client.health_check()
        }
    
    async def get_all_circuit_status(self) -> Dict[str, Any]:
        """Get status of all database circuits."""
        return await circuit_registry.get_all_status()


# Global database client manager
db_client_manager = DatabaseClientManager()


@asynccontextmanager
async def get_db_client() -> AsyncGenerator[ResilientDatabaseClient, None]:
    """Context manager for getting database client."""
    yield db_client_manager.postgres_client


@asynccontextmanager
async def get_clickhouse_client() -> AsyncGenerator[ClickHouseDatabaseClient, None]:
    """Context manager for getting ClickHouse client."""
    yield db_client_manager.clickhouse_client