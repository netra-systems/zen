"""
Database Connection Management for Tests
Handles database connections across PostgreSQL, ClickHouse, and Redis.
ARCHITECTURE: Under 300 lines, 8-line functions max
"""

import os
import asyncpg
import redis.asyncio as redis
import clickhouse_connect
from typing import Optional


class DatabaseConnectionManager:
    """Manages connections to all database types."""
    
    def __init__(self):
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
            self.clickhouse_client = clickhouse_connect.get_client(
                host=os.getenv("CLICKHOUSE_HOST", "localhost"),
                port=int(os.getenv("CLICKHOUSE_PORT", "8443")),
                secure=False
            )
        except Exception:
            self.clickhouse_client = None
            
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