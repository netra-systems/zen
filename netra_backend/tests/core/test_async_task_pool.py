"""
Tests for AsyncTaskPool - task management and concurrency control
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.core.async_resource_manager import AsyncTaskPool
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.tests.helpers.async_utils_helpers import (
    assert_task_pool_state,
    create_quick_operation,
    measure_timing,
)

class TestAsyncTaskPool:
    """Test AsyncTaskPool for task management"""
    
    @pytest.fixture
    def task_pool(self):
        return AsyncTaskPool(max_concurrent_tasks=3)
    
    def test_initialization(self, task_pool):
        """Test task pool initialization"""
        assert_task_pool_state(task_pool, 3)
        assert task_pool._semaphore._value == 3
    @pytest.mark.asyncio
    async def test_submit_task_success(self, task_pool):
        """Test successful task submission and execution"""
        result = await task_pool.submit_task(create_quick_operation())
        assert result == "success"
        assert len(task_pool._active_tasks) == 0
    @pytest.mark.asyncio
    async def test_submit_task_exception(self, task_pool):
        """Test task submission with exception"""
        async def failing_task():
            raise ValueError("Task failed")
        with pytest.raises(ValueError, match="Task failed"):
            await task_pool.submit_task(failing_task())
        assert len(task_pool._active_tasks) == 0
    @pytest.mark.asyncio
    async def test_submit_task_during_shutdown(self, task_pool):
        """Test task submission during shutdown"""
        task_pool._shutting_down = True
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.async_utils.ErrorContext.get_all_context', return_value={}):
            with pytest.raises(ServiceError, match="Task pool is shutting down"):
                await task_pool.submit_task(create_quick_operation())
    @pytest.mark.asyncio
    async def test_submit_background_task(self, task_pool):
        """Test background task submission"""
        task = task_pool.submit_background_task(create_quick_operation())
        assert task in task_pool._active_tasks
        result = await task
        assert result == "success"
        await asyncio.sleep(0.01)
        assert task not in task_pool._active_tasks
    @pytest.mark.asyncio
    async def test_submit_background_task_during_shutdown(self, task_pool):
        """Test background task submission during shutdown"""
        task_pool._shutting_down = True
        with pytest.raises(ServiceError, match="Task pool is shutting down"):
            task_pool.submit_background_task(create_quick_operation())
    
    def test_active_task_count(self, task_pool):
        """Test active task count property"""
        assert task_pool.active_task_count == 0
        # Mock: Generic component isolation for controlled unit testing
        task1, task2 = Mock(), Mock()
        task_pool._active_tasks.add(task1)
        task_pool._active_tasks.add(task2)
        assert task_pool.active_task_count == 2
    @pytest.mark.asyncio
    async def test_concurrent_task_limit(self):
        """Test that task pool respects concurrent task limits"""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        results = []
        start_time = time.time()
        tasks = [pool.submit_task(self._create_slow_task(i, results, start_time)) for i in range(4)]
        await asyncio.gather(*tasks)
        self._assert_concurrent_execution(results)
    
    async def _create_slow_task(self, task_id, results, start_time):
        """Helper for concurrent task test"""
        await asyncio.sleep(0.05)
        results.append((task_id, time.time() - start_time))
        return task_id
    
    def _assert_concurrent_execution(self, results):
        """Assert tasks were executed with proper concurrency"""
        assert len(results) == 4
        assert results[2][1] > results[0][1]
        assert results[3][1] > results[1][1]
    @pytest.mark.asyncio
    async def test_shutdown(self, task_pool):
        """Test graceful shutdown of task pool"""
        task = task_pool.submit_background_task(self._create_long_task())
        await task_pool.shutdown(timeout=0.1)
        assert task_pool._shutting_down == True
        assert len(task_pool._active_tasks) == 0
        with pytest.raises(asyncio.CancelledError):
            await task
    
    async def _create_long_task(self):
        """Helper for shutdown test"""
        try:
            await asyncio.sleep(1)
            return "completed"
        except asyncio.CancelledError:
            return "cancelled"
    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, task_pool):
        """Test that shutdown is idempotent"""
        await task_pool.shutdown()
        assert task_pool._shutting_down == True
        await task_pool.shutdown()
        assert task_pool._shutting_down == True
    @pytest.mark.asyncio
    async def test_shutdown_no_tasks(self, task_pool):
        """Test shutdown with no active tasks"""
        await task_pool.shutdown()
        assert_task_pool_state(task_pool, 3, True, 0)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])