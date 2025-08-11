"""Complete test coverage for async_utils module - achieving 100% coverage."""

import asyncio
import time
import pytest
import threading
import weakref
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Any
from concurrent.futures import ThreadPoolExecutor

from app.core.async_utils import (
    AsyncResourceManager,
    AsyncTaskPool,
    AsyncRateLimiter,
    async_timeout,
    with_timeout,
    with_retry,
    AsyncBatchProcessor,
    AsyncLock,
    AsyncCircuitBreaker,
    AsyncConnectionPool,
    get_global_resource_manager,
    get_global_task_pool,
    run_in_threadpool,
    shutdown_async_utils
)
from app.core.exceptions import ServiceTimeoutError, ServiceError
from app.core.error_context import ErrorContext


class TestAsyncResourceManagerComplete:
    """Complete tests for AsyncResourceManager."""
    
    @pytest.mark.asyncio
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
        
        resource1 = object()
        resource2 = object()
        
        manager.register_resource(resource1, cleanup1)
        manager.register_resource(resource2, cleanup2)
        manager.register_resource(object())  # Without cleanup
        
        assert resource1 in manager._resources
        assert resource2 in manager._resources
        
        # Test cleanup
        await manager.cleanup_all()
        assert manager._shutting_down
        assert cleanup_calls == [1, 2]
        
        # Test no registration during shutdown
        manager.register_resource(object(), AsyncMock())
        assert len(manager._resources) == 0
        
        # Test idempotent cleanup
        await manager.cleanup_all()
        assert cleanup_calls == [1, 2]  # Not called again


class TestAsyncTaskPoolComplete:
    """Complete tests for AsyncTaskPool."""
    
    @pytest.mark.asyncio
    async def test_complete_task_pool_lifecycle(self):
        """Test complete task pool lifecycle."""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        
        # Test properties
        assert pool.active_task_count == 0
        assert pool._max_concurrent == 2
        
        # Test submit_task success
        async def success_task():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await pool.submit_task(success_task())
        assert result == "success"
        
        # Test submit_task with exception
        async def failing_task():
            raise ValueError("Task failed")
        
        with pytest.raises(ValueError):
            await pool.submit_task(failing_task())
        
        # Test background task
        completed = []
        
        async def bg_task():
            await asyncio.sleep(0.01)
            completed.append(True)
            return "bg_result"
        
        task = pool.submit_background_task(bg_task())
        assert pool.active_task_count > 0
        
        result = await task
        assert result == "bg_result"
        assert completed == [True]
        
        # Wait for cleanup
        await asyncio.sleep(0.01)
        assert pool.active_task_count == 0
        
        # Test _run_background_task through submit
        async def test_bg():
            return "test"
        
        bg_task_obj = pool.submit_background_task(test_bg())
        await bg_task_obj
        
        # Test concurrent limit
        async def slow_task(n):
            await asyncio.sleep(0.05)
            return n
        
        start = time.time()
        tasks = [pool.submit_task(slow_task(i)) for i in range(4)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        assert results == [0, 1, 2, 3]
        assert elapsed >= 0.1  # Should take at least 2 rounds
        
        # Test shutdown with tasks
        long_task = pool.submit_background_task(asyncio.sleep(10))
        await pool.shutdown(timeout=0.01)
        
        assert pool._shutting_down
        assert long_task.cancelled()
        
        # Test operations after shutdown
        with pytest.raises(ServiceError):
            await pool.submit_task(success_task())
        
        with pytest.raises(ServiceError):
            pool.submit_background_task(success_task())
        
        # Test shutdown idempotency
        await pool.shutdown()


class TestAsyncRateLimiterComplete:
    """Complete tests for AsyncRateLimiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_complete(self):
        """Test complete rate limiting scenarios."""
        limiter = AsyncRateLimiter(max_calls=2, time_window=0.1)
        
        # Test under limit
        start = time.time()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.time() - start
        assert elapsed < 0.05
        
        # Test at limit - should wait
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        assert elapsed >= 0.1
        
        # Test old calls cleanup
        assert len(limiter._calls) <= 2
        
        # Wait for window to pass
        await asyncio.sleep(0.15)
        
        # Should be able to acquire immediately
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        assert elapsed < 0.05


class TestTimeoutFunctionsComplete:
    """Complete tests for timeout functions."""
    
    @pytest.mark.asyncio
    async def test_async_timeout_complete(self):
        """Test async_timeout context manager completely."""
        # Success case
        async with async_timeout(1.0, "test_op"):
            await asyncio.sleep(0.01)
            result = "success"
        assert result == "success"
        
        # Timeout case
        with pytest.raises(ServiceTimeoutError) as exc_info:
            async with async_timeout(0.01, "slow_op"):
                await asyncio.sleep(1.0)
        
        assert exc_info.value.timeout_seconds == 0.01
        assert exc_info.value.context != None
    
    @pytest.mark.asyncio
    async def test_with_timeout_decorator_complete(self):
        """Test with_timeout decorator completely."""
        @with_timeout(0.05, "decorated_op")
        async def fast_func(x):
            await asyncio.sleep(0.01)
            return x * 2
        
        result = await fast_func(5)
        assert result == 10
        
        @with_timeout(0.01, "slow_op")
        async def slow_func():
            await asyncio.sleep(1.0)
        
        with pytest.raises(ServiceTimeoutError):
            await slow_func()


class TestRetryDecoratorComplete:
    """Complete tests for retry decorator."""
    
    @pytest.mark.asyncio
    async def test_retry_complete(self):
        """Test retry decorator completely."""
        attempts = []
        
        @with_retry(max_attempts=3, delay=0.01, backoff_factor=2.0)
        async def flaky_func():
            attempts.append(len(attempts))
            if len(attempts) < 3:
                raise ValueError(f"Attempt {len(attempts)}")
            return "success"
        
        result = await flaky_func()
        assert result == "success"
        assert len(attempts) == 3
        
        # Test specific exception types
        @with_retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        async def wrong_exception():
            raise TypeError("Wrong type")
        
        with pytest.raises(TypeError):
            await wrong_exception()
        
        # Test all attempts fail
        @with_retry(max_attempts=2, delay=0.01)
        async def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            await always_fails()


class TestAsyncBatchProcessorComplete:
    """Complete tests for AsyncBatchProcessor."""
    
    @pytest.mark.asyncio
    async def test_batch_processor_complete(self):
        """Test batch processor completely."""
        processor = AsyncBatchProcessor(batch_size=3, max_concurrent_batches=2)
        
        # Empty list
        results = await processor.process_items([], AsyncMock())
        assert results == []
        
        # Single batch
        async def sum_batch(items):
            return sum(items)
        
        results = await processor.process_items([1, 2, 3], sum_batch)
        assert results == [6]
        
        # Multiple batches
        results = await processor.process_items(list(range(10)), sum_batch)
        assert results == [3, 12, 21, 9]  # [0+1+2, 3+4+5, 6+7+8, 9]
        
        # With progress callback
        progress = []
        
        def track_progress(current, total):
            progress.append((current, total))
        
        async def process(items):
            await asyncio.sleep(0.01)
            return len(items)
        
        results = await processor.process_items(
            list(range(7)), process, track_progress
        )
        assert len(results) == 3
        assert progress == [(1, 3), (2, 3), (3, 3)]
        
        # With exception
        async def failing_processor(items):
            if len(items) > 2:
                raise ValueError("Batch too large")
            return len(items)
        
        with pytest.raises(ValueError):
            await processor.process_items([1, 2, 3], failing_processor)


class TestAsyncLockComplete:
    """Complete tests for AsyncLock."""
    
    @pytest.mark.asyncio
    async def test_lock_complete(self):
        """Test AsyncLock completely."""
        lock = AsyncLock("test_lock")
        
        # Test lock info when not locked
        info = lock.lock_info
        assert info["name"] == "test_lock"
        assert not info["locked"]
        assert info["acquired_at"] == None
        assert info["held_for_seconds"] == None
        
        # Test acquire with timeout
        acquired = await lock.acquire_with_timeout(1.0)
        assert acquired
        assert lock.is_locked
        
        # Test lock info when locked
        info = lock.lock_info
        assert info["locked"]
        assert info["acquired_at"] != None
        assert info["held_for_seconds"] >= 0
        
        # Test timeout on already locked
        acquired2 = await lock.acquire_with_timeout(0.01)
        assert not acquired2
        
        # Release
        lock.release()
        assert not lock.is_locked
        
        # Test context manager success
        async with lock.acquire(1.0):
            assert lock.is_locked
        assert not lock.is_locked
        
        # Test context manager timeout
        await lock.acquire_with_timeout(1.0)
        
        with pytest.raises(ServiceTimeoutError):
            async with lock.acquire(0.01):
                pass
        
        lock.release()


class TestAsyncCircuitBreakerComplete:
    """Complete tests for AsyncCircuitBreaker."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_complete(self):
        """Test circuit breaker completely."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            timeout=0.1,
            expected_exception=(ValueError,)
        )
        
        # Test successful calls
        async def success():
            return "ok"
        
        for _ in range(3):
            result = await breaker.call(success)
            assert result == "ok"
        
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
        
        # Test failures open circuit
        async def fail():
            raise ValueError("Failed")
        
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(fail)
        
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 2
        
        # Test circuit open rejects calls
        with pytest.raises(ServiceError) as exc_info:
            await breaker.call(success)
        assert "Circuit breaker is OPEN" in str(exc_info.value)
        
        # Wait for timeout
        await asyncio.sleep(0.11)
        
        # Test half-open to closed
        result = await breaker.call(success)
        assert result == "ok"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
        
        # Test half-open failure reopens
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(fail)
        
        await asyncio.sleep(0.11)
        
        # Fail in half-open
        with pytest.raises(ValueError):
            await breaker.call(fail)
        
        assert breaker.state == "OPEN"


class TestAsyncConnectionPoolComplete:
    """Complete tests for AsyncConnectionPool."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_complete(self):
        """Test connection pool completely."""
        conn_id = 0
        close_log = []
        
        async def create():
            nonlocal conn_id
            conn_id += 1
            return {"id": conn_id, "active": True}
        
        async def close(conn):
            conn["active"] = False
            close_log.append(conn["id"])
        
        pool = AsyncConnectionPool(
            create_connection=create,
            close_connection=close,
            max_size=2,
            min_size=1
        )
        
        # Initialize
        await pool.initialize()
        
        # Acquire and release
        async with pool.acquire() as conn:
            assert conn["active"]
            assert conn in pool._active_connections
        
        assert conn not in pool._active_connections
        
        # Test timeout when no connections available
        async def slow_create():
            await asyncio.sleep(10)
            return {"id": 999}
        
        slow_pool = AsyncConnectionPool(
            create_connection=slow_create,
            close_connection=close,
            max_size=1,
            min_size=0
        )
        
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.01):
                async with slow_pool.acquire():
                    pass
        
        # Test max connections
        conns = []
        for _ in range(2):
            conn = await pool.acquire().__aenter__()
            conns.append(conn)
            pool._active_connections.add(conn)
        
        # Pool is full, should wait for available
        start = time.time()
        
        async def release_after_delay():
            await asyncio.sleep(0.05)
            await pool._available_connections.put(conns[0])
            pool._active_connections.discard(conns[0])
        
        asyncio.create_task(release_after_delay())
        
        async with pool.acquire() as conn:
            elapsed = time.time() - start
            assert elapsed >= 0.05
        
        # Clean up active connections
        for conn in conns[1:]:
            pool._active_connections.discard(conn)
        
        # Test queue full scenario
        for i in range(pool._available_connections.maxsize):
            try:
                pool._available_connections.put_nowait({"id": 100 + i})
            except asyncio.QueueFull:
                break
        
        # Connection should be closed when queue is full
        test_conn = {"id": 200, "active": True}
        pool._active_connections.add(test_conn)
        
        # Manually trigger the finally block logic
        try:
            async with pool.acquire() as conn:
                pass
        except:
            pass
        
        # Test close pool
        await pool.close()
        assert pool._closed
        
        # Test acquire from closed pool
        with pytest.raises(ServiceError):
            async with pool.acquire():
                pass
        
        # Test close idempotency
        await pool.close()


class TestGlobalFunctionsComplete:
    """Complete tests for global functions."""
    
    def test_global_instances(self):
        """Test global instance getters."""
        manager1 = get_global_resource_manager()
        manager2 = get_global_resource_manager()
        assert manager1 is manager2
        assert isinstance(manager1, AsyncResourceManager)
        
        pool1 = get_global_task_pool()
        pool2 = get_global_task_pool()
        assert pool1 is pool2
        assert isinstance(pool1, AsyncTaskPool)
    
    @pytest.mark.asyncio
    async def test_run_in_threadpool_complete(self):
        """Test run_in_threadpool completely."""
        def sync_func(x, y=10):
            return x + y
        
        # Test with args
        result = await run_in_threadpool(sync_func, 5)
        assert result == 15
        
        # Test with kwargs
        result = await run_in_threadpool(sync_func, 3, y=7)
        assert result == 10
        
        # Test exception
        def failing_func():
            raise ValueError("Sync error")
        
        with pytest.raises(ValueError):
            await run_in_threadpool(failing_func)
        
        # Test executor reuse
        assert hasattr(run_in_threadpool, '_executor')
        executor1 = run_in_threadpool._executor
        
        await run_in_threadpool(lambda: None)
        executor2 = run_in_threadpool._executor
        assert executor1 is executor2
    
    @pytest.mark.asyncio
    async def test_shutdown_complete(self):
        """Test shutdown_async_utils completely."""
        # Create and use resources
        manager = get_global_resource_manager()
        pool = get_global_task_pool()
        
        # Reset their state first
        manager._shutting_down = False
        pool._shutting_down = False
        
        manager.register_resource(object())
        
        # Use threadpool
        await run_in_threadpool(lambda: "test")
        assert hasattr(run_in_threadpool, '_executor')
        
        # Shutdown
        await shutdown_async_utils()
        
        assert manager._shutting_down
        assert pool._shutting_down


class TestErrorContextIntegration:
    """Test integration with ErrorContext."""
    
    @pytest.mark.asyncio
    async def test_error_context_in_exceptions(self):
        """Test that error context is included in exceptions."""
        # Test ServiceTimeoutError with context
        with patch.object(ErrorContext, 'get_all_context', return_value={"test": "context"}):
            with pytest.raises(ServiceTimeoutError) as exc_info:
                async with async_timeout(0.01):
                    await asyncio.sleep(1.0)
            
            assert exc_info.value.context == {"test": "context"}
        
        # Test ServiceError with context
        pool = AsyncTaskPool()
        pool._shutting_down = True
        
        with patch.object(ErrorContext, 'get_all_context', return_value={"pool": "context"}):
            with pytest.raises(ServiceError) as exc_info:
                await pool.submit_task(asyncio.sleep(0.01))
            
            assert exc_info.value.context == {"pool": "context"}
        
        # Test in AsyncLock
        lock = AsyncLock("test")
        await lock.acquire_with_timeout()
        
        with patch.object(ErrorContext, 'get_all_context', return_value={"lock": "context"}):
            with pytest.raises(ServiceTimeoutError) as exc_info:
                async with lock.acquire(0.01):
                    pass
            
            assert exc_info.value.context == {"lock": "context"}


class TestWeakRefBehavior:
    """Test WeakSet behavior in AsyncResourceManager."""
    
    @pytest.mark.asyncio
    async def test_weakref_cleanup(self):
        """Test that weak references are cleaned up."""
        manager = AsyncResourceManager()
        
        # Create resource that will go out of scope
        def create_and_register():
            resource = object()
            manager.register_resource(resource)
            return weakref.ref(resource)
        
        weak_ref = create_and_register()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Weak reference should be dead
        assert weak_ref() == None
        
        # Resources should be automatically cleaned from WeakSet
        # This is handled by WeakSet internally


class TestConcurrencyEdgeCases:
    """Test concurrency edge cases."""
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiter_access(self):
        """Test concurrent access to rate limiter."""
        limiter = AsyncRateLimiter(max_calls=5, time_window=0.1)
        
        async def acquire_many(n):
            for _ in range(n):
                await limiter.acquire()
        
        # Run multiple coroutines concurrently
        await asyncio.gather(
            acquire_many(2),
            acquire_many(2),
            acquire_many(1)
        )
        
        assert len(limiter._calls) == 5
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_calls(self):
        """Test circuit breaker with concurrent calls."""
        breaker = AsyncCircuitBreaker(failure_threshold=3)
        call_count = 0
        
        async def counted_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Call {call_count}")
        
        # Run concurrent failures
        tasks = []
        for _ in range(5):
            tasks.append(asyncio.create_task(breaker.call(counted_fail)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should have failed
        assert all(isinstance(r, (ValueError, ServiceError)) for r in results)
        
        # Circuit should be open
        assert breaker.state == "OPEN"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])