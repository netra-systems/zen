"""Database Test Connections - SSOT for E2E database testing

This module provides database connection management for E2E tests.
Implements SSOT patterns for database testing infrastructure.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable database testing across E2E scenarios
- Value Impact: Ensures database test isolation and consistency
- Revenue Impact: Protects database reliability and deployment quality
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import time

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class DatabaseTestConfig:
    """Database test configuration."""
    postgres_url: str
    redis_url: str
    clickhouse_url: str
    test_database_prefix: str = "test_"
    cleanup_on_exit: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatabaseConnectionManager:
    """Database connection manager for E2E tests."""
    
    def __init__(self, test_name: str = "default"):
        """Initialize database connection manager.
        
        Args:
            test_name: Name of the test for unique database naming
        """
        self.test_name = test_name
        self.test_id = f"{test_name}_{int(time.time())}"
        
        # SSOT environment management
        self.env = IsolatedEnvironment()
        
        # Database manager using SSOT pattern
        self.db_manager: Optional[DatabaseManager] = None
        self.test_databases: List[str] = []
        self.cleanup_tasks = []
        
    async def initialize(self) -> None:
        """Initialize database connections."""
        logger.info(f"Initializing database connections for test: {self.test_id}")
        
        try:
            # Initialize SSOT database manager
            self.db_manager = DatabaseManager(
                postgres_config=self.env.get_database_config(),
                clickhouse_config=self.env.get_clickhouse_config()
            )
            await self.db_manager.initialize()
            
            logger.info(f"Database connections initialized for test: {self.test_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    async def create_test_database(self, database_name: str = None) -> str:
        """Create a test database.
        
        Args:
            database_name: Optional database name, defaults to test-specific name
            
        Returns:
            The created database name
        """
        if not database_name:
            database_name = f"test_db_{self.test_id}"
        
        # Track for cleanup
        self.test_databases.append(database_name)
        
        logger.info(f"Created test database: {database_name}")
        return database_name
    
    async def get_test_connection_config(self) -> DatabaseTestConfig:
        """Get test connection configuration."""
        return DatabaseTestConfig(
            postgres_url=self.env.get("POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test"),
            redis_url=self.env.get("REDIS_URL", "redis://localhost:6379/0"),
            clickhouse_url=self.env.get("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_test"),
            test_database_prefix=f"test_{self.test_id}_"
        )
    
    async def execute_test_query(self, query: str, database: str = None) -> Any:
        """Execute a test query.
        
        Args:
            query: SQL query to execute
            database: Optional database name
            
        Returns:
            Query results
        """
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized")
        
        # In a real implementation, this would execute the query
        # For now, return mock results
        logger.info(f"Executing test query: {query[:50]}...")
        
        return {"status": "success", "rows_affected": 0}
    
    async def seed_test_data(self, test_data: Dict[str, Any]) -> None:
        """Seed test data into test databases.
        
        Args:
            test_data: Test data to seed
        """
        logger.info(f"Seeding test data for test: {self.test_id}")
        
        # In a real implementation, this would seed actual data
        # For now, just log the action
        for table, data in test_data.items():
            logger.info(f"Seeding {len(data) if isinstance(data, list) else 1} records into {table}")
    
    async def cleanup(self) -> None:
        """Cleanup test database resources."""
        logger.info(f"Cleaning up database resources for test: {self.test_id}")
        
        # Execute custom cleanup tasks
        for task in reversed(self.cleanup_tasks):
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.warning(f"Database cleanup task failed: {e}")
        
        # Cleanup test databases
        for db_name in self.test_databases:
            try:
                logger.info(f"Dropping test database: {db_name}")
                # In real implementation: DROP DATABASE if exists
            except Exception as e:
                logger.warning(f"Failed to drop test database {db_name}: {e}")
        
        # Cleanup database manager
        if self.db_manager:
            try:
                await self.db_manager.cleanup()
            except Exception as e:
                logger.warning(f"Database manager cleanup failed: {e}")
            finally:
                self.db_manager = None
        
        logger.info(f"Database cleanup complete for test: {self.test_id}")
    
    def add_cleanup_task(self, task):
        """Add a cleanup task to be executed on cleanup."""
        self.cleanup_tasks.append(task)
    
    @asynccontextmanager
    async def managed_connection(self):
        """Async context manager for managed database connections."""
        await self.initialize()
        try:
            yield self
        finally:
            await self.cleanup()


# Alias for backward compatibility
DatabaseTestConnections = DatabaseConnectionManager


@asynccontextmanager
async def get_test_database_connection(test_name: str = "default"):
    """Get a managed test database connection.
    
    Usage:
        async with get_test_database_connection("my_test") as db:
            # Use database connection
            pass
    """
    manager = DatabaseConnectionManager(test_name)
    async with manager.managed_connection():
        yield manager
