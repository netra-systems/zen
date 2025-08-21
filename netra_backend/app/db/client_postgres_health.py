"""PostgreSQL Health Checking

Health monitoring and circuit breaker status for PostgreSQL client.
"""

from typing import Any, Dict

from app.logging_config import central_logger
from netra_backend.app.client_config import CircuitBreakerManager, HealthAssessment
from netra_backend.app.client_postgres_executors import QueryExecutor

logger = central_logger.get_logger(__name__)


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
    async def _get_all_circuits():
        """Get all circuit breaker instances."""
        postgres_circuit = await CircuitBreakerManager.get_postgres_circuit()
        read_circuit = await CircuitBreakerManager.get_read_circuit()
        write_circuit = await CircuitBreakerManager.get_write_circuit()
        return postgres_circuit, read_circuit, write_circuit

    @staticmethod
    async def get_circuits_status() -> Dict[str, Dict[str, Any]]:
        """Get status of all database circuits."""
        status = {}
        postgres_circuit, read_circuit, write_circuit = await PostgresHealthChecker._get_all_circuits()
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