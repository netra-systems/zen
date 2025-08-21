"""
Tests for Redis Manager connection pooling functionality
Tests connection pool creation, management, and concurrent usage
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio

# Add project root to path

from netra_backend.tests.helpers.redis_test_fixtures import (

# Add project root to path
    enhanced_redis_manager, connection_pool, MockRedisClient
)
from netra_backend.tests.helpers.redis_test_helpers import (
    verify_connection_pool_state, create_concurrent_tasks, verify_concurrent_results,
    verify_pool_cleanup
)


class TestRedisManagerConnectionPooling:
    """Test Redis connection pooling functionality"""
    async def test_connection_pool_creation(self, enhanced_redis_manager, connection_pool):
        """Test connection pool creation and setup"""
        enhanced_redis_manager.set_connection_pool(connection_pool)
        
        assert enhanced_redis_manager.connection_pool is connection_pool
        verify_connection_pool_state(connection_pool, 0, 5)
    async def test_connection_pool_get_connection(self, connection_pool):
        """Test getting connection from pool"""
        connection = await connection_pool.get_connection()
        
        assert connection != None
        assert isinstance(connection, MockRedisClient)
        assert connection_pool.active_connections == 1
        assert connection_pool.total_connections_created == 1
    async def test_connection_pool_return_connection(self, connection_pool):
        """Test returning connection to pool"""
        connection = await connection_pool.get_connection()
        await connection_pool.return_connection(connection)
        
        verify_connection_pool_state(connection_pool, 0, 5)
    async def test_connection_pool_max_connections(self, connection_pool):
        """Test connection pool max connections limit"""
        connections = []
        
        for i in range(connection_pool.max_connections):
            conn = await connection_pool.get_connection()
            connections.append(conn)
        
        assert connection_pool.active_connections == connection_pool.max_connections
        assert len(connections) == connection_pool.max_connections
    async def test_concurrent_connection_usage(self, enhanced_redis_manager, connection_pool):
        """Test concurrent usage of pooled connections"""
        enhanced_redis_manager.set_connection_pool(connection_pool)
        
        async def perform_operations(operation_id):
            """Perform Redis operations using pooled connection"""
            connection = await enhanced_redis_manager.get_pooled_connection()
            await connection.set(f"key_{operation_id}", f"value_{operation_id}")
            result = await connection.get(f"key_{operation_id}")
            await enhanced_redis_manager.return_pooled_connection(connection)
            return result
        
        tasks = create_concurrent_tasks(perform_operations, 10)
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert verify_concurrent_results(results, 10)
    async def test_connection_pool_cleanup(self, connection_pool):
        """Test connection pool cleanup"""
        connections = []
        for i in range(3):
            conn = await connection_pool.get_connection()
            connections.append(conn)
        
        assert connection_pool.active_connections == 3
        
        await connection_pool.close_all()
        verify_pool_cleanup(connection_pool)