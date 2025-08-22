"""
Database connection and infrastructure tests
Tests ClickHouse connection pooling, migration safety, and health checks
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from netra_backend.app.db.health_checks import DatabaseHealthChecker
from netra_backend.app.db.migrations.migration_runner import MigrationRunner

class TestClickHouseConnectionPool:
    """test_clickhouse_connection_pool - Test connection pooling and query timeout"""
    
    async def test_connection_pooling(self):
        """Test connection pooling functionality"""
        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            db = _create_test_db()
            
            # Test pool creation
            await db.initialize_pool()
            assert db.pool_size == 5
            
            # Test connection reuse
            conn1 = await db.get_connection()
            await db.release_connection(conn1)
            conn2 = await db.get_connection()
            assert conn1 is conn2  # Should reuse connection
            
            # Test pool exhaustion handling
            connections = []
            for _ in range(5):
                connections.append(await db.get_connection())
            
            # Pool exhausted, should wait or create new
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(db.get_connection(), timeout=0.1)
    
    async def test_query_timeout(self):
        """Test query timeout handling"""
        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Simulate slow query
            async def slow_query(*args, **kwargs):
                await asyncio.sleep(5)
                return []
            
            mock_client.execute_query = slow_query
            
            db = ClickHouseDatabase(
                host="localhost",
                query_timeout=1
            )
            
            with pytest.raises(asyncio.TimeoutError):
                await db.execute_query("SELECT sleep(10)")

class TestMigrationRunnerSafety:
    """test_migration_runner_safety - Test migration safety and rollback capability"""
    
    async def test_migration_rollback(self):
        """Test migration rollback on failure"""
        mock_session = AsyncMock(spec=AsyncSession)
        runner = MigrationRunner(mock_session)
        
        # Test rollback on failure
        migration = _create_failing_migration()
        
        with pytest.raises(Exception):
            await runner.run_migration(migration)
        
        # Verify rollback was called
        assert mock_session.rollback.called
    
    async def test_migration_transaction_safety(self):
        """Test migration transaction safety"""
        mock_session = AsyncMock(spec=AsyncSession)
        runner = MigrationRunner(mock_session)
        
        # Test transaction boundaries
        migration = _create_test_migration()
        
        await runner.run_migration(migration)
        
        # Verify transaction was used
        assert mock_session.begin.called
        assert mock_session.commit.called

class TestDatabaseHealthChecks:
    """test_database_health_checks - Test health monitoring and alert thresholds"""
    
    async def test_health_monitoring(self):
        """Test database health monitoring"""
        mock_session = AsyncMock(spec=AsyncSession)
        checker = DatabaseHealthChecker(mock_session)
        
        # Test connection health
        mock_session.execute.return_value.scalar.return_value = 1
        
        health = await checker.check_connection_health()
        assert health["status"] == "healthy"
        assert health["response_time"] < 1000  # ms
        
        # Test unhealthy connection
        mock_session.execute.side_effect = Exception("Connection failed")
        
        health = await checker.check_connection_health()
        assert health["status"] == "unhealthy"
        assert "error" in health
    
    async def test_alert_thresholds(self):
        """Test alert threshold monitoring"""
        mock_session = AsyncMock(spec=AsyncSession)
        checker = DatabaseHealthChecker(mock_session)
        
        # Test slow query alert
        _setup_slow_query_mock(mock_session)
        
        alerts = await checker.check_slow_queries(threshold_ms=1000)
        assert len(alerts) == 1
        assert alerts[0]["query_time"] == 5000
        
        # Test connection pool alert
        mock_session.execute.return_value.scalar.return_value = 95  # 95% pool usage
        
        pool_alert = await checker.check_connection_pool(threshold_percent=80)
        assert pool_alert["alert"] == True
        assert pool_alert["usage"] == 95

def _create_test_db():
    """Create test database configuration."""
    return ClickHouseDatabase(
        host="localhost",
        port=9000,
        database="test",
        pool_size=5
    )

def _create_failing_migration():
    """Create migration that fails."""
    class FailingMigration:
        async def up(self, session):
            raise Exception("Migration failed")
        
        async def down(self, session):
            pass
    
    return FailingMigration()

def _create_test_migration():
    """Create test migration."""
    class TestMigration:
        async def up(self, session):
            await session.execute("CREATE TABLE test_table (id INT)")
            await session.execute("INSERT INTO test_table VALUES (1)")
    
    return TestMigration()

def _setup_slow_query_mock(mock_session):
    """Setup slow query mock."""
    mock_session.execute.return_value.all.return_value = [
        ("SELECT * FROM large_table", 5000)  # 5 second query
    ]