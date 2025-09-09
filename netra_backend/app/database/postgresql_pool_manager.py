"""PostgreSQL Pool Manager for asyncpg-style database operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal (database infrastructure)
- Business Goal: Provide consistent database connection pool interface
- Value Impact: Enables reliable database operations for analytics pipelines
- Strategic Impact: Supports data-driven business insights and operations
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import json

from netra_backend.app.logging_config import central_logger
from netra_backend.app.database import get_db

logger = central_logger.get_logger(__name__)


class AsyncPGConnection:
    """Wrapper to provide asyncpg-like interface for SQLAlchemy sessions."""
    
    def __init__(self, session):
        """Initialize connection wrapper.
        
        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session
    
    async def execute(self, query: str, *args) -> None:
        """Execute a query with parameters.
        
        Args:
            query: SQL query string
            *args: Query parameters
        """
        try:
            from sqlalchemy import text
            
            # Convert positional args to named parameters if needed
            if args:
                # Simple parameter conversion - for more complex cases, this could be enhanced
                param_dict = {}
                query_with_params = query
                
                for i, arg in enumerate(args):
                    param_name = f"param_{i + 1}"
                    param_dict[param_name] = arg
                    # Replace $1, $2, etc. with :param_1, :param_2, etc.
                    query_with_params = query_with_params.replace(f"${i + 1}", f":{param_name}")
                
                await self.session.execute(text(query_with_params), param_dict)
            else:
                await self.session.execute(text(query))
                
            logger.debug(f"Executed query with {len(args)} parameters")
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    async def executemany(self, query: str, params: List[tuple]) -> None:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params: List of parameter tuples
        """
        try:
            from sqlalchemy import text
            
            for param_tuple in params:
                # Convert positional args to named parameters
                param_dict = {}
                query_with_params = query
                
                for i, arg in enumerate(param_tuple):
                    param_name = f"param_{i + 1}"
                    param_dict[param_name] = arg
                    query_with_params = query_with_params.replace(f"${i + 1}", f":{param_name}")
                
                await self.session.execute(text(query_with_params), param_dict)
            
            logger.debug(f"Executed query {len(params)} times")
            
        except Exception as e:
            logger.error(f"Executemany failed: {str(e)}")
            raise
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch multiple rows from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        try:
            from sqlalchemy import text
            
            # Convert positional args to named parameters if needed
            if args:
                param_dict = {}
                query_with_params = query
                
                for i, arg in enumerate(args):
                    param_name = f"param_{i + 1}"
                    param_dict[param_name] = arg
                    query_with_params = query_with_params.replace(f"${i + 1}", f":{param_name}")
                
                result = await self.session.execute(text(query_with_params), param_dict)
            else:
                result = await self.session.execute(text(query))
            
            # Convert rows to dictionaries
            rows = []
            for row in result.fetchall():
                row_dict = {}
                for key, value in row._mapping.items():
                    # Handle JSONB columns by parsing JSON strings
                    if isinstance(value, str) and key.endswith('_data'):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass  # Keep original value if not valid JSON
                    row_dict[key] = value
                rows.append(row_dict)
            
            logger.debug(f"Fetched {len(rows)} rows")
            return rows
            
        except Exception as e:
            logger.error(f"Fetch query failed: {str(e)}")
            raise
    
    async def fetchone(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch one row from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Dictionary representing the row, or None if no row found
        """
        try:
            rows = await self.fetch(query, *args)
            return rows[0] if rows else None
            
        except Exception as e:
            logger.error(f"Fetchone query failed: {str(e)}")
            raise
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Single value from the query result
        """
        try:
            row = await self.fetchone(query, *args)
            if row:
                # Return the first column value
                return list(row.values())[0] if row else None
            return None
            
        except Exception as e:
            logger.error(f"Fetchval query failed: {str(e)}")
            raise


class PostgreSQLPoolManager:
    """Pool manager for PostgreSQL connections with asyncpg-compatible interface."""
    
    def __init__(self):
        """Initialize PostgreSQL pool manager."""
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the pool manager."""
        if not self._initialized:
            self._initialized = True
            logger.info("PostgreSQL Pool Manager initialized")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection with asyncpg-compatible interface.
        
        Yields:
            AsyncPGConnection: Connection wrapper with asyncpg-like methods
        """
        try:
            async with get_db() as session:
                connection = AsyncPGConnection(session)
                logger.debug("Created asyncpg-compatible connection wrapper")
                yield connection
                
        except Exception as e:
            logger.error(f"Failed to get database connection: {str(e)}")
            raise
    
    async def execute(self, query: str, *args) -> None:
        """Execute a query without returning results.
        
        Args:
            query: SQL query string
            *args: Query parameters
        """
        async with self.get_connection() as conn:
            await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch multiple rows from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchone(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch one row from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Dictionary representing the row, or None if no row found
        """
        async with self.get_connection() as conn:
            return await conn.fetchone(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Single value from the query result
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def close(self) -> None:
        """Close the pool manager."""
        logger.debug("PostgreSQL Pool Manager closed")
        # Since we're using SQLAlchemy sessions, no explicit cleanup needed
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get pool status information.
        
        Returns:
            Dictionary with pool status details
        """
        return {
            "initialized": self._initialized,
            "pool_type": "SQLAlchemy AsyncSession Pool",
            "status": "active" if self._initialized else "inactive"
        }