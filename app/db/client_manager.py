"""Database Client Manager

Manages all database clients and provides unified interface.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncGenerator

from app.core.circuit_breaker import circuit_registry
from .client_postgres import ResilientDatabaseClient
from .client_clickhouse import ClickHouseDatabaseClient


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