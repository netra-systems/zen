"""PostgreSQL Index Connection Management

Connection management for PostgreSQL index operations.
"""

from app.logging_config import central_logger
from app.db.postgres import async_engine
from app.db.index_optimizer_core import DatabaseValidation

logger = central_logger.get_logger(__name__)


class PostgreSQLConnectionManager:
    """Manage PostgreSQL async connections safely."""
    
    @staticmethod
    async def get_raw_connection():
        """Get raw connection with proper validation."""
        if not DatabaseValidation.validate_async_engine(async_engine):
            return None
        if not DatabaseValidation.validate_raw_connection_method(async_engine):
            logger.error("async_engine missing raw_connection method")
            return None
        try:
            return await async_engine.raw_connection()
        except Exception as e:
            logger.error(f"Failed to get raw connection: {e}")
            return None
    
    @staticmethod
    async def execute_on_raw_connection(conn, query: str):
        """Execute query on raw connection."""
        async_conn = conn.driver_connection
        await async_conn.execute(query)
    
    @staticmethod
    async def close_connection_safely(conn):
        """Close connection with error handling."""
        try:
            await conn.close()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")