"""
ClickHouse Service
Provides service layer abstraction for ClickHouse database operations
"""
from typing import List

from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ClickHouseService:
    """Service layer for ClickHouse operations."""
    
    async def list_corpus_tables(self) -> List[str]:
        """List corpus tables from ClickHouse."""
        try:
            async with get_clickhouse_client() as client:
                tables = await client.fetch("SHOW TABLES LIKE 'netra_content_corpus_%'")
                return [table['name'] for table in tables]
        except Exception as e:
            logger.error(f"Failed to list corpus tables: {e}")
            raise
    
    async def list_all_tables(self) -> List[str]:
        """List all tables from ClickHouse."""
        try:
            async with get_clickhouse_client() as client:
                result = await client.execute_query("SHOW TABLES")
                if result:
                    return [row[0] for row in result]
                return []
        except Exception as e:
            logger.error(f"Failed to list ClickHouse tables: {e}")
            raise
    
    async def execute_health_check(self) -> bool:
        """Execute ClickHouse health check."""
        try:
            async with get_clickhouse_client() as client:
                await client.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False


# Singleton instance
clickhouse_service = ClickHouseService()

# Legacy function for backward compatibility
async def list_corpus_tables():
    return await clickhouse_service.list_corpus_tables()
