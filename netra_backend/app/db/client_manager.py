"""Database Client Manager

Manages all database clients and provides unified interface.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from netra_backend.app.core.circuit_breaker import circuit_registry
from netra_backend.app.db.clickhouse import ClickHouseService
from netra_backend.app.db.client_postgres import ResilientDatabaseClient


class DatabaseClientManager:
    """DEPRECATED: Manager for all database clients - Use DatabaseManager instead.
    
    This class has been DEPRECATED to eliminate SSOT violations.
    Use netra_backend.app.db.database_manager.DatabaseManager directly.
    """
    
    def __init__(self) -> None:
        import warnings
        warnings.warn(
            "DatabaseClientManager is deprecated. Use DatabaseManager from netra_backend.app.db.database_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to DatabaseManager
        from netra_backend.app.db.database_manager import DatabaseManager
        self._database_manager = DatabaseManager.get_connection_manager()

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """DEPRECATED: Health check - delegates to DatabaseManager."""
        from netra_backend.app.db.database_manager import DatabaseManager
        return await DatabaseManager.health_check_all()

    async def get_all_circuit_status(self) -> Dict[str, Any]:
        """DEPRECATED: Get circuits status - delegates to DatabaseManager."""
        from netra_backend.app.db.database_manager import DatabaseManager
        return DatabaseManager.get_all_circuit_status()


# Global database client manager
db_client_manager = DatabaseClientManager()


@asynccontextmanager
async def get_db_client() -> AsyncGenerator[ResilientDatabaseClient, None]:
    """Context manager for getting database client."""
    yield db_client_manager.postgres_client


@asynccontextmanager
async def get_clickhouse_client() -> AsyncGenerator[ClickHouseService, None]:
    """Context manager for getting ClickHouse client."""
    yield db_client_manager.clickhouse_client