"""ClickHouse Database Client

ClickHouse-specific database client with circuit breaker protection.
"""

from typing import Any, Dict, List, Optional

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.logging_config import central_logger
from .client_config import CircuitBreakerManager

logger = central_logger.get_logger(__name__)


class ClickHouseQueryExecutor:
    """Execute ClickHouse queries with circuit breaker protection."""
    
    @staticmethod
    async def create_clickhouse_query_executor(query: str, params: Optional[Dict[str, Any]]):
        """Create ClickHouse query executor function."""
        async def _execute_ch_query() -> List[Dict[str, Any]]:
            from app.db.clickhouse import get_clickhouse_client
            async with get_clickhouse_client() as ch_client:
                return await ch_client.execute_query(query, params)
        return _execute_ch_query

    @staticmethod
    async def handle_clickhouse_circuit_open() -> List[Dict[str, Any]]:
        """Handle ClickHouse circuit breaker open."""
        logger.warning("ClickHouse query blocked - circuit breaker open")
        return []

    @staticmethod
    async def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with circuit breaker."""
        circuit = await CircuitBreakerManager.get_clickhouse_circuit()
        try:
            query_executor = await ClickHouseQueryExecutor.create_clickhouse_query_executor(query, params)
            return await circuit.call(query_executor)
        except CircuitBreakerOpenError:
            return await ClickHouseQueryExecutor.handle_clickhouse_circuit_open()


class ClickHouseHealthChecker:
    """Health checking for ClickHouse connections."""
    
    @staticmethod
    async def test_clickhouse_connectivity() -> None:
        """Test basic ClickHouse connectivity."""
        await ClickHouseQueryExecutor.execute_query("SELECT 1")

    @staticmethod
    async def build_healthy_response(circuit_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build healthy health check response."""
        return {"status": "healthy", "circuit": circuit_status}

    @staticmethod
    async def build_unhealthy_response(error: Exception) -> Dict[str, Any]:
        """Build unhealthy health check response."""
        return {"status": "unhealthy", "error": str(error)}

    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """ClickHouse health check."""
        try:
            circuit = await CircuitBreakerManager.get_clickhouse_circuit()
            circuit_status = circuit.get_status()
            await ClickHouseHealthChecker.test_clickhouse_connectivity()
            return await ClickHouseHealthChecker.build_healthy_response(circuit_status)
        except Exception as e:
            return await ClickHouseHealthChecker.build_unhealthy_response(e)


class ClickHouseDatabaseClient:
    """ClickHouse client with circuit breaker protection."""
    
    def __init__(self) -> None:
        pass

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with circuit breaker."""
        return await ClickHouseQueryExecutor.execute_query(query, params)

    async def health_check(self) -> Dict[str, Any]:
        """ClickHouse health check."""
        return await ClickHouseHealthChecker.health_check()