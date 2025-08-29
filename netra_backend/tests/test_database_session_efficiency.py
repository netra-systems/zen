"""
Test database session efficiency and logging optimization.

This test validates that database connection pooling is working efficiently
and that excessive logging is reduced during normal operations.
"""

import asyncio
import logging
import pytest
from unittest.mock import Mock, patch
from contextlib import contextmanager
from io import StringIO

from netra_backend.app.db.postgres import (
    initialize_postgres,
    get_async_db,
    async_engine,
    async_session_factory
)
from netra_backend.app.db.postgres_core import create_async_database
from netra_backend.app.logging_config import central_logger


class TestDatabaseSessionEfficiency:
    """Test database session management efficiency."""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup test environment."""
        # Force postgres initialization for tests
        from netra_backend.app.core.isolated_environment import IsolatedEnvironment
        with IsolatedEnvironment() as env:
            env.set('TEST_COLLECTION_MODE', '0')  # Disable test collection mode
            initialize_postgres()
        yield
        # Cleanup if needed

    def test_connection_pool_reuse(self):
        """Test that connection pool properly reuses connections."""
        # Verify that multiple sessions reuse the connection pool
        assert async_engine is not None
        assert async_session_factory is not None
        
        # Check that the engine has proper pooling configured
        if hasattr(async_engine.pool, 'size'):
            assert async_engine.pool.size() > 0

    async def test_session_context_manager_efficiency(self):
        """Test that session context managers properly close sessions."""
        initial_pool_stats = None
        if hasattr(async_engine.pool, 'checkedout'):
            initial_pool_stats = {
                'checked_out': async_engine.pool.checkedout(),
                'checked_in': async_engine.pool.checkedin()
            }

        # Use session and ensure it's properly closed
        async with get_async_db() as session:
            # Perform a simple query
            result = await session.execute("SELECT 1")
            assert result is not None

        # After context exit, session should be returned to pool
        if initial_pool_stats:
            final_checked_out = async_engine.pool.checkedout()
            # Should be same as initial or less (connection returned to pool)
            assert final_checked_out <= initial_pool_stats['checked_out']

    async def test_concurrent_session_handling(self):
        """Test that multiple concurrent sessions are handled efficiently."""
        async def run_query(session_id):
            async with get_async_db() as session:
                result = await session.execute("SELECT 1 as session_id")
                return result.scalar()

        # Run multiple concurrent queries
        tasks = [run_query(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert result == 1

    def test_logging_noise_reduction(self):
        """Test that database operations don't create excessive logging."""
        # Test that the engine is configured to reduce logging noise
        assert async_engine is not None
        
        # Check that echo is disabled to reduce noise
        assert async_engine.echo is False, "Database echo should be disabled to reduce logging noise"
        
        # Perform simple database operations to verify they work without noise
        async def perform_operations():
            async with get_async_db() as session:
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
            async with get_async_db() as session:
                result = await session.execute("SELECT 2")
                assert result.scalar() == 2
        
        asyncio.run(perform_operations())

    async def test_async_database_instance_efficiency(self):
        """Test AsyncDatabase instance for efficient operations."""
        async_db = create_async_database()
        
        # Test connection with minimal retries for efficiency
        connection_ok = await async_db.test_connection_with_retry(max_retries=2, base_delay=0.1)
        assert connection_ok, "Database connection should be successful"
        
        # Test session creation
        session = await async_db.get_session()
        assert session is not None
        
        # Test pool status
        pool_status = await async_db.get_pool_status()
        assert isinstance(pool_status, dict)
        
        # Clean up
        await session.close()
        await async_db.close()

    def test_pool_configuration_resilience(self):
        """Test that pool configuration has resilient defaults."""
        if hasattr(async_engine, 'pool'):
            pool = async_engine.pool
            
            # Check that pool has reasonable sizing for resilience
            if hasattr(pool, '_pool_size'):
                assert pool._pool_size >= 10, "Pool size should be at least 10 for resilience"
            
            if hasattr(pool, '_max_overflow'):
                assert pool._max_overflow >= 20, "Max overflow should be at least 20 for resilience"

    async def test_session_validation_efficiency(self):
        """Test that session validation is efficient."""
        from netra_backend.app.db.postgres_session import validate_session
        
        async with get_async_db() as session:
            # Validate session should be fast and not throw errors
            is_valid = validate_session(session)
            # Should return boolean result efficiently
            assert isinstance(is_valid, bool)

    def test_connection_health_checks_optimized(self):
        """Test that connection health checks are optimized."""
        # Verify that pre_ping is enabled for connection health
        assert hasattr(async_engine.pool, '_pre_ping')
        if hasattr(async_engine.pool, '_pre_ping'):
            # Pre-ping should be enabled for health checks
            assert async_engine.pool._pre_ping is True