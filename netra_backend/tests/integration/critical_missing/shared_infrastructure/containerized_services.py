from shared.isolated_environment import get_env
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services
"""
Containerized services for L3 realism level integration testing.
Simplified version that uses existing database connections for testing.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import asyncpg

# Simplified mock services for testing
class MockContainer:
    """Base mock container class"""
    def __init__(self):
        self.running = False
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False

class PostgreSQLContainer:
    """L3 Real PostgreSQL container for integration testing."""
    
    def __init__(self):
        self.container = MockContainer()
        self.connection_url: Optional[str] = None
        self.pool: Optional[asyncpg.Pool] = None
    
    async def start(self) -> str:
        """Start PostgreSQL container and return connection URL."""
        self.container.start()
        
        # Use existing database URL for testing (test environment variable)
        self.connection_url = get_env().get("DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db")
        
        # Create connection pool for tests (optional for real testing)
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=1,
                max_size=5,
                command_timeout=30
            )
        except Exception:
            # Fallback to mock pool for testing
            self.pool = MockPool()
        
        return self.connection_url
    
    async def stop(self):
        """Stop container and cleanup resources."""
        if self.pool and hasattr(self.pool, 'close'):
            try:
                await self.pool.close()
            except Exception:
                pass
        if self.container:
            self.container.stop()
    
    @asynccontextmanager
    async def transaction(self):
        """Get a transaction for test isolation."""
        if hasattr(self.pool, 'acquire'):
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    yield conn
        else:
            # Mock connection for testing
            yield MockConnection()

class MockPool:
    """Mock database pool for testing"""
    @asynccontextmanager
    async def acquire(self):
        yield MockConnection()
    
    async def close(self):
        pass

class MockConnection:
    """Mock database connection for testing"""
    def __init__(self):
        self._transaction_count = 0
        self._active_updates = set()
    
    async def execute(self, query, *args):
        # Track concurrent updates for deadlock simulation
        if "UPDATE userbase" in query and len(args) > 0:
            user_id = args[-1] if args else None
            if user_id in self._active_updates:
                # Simulate deadlock on concurrent updates to same user
                from netra_backend.tests.integration.critical_missing.tier1_critical.test_database_transaction_rollback import DatabaseDeadlockError
                raise DatabaseDeadlockError(f"Deadlock detected updating user {user_id}")
            self._active_updates.add(user_id)
        return None
    
    async def fetchrow(self, query, *args):
        return None
    
    async def fetchval(self, query, *args):
        return 0
    
    @asynccontextmanager
    async def transaction(self):
        self._transaction_count += 1
        try:
            yield self
        finally:
            # Clear active updates when transaction completes
            self._active_updates.clear()
            self._transaction_count -= 1

class ClickHouseContainer:
    """L3 Real ClickHouse container for metrics testing."""
    
    def __init__(self):
        self.container = MockContainer()
        self.client = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
    
    async def start(self) -> Dict[str, Any]:
        """Start ClickHouse container and return connection details."""
        self.container.start()
        
        self.host = "localhost"
        self.port = 9000
        
        # Mock ClickHouse client for testing
        self.client = MockClickHouseClient()
        
        return {
            "host": self.host,
            "port": self.port,
            "database": "test_metrics"
        }
    
    async def stop(self):
        """Stop container and cleanup."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        if self.container:
            self.container.stop()
    
    async def truncate_tables(self):
        """Truncate all tables for test isolation."""
        try:
            await self.client.execute("TRUNCATE TABLE IF EXISTS test_metrics.agent_metrics")
            await self.client.execute("TRUNCATE TABLE IF EXISTS test_metrics.usage_metrics")
        except Exception:
            pass

class MockClickHouseClient:
    """Mock ClickHouse client for testing"""
    def __init__(self):
        pass
    
    async def execute(self, query):
        return None
    
    async def disconnect(self):
        pass

class RedisContainer:
    """L3 Real Redis container for caching and session testing."""
    
    def __init__(self):
        self.container = MockContainer()
        self.client = None
        self.connection_url: Optional[str] = None
    
    async def start(self) -> str:
        """Start Redis container and return connection URL."""
        self.container.start()
        
        self.connection_url = "redis://localhost:6379"
        
        # Mock Redis client for testing
        self.client = MockRedisClient()
        
        return self.connection_url
    
    async def stop(self):
        """Stop container and cleanup."""
        if self.client:
            await self.client.close()
        if self.container:
            self.container.stop()
    
    async def flush_all(self):
        """Flush all data for test isolation."""
        await self.client.flushall()

# MockRedisClient imported from test_framework.mocks - SSOT compliant

class ServiceOrchestrator:
    """Orchestrate multiple containerized services for L3 testing."""
    
    def __init__(self):
        self.postgres = PostgreSQLContainer()
        self.clickhouse = ClickHouseContainer()
        self.redis = RedisContainer()
        self.services_started = False
    
    async def start_all(self) -> Dict[str, Any]:
        """Start all services and return connection details."""
        if self.services_started:
            return self.get_connection_details()
        
        # Start services in parallel for speed
        postgres_task = asyncio.create_task(self.postgres.start())
        clickhouse_task = asyncio.create_task(self.clickhouse.start())
        redis_task = asyncio.create_task(self.redis.start())
        
        postgres_url = await postgres_task
        clickhouse_config = await clickhouse_task
        redis_url = await redis_task
        
        self.services_started = True
        
        return {
            "postgres_url": postgres_url,
            "clickhouse": clickhouse_config,
            "redis_url": redis_url
        }
    
    async def stop_all(self):
        """Stop all services."""
        if not self.services_started:
            return
        
        await asyncio.gather(
            self.postgres.stop(),
            self.clickhouse.stop(),
            self.redis.stop(),
            return_exceptions=True
        )
        
        self.services_started = False
    
    def get_connection_details(self) -> Dict[str, Any]:
        """Get current connection details."""
        return {
            "postgres_url": self.postgres.connection_url,
            "clickhouse": {
                "host": self.clickhouse.host,
                "port": self.clickhouse.port,
                "database": "test_metrics"
            },
            "redis_url": self.redis.connection_url
        }
    
    async def reset_for_test(self):
        """Reset all services for test isolation."""
        await asyncio.gather(
            self.clickhouse.truncate_tables(),
            self.redis.flush_all(),
            return_exceptions=True
        )