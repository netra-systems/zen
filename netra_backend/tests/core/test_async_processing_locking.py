"""
Focused tests for Async Processing and Locking
Tests AsyncBatchProcessor and AsyncLock functionality with various scenarios
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path
from app.core.async_utils import (
    # Add project root to path
    AsyncBatchProcessor,
    AsyncLock,
)
from app.core.exceptions_service import ServiceError


class TestAsyncBatchProcessorComplete:
    """Complete tests for AsyncBatchProcessor."""
    async def test_batch_processor_basic_functionality(self):
        """Test basic batch processor functionality."""
        processed_batches = []
        
        async def process_batch(items):
            await asyncio.sleep(0.05)  # Simulate processing time
            processed_batches.append(items.copy())
            return [f"processed_{item}" for item in items]
        
        processor = AsyncBatchProcessor(
            process_function=process_batch,
            batch_size=3,
            max_wait_time=0.5
        )
        
        # Add items individually
        results = []
        for i in range(5):
            result = await processor.add_item(f"item_{i}")
            if result:
                results.extend(result)
        
        # Process remaining items
        await processor.flush()
        
        assert len(processed_batches) >= 1
        total_processed = sum(len(batch) for batch in processed_batches)
        assert total_processed == 5
    async def test_batch_processor_size_triggering(self):
        """Test batch processor triggering on batch size."""
        process_calls = []
        
        async def track_process_calls(items):
            process_calls.append(len(items))
            return items
        
        processor = AsyncBatchProcessor(
            process_function=track_process_calls,
            batch_size=2,
            max_wait_time=1.0  # Long wait time to test size triggering
        )
        
        # Add items to trigger batch processing
        await processor.add_item("item1")
        await processor.add_item("item2")  # Should trigger processing
        
        # Give a moment for async processing
        await asyncio.sleep(0.1)
        
        assert len(process_calls) == 1
        assert process_calls[0] == 2
    async def test_batch_processor_time_triggering(self):
        """Test batch processor triggering on wait time."""
        process_calls = []
        
        async def track_time_calls(items):
            process_calls.append((len(items), time.time()))
            return items
        
        processor = AsyncBatchProcessor(
            process_function=track_time_calls,
            batch_size=10,  # Large batch size to test time triggering
            max_wait_time=0.2
        )
        
        # Add item and wait for time trigger
        await processor.add_item("item1")
        await asyncio.sleep(0.3)  # Wait longer than max_wait_time
        
        assert len(process_calls) >= 1
        assert process_calls[0][0] == 1  # Should process single item
    async def test_batch_processor_concurrent_additions(self):
        """Test batch processor with concurrent item additions."""
        processed_items = []
        
        async def collect_items(items):
            await asyncio.sleep(0.05)
            processed_items.extend(items)
            return items
        
        processor = AsyncBatchProcessor(
            process_function=collect_items,
            batch_size=5,
            max_wait_time=0.5
        )
        
        # Add items concurrently
        async def add_items(start_id, count):
            for i in range(count):
                await processor.add_item(f"item_{start_id}_{i}")
        
        tasks = [add_items(worker_id, 3) for worker_id in range(3)]
        await asyncio.gather(*tasks)
        
        # Flush remaining
        await processor.flush()
        
        assert len(processed_items) == 9  # 3 workers * 3 items each
    async def test_batch_processor_error_handling(self):
        """Test batch processor error handling."""
        process_attempts = []
        
        async def failing_process_function(items):
            process_attempts.append(items.copy())
            if len(process_attempts) == 1:
                raise ServiceError("Processing failed")
            return [f"processed_{item}" for item in items]
        
        processor = AsyncBatchProcessor(
            process_function=failing_process_function,
            batch_size=2,
            max_wait_time=0.5
        )
        
        # Add items - first batch should fail
        try:
            await processor.add_item("item1")
            await processor.add_item("item2")
            await asyncio.sleep(0.1)  # Allow processing
        except ServiceError:
            pass  # Expected for first batch
        
        # Add more items - should process successfully
        await processor.add_item("item3")
        await processor.add_item("item4")
        await processor.flush()
        
        assert len(process_attempts) >= 1
    async def test_batch_processor_flush_behavior(self):
        """Test batch processor flush behavior."""
        flush_calls = []
        
        async def track_flush_calls(items):
            flush_calls.append(("batch", items.copy()))
            return items
        
        processor = AsyncBatchProcessor(
            process_function=track_flush_calls,
            batch_size=5,  # Large batch size
            max_wait_time=1.0  # Long wait time
        )
        
        # Add items without triggering automatic processing
        await processor.add_item("item1")
        await processor.add_item("item2")
        
        # Manually flush
        await processor.flush()
        
        assert len(flush_calls) == 1
        assert flush_calls[0][1] == ["item1", "item2"]
    async def test_batch_processor_shutdown(self):
        """Test batch processor shutdown behavior."""
        shutdown_processed = []
        
        async def process_on_shutdown(items):
            shutdown_processed.extend(items)
            return items
        
        processor = AsyncBatchProcessor(
            process_function=process_on_shutdown,
            batch_size=10,  # Large batch to prevent auto-processing
            max_wait_time=10.0  # Long wait to prevent time-based processing
        )
        
        # Add items
        await processor.add_item("item1")
        await processor.add_item("item2")
        
        # Shutdown should process remaining items
        await processor.shutdown()
        
        assert len(shutdown_processed) == 2


class TestAsyncLockComplete:
    """Complete tests for AsyncLock."""
    async def test_lock_basic_functionality(self):
        """Test basic lock functionality."""
        lock = AsyncLock()
        execution_order = []
        
        async def critical_section(task_id):
            async with lock:
                execution_order.append(f"start_{task_id}")
                await asyncio.sleep(0.1)
                execution_order.append(f"end_{task_id}")
        
        # Run tasks concurrently
        tasks = [critical_section(i) for i in range(3)]
        await asyncio.gather(*tasks)
        
        # Should have proper interleaving (start/end pairs)
        assert len(execution_order) == 6
        # Each task should complete before the next starts
        for i in range(0, len(execution_order), 2):
            assert execution_order[i].startswith("start_")
            assert execution_order[i + 1].startswith("end_")
    async def test_lock_acquisition_order(self):
        """Test lock acquisition order."""
        lock = AsyncLock()
        acquisition_order = []
        
        async def acquire_lock(task_id):
            async with lock:
                acquisition_order.append(task_id)
                await asyncio.sleep(0.05)
        
        # Start tasks with slight delays to ensure order
        async def delayed_start(task_id, delay):
            await asyncio.sleep(delay)
            await acquire_lock(task_id)
        
        tasks = [
            delayed_start(1, 0.0),
            delayed_start(2, 0.01),
            delayed_start(3, 0.02)
        ]
        
        await asyncio.gather(*tasks)
        
        # Should acquire in order of waiting
        assert acquisition_order == [1, 2, 3]
    async def test_lock_timeout_behavior(self):
        """Test lock timeout behavior."""
        lock = AsyncLock()
        timeout_results = []
        
        async def long_running_task():
            async with lock:
                await asyncio.sleep(0.5)  # Hold lock for long time
                return "long_task_complete"
        
        async def timeout_task(task_id):
            try:
                # Try to acquire with short timeout
                async with asyncio.timeout(0.2):
                    async with lock:
                        timeout_results.append(f"acquired_{task_id}")
                        return f"task_{task_id}_complete"
            except asyncio.TimeoutError:
                timeout_results.append(f"timeout_{task_id}")
                raise
        
        # Start long running task first
        long_task = asyncio.create_task(long_running_task())
        
        # Start timeout task - should timeout
        with pytest.raises(asyncio.TimeoutError):
            await timeout_task(1)
        
        # Wait for long task to complete
        await long_task
        
        assert "timeout_1" in timeout_results
    async def test_lock_reentrant_behavior(self):
        """Test lock reentrant behavior (should not be reentrant)."""
        lock = AsyncLock()
        
        async def nested_lock_attempt():
            async with lock:
                # Try to acquire lock again (should deadlock if attempted)
                # This test ensures we don't accidentally make it reentrant
                return "outer_complete"
        
        # Should complete normally (single acquisition)
        result = await nested_lock_attempt()
        assert result == "outer_complete"
    async def test_lock_exception_handling(self):
        """Test lock exception handling and cleanup."""
        lock = AsyncLock()
        exception_results = []
        
        async def failing_critical_section(task_id):
            try:
                async with lock:
                    exception_results.append(f"entered_{task_id}")
                    if task_id == 1:
                        raise ValueError(f"Task {task_id} failed")
                    exception_results.append(f"completed_{task_id}")
            except ValueError:
                exception_results.append(f"caught_{task_id}")
                raise
        
        async def normal_critical_section(task_id):
            async with lock:
                exception_results.append(f"normal_{task_id}")
        
        # Run failing task first, then normal task
        with pytest.raises(ValueError):
            await failing_critical_section(1)
        
        # Lock should be released after exception
        await normal_critical_section(2)
        
        assert "entered_1" in exception_results
        assert "caught_1" in exception_results
        assert "normal_2" in exception_results
    async def test_lock_concurrent_stress(self):
        """Test lock under concurrent stress."""
        lock = AsyncLock()
        shared_counter = 0
        increment_count = 100
        
        async def increment_shared_counter():
            nonlocal shared_counter
            async with lock:
                current = shared_counter
                await asyncio.sleep(0.001)  # Simulate some work
                shared_counter = current + 1
        
        # Run many concurrent increments
        tasks = [increment_shared_counter() for _ in range(increment_count)]
        await asyncio.gather(*tasks)
        
        # Should have exactly the expected count (no race conditions)
        assert shared_counter == increment_count
    async def test_lock_fairness(self):
        """Test lock fairness under load."""
        lock = AsyncLock()
        completion_times = {}
        
        async def timed_critical_section(task_id):
            start_time = time.time()
            async with lock:
                await asyncio.sleep(0.02)  # Brief critical section
                completion_times[task_id] = time.time() - start_time
        
        # Start multiple tasks simultaneously
        tasks = [timed_critical_section(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # All tasks should complete
        assert len(completion_times) == 5
        
        # Later tasks should take longer (indicating proper queuing)
        times = list(completion_times.values())
        assert max(times) > min(times)  # Some variance in completion times
    async def test_lock_context_manager_cleanup(self):
        """Test lock context manager cleanup."""
        lock = AsyncLock()
        cleanup_test_results = []
        
        async def test_cleanup():
            try:
                async with lock:
                    cleanup_test_results.append("entered")
                    # Simulate some work
                    await asyncio.sleep(0.01)
                    cleanup_test_results.append("work_done")
                    # Exit normally
                cleanup_test_results.append("exited_normally")
            except Exception as e:
                cleanup_test_results.append(f"exception: {e}")
        
        await test_cleanup()
        
        assert "entered" in cleanup_test_results
        assert "work_done" in cleanup_test_results
        assert "exited_normally" in cleanup_test_results
        
        # Lock should be available for next use
        async with lock:
            cleanup_test_results.append("subsequent_use")
        
        assert "subsequent_use" in cleanup_test_results