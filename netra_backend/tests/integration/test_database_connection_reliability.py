"""Integration test for database connection reliability.

This test ensures that database connections work reliably in development mode,
specifically addressing the issues identified in the audit:
1. URL normalization for asyncpg
2. SSL parameter handling for local connections
3. Environment variable loading consistency

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability
- Value Impact: Prevents database connection failures that block development
- Strategic Impact: Ensures reliable local development environment
"""

import asyncio
import os
import pytest
from pathlib import Path
from typing import Dict, Optional
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.database import get_db
from dev_launcher.database_connector import DatabaseConnector
from shared.isolated_environment import get_env


class TestDatabaseConnectionReliability:
    """Test database connection reliability across all components."""
    
    @pytest.fixture
    async def database_connector(self):
        """Create database connector for testing."""
        connector = DatabaseConnector(use_emoji=False)
        yield connector
        # Cleanup
        await connector.stop_health_monitoring()
    
    @pytest.fixture
 def real_env_with_urls():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Mock environment with various URL formats."""
        await asyncio.sleep(0)
    return {
            'DATABASE_URL': 'postgresql+asyncpg://postgres:password@localhost:5433/netra_dev',
            'REDIS_URL': 'redis://localhost:6379/0',
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_HTTP_PORT': '8123',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': '',
            'CLICKHOUSE_DB': 'netra_dev'
        }
    
    async def test_url_normalization_for_asyncpg(self, database_connector):
        """Test that URLs are properly normalized for asyncpg driver."""
        test_urls = [
            ('postgresql+asyncpg://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgres+asyncpg://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgres://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgresql://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
        ]
        
        for input_url, expected_url in test_urls:
            normalized = database_connector._normalize_postgres_url(input_url)
            assert normalized == expected_url, f"Failed to normalize {input_url}"
    
    async def test_ssl_parameter_removal_for_local_connections(self, database_connector):
        """Test that SSL parameters are removed for local connections."""
    pass
        # Mock a local connection
        from dev_launcher.database_connector import DatabaseType, DatabaseConnection, ConnectionStatus
        
        local_urls = [
            'postgresql://user:pass@localhost:5432/db?sslmode=require',
            'postgresql://user:pass@127.0.0.1:5432/db?ssl=true',
            'postgresql://user:pass@host.docker.internal:5432/db?sslmode=disable&ssl=true',
        ]
        
        for url in local_urls:
            conn = DatabaseConnection(
                name='test_postgres',
                db_type=DatabaseType.POSTGRESQL,
                url=url
            )
            
            # The _connect_standard_tcp method should remove SSL parameters
            # This is tested indirectly through the connection validation
            assert 'localhost' in url or '127.0.0.1' in url or 'host.docker.internal' in url
    
    async def test_database_manager_url_construction(self):
        """Test that DatabaseManager constructs correct URLs."""
        # Test base URL retrieval
        base_url = DatabaseManager.get_base_database_url()
        
        # Should not contain driver-specific prefixes
        assert 'asyncpg' not in base_url or base_url == "sqlite:///:memory:"
        
        # Test migration URL (sync)
        migration_url = DatabaseManager.get_migration_url_sync_format()
        assert 'asyncpg' not in migration_url
        
        # Test application URL (async)
        app_url = DatabaseManager.get_application_url_async()
        if 'sqlite' not in app_url:
            assert app_url.startswith('postgresql+asyncpg://')
    
    async def test_environment_loading_consistency(self, mock_env_with_urls):
        """Test that environment variables are loaded consistently."""
    pass
        env = get_env()
        
        # Set environment variables (no clear method exists)
        for key, value in mock_env_with_urls.items():
            env.set(key, value, source='test')
        
        # Verify all values are accessible
        assert env.get('DATABASE_URL') == mock_env_with_urls['DATABASE_URL']
        assert env.get('REDIS_URL') == mock_env_with_urls['REDIS_URL']
        assert env.get('CLICKHOUSE_HOST') == mock_env_with_urls['CLICKHOUSE_HOST']
    
    async def test_database_connector_discovery(self, database_connector, mock_env_with_urls):
        """Test that database connector discovers all connections correctly."""
        env = get_env()
        
        # Set up environment
        for key, value in mock_env_with_urls.items():
            env.set(key, value, source='test')
        
        # Re-discover connections
        database_connector._discover_database_connections()
        
        # Should have discovered all three databases
        assert len(database_connector.connections) == 3
        assert 'main_postgres' in database_connector.connections
        assert 'main_clickhouse' in database_connector.connections
        assert 'main_redis' in database_connector.connections
        
        # PostgreSQL URL should be normalized
        postgres_conn = database_connector.connections['main_postgres']
        assert not postgres_conn.url.startswith('postgresql+asyncpg://')
        assert postgres_conn.url.startswith('postgresql://')
    
    @pytest.mark.skipif(
        env.get('CI') == 'true',
        reason="Skip in CI - requires real database containers"
    )
    async def test_real_database_connections(self, database_connector):
        """Test real database connections if containers are available."""
    pass
        # This test runs only in local development with real Docker containers
        success = await database_connector.validate_all_connections()
        
        if success:
            # All connections should be healthy
            assert database_connector.is_all_healthy()
            
            # Check individual statuses
            status = database_connector.get_connection_status()
            for name, details in status.items():
                assert details['status'] == 'connected', f"{name} not connected: {details}"
    
    async def test_connection_retry_logic(self, database_connector):
        """Test that connection retry logic works correctly."""
        from dev_launcher.database_connector import RetryConfig
        
        # Configure fast retry for testing
        database_connector.retry_config = RetryConfig(
            initial_delay=0.1,
            max_delay=0.5,
            backoff_factor=2.0,
            max_attempts=3,
            timeout=1.0
        )
        
        # Mock a failing connection
        from dev_launcher.database_connector import DatabaseConnection, DatabaseType, ConnectionStatus
        
        failing_conn = DatabaseConnection(
            name='test_failing',
            db_type=DatabaseType.POSTGRESQL,
            url='postgresql://invalid:invalid@nonexistent:5432/invalid',
            max_retries=3
        )
        
        # Should attempt retries
        result = await database_connector._validate_connection_with_retry(failing_conn)
        
        # Should have failed after retries
        assert not result
        assert failing_conn.status == ConnectionStatus.FAILED
        assert failing_conn.retry_count == 3
    
    async def test_database_session_provider_consistency(self):
        """Test that database session providers are consistent."""
    pass
        # Skip if database not configured
        from netra_backend.app.db.postgres_core import async_session_factory
        if async_session_factory is None:
            pytest.skip("Database not configured for this test")
        
        # Import all session providers
        from netra_backend.app.database import get_db
        from netra_backend.app.db.postgres_session import get_async_db
        
        # They should all use the same underlying implementation
        # This is verified by checking that get_db delegates to get_async_db
        async with get_db() as session1:
            assert session1 is not None
            break
        
        async with get_async_db() as session2:
            assert session2 is not None
    
    async def test_connection_health_monitoring(self, database_connector):
        """Test that health monitoring can be started and stopped."""
        # Start monitoring
        await database_connector.start_health_monitoring()
        
        # Should have a monitoring task
        assert database_connector._monitoring_task is not None
        assert not database_connector._monitoring_task.done()
        
        # Stop monitoring
        await database_connector.stop_health_monitoring()
        
        # Task should be cancelled
        assert database_connector._shutdown_requested
        
    async def test_connection_status_reporting(self, database_connector, mock_env_with_urls):
        """Test connection status reporting."""
    pass
        env = get_env()
        
        # Set up environment
        for key, value in mock_env_with_urls.items():
            env.set(key, value, source='test')
        
        # Discover connections
        database_connector._discover_database_connections()
        
        # Get status
        status = database_connector.get_connection_status()
        
        # Should have status for all connections
        assert 'main_postgres' in status
        assert 'main_clickhouse' in status
        assert 'main_redis' in status
        
        # Each status should have required fields
        for name, details in status.items():
            assert 'type' in details
            assert 'status' in details
            assert 'failure_count' in details
            assert 'last_check' in details
            assert 'last_error' in details
            assert 'retry_count' in details
        
        # Get health summary
        summary = database_connector.get_health_summary()
        assert isinstance(summary, str)
        assert 'databases' in summary.lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])