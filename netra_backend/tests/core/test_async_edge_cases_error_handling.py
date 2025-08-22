"""
Focused tests for Async Edge Cases and Error Handling
Tests error context integration, weak reference behavior, and concurrency edge cases
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import gc
import threading
import time
import weakref
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.async_utils import (
    AsyncCircuitBreaker,
    AsyncRateLimiter,
    AsyncResourceManager,
    AsyncTaskPool,
    shutdown_async_utils,
)
from netra_backend.app.core.error_context import ErrorContext
from netra_backend.app.core.exceptions_service import ServiceError, ServiceTimeoutError

class TestErrorContextIntegration:
    """Test error context integration with async utilities."""
    async def test_error_context_with_task_pool(self):
        """Test error context integration with task pool."""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        error_contexts = []
        
        async def context_aware_task(task_id, should_fail=False):
            with ErrorContext(f"task_{task_id}"):
                if should_fail:
                    raise ServiceError(f"Task {task_id} failed")
                return f"success_{task_id}"
        
        # Submit mix of successful and failing tasks
        tasks = [
            pool.submit(context_aware_task(1, False)),
            pool.submit(context_aware_task(2, True)),
            pool.submit(context_aware_task(3, False))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        assert results[0] == "success_1"
        assert isinstance(results[1], ServiceError)
        assert results[2] == "success_3"
    async def test_error_context_with_circuit_breaker(self):
        """Test error context with circuit breaker."""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.5)
        context_failures = []
        
        async def context_operation(op_id, should_fail=False):
            with ErrorContext(f"circuit_op_{op_id}") as ctx:
                if should_fail:
                    context_failures.append(ctx.context_id)
                    raise ServiceError(f"Operation {op_id} failed")
                return f"success_{op_id}"
        
        # Cause failures to open circuit
        for i in range(3):
            try:
                await breaker.call(lambda i=i: context_operation(i, True))
            except ServiceError:
                pass
        
        assert len(context_failures) >= 2
    async def test_error_context_propagation(self):
        """Test error context propagation through async calls."""
        propagation_log = []
        
        async def level_3_operation():
            with ErrorContext("level_3"):
                propagation_log.append("level_3")
                raise ServiceError("Level 3 error")
        
        async def level_2_operation():
            with ErrorContext("level_2"):
                propagation_log.append("level_2")
                await level_3_operation()
        
        async def level_1_operation():
            with ErrorContext("level_1"):
                propagation_log.append("level_1")
                await level_2_operation()
        
        with pytest.raises(ServiceError):
            await level_1_operation()
        
        assert propagation_log == ["level_1", "level_2", "level_3"]
    async def test_error_context_with_timeout(self):
        """Test error context with timeout operations."""
        timeout_contexts = []
        
        async def timeout_operation():
            with ErrorContext("timeout_test") as ctx:
                timeout_contexts.append(ctx.context_id)
                await asyncio.sleep(1.0)  # Will timeout
                return "should not complete"
        
        with pytest.raises((asyncio.TimeoutError, ServiceTimeoutError)):
            await asyncio.wait_for(timeout_operation(), timeout=0.2)
        
        assert len(timeout_contexts) == 1
    async def test_error_context_cleanup_on_exception(self):
        """Test error context cleanup when exceptions occur."""
        cleanup_log = []
        
        class TrackingErrorContext(ErrorContext):
            def __exit__(self, exc_type, exc_val, exc_tb):
                cleanup_log.append((self.context_id, exc_type is not None))
                return super().__exit__(exc_type, exc_val, exc_tb)
        
        async def failing_operation():
            with TrackingErrorContext("cleanup_test"):
                raise ValueError("Test exception")
        
        with pytest.raises(ValueError):
            await failing_operation()
        
        assert len(cleanup_log) == 1
        assert cleanup_log[0][1] == True  # Exception occurred

class TestWeakRefBehavior:
    """Test weak reference behavior in async utilities."""
    async def test_resource_manager_weak_ref_cleanup(self):
        """Test resource manager weak reference cleanup."""
        manager = AsyncResourceManager()
        cleanup_calls = []
        
        async def create_and_register_resource():
            class TestResource:
                def __init__(self, resource_id):
                    self.id = resource_id
            
            resource = TestResource("test_resource")
            
            async def cleanup():
                cleanup_calls.append(resource.id)
            
            manager.register_cleanup(resource, cleanup)
            return resource
        
        # Create resource
        resource = await create_and_register_resource()
        assert len(manager._cleanup_callbacks) == 1
        
        # Delete resource and force garbage collection
        del resource
        gc.collect()
        
        # Clean up dead references
        manager._cleanup_dead_refs()
        assert len(manager._cleanup_callbacks) == 0
    async def test_weak_ref_with_circular_references(self):
        """Test weak references with circular reference scenarios."""
        manager = AsyncResourceManager()
        
        class CircularResource:
            def __init__(self, name):
                self.name = name
                self.ref = None
        
        # Create circular reference
        resource1 = CircularResource("resource1")
        resource2 = CircularResource("resource2")
        resource1.ref = resource2
        resource2.ref = resource1
        
        cleanup_calls = []
        
        async def cleanup1():
            cleanup_calls.append("cleanup1")
        
        async def cleanup2():
            cleanup_calls.append("cleanup2")
        
        manager.register_cleanup(resource1, cleanup1)
        manager.register_cleanup(resource2, cleanup2)
        
        # Break circular reference and delete
        resource1.ref = None
        resource2.ref = None
        del resource1, resource2
        gc.collect()
        
        # Clean up dead references
        manager._cleanup_dead_refs()
        assert len(manager._cleanup_callbacks) == 0
    async def test_weak_ref_callback_exceptions(self):
        """Test weak reference callback exceptions don't break cleanup."""
        manager = AsyncResourceManager()
        
        class TestResource:
            pass
        
        resources = [TestResource() for _ in range(3)]
        cleanup_calls = []
        
        async def good_cleanup(resource_id):
            cleanup_calls.append(f"good_{resource_id}")
        
        async def bad_cleanup(resource_id):
            cleanup_calls.append(f"bad_{resource_id}")
            raise ValueError(f"Cleanup failed for {resource_id}")
        
        # Register mix of good and bad cleanups
        manager.register_cleanup(resources[0], lambda: good_cleanup(0))
        manager.register_cleanup(resources[1], lambda: bad_cleanup(1))
        manager.register_cleanup(resources[2], lambda: good_cleanup(2))
        
        # Cleanup all (should handle exceptions gracefully)
        await manager.cleanup()
        
        assert "good_0" in cleanup_calls
        assert "bad_1" in cleanup_calls
        assert "good_2" in cleanup_calls

class TestConcurrencyEdgeCases:
    """Test concurrency edge cases and race conditions."""
    async def test_rapid_task_submission(self):
        """Test rapid task submission to task pool."""
        pool = AsyncTaskPool(max_concurrent_tasks=5)
        submission_count = 100
        completion_count = 0
        
        async def rapid_task(task_id):
            nonlocal completion_count
            await asyncio.sleep(0.001)  # Minimal work
            completion_count += 1
            return task_id
        
        # Submit tasks rapidly
        tasks = []
        for i in range(submission_count):
            task = pool.submit(rapid_task(i))
            tasks.append(task)
        
        # Wait for all completions
        results = await asyncio.gather(*tasks)
        
        assert len(results) == submission_count
        assert completion_count == submission_count
    async def test_concurrent_rate_limiter_stress(self):
        """Test rate limiter under concurrent stress."""
        limiter = AsyncRateLimiter(rate=10, window=1.0)
        request_times = []
        
        async def stress_request(request_id):
            start_time = time.time()
            await limiter.acquire()
            end_time = time.time()
            request_times.append((request_id, end_time - start_time))
        
        # Submit many concurrent requests
        stress_count = 25
        tasks = [stress_request(i) for i in range(stress_count)]
        await asyncio.gather(*tasks)
        
        # Should have processed all requests
        assert len(request_times) == stress_count
        
        # Some should be delayed (beyond rate limit)
        delayed_requests = [t for t in request_times if t[1] > 0.1]
        assert len(delayed_requests) > 0
    async def test_circuit_breaker_race_conditions(self):
        """Test circuit breaker race conditions."""
        breaker = AsyncCircuitBreaker(failure_threshold=5, timeout=0.5)
        race_results = []
        
        async def concurrent_operation(op_id):
            try:
                async def operation():
                    if op_id % 3 == 0:  # Some operations fail
                        raise ServiceError(f"Op {op_id} failed")
                    return f"success_{op_id}"
                
                result = await breaker.call(operation)
                race_results.append(("success", op_id, result))
                return result
            except (ServiceError, Exception) as e:
                race_results.append(("error", op_id, str(e)))
                raise
        
        # Run many concurrent operations
        operations = [concurrent_operation(i) for i in range(20)]
        results = await asyncio.gather(*operations, return_exceptions=True)
        
        # Should have mix of successes and failures
        successes = [r for r in race_results if r[0] == "success"]
        errors = [r for r in race_results if r[0] == "error"]
        
        assert len(successes) > 0
        assert len(errors) > 0
    async def test_shutdown_during_active_operations(self):
        """Test shutdown behavior during active operations."""
        pool = AsyncTaskPool(max_concurrent_tasks=3)
        shutdown_results = []
        
        async def long_running_task(task_id):
            try:
                shutdown_results.append(f"started_{task_id}")
                await asyncio.sleep(0.5)  # Long running
                shutdown_results.append(f"completed_{task_id}")
                return f"result_{task_id}"
            except asyncio.CancelledError:
                shutdown_results.append(f"cancelled_{task_id}")
                raise
        
        # Start long running tasks
        tasks = [pool.submit(long_running_task(i)) for i in range(5)]
        
        # Give tasks time to start
        await asyncio.sleep(0.1)
        
        # Shutdown pool
        await pool.shutdown(wait=False)
        
        # Wait for tasks to complete or be cancelled
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some should have started
        started_count = len([r for r in shutdown_results if r.startswith("started_")])
        assert started_count > 0
    async def test_memory_cleanup_under_load(self):
        """Test memory cleanup under sustained load."""
        import os

        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and destroy many resources
        for cycle in range(5):
            manager = AsyncResourceManager()
            
            # Create many resources
            resources = []
            for i in range(100):
                class TestResource:
                    def __init__(self, data):
                        self.data = data
                
                resource = TestResource(f"data_{cycle}_{i}")
                resources.append(resource)
                
                async def cleanup():
                    pass
                
                manager.register_cleanup(resource, cleanup)
            
            # Cleanup
            await manager.cleanup()
            del manager, resources
            gc.collect()
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50 * 1024 * 1024
    async def test_global_shutdown_cleanup(self):
        """Test global shutdown cleanup behavior."""
        # This should work without errors even when called multiple times
        await shutdown_async_utils()
        await shutdown_async_utils()  # Should be idempotent
        
        # Should still be able to create new utilities after shutdown
        new_manager = AsyncResourceManager()
        assert new_manager is not None
    async def test_exception_propagation_edge_cases(self):
        """Test exception propagation in edge case scenarios."""
        edge_case_results = []
        
        async def nested_exception_operation():
            try:
                async def inner_operation():
                    raise ValueError("Inner exception")
                
                await inner_operation()
            except ValueError as e:
                edge_case_results.append(f"caught_inner: {e}")
                raise ServiceError("Wrapped exception") from e
        
        with pytest.raises(ServiceError) as exc_info:
            await nested_exception_operation()
        
        assert "Wrapped exception" in str(exc_info.value)
        assert len(edge_case_results) == 1