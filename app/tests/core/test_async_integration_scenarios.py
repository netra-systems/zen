"""
Integration tests combining multiple async utilities
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from app.core.async_connection_pool import AsyncConnectionPool
from app.core.async_rate_limiter import AsyncRateLimiter
from app.core.async_retry_logic import AsyncCircuitBreaker, with_retry
from app.core.async_resource_manager import (
    AsyncResourceManager,
    AsyncTaskPool,
    AsyncBatchProcessor,
)
from app.tests.helpers.shared_test_types import TestIntegrationScenarios as SharedTestIntegrationScenarios


class TestIntegrationScenarios(SharedTestIntegrationScenarios):
    """Integration tests combining multiple async utilities"""
    async def test_resource_manager_with_task_pool(self):
        """Test resource manager integrated with task pool"""
        resource_manager, task_pool = self._create_manager_and_pool()
        cleanup_callback = AsyncMock()
        resource_manager.register_resource(task_pool, cleanup_callback)
        result = await task_pool.submit_task(self._sample_task())
        assert result == "completed"
        await resource_manager.cleanup_all()
        cleanup_callback.assert_called_once()
    
    def _create_manager_and_pool(self):
        """Helper to create manager and task pool"""
        resource_manager = AsyncResourceManager()
        task_pool = AsyncTaskPool(max_concurrent_tasks=2)
        return resource_manager, task_pool
    
    async def _sample_task(self):
        """Helper task for testing"""
        await asyncio.sleep(0.01)
        return "completed"
    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker with retry decorator"""
        circuit_breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.1)
        call_count = {'value': 0}
        @with_retry(max_attempts=5, delay=0.01)
        async def unreliable_service():
            return await circuit_breaker.call(self._create_operation(call_count))
        result = await unreliable_service()
        assert result == "success"
        assert call_count['value'] > 2
    
    def _create_operation(self, call_count):
        """Helper to create unreliable operation"""
        async def operation():
            call_count['value'] += 1
            if call_count['value'] <= 3:
                raise ValueError("Service unavailable")
            return "success"
        return operation
    async def test_batch_processor_with_rate_limiter(self):
        """Test batch processor with rate limiting"""
        rate_limiter, batch_processor = self._create_rate_limited_processor()
        items = list(range(6))
        start_time = time.time()
        results = await batch_processor.process_items(items, self._create_processor(rate_limiter))
        end_time = time.time()
        assert results == [2, 2, 2]
        assert end_time - start_time >= 0.1
    
    def _create_rate_limited_processor(self):
        """Helper to create rate limiter and batch processor"""
        rate_limiter = AsyncRateLimiter(max_calls=2, time_window=0.1)
        batch_processor = AsyncBatchProcessor(batch_size=2)
        return rate_limiter, batch_processor
    
    def _create_processor(self, rate_limiter):
        """Helper to create rate limited processor function"""
        async def processor(batch):
            await rate_limiter.acquire()
            await asyncio.sleep(0.01)
            return len(batch)
        return processor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])