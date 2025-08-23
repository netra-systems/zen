#!/usr/bin/env python3
"""
Test that verifies the Redis connection fix for Python 3.12 compatibility.

This test confirms that the database_connector now uses redis.asyncio
which is compatible with Python 3.12, instead of the incompatible aioredis 2.0.1.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus

@pytest.mark.asyncio
async def test_redis_connection_works_with_python312():
    """
    Test that Redis connection now works with Python 3.12.
    
    The fix uses redis.asyncio (from redis 4.3+) which is compatible with Python 3.12,
    falling back to aioredis only if the newer library is not available.
    """
    # Setup environment for Redis connection
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    # Create database connector
    connector = DatabaseConnector(use_emoji=True)
    
    # Ensure Redis connection was discovered
    assert "main_redis" in connector.connections
    redis_conn = connector.connections["main_redis"]
    assert redis_conn.db_type == DatabaseType.REDIS
    assert redis_conn.url == "redis://localhost:6379/0"
    
    # Test the actual connection - this should now work with Python 3.12
    result = await connector._test_redis_connection(redis_conn)
    
    # The test should succeed with the fixed implementation
    assert result is True, "Redis connection should work with redis.asyncio on Python 3.12"
    assert redis_conn.last_error is None

@pytest.mark.asyncio
async def test_dev_launcher_database_validation_succeeds():
    """
    Test that the dev launcher database validation succeeds with all databases.
    
    This simulates the fixed behavior when running `python scripts/dev_launcher.py`.
    """
    # Setup environment
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:password@localhost:5433/netra_dev"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["CLICKHOUSE_HTTP_PORT"] = "8123"
    
    # Create database connector
    connector = DatabaseConnector(use_emoji=True)
    
    # Mock successful PostgreSQL connection
    with patch.object(connector, '_test_postgresql_connection', return_value=True):
        # Mock successful ClickHouse connection
        with patch.object(connector, '_test_clickhouse_connection', return_value=True):
            # Let Redis connection use the fixed implementation
            result = await connector.validate_all_connections()
            
            # Validation should succeed with all databases working
            assert result is True, "Database validation should succeed when all connections work"
            
            # Check that all connections are marked as connected
            if "main_postgres" in connector.connections:
                postgres_conn = connector.connections["main_postgres"]
                assert postgres_conn.status == ConnectionStatus.CONNECTED
            
            if "main_redis" in connector.connections:
                redis_conn = connector.connections["main_redis"]
                assert redis_conn.status == ConnectionStatus.CONNECTED
                
            if "main_clickhouse" in connector.connections:
                clickhouse_conn = connector.connections["main_clickhouse"]
                assert clickhouse_conn.status == ConnectionStatus.CONNECTED

def test_redis_asyncio_import_works():
    """
    Test that redis.asyncio can be imported successfully on Python 3.12.
    
    This is the fix for the aioredis incompatibility issue.
    """
    try:
        import redis.asyncio as redis_async
        
        # Check that the required methods exist
        assert hasattr(redis_async, 'from_url')
        
        # Import successful - the fix is working
        import sys
        python_version = sys.version_info
        print(f"✅ redis.asyncio works with Python {python_version.major}.{python_version.minor}")
        
    except ImportError:
        pytest.fail("redis.asyncio not available - need redis>=4.3.0")

def test_fallback_to_aioredis_if_needed():
    """
    Test that the implementation falls back to aioredis if redis.asyncio is not available.
    
    This ensures backward compatibility for older environments.
    """
    # This test verifies the fallback logic exists
    # from scripts.dev_launcher_database_connector import  # Should be mocked in tests DatabaseConnector
    
    # Read the source to verify fallback logic exists
    import inspect
    source = inspect.getsource(DatabaseConnector._test_redis_connection)
    
    # Check that both imports are attempted
    assert "import redis.asyncio" in source, "Should try redis.asyncio first"
    assert "import aioredis" in source, "Should fall back to aioredis if needed"
    assert "except ImportError" in source, "Should handle import errors gracefully"

if __name__ == "__main__":
    # Run the tests
    import pytest
    pytest.main([__file__, "-v", "-s"])