"""Circuit breaker-enabled database client for reliable data operations.

This module provides database clients with circuit breaker protection,
connection pooling, and comprehensive error handling for production environments.

This module has been refactored into focused sub-modules for maintainability.
"""

# Import all components from the refactored modules
from netra_backend.app.db.client_config import (
    DatabaseClientConfig, CircuitBreakerManager, HealthAssessment
)
from netra_backend.app.db.client_postgres_session import (
    SessionManager, TransactionHandler
)
from netra_backend.app.db.client_postgres_executors import (
    QueryExecutor, WriteExecutor, TransactionExecutor
)
from netra_backend.app.db.client_postgres_health import (
    PostgresHealthChecker
)
from netra_backend.app.db.client_postgres import (
    ResilientDatabaseClient
)
from netra_backend.app.db.client_clickhouse import (
    ClickHouseQueryExecutor, ClickHouseHealthChecker, ClickHouseDatabaseClient
)
from netra_backend.app.db.client_manager import (
    DatabaseClientManager, db_client_manager, get_db_client, get_clickhouse_client
)

# Maintain backward compatibility exports
__all__ = [
    'DatabaseClientConfig',
    'ResilientDatabaseClient',
    'ClickHouseDatabaseClient',
    'DatabaseClientManager',
    'db_client_manager',
    'get_db_client',
    'get_clickhouse_client'
]