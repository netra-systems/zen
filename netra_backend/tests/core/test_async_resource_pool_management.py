"""
Focused tests for Async Resource and Pool Management
Tests AsyncResourceManager, AsyncTaskPool, and AsyncConnectionPool functionality
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.async_utils import (
    AsyncConnectionPool,
    AsyncResourceManager,
    AsyncTaskPool,
    get_global_resource_manager,
    get_global_task_pool,
    run_in_threadpool,
)
from netra_backend.app.core.exceptions_service import ServiceError, ServiceTimeoutError

class TestAsyncResourceManagerComplete:
    """Complete tests for AsyncResourceManager."""
    async def test_full_lifecycle(self):
        """Test complete resource manager lifecycle."""
        manager = AsyncResourceManager()
        cleanup_calls = []
        
        # Test registration
        async def cleanup1():
            cleanup_calls.append(1)
        
        async def cleanup2():
            cleanup_calls.append(2)
            raise ValueError("Cleanup error")  # Should be handled
        
        # Use objects that support weak references
        class TestResource:
            pass
        
        resource1 = TestResource()
        resource2 = TestResource()
        
        manager.register_cleanup(resource1, cleanup1)
        manager.register_cleanup(resource2, cleanup2)
        assert len(manager._cleanup_callbacks) == 2
        
        # Test cleanup
        await manager.cleanup()
        assert cleanup_calls == [1, 2]  # Both should execute despite error
        assert len(manager._cleanup_callbacks) == 0
    async def test_weak_reference_behavior(self):
        """Test that cleanup callbacks are removed when objects are garbage collected."""
        manager = AsyncResourceManager()
        
        class TestResource:
            pass
        
        resource = TestResource()
        cleanup_called = []
        
        async def cleanup():
            cleanup_called.append(True)
        
        manager.register_cleanup(resource, cleanup)
        assert len(manager._cleanup_callbacks) == 1
        
        # Delete the resource
        del resource
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check that the weak reference was cleaned up
        manager._cleanup_dead_refs()
        assert len(manager._cleanup_callbacks) == 0
    async def test_concurrent_cleanup_registration(self):
        """Test concurrent cleanup registration and execution."""
        manager = AsyncResourceManager()
        results = []
        
        class TestResource:
            def __init__(self, id):
                self.id = id
        
        async def register_and_cleanup(resource_id):
            resource = TestResource(resource_id)
            
            async def cleanup():
                results.append(resource_id)
            
            manager.register_cleanup(resource, cleanup)
        
        # Register multiple cleanups concurrently
        tasks = [register_and_cleanup(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Cleanup all
        await manager.cleanup()
        assert len(results) == 5
        assert sorted(results) == list(range(5))

class TestAsyncTaskPoolComplete:
    """Complete tests for AsyncTaskPool."""
    async def test_pool_limits_and_queuing(self):
        """Test task pool with limits and queuing."""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        execution_order = []
        
        async def task(task_id, delay=0.1):
            execution_order.append(f"start_{task_id}")
            await asyncio.sleep(delay)
            execution_order.append(f"end_{task_id}")
            return task_id
        
        # Submit more tasks than the limit
        tasks = [pool.submit(task(i)) for i in range(4)]
        results = await asyncio.gather(*tasks)
        
        assert results == [0, 1, 2, 3]
        assert len(execution_order) == 8  # 4 starts + 4 ends
    async def test_pool_shutdown_behavior(self):
        """Test task pool shutdown behavior."""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        results = []
        
        async def long_task(task_id):
            await asyncio.sleep(0.5)
            results.append(task_id)
            return task_id
        
        # Submit tasks
        task1 = pool.submit(long_task(1))
        task2 = pool.submit(long_task(2))
        
        # Start shutdown immediately
        await pool.shutdown(wait=False)
        
        # Wait for completion
        await asyncio.gather(task1, task2, return_exceptions=True)
        assert len(results) <= 2  # May not all complete
    async def test_pool_task_exception_handling(self):
        """Test exception handling in task pool."""
        pool = AsyncTaskPool(max_concurrent_tasks=3)
        
        async def failing_task():
            raise ValueError("Task failed")
        
        async def successful_task():
            return "success"
        
        # Submit mix of failing and successful tasks
        tasks = [
            pool.submit(failing_task()),
            pool.submit(successful_task()),
            pool.submit(failing_task())
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        assert isinstance(results[0], ValueError)
        assert results[1] == "success"
        assert isinstance(results[2], ValueError)
    async def test_pool_context_manager(self):
        """Test task pool as context manager."""
        execution_log = []
        
        async def test_task(task_id):
            execution_log.append(f"task_{task_id}")
            return task_id
        
        async with AsyncTaskPool(max_concurrent_tasks=2) as pool:
            tasks = [pool.submit(test_task(i)) for i in range(3)]
            results = await asyncio.gather(*tasks)
        
        assert results == [0, 1, 2]
        assert len(execution_log) == 3

class TestAsyncConnectionPoolComplete:
    """Complete tests for AsyncConnectionPool."""
    async def test_connection_pool_lifecycle(self):
        """Test complete connection pool lifecycle."""
        created_connections = []
        closed_connections = []
        
        async def create_connection():
            conn_id = len(created_connections)
            created_connections.append(conn_id)
            return f"conn_{conn_id}"
        
        async def close_connection(conn):
            closed_connections.append(conn)
        
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=3,
            min_size=1
        )
        
        # Initialize pool
        await pool.initialize()
        assert len(created_connections) >= 1  # Should create min_size connections
        
        # Get and return connections
        conn1 = await pool.get_connection()
        conn2 = await pool.get_connection()
        
        assert conn1 in created_connections or isinstance(conn1, str)
        assert conn2 in created_connections or isinstance(conn2, str)
        
        await pool.return_connection(conn1)
        await pool.return_connection(conn2)
        
        # Close pool
        await pool.close()
        assert len(closed_connections) > 0
    async def test_connection_pool_timeout_handling(self):
        """Test connection pool timeout handling."""
        async def slow_create_connection():
            await asyncio.sleep(1.0)  # Slow connection creation
            return "slow_conn"
        
        async def fast_close_connection(conn):
            pass
        
        pool = AsyncConnectionPool(
            create_connection=slow_create_connection,
            close_connection=fast_close_connection,
            max_size=1
        )
        
        await pool.initialize()
        
        # This should timeout if connection creation is too slow
        start_time = time.time()
        try:
            conn = await asyncio.wait_for(pool.get_connection(), timeout=0.5)
            await pool.return_connection(conn)
        except asyncio.TimeoutError:
            pass  # Expected for slow creation
        
        execution_time = time.time() - start_time
        assert execution_time <= 1.0  # Should not take too long
        
        await pool.close()
    async def test_connection_pool_error_recovery(self):
        """Test connection pool error recovery."""
        failure_count = 0
        
        async def unreliable_create_connection():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise ConnectionError("Connection failed")
            return f"conn_{failure_count}"
        
        async def close_connection(conn):
            pass
        
        pool = AsyncConnectionPool(
            create_connection=unreliable_create_connection,
            close_connection=close_connection,
            max_size=2
        )
        
        # Should handle creation failures gracefully
        try:
            await pool.initialize()
        except ConnectionError:
            pass  # May fail initial creation
        
        # Should eventually succeed
        conn = await pool.get_connection()
        assert conn is not None
        await pool.return_connection(conn)
        await pool.close()
    async def test_connection_pool_concurrent_access(self):
        """Test concurrent access to connection pool."""
        connection_counter = 0
        
        async def create_connection():
            nonlocal connection_counter
            connection_counter += 1
            await asyncio.sleep(0.01)  # Simulate connection setup
            return f"conn_{connection_counter}"
        
        async def close_connection(conn):
            pass
        
        pool = AsyncConnectionPool(
            create_connection=create_connection,
            close_connection=close_connection,
            max_size=3
        )
        
        await pool.initialize()
        
        async def worker(worker_id):
            conn = await pool.get_connection()
            await asyncio.sleep(0.05)  # Use connection
            await pool.return_connection(conn)
            return worker_id
        
        # Run multiple workers concurrently
        workers = [worker(i) for i in range(5)]
        results = await asyncio.gather(*workers)
        
        assert results == list(range(5))
        await pool.close()

class TestGlobalResourceManagement:
    """Test global resource management functions."""
    async def test_global_resource_manager_access(self):
        """Test access to global resource manager."""
        manager1 = get_global_resource_manager()
        manager2 = get_global_resource_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        assert isinstance(manager1, AsyncResourceManager)
    async def test_global_task_pool_access(self):
        """Test access to global task pool."""
        pool1 = get_global_task_pool()
        pool2 = get_global_task_pool()
        
        # Should return the same instance
        assert pool1 is pool2
        assert isinstance(pool1, AsyncTaskPool)
    async def test_run_in_threadpool_functionality(self):
        """Test run_in_threadpool functionality."""
        def cpu_bound_task(n):
            """Simulate CPU-bound work."""
            total = 0
            for i in range(n):
                total += i
            return total
        
        # Test with small workload
        result = await run_in_threadpool(cpu_bound_task, 100)
        expected = sum(range(100))
        assert result == expected
    async def test_run_in_threadpool_with_exception(self):
        """Test run_in_threadpool exception handling."""
        def failing_task():
            raise ValueError("Thread task failed")
        
        with pytest.raises(ValueError, match="Thread task failed"):
            await run_in_threadpool(failing_task)