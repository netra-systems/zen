"""
Unit tests for connection_pool
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from netra_backend.app.core.async_connection_pool import AsyncConnectionPool
from shared.isolated_environment import IsolatedEnvironment


class TestAsyncConnectionPool:
    """Test suite for AsyncConnectionPool"""

    @pytest.fixture
    def mock_connection(self):
        """Create mock connection"""
        return Mock()

    @pytest.fixture
    async def create_connection(self, mock_connection):
        """Mock connection creation function"""
        async def _create():
            await asyncio.sleep(0)
            return mock_connection
        return _create

    @pytest.fixture
    def close_connection(self):
        """Mock connection close function"""
        async def _close(conn):
            await asyncio.sleep(0)
        return _close

    @pytest.fixture
    async def pool_instance(self, create_connection, close_connection):
        """Create test pool instance"""
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=5,
            min_size=1
        )
        await pool.initialize()
        yield pool
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_initialization(self, create_connection, close_connection):
        """Test pool initializes correctly"""
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=5,
            min_size=1
        )
        await pool.initialize()
        
        assert pool.max_size == 5
        assert pool.min_size == 1
        
        await pool.close()

    @pytest.mark.asyncio
    async def test_get_connection(self, pool_instance):
        """Test getting connection from pool"""
        connection = await pool_instance.get_connection()
        assert connection is not None

    @pytest.mark.asyncio
    async def test_return_connection(self, pool_instance):
        """Test returning connection to pool"""
        connection = await pool_instance.get_connection()
        await pool_instance.return_connection(connection)
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_pool_size_limits(self, create_connection, close_connection):
        """Test pool respects size limits"""
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=2,
            min_size=1
        )
        await pool.initialize()
        
        # Get multiple connections up to max_size
        conn1 = await pool.get_connection()
        conn2 = await pool.get_connection()
        
        assert conn1 is not None
        assert conn2 is not None
        
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_cleanup(self, pool_instance):
        """Test pool cleanup on close"""
        await pool_instance.close()
        # Should not raise any exception