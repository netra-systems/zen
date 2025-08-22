"""
Database Connection Management for Tests
Handles database connections across PostgreSQL, ClickHouse, and Redis.
ARCHITECTURE: Under 300 lines, 25-line functions max
"""

import os
from typing import Optional

import asyncpg
import clickhouse_connect
import redis.asyncio as redis

# Import test environment config for environment-aware configuration
try:
    from tests.e2e.test_environment_config import TestEnvironmentConfig
except ImportError:
    TestEnvironmentConfig = None


class DatabaseConnectionManager:
    """Manages connections to all database types."""
    
    def __init__(self, env_config=None):
        """Initialize database connection manager.
        
        Args:
            env_config: Optional TestEnvironmentConfig for environment-aware database configuration
        """
        self.env_config = env_config
        self.postgres_pool = None
        self.redis_client = None
        self.clickhouse_client = None
        
    async def initialize_connections(self):
        """Initialize all database connections."""
        await self._init_postgres()
        await self._init_redis()
        await self._init_clickhouse()
        
    async def _init_postgres(self):
        """Initialize PostgreSQL connection pool."""
        # Use environment config if available
        if self.env_config:
            database_url = self.env_config.database.url
        else:
            database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/netra_test")
        
        try:
            self.postgres_pool = await asyncpg.create_pool(
                database_url, min_size=1, max_size=5
            )
        except Exception:
            self.postgres_pool = None
            
    async def _init_redis(self):
        """Initialize Redis connection."""
        try:
            # Use environment config if available
            if self.env_config:
                redis_url = os.getenv("REDIS_URL", self.env_config._get_redis_url())
                self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    decode_responses=True
                )
            await self.redis_client.ping()
        except Exception:
            self.redis_client = None
            
    async def _init_clickhouse(self):
        """Initialize ClickHouse connection."""
        try:
            # Use environment config if available
            if self.env_config:
                clickhouse_url = os.getenv("CLICKHOUSE_URL", self.env_config._get_clickhouse_url())
                # Parse ClickHouse URL for connection parameters
                if clickhouse_url.startswith("clickhouse://"):
                    url_parts = clickhouse_url.replace("clickhouse://", "").split("/")
                    host_port = url_parts[0].split(":")
                    host = host_port[0]
                    port = int(host_port[1]) if len(host_port) > 1 else 8123
                    database = url_parts[1] if len(url_parts) > 1 else "default"
                else:
                    host = "localhost"
                    port = 8123
                    database = "default"
            else:
                host = os.getenv("CLICKHOUSE_HOST", "localhost")
                port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
                database = "default"
            
            self.clickhouse_client = clickhouse_connect.get_client(
                host=host,
                port=port,
                secure=False
            )
        except Exception:
            self.clickhouse_client = None
            
    async def postgres_session(self):
        """Get PostgreSQL session context manager."""
        if not self.postgres_pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        return self.postgres_pool.acquire()

    async def cleanup(self):
        """Close all database connections."""
        await self._cleanup_postgres()
        await self._cleanup_redis()
        self._cleanup_clickhouse()
            
    async def _cleanup_postgres(self):
        """Cleanup PostgreSQL connections."""
        if self.postgres_pool:
            await self.postgres_pool.close()
            
    async def _cleanup_redis(self):
        """Cleanup Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
            
    def _cleanup_clickhouse(self):
        """Cleanup ClickHouse connections."""
        if self.clickhouse_client:
            self.clickhouse_client.close()


class DatabaseTestConnections(DatabaseConnectionManager):
    """Test-specific database connections with additional helper methods."""
    
    def __init__(self):
        super().__init__()
        self.auth_connection = None
        self.backend_connection = None
        
    async def connect_all(self):
        """Connect to all databases for testing."""
        await self.initialize_connections()
        await self._create_dedicated_connections()
        
    async def _create_dedicated_connections(self):
        """Create dedicated connections for auth and backend."""
        if self.postgres_pool:
            self.auth_connection = await self.postgres_pool.acquire()
            self.backend_connection = await self.postgres_pool.acquire()
            
    async def get_auth_connection(self):
        """Get dedicated Auth service database connection."""
        return self.auth_connection
        
    async def get_backend_connection(self):
        """Get dedicated Backend service database connection."""
        return self.backend_connection
        
    async def get_clickhouse_connection(self):
        """Get ClickHouse connection with helper methods."""
        return ClickHouseTestHelper(self.clickhouse_client)
        
    async def disconnect_all(self):
        """Disconnect all test database connections."""
        await self._release_dedicated_connections()
        await self.cleanup()
        
    async def _release_dedicated_connections(self):
        """Release dedicated database connections."""
        if self.postgres_pool:
            if self.auth_connection:
                await self.postgres_pool.release(self.auth_connection)
            if self.backend_connection:
                await self.postgres_pool.release(self.backend_connection)


class ClickHouseTestHelper:
    """Helper class for ClickHouse operations in tests."""
    
    def __init__(self, client):
        self.client = client
        
    async def insert_user_event(self, user_id: str, event_data: dict):
        """Insert user event into ClickHouse for testing."""
        if not self.client:
            return
            
        query = """
            INSERT INTO user_events (user_id, event_type, event_data, timestamp)
            VALUES (%(user_id)s, %(event_type)s, %(event_data)s, now())
        """
        
        self.client.command(query, parameters={
            'user_id': user_id,
            'event_type': event_data.get('event_type', 'test'),
            'event_data': str(event_data)
        })
        
    async def get_user_metrics(self, user_id: str):
        """Get user metrics from ClickHouse for testing."""
        if not self.client:
            return []
            
        query = "SELECT * FROM user_events WHERE user_id = %(user_id)s"
        result = self.client.query(query, parameters={'user_id': user_id})
        
        return [{'data': {'transaction_id': row[2]}} for row in result.result_rows]
