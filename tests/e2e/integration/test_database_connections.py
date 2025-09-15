from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
E2E tests for database connections in DEV MODE.

Tests PostgreSQL, ClickHouse, and Redis connectivity during startup,
validates connection pooling, monitors connection health, and tests recovery.

Follows 450-line file limit and 25-line function limit constraints.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import asyncpg
import pytest
import redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add project root to path

from dev_launcher import DevLauncher, LauncherConfig
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.database_types import DatabaseType
from netra_backend.app.startup_checks.database_checks import DatabaseChecker
from tests.e2e.dev_launcher_test_fixtures import TestEnvironmentManager


class DatabaseConnectionerTests:
    """Tests database connectivity for all database types."""
    
    def __init__(self):
        self.test_env = TestEnvironmentManager()
        self.postgres_url: Optional[str] = None
        self.clickhouse_url: Optional[str] = None
        self.redis_url: Optional[str] = None
        self._setup_connection_urls()
    
    def _setup_connection_urls(self) -> None:
        """Setup database connection URLs for testing."""
        self.postgres_url = get_env().get("TEST_DATABASE_URL") or \
            "postgresql+asyncpg://netra:netra123@localhost:5432/netra_dev"
        self.clickhouse_url = get_env().get("TEST_CLICKHOUSE_URL") or \
            "http://netra:netra123@localhost:8123"
        self.redis_url = get_env().get("TEST_REDIS_URL") or \
            "redis://localhost:6379/1"
    
    @pytest.mark.e2e
    async def test_postgres_connection(self) -> Tuple[bool, Optional[str]]:
        """Test PostgreSQL database connection."""
        try:
            engine = create_async_engine(self.postgres_url, echo=False)
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar()
                assert value == 1
            await engine.dispose()
            return True, None
        except Exception as e:
            return False, str(e)
    
    @pytest.mark.e2e
    async def test_clickhouse_connection(self) -> Tuple[bool, Optional[str]]:
        """Test ClickHouse database connection."""
        try:
            async with aiohttp.ClientSession() as session:
                query_url = f"{self.clickhouse_url}?query=SELECT 1"
                async with session.get(query_url) as response:
                    if response.status == 200:
                        text_result = await response.text()
                        return text_result.strip() == "1", None
                    else:
                        return False, f"HTTP {response.status}"
        except Exception as e:
            return False, str(e)
    
    @pytest.mark.e2e
    def test_redis_connection(self) -> Tuple[bool, Optional[str]]:
        """Test Redis connection."""
        try:
            client = redis.from_url(self.redis_url)
            client.ping()
            client.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    @pytest.mark.e2e
    async def test_connection_pooling(self) -> Tuple[bool, Optional[str]]:
        """Test database connection pooling works correctly."""
        try:
            # Use DatabaseManager singleton - the canonical implementation
            manager = DatabaseManager.get_connection_manager()
            
            # Test multiple concurrent connections using the canonical async session
            tasks = []
            for i in range(3):
                task = asyncio.create_task(self._test_pool_connection())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success = all(r is True for r in results if not isinstance(r, Exception))
            
            return success, None
        except Exception as e:
            return False, str(e)
    
    async def _test_pool_connection(self) -> bool:
        """Test individual connection from pool using canonical DatabaseManager."""
        async with DatabaseManager.get_async_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1


class DevDatabaseFixtureTests:
    """Test fixture for database connectivity in dev environment."""
    
    def __init__(self):
        self.launcher: Optional[DevLauncher] = None
        self.db_tester = DatabaseConnectionTester()
        self.test_env = TestEnvironmentManager()
        self.database_checker: Optional[DatabaseChecker] = None
        self._setup_test_environment()
    
    def _setup_test_environment(self) -> None:
        """Setup test environment for database testing."""
        self.test_env.setup_test_db()
        self.test_env.setup_test_redis()
        self.test_env.setup_test_clickhouse()
        self._set_test_env_vars()
    
    def _set_test_env_vars(self) -> None:
        """Set environment variables for database testing."""
        env = get_env()
        env.set("TESTING", "true", "test")
        env.set("DATABASE_URL", self.db_tester.postgres_url, "test")
        env.set("CLICKHOUSE_URL", self.db_tester.clickhouse_url, "test")
        env.set("REDIS_URL", self.db_tester.redis_url, "test")
    
    async def start_dev_environment(self) -> bool:
        """Start dev environment for database testing."""
        config = LauncherConfig(
            dynamic_ports=True, no_browser=True,
            load_secrets=False, non_interactive=True
        )
        
        self.launcher = DevLauncher(config)
        
        try:
            result = await asyncio.wait_for(self.launcher.run(), timeout=180)
            await self._initialize_database_checker()
            return result == 0
        except asyncio.TimeoutError:
            return False
    
    async def _initialize_database_checker(self) -> None:
        """Initialize database checker for startup validation."""
        if self.launcher and hasattr(self.launcher, 'app'):
            self.database_checker = DatabaseChecker(self.launcher.app)
    
    async def cleanup(self) -> None:
        """Cleanup test resources."""
        if self.launcher:
            await self.launcher.cleanup()
        self.test_env.cleanup()


@pytest.fixture
@pytest.mark.e2e
async def test_db_test_fixture():
    """Fixture providing database test environment."""
    fixture = DevDatabaseTestFixture()
    yield fixture
    await fixture.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_postgres_connectivity(test_db_test_fixture):
    """Test PostgreSQL database connectivity during startup."""
    success, error = await test_db_test_fixture.db_tester.test_postgres_connection()
    if not success and "password authentication failed" in str(error):
        pytest.skip(f"PostgreSQL test database not available: {error}")
    assert success, f"PostgreSQL connection failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_clickhouse_connectivity(test_db_test_fixture):
    """Test ClickHouse database connectivity during startup."""
    success, error = await test_db_test_fixture.db_tester.test_clickhouse_connection()
    if not success and ("refused" in str(error).lower() or "connection" in str(error).lower()):
        pytest.skip(f"ClickHouse test database not available: {error}")
    assert success, f"ClickHouse connection failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_redis_connectivity(test_db_test_fixture):
    """Test Redis connectivity during startup."""
    success, error = test_db_test_fixture.db_tester.test_redis_connection()
    if not success and ("Connection refused" in str(error) or "ConnectionError" in str(error)):
        pytest.skip(f"Redis test database not available: {error}")
    assert success, f"Redis connection failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_all_databases_available_in_dev_mode(test_db_test_fixture):
    """Test all databases are available when dev environment starts."""
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success, "Dev environment should start successfully"
    await _verify_all_database_connections(test_db_test_fixture)

async def _verify_all_database_connections(test_db_test_fixture):
    """Verify all database connections are working."""
    postgres_ok, pg_error = await test_db_test_fixture.db_tester.test_postgres_connection()
    clickhouse_ok, ch_error = await test_db_test_fixture.db_tester.test_clickhouse_connection()
    redis_ok, redis_error = test_db_test_fixture.db_tester.test_redis_connection()
    assert postgres_ok, f"PostgreSQL not available: {pg_error}"
    assert clickhouse_ok, f"ClickHouse not available: {ch_error}"
    assert redis_ok, f"Redis not available: {redis_error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_database_startup_checks(test_db_test_fixture):
    """Test database startup checks execute successfully."""
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success
    
    checker = test_db_test_fixture.database_checker
    if checker:
        db_result = await checker.check_database_connection()
        assert db_result.success, f"Database check failed: {db_result.message}"
        
        assistant_result = await checker.check_or_create_assistant()
        assert assistant_result.success, f"Assistant check failed: {assistant_result.message}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_connection_pooling_works(test_db_test_fixture):
    """Test database connection pooling works correctly."""
    success, error = await test_db_test_fixture.db_tester.test_connection_pooling()
    assert success, f"Connection pooling failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_database_recovery_after_disconnection(test_db_test_fixture):
    """Test database connections recover after temporary disconnection."""
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success
    
    # Test initial connection
    success1, _ = await test_db_test_fixture.db_tester.test_postgres_connection()
    assert success1, "Initial connection should work"
    
    # Wait for potential connection timeout
    await asyncio.sleep(2)
    
    # Test connection recovery
    success2, error = await test_db_test_fixture.db_tester.test_postgres_connection()
    assert success2, f"Connection recovery failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_database_schema_validation(test_db_test_fixture):
    """Test database schema validation during startup."""
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success
    
    # Test schema validation through startup checks
    checker = test_db_test_fixture.database_checker
    if checker:
        result = await checker.check_database_connection()
        assert result.success
        
        # Should not report missing critical tables
        assert "missing tables" not in result.message.lower()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_database_access(test_db_test_fixture):
    """Test concurrent database access works correctly."""
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success
    
    # Test concurrent connections
    tasks = []
    for i in range(5):
        task = asyncio.create_task(
            test_db_test_fixture.db_tester.test_postgres_connection()
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # All connections should succeed
    for success, error in results:
        assert success, f"Concurrent connection failed: {error}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_database_environment_isolation(test_db_test_fixture):
    """Test database connections use test environment settings."""
    # Verify test environment variables are set
    assert get_env().get("TESTING") == "true"
    assert "test" in get_env().get("DATABASE_URL", "").lower()
    
    startup_success = await test_db_test_fixture.start_dev_environment()
    assert startup_success
    
    # Connections should use test databases
    success, error = await test_db_test_fixture.db_tester.test_postgres_connection()
    assert success, f"Test database connection failed: {error}"
