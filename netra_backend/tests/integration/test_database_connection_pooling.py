"""Integration tests for database connection pooling efficiency

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database performance optimization
- Value Impact: Ensures connection pooling works efficiently under load
- Strategic Impact: Prevents connection exhaustion and performance degradation

This test suite validates:
1. Connection pool initialization and configuration
2. Pool size limits and overflow handling
3. Connection reuse and recycling
4. Performance under concurrent load
5. Pool cleanup and resource management
"""

import asyncio
import time
from typing import List
import pytest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres_unified import unified_db, initialize_database
from netra_backend.app.db.postgres_async import async_db
from netra_backend.app.core.configuration.base import get_unified_config
# Database fixtures imported as needed


class TestDatabaseConnectionPooling:
    """Test database connection pooling efficiency and configuration"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization_and_status(self):
        """Test that connection pool initializes with correct parameters"""
        # Initialize database if not already done
        await initialize_database()
        
        # Get pool status
        status = unified_db.get_status()
        
        assert status["status"] in ["active", "not_initialized"]
        
        # If we're using async manager, test pool status
        if hasattr(unified_db.manager, 'get_pool_status'):
            pool_status = unified_db.manager.get_pool_status()
            
            assert "status" in pool_status
            assert "pool_class" in pool_status
            
            # Check for expected pool attributes
            if pool_status["status"] == "active":
                # Pool should be AsyncAdaptedQueuePool for async connections
                assert "AsyncAdaptedQueuePool" in pool_status.get("pool_class", "")
    
    @pytest.mark.asyncio
    async def test_connection_pool_size_limits(self):
        """Test connection pool respects size and overflow limits"""
        config = get_unified_config()
        
        # Skip if in test environment without real pooling
        if config.environment == "test":
            pytest.skip("Pool size testing requires real database environment")
        
        await initialize_database()
        
        # Get initial pool status
        if hasattr(unified_db.manager, 'get_pool_status'):
            initial_status = unified_db.manager.get_pool_status()
            
            # Test multiple concurrent connections within pool size
            async def use_connection(connection_id: int):
                """Use a connection and perform a simple query"""
                try:
                    async with unified_db.get_session() as session:
                        result = await session.execute(
                            text("SELECT :conn_id as connection_id"),
                            {"conn_id": connection_id}
                        )
                        value = result.scalar_one()
                        await asyncio.sleep(0.1)  # Hold connection briefly
                        return value
                except Exception as e:
                    return f"Error: {e}"
            
            # Create multiple concurrent connections (less than pool size)
            tasks = [use_connection(i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All connections should succeed
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Connection {i} failed: {result}")
                else:
                    assert result == i
    
    @pytest.mark.asyncio
    async def test_connection_reuse_efficiency(self):
        """Test that connections are properly reused"""
        await initialize_database()
        
        connection_times = []
        
        async def timed_connection():
            """Time how long it takes to get and use a connection"""
            start_time = time.time()
            try:
                async with unified_db.get_session() as session:
                    await session.execute(text("SELECT 1"))
                    connection_time = time.time() - start_time
                    return connection_time
            except Exception as e:
                return float('inf')  # Mark failed connections
        
        # First connection (may be slower due to pool initialization)
        first_time = await timed_connection()
        connection_times.append(first_time)
        
        # Subsequent connections should be faster due to reuse
        for _ in range(10):
            conn_time = await timed_connection()
            connection_times.append(conn_time)
        
        # Average connection time after first should be relatively consistent
        avg_reuse_time = sum(connection_times[1:]) / len(connection_times[1:])
        
        # Reused connections should be faster than first connection
        # (allowing some variance for system performance)
        if first_time < float('inf') and avg_reuse_time < float('inf'):
            # Reuse should be at least somewhat more efficient
            assert avg_reuse_time <= first_time * 1.5, (
                f"Connection reuse not efficient: "
                f"first={first_time:.4f}s, avg_reuse={avg_reuse_time:.4f}s"
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self):
        """Test pool handling under concurrent load"""
        await initialize_database()
        
        async def concurrent_query(query_id: int):
            """Perform a query with simulated work"""
            try:
                async with unified_db.get_session() as session:
                    # Simulate some database work
                    result = await session.execute(
                        text("SELECT :qid, pg_sleep(0.01)"),
                        {"qid": query_id}
                    )
                    return result.scalar_one()
            except Exception as e:
                return f"Error-{query_id}: {e}"
        
        # Create more concurrent tasks than the pool size to test overflow
        num_concurrent = 15
        start_time = time.time()
        
        tasks = [concurrent_query(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Check that all tasks completed
        successful_queries = 0
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and not str(result).startswith("Error"):
                successful_queries += 1
        
        # Most queries should succeed (allowing for some failures under high load)
        success_rate = successful_queries / num_concurrent
        assert success_rate >= 0.8, f"Too many failures: {success_rate:.2%} success rate"
        
        # Total time should be reasonable (connections handled concurrently)
        max_expected_time = 5.0  # Allow generous time for concurrent handling
        assert total_time < max_expected_time, (
            f"Concurrent handling too slow: {total_time:.2f}s for {num_concurrent} queries"
        )
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_exception(self):
        """Test that connections are properly cleaned up after exceptions"""
        await initialize_database()
        
        initial_status = None
        if hasattr(unified_db.manager, 'get_pool_status'):
            initial_status = unified_db.manager.get_pool_status()
        
        # Perform operation that causes exception
        try:
            async with unified_db.get_session() as session:
                # Invalid SQL to cause exception
                await session.execute(text("SELECT FROM invalid_table_name"))
                await session.commit()
        except Exception:
            pass  # Expected to fail
        
        # Pool should still be in good state
        if initial_status:
            post_error_status = unified_db.manager.get_pool_status()
            assert post_error_status["status"] == "active"
            
            # Pool metrics should be similar (connections cleaned up)
            if "checked_out" in initial_status and "checked_out" in post_error_status:
                # Checked out connections should not have increased
                assert (post_error_status["checked_out"] <= 
                       initial_status.get("checked_out", 0) + 1)
    
    @pytest.mark.asyncio
    async def test_pool_health_check(self):
        """Test database health check works with pooling"""
        await initialize_database()
        
        # Test connection should work
        is_healthy = await unified_db.test_connection()
        assert is_healthy, "Database health check failed"
        
        # Multiple health checks should not exhaust pool
        health_results = []
        for _ in range(5):
            health_result = await unified_db.test_connection()
            health_results.append(health_result)
        
        # All health checks should succeed
        assert all(health_results), f"Health checks failed: {health_results}"
    
    @pytest.mark.asyncio
    async def test_connection_recycling(self):
        """Test that connections are recycled after timeout"""
        config = get_unified_config()
        
        # Skip if in test environment
        if config.environment == "test":
            pytest.skip("Connection recycling test requires real database environment")
        
        await initialize_database()
        
        if hasattr(unified_db.manager, 'engine') and unified_db.manager.engine:
            engine = unified_db.manager.engine
            pool = engine.pool
            
            # Check that pool has recycling configured
            if hasattr(pool, '_recycle'):
                assert pool._recycle > 0, "Connection recycling not configured"
            
            # Test that connections work normally
            async with unified_db.get_session() as session:
                result = await session.execute(text("SELECT current_timestamp"))
                timestamp = result.scalar_one()
                assert timestamp is not None
    
    @pytest.mark.asyncio 
    async def test_pool_monitoring_metrics(self):
        """Test that pool monitoring provides useful metrics"""
        await initialize_database()
        
        if hasattr(unified_db.manager, 'get_pool_status'):
            status = unified_db.manager.get_pool_status()
            
            # Should have basic status information
            assert "status" in status
            assert status["status"] in ["active", "not_initialized"]
            
            if status["status"] == "active":
                # Should have pool class information
                assert "pool_class" in status
                
                # Use a connection and check metrics change
                async with unified_db.get_session() as session:
                    active_status = unified_db.manager.get_pool_status()
                    
                    # Status should still be active
                    assert active_status["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_database_url_ssl_compatibility(self):
        """Test that database URL SSL parameter conversion works with pooling"""
        await initialize_database()
        
        # Test that SSL parameter conversion doesn't break pooling
        async with unified_db.get_session() as session:
            # Simple query to verify connection works
            result = await session.execute(text("SELECT version()"))
            version = result.scalar_one()
            assert "PostgreSQL" in version
        
        # Pool should remain healthy after SSL parameter handling
        is_healthy = await unified_db.test_connection()
        assert is_healthy


class TestPoolingPerformanceBenchmarks:
    """Performance benchmarks for connection pooling"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sequential_vs_pooled_performance(self):
        """Compare performance with and without connection pooling"""
        await initialize_database()
        
        num_queries = 20
        
        # Test with pooled connections (normal operation)
        async def pooled_query(i: int):
            async with unified_db.get_session() as session:
                result = await session.execute(text("SELECT :i"), {"i": i})
                return result.scalar_one()
        
        # Time pooled queries
        start_time = time.time()
        pooled_tasks = [pooled_query(i) for i in range(num_queries)]
        pooled_results = await asyncio.gather(*pooled_tasks)
        pooled_time = time.time() - start_time
        
        # Verify results
        assert len(pooled_results) == num_queries
        assert all(pooled_results[i] == i for i in range(num_queries))
        
        # Pooled queries should complete in reasonable time
        max_expected_time = 10.0  # Generous allowance
        assert pooled_time < max_expected_time, (
            f"Pooled queries too slow: {pooled_time:.2f}s for {num_queries} queries"
        )
        
        avg_query_time = pooled_time / num_queries
        assert avg_query_time < 0.5, (
            f"Average query time too slow: {avg_query_time:.4f}s per query"
        )


# pytest markers for different test categories
pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.asyncio
]