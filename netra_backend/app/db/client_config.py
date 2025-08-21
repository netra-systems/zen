"""Database Client Configuration

Circuit breaker configurations and client settings for database operations.
"""

from netra_backend.app.core.circuit_breaker import CircuitConfig


class DatabaseClientConfig:
    """Configuration for database circuit breakers with pragmatic rigor.
    
    Circuit breakers are configured to be resilient and permissive,
    defaulting to functional operation rather than strict failure modes.
    """
    
    # PostgreSQL circuit breaker config - more lenient for resilience
    POSTGRES_CONFIG = CircuitConfig(
        name="postgres",
        failure_threshold=8,  # Increased from 5 for more tolerance
        recovery_timeout=20.0,  # Reduced from 30 for faster recovery
        timeout_seconds=25.0,  # Increased from 15 for more patience
        half_open_max_calls=5  # Increased from 2 for better testing
    )
    
    # ClickHouse circuit breaker config - less aggressive
    CLICKHOUSE_CONFIG = CircuitConfig(
        name="clickhouse",
        failure_threshold=6,  # Increased from 3 for tolerance
        recovery_timeout=30.0,  # Reduced from 45 for faster recovery
        timeout_seconds=30.0,  # Increased from 20 for more patience
        half_open_max_calls=3  # Increased from 1 for better recovery
    )
    
    # Read-only operations (very lenient for resilience)
    READ_CONFIG = CircuitConfig(
        name="db_read",
        failure_threshold=10,  # Increased from 7 for more tolerance
        recovery_timeout=15.0,  # Reduced from 20 for faster recovery
        timeout_seconds=12.0,  # Slightly increased for patience
        half_open_max_calls=5  # More calls for testing recovery
    )
    
    # Write operations (more tolerant but careful)
    WRITE_CONFIG = CircuitConfig(
        name="db_write",
        failure_threshold=5,  # Increased from 3 for tolerance
        recovery_timeout=45.0,  # Reduced from 60 for faster recovery
        timeout_seconds=20.0,  # Increased from 15 for patience
        half_open_max_calls=3  # More calls for testing recovery
    )
    
    # Retry configuration for exponential backoff
    RETRY_CONFIG = {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 10.0,
        "exponential_base": 2.0,
        "jitter": True
    }
    
    # Cache configuration for fallback responses
    CACHE_CONFIG = {
        "query_cache_ttl": 300,  # 5 minutes
        "health_cache_ttl": 60,   # 1 minute
        "max_cache_size": 1000
    }


class CircuitBreakerManager:
    """Manage circuit breaker instances for database operations.
    
    Provides resilient circuit breakers configured for pragmatic operation,
    with fallback mechanisms and degraded service capabilities.
    """
    
    @staticmethod
    async def get_postgres_circuit():
        """Get PostgreSQL circuit breaker."""
        from netra_backend.app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "postgres", DatabaseClientConfig.POSTGRES_CONFIG
        )

    @staticmethod
    async def get_read_circuit():
        """Get read operations circuit breaker."""
        from netra_backend.app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "db_read", DatabaseClientConfig.READ_CONFIG
        )

    @staticmethod
    async def get_write_circuit():
        """Get write operations circuit breaker."""
        from netra_backend.app.core.circuit_breaker import circuit_registry
        return circuit_registry.get_breaker(
            "db_write", DatabaseClientConfig.WRITE_CONFIG
        )

    @staticmethod
    async def get_clickhouse_circuit():
        """Get ClickHouse circuit breaker."""
        from netra_backend.app.core.circuit_breaker import circuit_registry
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