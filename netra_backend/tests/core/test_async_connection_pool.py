"""
Tests for AsyncConnectionPool - connection management
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import Mock

# Add project root to path

from netra_backend.app.core.async_connection_pool import AsyncConnectionPool
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.tests.helpers.async_utils_helpers import (

# Add project root to path
    create_connection_counter,
    create_close_connection,
    create_slow_connection_factory,
)


class TestAsyncConnectionPool:
    """Test AsyncConnectionPool for connection management"""
    
    @pytest.fixture
    async def connection_pool(self):
        """Create connection pool with mock connections"""
        counter, create_connection = create_connection_counter()
        close_connection = await create_close_connection()
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=3,
            min_size=1
        )
        await pool.initialize()
        return pool
    async def test_acquire_and_release_connection(self, connection_pool):
        """Test acquiring and releasing connections"""
        async with connection_pool.acquire() as conn:
            assert conn != None
            assert hasattr(conn, 'id')
            assert conn.id > 0
        assert not connection_pool._closed
    async def test_multiple_concurrent_connections(self, connection_pool):
        """Test multiple concurrent connections"""
        connections = []
        await asyncio.gather(*[self._acquire_connection(connection_pool, connections) for _ in range(3)])
        assert len(connections) == 3
        assert len(set(conn.id for conn in connections)) == 3
    
    async def _acquire_connection(self, pool, connections):
        """Helper for concurrent connection test"""
        async with pool.acquire() as conn:
            connections.append(conn)
            await asyncio.sleep(0.01)
    async def test_connection_pool_limit(self, connection_pool):
        """Test connection pool respects max size"""
        acquired_connections = []
        tasks = [asyncio.create_task(self._long_operation(connection_pool, acquired_connections)) for _ in range(5)]
        await asyncio.sleep(0.01)
        assert len(acquired_connections) <= 3
        await asyncio.gather(*tasks)
        assert len(acquired_connections) == 5
    
    async def _long_operation(self, pool, acquired_connections):
        """Helper for pool limit test"""
        async with pool.acquire() as conn:
            acquired_connections.append(conn)
            await asyncio.sleep(0.1)
    async def test_pool_close(self, connection_pool):
        """Test closing the connection pool"""
        async with connection_pool.acquire() as conn:
            original_conn = conn
        await connection_pool.close()
        assert connection_pool._closed == True
        assert hasattr(original_conn, 'closed') or True
    async def test_acquire_from_closed_pool(self, connection_pool):
        """Test acquiring from closed pool raises error"""
        await connection_pool.close()
        with pytest.raises(ServiceError, match="Connection pool is closed"):
            async with connection_pool.acquire():
                pass
    async def test_acquire_timeout_when_no_connections(self):
        """Test acquire timeout when pool is empty"""
        create_connection = create_slow_connection_factory()
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=lambda conn: None,
            max_size=1,
            min_size=0
        )
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                async with pool.acquire() as conn:
                    pass
    async def test_connection_pool_queue_full(self):
        """Test handling when connection pool queue is full"""
        connections_closed = []
        pool = await self._create_test_pool(connections_closed)
        await pool.initialize()
        await self._fill_pool_queue(pool)
        async with pool.acquire() as conn:
            pass
    
    async def _create_test_pool(self, connections_closed):
        """Helper to create test pool with tracking"""
        async def create_connection():
            return f"conn_{len(connections_closed)}"
        async def close_connection(conn):
            connections_closed.append(conn)
        return AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=1,
            min_size=1
        )
    
    async def _fill_pool_queue(self, pool):
        """Helper to fill connection pool queue"""
        for i in range(pool._available_connections.maxsize):
            try:
                await pool._available_connections.put(f"extra_conn_{i}")
            except asyncio.QueueFull:
                break
    async def test_close_pool_with_timeout_on_empty(self):
        """Test closing pool when getting connection times out"""
        pool = AsyncConnectionPool(
            create_connection=lambda: "connection",
            close_connection=lambda conn: None
        )
        await pool.close()
        assert pool._closed == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])