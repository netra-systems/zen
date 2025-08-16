"""Database Client Configuration

Circuit breaker configurations and client settings for database operations.
"""

from app.core.circuit_breaker import CircuitConfig


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


class CircuitBreakerManager:
    """Manage circuit breaker instances for database operations."""
    
    @staticmethod
    async def get_postgres_circuit():
        """Get PostgreSQL circuit breaker."""
        from app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "postgres", DatabaseClientConfig.POSTGRES_CONFIG
        )

    @staticmethod
    async def get_read_circuit():
        """Get read operations circuit breaker."""
        from app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "db_read", DatabaseClientConfig.READ_CONFIG
        )

    @staticmethod
    async def get_write_circuit():
        """Get write operations circuit breaker."""
        from app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "db_write", DatabaseClientConfig.WRITE_CONFIG
        )

    @staticmethod
    async def get_clickhouse_circuit():
        """Get ClickHouse circuit breaker."""
        from app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "clickhouse", DatabaseClientConfig.CLICKHOUSE_CONFIG
        )


class HealthAssessment:
    """Assess database health from various status indicators."""
    
    @staticmethod
    def get_circuit_health_states(circuits_status) -> list:
        """Extract health states from circuits status."""
        return [c.get("health", "unknown") for c in circuits_status.values()]

    @staticmethod
    def evaluate_circuit_health(circuit_states: list) -> str:
        """Evaluate overall health from circuit states."""
        if "unhealthy" in circuit_states:
            return "degraded"
        elif "recovering" in circuit_states:
            return "recovering"
        else:
            return "healthy"

    @staticmethod
    def assess_overall_health(connection_status, circuits_status) -> str:
        """Assess overall database health."""
        if connection_status.get("status") != "healthy":
            return "unhealthy"
        
        circuit_states = HealthAssessment.get_circuit_health_states(circuits_status)
        return HealthAssessment.evaluate_circuit_health(circuit_states)

    @staticmethod
    def build_health_response(connection_status, circuits_status) -> dict:
        """Build comprehensive health check response."""
        return {
            "connection": connection_status,
            "circuits": circuits_status,
            "overall_health": HealthAssessment.assess_overall_health(connection_status, circuits_status)
        }