"""Race condition tests for AuthTraceLogger NoneType error bug.

This test suite focuses specifically on race conditions and thread safety issues
that can trigger the NoneType error in concurrent authentication scenarios.

Business Value: Ensures authentication debugging is thread-safe in multi-user environment.
Bug Reference: auth_trace_logger.py:368 - context.error_context.update(additional_context)
"""

import pytest
import threading
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


@pytest.mark.unit
class TestAuthTraceLoggerRaceConditions:
    """Test suite focused on race conditions that trigger the NoneType bug."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = AuthTraceLogger()
    
    def test_same_context_concurrent_log_failure_calls(self):
        """
        Test multiple threads calling log_failure with the same context.
        This is a critical race condition scenario.
        """
        # Shared context that will be accessed concurrently
        shared_context = AuthTraceContext(
            user_id="shared_user",
            request_id="shared_req", 
            correlation_id="shared_corr",
            operation="shared_operation",
            error_context=None  # Critical - starts as None
        )
        
        errors = []
        results = []
        
        def concurrent_log_failure(thread_id):
            try:
                error = Exception(f"Thread {thread_id} auth failure")
                additional_context = {
                    "thread_id": thread_id,
                    "timestamp": time.time(),
                    "operation_type": "concurrent_test"
                }
                self.logger.log_failure(shared_context, error, additional_context)
                results.append(f"Thread {thread_id} success")
            except Exception as e:
                errors.append(str(e))
        
        # Start 10 threads simultaneously on the same context
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_log_failure, args=(i,))
            threads.append(thread)
        
        # Start all threads at nearly the same time
        for thread in threads:
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Should have race condition errors
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0, f"Expected NoneType errors, got: {errors}"
    
    def test_rapid_context_creation_and_failure_logging(self):
        """
        Test rapidly creating contexts and logging failures.
        Tests for race conditions in context initialization.
        """
        errors = []
        
        def rapid_log_failure(iteration):
            try:
                # Create new context rapidly
                context = AuthTraceContext(
                    user_id=f"rapid_user_{iteration}",
                    request_id=f"rapid_req_{iteration}",
                    correlation_id=f"rapid_corr_{iteration}",
                    operation=f"rapid_op_{iteration}",
                    error_context=None  # Always None initially
                )
                
                # Immediately log failure
                error = Exception(f"Rapid auth failure {iteration}")
                additional_context = {"iteration": iteration, "rapid_test": True}
                self.logger.log_failure(context, error, additional_context)
                
            except Exception as e:
                errors.append(str(e))
        
        # Use ThreadPoolExecutor for more controlled threading
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(rapid_log_failure, i) for i in range(20)]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(str(e))
        
        # Should capture some NoneType errors
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0
    
    @pytest.mark.asyncio 
    async def test_async_context_modification_race(self):
        """
        Test async race conditions when modifying context.error_context.
        """
        context = AuthTraceContext(
            user_id="async_race_user",
            request_id="async_race_req",
            correlation_id="async_race_corr", 
            operation="async_race_test",
            error_context=None
        )
        
        errors = []
        
        async def async_log_failure(task_id):
            try:
                await asyncio.sleep(0.001)  # Small delay to create race conditions
                error = Exception(f"Async task {task_id} auth failure")
                additional_context = {
                    "task_id": task_id,
                    "async_test": True,
                    "coroutine_name": f"task_{task_id}"
                }
                self.logger.log_failure(context, error, additional_context)
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple async tasks concurrently
        tasks = [async_log_failure(i) for i in range(5)]
        
        # Should trigger race conditions
        with pytest.raises(Exception) as exc_info:
            await asyncio.gather(*tasks)
        
        # Check if it's the NoneType error or if it's captured in errors
        if errors:
            none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
            assert len(none_type_errors) > 0
        else:
            assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)
    
    def test_context_attribute_assignment_race(self):
        """
        Test race condition in context attribute assignment.
        Multiple threads trying to initialize error_context simultaneously.
        """
        context = AuthTraceContext(
            user_id="attr_race_user",
            request_id="attr_race_req",
            correlation_id="attr_race_corr",
            operation="attr_assignment_test",
            error_context=None
        )
        
        errors = []
        
        def attribute_race_worker(worker_id):
            try:
                # Try to modify context attributes concurrently
                if not hasattr(context, 'error_context') or context.error_context is None:
                    # Simulate the exact code path from the bug
                    context.error_context = {}
                
                # Then immediately try to update it
                context.error_context.update({
                    "worker_id": worker_id,
                    "race_test": True
                })
                
                # Now call log_failure
                error = Exception(f"Attribute race worker {worker_id}")
                additional_context = {"worker_id": worker_id}
                self.logger.log_failure(context, error, additional_context)
                
            except Exception as e:
                errors.append(str(e))
        
        # Start threads that will race to modify the same context
        threads = []
        for i in range(8):
            thread = threading.Thread(target=attribute_race_worker, args=(i,))
            threads.append(thread)
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join()
        
        # Should have some race condition errors
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0
    
    def test_mixed_thread_async_race_condition(self):
        """
        Test complex race condition with both threads and async tasks.
        This mimics real production scenarios.
        """
        context = AuthTraceContext(
            user_id="mixed_race_user",
            request_id="mixed_race_req",
            correlation_id="mixed_race_corr",
            operation="mixed_concurrency_test",
            error_context=None
        )
        
        errors = []
        
        def thread_worker(thread_id):
            try:
                error = Exception(f"Thread {thread_id} mixed race failure")
                additional_context = {
                    "worker_type": "thread",
                    "worker_id": thread_id
                }
                self.logger.log_failure(context, error, additional_context)
            except Exception as e:
                errors.append(str(e))
        
        async def async_worker(async_id):
            try:
                await asyncio.sleep(0.001)
                error = Exception(f"Async {async_id} mixed race failure")
                additional_context = {
                    "worker_type": "async", 
                    "worker_id": async_id
                }
                self.logger.log_failure(context, error, additional_context)
            except Exception as e:
                errors.append(str(e))
        
        # Start threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Start async tasks in a separate thread
        def run_async_tasks():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tasks = [async_worker(i) for i in range(3)]
                loop.run_until_complete(asyncio.gather(*tasks))
                loop.close()
            except Exception as e:
                errors.append(str(e))
        
        async_thread = threading.Thread(target=run_async_tasks)
        async_thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        async_thread.join()
        
        # Should have race condition errors
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0
    
    def test_error_context_state_transitions_race(self):
        """
        Test race conditions during error_context state transitions.
        None -> {} -> populated dict transitions in concurrent access.
        """
        context = AuthTraceContext(
            user_id="state_race_user",
            request_id="state_race_req", 
            correlation_id="state_race_corr",
            operation="state_transition_test",
            error_context=None
        )
        
        errors = []
        state_log = []
        
        def state_transition_worker(worker_id, delay):
            try:
                time.sleep(delay)  # Stagger the workers slightly
                
                # Log the initial state
                initial_state = context.error_context
                state_log.append(f"Worker {worker_id}: Initial state = {initial_state}")
                
                # Call log_failure which should transition None -> {}
                error = Exception(f"State transition worker {worker_id}")
                additional_context = {
                    "worker_id": worker_id, 
                    "state_test": True,
                    "delay": delay
                }
                self.logger.log_failure(context, error, additional_context)
                
                # Log final state
                final_state = context.error_context
                state_log.append(f"Worker {worker_id}: Final state = {final_state}")
                
            except Exception as e:
                errors.append(str(e))
                state_log.append(f"Worker {worker_id}: Error = {str(e)}")
        
        # Start workers with slight delays to create race conditions
        threads = []
        delays = [0.001, 0.002, 0.001, 0.003, 0.001]  # Overlapping timing
        for i, delay in enumerate(delays):
            thread = threading.Thread(target=state_transition_worker, args=(i, delay))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Debug: Print state transitions
        for log_entry in state_log:
            print(log_entry)
        
        # Should capture race condition errors
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0
    
    def test_high_frequency_concurrent_log_failures(self):
        """
        Test high-frequency concurrent log_failure calls.
        This simulates production load scenarios.
        """
        errors = []
        
        def high_frequency_worker(batch_id):
            for i in range(10):  # Each worker does 10 operations
                try:
                    context = AuthTraceContext(
                        user_id=f"hf_user_{batch_id}_{i}",
                        request_id=f"hf_req_{batch_id}_{i}",
                        correlation_id=f"hf_corr_{batch_id}_{i}",
                        operation=f"high_frequency_test_{batch_id}_{i}",
                        error_context=None
                    )
                    
                    error = Exception(f"High frequency error {batch_id}-{i}")
                    additional_context = {
                        "batch_id": batch_id,
                        "operation_number": i,
                        "high_frequency": True
                    }
                    
                    self.logger.log_failure(context, error, additional_context)
                    
                except Exception as e:
                    errors.append(str(e))
        
        # Start multiple workers doing high-frequency operations
        threads = []
        for batch_id in range(5):
            thread = threading.Thread(target=high_frequency_worker, args=(batch_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have some NoneType errors under high load
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0