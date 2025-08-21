"""PostgreSQL Index Creation

Index creation operations for PostgreSQL optimization.
"""

from typing import List
from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.index_optimizer_core import (
    IndexCreationResult,
    IndexExistenceChecker,
    DatabaseErrorHandler
)
from netra_backend.app.db.postgres_index_connection import PostgreSQLConnectionManager

logger = central_logger.get_logger(__name__)


class PostgreSQLIndexCreator:
    """Handle PostgreSQL index creation operations."""
    
    def __init__(self):
        self.connection_manager = PostgreSQLConnectionManager()
        self.index_checker = IndexExistenceChecker()
    
    async def _build_create_index_query(self, table_name: str, columns: List[str],
                                      index_name: str, index_type: str) -> str:
        """Build CREATE INDEX query."""
        column_list = ", ".join(columns)
        return f"""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} 
            ON {table_name} USING {index_type} ({column_list})
        """
    
    async def _execute_index_creation(self, query: str) -> bool:
        """Execute index creation with proper connection handling."""
        conn = await self.connection_manager.get_raw_connection()
        if conn is None:
            return False
        
        try:
            await self.connection_manager.execute_on_raw_connection(conn, query)
            return True
        finally:
            await self.connection_manager.close_connection_safely(conn)
    
    async def _handle_existing_index(self, index_name: str) -> IndexCreationResult:
        """Handle case where index already exists."""
        return IndexCreationResult(index_name, True, "", True)
    
    async def _handle_creation_success(self, index_name: str) -> IndexCreationResult:
        """Handle successful index creation."""
        self.index_checker.add_existing_index(index_name)
        return IndexCreationResult(index_name, True)
    
    async def _handle_creation_failure(self, index_name: str) -> IndexCreationResult:
        """Handle index creation failure."""
        return IndexCreationResult(index_name, False, "Connection failed")
    
    async def _handle_creation_exception(self, e: Exception, index_name: str) -> IndexCreationResult:
        """Handle exception during index creation."""
        if DatabaseErrorHandler.is_already_exists_error(e):
            self.index_checker.add_existing_index(index_name)
            return IndexCreationResult(index_name, True, "", True)
        else:
            error_msg = str(e)
            DatabaseErrorHandler.log_index_creation_error(index_name, e)
            return IndexCreationResult(index_name, False, error_msg)
    
    async def create_single_index(self, table_name: str, columns: List[str],
                                index_name: str, index_type: str = "btree") -> IndexCreationResult:
        """Create a single database index."""
        if self.index_checker.index_exists(index_name):
            return await self._handle_existing_index(index_name)
        
        try:
            query = await self._build_create_index_query(table_name, columns, index_name, index_type)
            success = await self._execute_index_creation(query)
            return await self._handle_creation_success(index_name) if success else await self._handle_creation_failure(index_name)
        except Exception as e:
            return await self._handle_creation_exception(e, index_name)