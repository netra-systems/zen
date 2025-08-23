"""
Tests for global instances, threadpool, and shutdown functionality
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from unittest.mock import Mock

import pytest

from netra_backend.app.core.async_resource_manager import (
    AsyncResourceManager,
    AsyncTaskPool,
    get_global_resource_manager,
    get_global_task_pool,
    run_in_threadpool,
    shutdown_async_utils,
)

class TestGlobalInstances:
    """Test global instance management"""
    
    def test_get_global_resource_manager(self):
        """Test getting global resource manager"""
        manager = get_global_resource_manager()
        assert isinstance(manager, AsyncResourceManager)
        manager2 = get_global_resource_manager()
        assert manager is manager2
    
    def test_get_global_task_pool(self):
        """Test getting global task pool"""
        pool = get_global_task_pool()
        assert isinstance(pool, AsyncTaskPool)
        pool2 = get_global_task_pool()
        assert pool is pool2

class TestRunInThreadpool:
    """Test thread pool execution"""
    async def test_run_sync_function_in_threadpool(self):
        """Test running synchronous function in thread pool"""
        def sync_function(x, y):
            time.sleep(0.01)
            return x + y
        result = await run_in_threadpool(sync_function, 2, 3)
        assert result == 5
    async def test_run_sync_function_with_kwargs(self):
        """Test running sync function with keyword arguments"""
        def sync_function_with_kwargs(x, y=10, z=20):
            return x + y + z
        result = await run_in_threadpool(sync_function_with_kwargs, 5, y=15, z=25)
        assert result == 45
    async def test_threadpool_reuses_executor(self):
        """Test that thread pool executor is reused"""
        def get_thread_id():
            import threading
            return threading.current_thread().ident
        thread_id1 = await run_in_threadpool(get_thread_id)
        thread_id2 = await run_in_threadpool(get_thread_id)
        assert thread_id1 != None
        assert thread_id2 != None
        assert hasattr(run_in_threadpool, '_executor')

class TestShutdownAsyncUtils:
    """Test shutdown functionality"""
    async def test_shutdown_async_utils(self):
        """Test shutting down async utilities"""
        resource_manager = get_global_resource_manager()
        task_pool = get_global_task_pool()
        resource_manager.register_resource(Mock())
        task_pool.submit_background_task(asyncio.sleep(0.01))
        await shutdown_async_utils()
        assert resource_manager._shutting_down == True
        assert task_pool._shutting_down == True
    async def test_shutdown_with_thread_pool_executor(self):
        """Test shutdown including thread pool executor"""
        def sync_func():
            return "result"
        result = await run_in_threadpool(sync_func)
        assert result == "result"
        assert hasattr(run_in_threadpool, '_executor')
        await shutdown_async_utils()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])