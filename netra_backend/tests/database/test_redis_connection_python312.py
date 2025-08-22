#!/usr/bin/env python3
"""
Test that reproduces the Redis connection failure in dev environment.

The issue is that aioredis 2.0.1 is incompatible with Python 3.12.4 due to 
a TypeError: duplicate base class TimeoutError.

This test will fail until we fix the aioredis compatibility issue.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to path for imports
# from scripts.dev_launcher_database_connector import  # Should be mocked in tests DatabaseConnector, DatabaseType, ConnectionStatus

@pytest.mark.asyncio
async def test_redis_connection_fails_with_python312():
    """
    Test that reproduces the Redis connection failure in dev environment.
    
    This test demonstrates that the current aioredis 2.0.1 version is incompatible
    with Python 3.12, causing a TypeError when trying to import aioredis.
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
    
    # Test the actual connection - this should fail with aioredis 2.0.1 on Python 3.12
    result = await connector._test_redis_connection(redis_conn)
    
    # The test should fail due to aioredis incompatibility
    assert result is False, "Redis connection should fail with aioredis 2.0.1 on Python 3.12"
    assert redis_conn.last_error is not None
    assert "Redis connection failed" in redis_conn.last_error or "TimeoutError" in redis_conn.last_error

@pytest.mark.asyncio
async def test_dev_launcher_database_validation_fails():
    """
    Test that the dev launcher database validation fails when Redis connection fails.
    
    This simulates what happens when running `python scripts/dev_launcher.py`.
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
            # Let Redis connection fail naturally due to aioredis issue
            result = await connector.validate_all_connections()
            
            # Validation should fail because Redis connection fails
            assert result is False, "Database validation should fail when Redis connection fails"
            
            # Check that PostgreSQL was marked as connected
            if "main_postgres" in connector.connections:
                postgres_conn = connector.connections["main_postgres"]
                assert postgres_conn.status == ConnectionStatus.CONNECTED
            
            # Check that Redis was marked as failed
            redis_conn = connector.connections["main_redis"]
            assert redis_conn.status == ConnectionStatus.FAILED
            assert redis_conn.last_error is not None

def test_aioredis_import_fails_on_python312():
    """
    Test that directly importing aioredis fails on Python 3.12.
    
    This is the root cause of the Redis connection failure.
    """
    try:
        import aioredis
        # If import succeeds, check version
        import sys
        python_version = sys.version_info
        
        # This should only succeed if Python < 3.12 or aioredis has been updated
        assert python_version.major < 3 or python_version.minor < 12, \
            f"aioredis 2.0.1 should not work with Python {python_version.major}.{python_version.minor}"
    except TypeError as e:
        # Expected error with Python 3.12 and aioredis 2.0.1
        assert "duplicate base class TimeoutError" in str(e)
        # Test passes - we've reproduced the issue
    except ImportError:
        # aioredis not installed
        pytest.skip("aioredis not installed")

if __name__ == "__main__":
    # Run the tests
    import pytest
    pytest.main([__file__, "-v", "-s"])