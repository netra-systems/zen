"""
SSOT Database Query Executor - Centralized database operation patterns.

This module provides Single Source of Truth patterns for database operations,
ensuring consistent SQLAlchemy 2.0+ compatibility and proper error handling.

CRITICAL: All database raw SQL queries MUST use this SSOT executor to ensure:
- SQLAlchemy 2.0+ compatibility with text() wrapper
- Consistent error handling and logging
- Proper session management
- Type safety with strongly typed results

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Eliminates SQLAlchemy 2.0+ compatibility errors in staging/production
- Strategic Impact: Single source of truth for all database query patterns

Key Features:
- Automatic text() wrapper for raw SQL queries
- Consistent error handling and logging
- Session management integration
- Type-safe query result handling
- PostgreSQL and SQLite compatibility

USAGE EXAMPLES:

# Health checks
result = await executor.execute_scalar_query(
    session, "SELECT 1 as test_value"
)

# Table existence checks  
table_count = await executor.execute_scalar_query(
    session, 
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
)

# Index information
indexes = await executor.execute_fetchall_query(
    session,
    "SELECT COUNT(*) FROM pg_indexes WHERE tablename IN ('users', 'sessions')"
)
"""

import logging
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

logger = logging.getLogger(__name__)


class SSOTDatabaseQueryExecutor:
    """
    Single Source of Truth for database query execution patterns.
    
    Provides centralized, SQLAlchemy 2.0+ compatible query execution
    with proper error handling, logging, and type safety.
    """
    
    def __init__(self):
        """Initialize SSOT database query executor."""
        self.logger = logger

    async def execute_scalar_query(
        self, 
        session: AsyncSession, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a query and return a single scalar value.
        
        Args:
            session: SQLAlchemy async session
            query: Raw SQL query string
            parameters: Optional query parameters
            
        Returns:
            Single scalar value result
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            self.logger.debug(f"Executing scalar query: {query[:100]}...")
            
            # CRITICAL: Use text() wrapper for SQLAlchemy 2.0+ compatibility
            if parameters:
                result = await session.execute(text(query), parameters)
            else:
                result = await session.execute(text(query))
            
            scalar_result = result.scalar()
            
            self.logger.debug(f"Scalar query result: {scalar_result}")
            return scalar_result
            
        except Exception as e:
            error_msg = f"Scalar query execution failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseQueryError(error_msg, query=query, parameters=parameters) from e
    
    async def execute_fetchall_query(
        self, 
        session: AsyncSession, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Execute a query and return all results as a list.
        
        Args:
            session: SQLAlchemy async session
            query: Raw SQL query string
            parameters: Optional query parameters
            
        Returns:
            List of result rows
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            self.logger.debug(f"Executing fetchall query: {query[:100]}...")
            
            # CRITICAL: Use text() wrapper for SQLAlchemy 2.0+ compatibility
            if parameters:
                result = await session.execute(text(query), parameters)
            else:
                result = await session.execute(text(query))
            
            all_results = result.fetchall()
            
            self.logger.debug(f"Fetchall query returned {len(all_results)} rows")
            return all_results
            
        except Exception as e:
            error_msg = f"Fetchall query execution failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseQueryError(error_msg, query=query, parameters=parameters) from e
    
    async def execute_fetchone_query(
        self, 
        session: AsyncSession, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Execute a query and return the first result row.
        
        Args:
            session: SQLAlchemy async session
            query: Raw SQL query string
            parameters: Optional query parameters
            
        Returns:
            First result row or None
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            self.logger.debug(f"Executing fetchone query: {query[:100]}...")
            
            # CRITICAL: Use text() wrapper for SQLAlchemy 2.0+ compatibility
            if parameters:
                result = await session.execute(text(query), parameters)
            else:
                result = await session.execute(text(query))
            
            first_result = result.fetchone()
            
            self.logger.debug(f"Fetchone query result: {first_result}")
            return first_result
            
        except Exception as e:
            error_msg = f"Fetchone query execution failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseQueryError(error_msg, query=query, parameters=parameters) from e
    
    async def execute_health_check_query(
        self, 
        session: AsyncSession, 
        test_value: int = 1
    ) -> bool:
        """
        Execute standard health check query.
        
        Args:
            session: SQLAlchemy async session
            test_value: Expected test value (default: 1)
            
        Returns:
            True if health check passes, False otherwise
        """
        try:
            result = await self.execute_scalar_query(
                session, 
                f"SELECT {test_value} as test_value"
            )
            
            is_healthy = (result == test_value)
            self.logger.debug(f"Health check result: {is_healthy} (expected: {test_value}, got: {result})")
            
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"Health check query failed: {str(e)}")
            return False
    
    async def execute_table_count_query(
        self, 
        session: AsyncSession, 
        schema: str = "public"
    ) -> int:
        """
        Get count of tables in specified schema.
        
        Args:
            session: SQLAlchemy async session
            schema: Database schema name (default: public)
            
        Returns:
            Number of tables in schema
        """
        try:
            query = """
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = :schema
            """
            
            result = await self.execute_scalar_query(
                session, 
                query, 
                parameters={"schema": schema}
            )
            
            return int(result) if result is not None else 0
            
        except Exception as e:
            self.logger.error(f"Table count query failed: {str(e)}")
            return 0
    
    async def execute_table_exists_query(
        self, 
        session: AsyncSession, 
        table_name: str, 
        schema: str = "public"
    ) -> bool:
        """
        Check if a specific table exists.
        
        Args:
            session: SQLAlchemy async session
            table_name: Name of table to check
            schema: Database schema name (default: public)
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            query = """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = :table_name AND table_schema = :schema
            """
            
            result = await self.execute_scalar_query(
                session, 
                query, 
                parameters={"table_name": table_name, "schema": schema}
            )
            
            return int(result) > 0 if result is not None else False
            
        except Exception as e:
            self.logger.error(f"Table exists query failed for {table_name}: {str(e)}")
            return False
    
    async def execute_index_count_query(
        self, 
        session: AsyncSession, 
        table_names: List[str]
    ) -> int:
        """
        Get count of indexes for specified tables.
        
        Args:
            session: SQLAlchemy async session
            table_names: List of table names to check
            
        Returns:
            Number of indexes found
        """
        try:
            # Create IN clause parameters
            table_params = {f"table_{i}": name for i, name in enumerate(table_names)}
            in_clause = ", ".join(f":{param}" for param in table_params.keys())
            
            query = f"""
                SELECT COUNT(*) as index_count
                FROM pg_indexes 
                WHERE tablename IN ({in_clause})
            """
            
            result = await self.execute_scalar_query(
                session, 
                query, 
                parameters=table_params
            )
            
            return int(result) if result is not None else 0
            
        except Exception as e:
            self.logger.error(f"Index count query failed: {str(e)}")
            return 0


class DatabaseQueryError(Exception):
    """Exception raised for database query execution errors."""
    
    def __init__(self, message: str, query: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.query = query
        self.parameters = parameters


# SSOT Instance for global use
ssot_query_executor = SSOTDatabaseQueryExecutor()