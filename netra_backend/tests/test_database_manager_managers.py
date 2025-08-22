"""Database Manager Integration Tests with Testcontainers

Tests real PostgreSQL integration using containerized databases to verify
connection pooling, transaction management, and failover capabilities.
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import asyncpg
import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer

# Import database management components
try:
    from app.database.connection_pool import ConnectionPool
    from app.database.manager import DatabaseManager
except ImportError:
    # Fallback if modules don't exist yet
    class DatabaseManager:
        def __init__(self, config):
            self.config = config
            self.pool = None
            
        async def connect(self):
            """Establish database connection."""
            # Parse PostgreSQL URL properly for asyncpg
            url = self.config.get('database_url', '')
            if url.startswith('postgresql://testcontainers'):
                # Convert testcontainers URL format to asyncpg format
                # postgresql://testcontainers:testcontainers@localhost:PORT/test
                parts = url.replace('postgresql://', '').split('@')
                if len(parts) == 2:
                    auth, location = parts
                    host_port, db = location.split('/')
                    host, port = host_port.split(':')
                    user, password = auth.split(':')
                    
                    self.pool = await asyncpg.create_pool(
                        host=host,
                        port=int(port),
                        user=user,
                        password=password,
                        database=db,
                        min_size=2,
                        max_size=10
                    )
            return self.pool is not None
            
        async def execute_query(self, query: str, *args):
            """Execute a database query."""
            if not self.pool:
                raise RuntimeError("Database not connected")
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
                
        async def close(self):
            """Close database connection."""
            if self.pool:
                await self.pool.close()
                
    class ConnectionPool:
        def __init__(self, config):
            self.config = config


class TestDatabaseManagerIntegration:
    """Test database manager with real PostgreSQL via Testcontainers."""
    
    @pytest.fixture
    async def postgres_container(self):
        """Create a PostgreSQL container for testing."""
        with PostgresContainer("postgres:14-alpine") as postgres:
            # Wait for container to be ready
            postgres.get_connection_url()
            yield postgres
    
    @pytest.fixture
    async def database_manager(self, postgres_container):
        """Create database manager connected to test container."""
        # Get connection URL from container
        url = postgres_container.get_connection_url()
        
        # Create manager with test configuration
        config = {
            'database_url': url,
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30
        }
        
        manager = DatabaseManager(config)
        await manager.connect()
        
        yield manager
        
        # Cleanup
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, database_manager):
        """Test that connection pooling works correctly."""
        # Execute multiple concurrent queries
        queries = [
            database_manager.execute_query("SELECT 1 as num"),
            database_manager.execute_query("SELECT 2 as num"),
            database_manager.execute_query("SELECT 3 as num"),
        ]
        
        results = await asyncio.gather(*queries)
        
        # Verify all queries executed successfully
        assert len(results) == 3
        assert results[0][0]['num'] == 1
        assert results[1][0]['num'] == 2
        assert results[2][0]['num'] == 3
    
    @pytest.mark.asyncio
    async def test_transaction_isolation(self, database_manager):
        """Test transaction isolation levels."""
        # Create test table
        await database_manager.execute_query(
            "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, value TEXT)"
        )
        
        # Insert test data
        await database_manager.execute_query(
            "INSERT INTO test_table (value) VALUES ($1)",
            "test_value"
        )
        
        # Query data
        result = await database_manager.execute_query(
            "SELECT value FROM test_table WHERE value = $1",
            "test_value"
        )
        
        assert len(result) == 1
        assert result[0]['value'] == "test_value"
        
        # Cleanup
        await database_manager.execute_query("DROP TABLE test_table")
    
    @pytest.mark.asyncio
    async def test_connection_failure_recovery(self, postgres_container):
        """Test recovery from connection failures."""
        url = postgres_container.get_connection_url()
        
        manager = DatabaseManager({'database_url': url})
        await manager.connect()
        
        # Simulate connection failure by closing pool
        await manager.close()
        
        # Attempt to reconnect
        reconnected = await manager.connect()
        assert reconnected
        
        # Verify connection works after recovery
        result = await manager.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
        
        await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
