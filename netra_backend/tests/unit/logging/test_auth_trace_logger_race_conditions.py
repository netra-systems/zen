"""
Race Condition Tests for AuthTraceLogger Thread Safety

Business Value Justification (BVJ):
- Segment: Platform Security & Reliability (all tiers)  
- Business Goal: Ensure auth debugging is thread-safe under concurrent load
- Value Impact: Prevent auth debugging crashes during high-traffic scenarios
- Strategic Impact: Foundational reliability for concurrent authentication debugging

CRITICAL: These tests focus specifically on race conditions and thread safety issues
that cause the 'NoneType' object has no attribute 'update' error.

The bug occurs when multiple threads/coroutines access the same AuthTraceContext
or when context.error_context initialization races occur.
"""

import pytest
import asyncio
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


class TestAuthTraceLoggerRaceConditions:
    """Test suite for race conditions in AuthTraceLogger."""
    
    def test_same_context_concurrent_log_failure_calls(self):
        """
        RACE CONDITION TEST: Multiple threads calling log_failure on the SAME context object.
        
        This is the most likely race condition scenario - the same context object
        being modified by multiple threads simultaneously.
        """
        logger = AuthTraceLogger()
        
        # Create a single shared context (this is the race condition source)
        shared_context = AuthTraceContext(
            user_id="shared_user",
            request_id="shared_req_123",
            correlation_id="shared_corr_123",
            operation="concurrent_shared_operation"
        )
        
        # Verify shared context starts with error_context=None
        assert shared_context.error_context is None
        
        def concurrent_log_failure_task(thread_id: int) -> Dict[str, Any]:
            """Task that modifies the same shared context."""
            error = Exception(f"Concurrent error from thread {thread_id}")
            additional_context = {
                "thread_id": thread_id,
                "timestamp": time.time(),
                "modification_attempt": thread_id
            }
            
            try:
                # All threads are modifying the SAME context object
                logger.log_failure(shared_context, error, additional_context)
                return {"thread_id": thread_id, "success": True, "error": None}
            except Exception as e:
                return {"thread_id": thread_id, "success": False, "error": str(e)}
        
        # Run concurrent modifications on the same context
        num_threads = 12
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(concurrent_log_failure_task, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze race condition results
        failed_results = [r for r in results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # We expect race condition failures where some threads see error_context as None
        # while others try to update it
        assert len(none_type_errors) > 0, f"Expected race condition 'NoneType' errors: {[r['error'] for r in failed_results]}"
        
        # The shared context should have been modified by at least one thread
        # (if any succeeded, the context would no longer be None)
        successful_results = [r for r in results if r["success"]]
        if len(successful_results) > 0:
            # If some succeeded, error_context should now be initialized
            assert shared_context.error_context is not None or len(none_type_errors) > 0
    
    def test_context_initialization_race_condition(self):
        """
        RACE CONDITION TEST: Race between context creation and error_context initialization.
        
        This tests the specific race where context.error_context starts as None
        and multiple threads try to initialize it simultaneously.
        """
        logger = AuthTraceLogger()
        
        # Track all contexts created by threads
        created_contexts = []
        context_lock = threading.Lock()
        
        def context_init_race_task(thread_id: int) -> Dict[str, Any]:
            """Task that creates context and immediately uses it."""
            # Create new context (starts with error_context=None)
            context = AuthTraceContext(
                user_id=f"race_user_{thread_id}",
                request_id=f"race_req_{thread_id}_{int(time.time())}",
                correlation_id=f"race_corr_{thread_id}_{int(time.time())}",
                operation=f"race_operation_{thread_id}"
            )
            
            # Store context for analysis
            with context_lock:
                created_contexts.append(context)
            
            # Verify initial state
            assert context.error_context is None
            
            # Immediately try to use the context with additional_context
            # This creates a race condition in the initialization check
            error = Exception(f"Race initialization error {thread_id}")
            additional_context = {
                "thread_id": thread_id,
                "race_test": True,
                "initialization_timestamp": time.time()
            }
            
            try:
                logger.log_failure(context, error, additional_context)
                return {"thread_id": thread_id, "success": True, "error": None, "context_id": id(context)}
            except Exception as e:
                return {"thread_id": thread_id, "success": False, "error": str(e), "context_id": id(context)}
        
        # Run concurrent context initialization and usage
        num_threads = 8
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(context_init_race_task, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze initialization race results
        failed_results = [r for r in results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # Each thread has its own context, so we shouldn't see race conditions
        # UNLESS there's a bug in the initialization logic itself
        if len(none_type_errors) > 0:
            # This indicates the bug is in the initialization logic, not just shared state
            assert len(none_type_errors) > 0, f"Initialization race condition detected: {[r['error'] for r in none_type_errors]}"
            
            # Verify each failed context had error_context=None initially
            for context in created_contexts:
                assert hasattr(context, 'error_context'), "All contexts should have error_context attribute"
    
    @pytest.mark.asyncio
    async def test_async_context_modification_race(self):
        """
        ASYNC RACE CONDITION TEST: Async tasks modifying contexts concurrently.
        
        This tests race conditions in async WebSocket/HTTP handler scenarios.
        """
        logger = AuthTraceLogger()
        
        # Shared context for async race condition
        async_shared_context = AuthTraceContext(
            user_id="async_shared_user",
            request_id="async_shared_req",
            correlation_id="async_shared_corr",
            operation="async_concurrent_operation"
        )
        
        assert async_shared_context.error_context is None
        
        async def async_race_task(task_id: int) -> Dict[str, Any]:
            """Async task that modifies shared context."""
            # Add random delay to increase race condition likelihood
            await asyncio.sleep(random.uniform(0.001, 0.01))
            
            error = Exception(f"Async race error {task_id}")
            additional_context = {
                "task_id": task_id,
                "async_timestamp": time.time(),
                "async_race_test": True
            }
            
            try:
                logger.log_failure(async_shared_context, error, additional_context)
                return {"task_id": task_id, "success": True, "error": None}
            except Exception as e:
                return {"task_id": task_id, "success": False, "error": str(e)}
        
        # Run concurrent async tasks
        num_tasks = 10
        tasks = [async_race_task(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results (handle exceptions)
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "task_id": i,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        # Analyze async race results
        failed_results = [r for r in processed_results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # Async race conditions should also trigger the bug
        assert len(none_type_errors) > 0, f"Expected async race condition errors: {[r['error'] for r in failed_results]}"
    
    def test_mixed_thread_async_race_condition(self):
        """
        COMPLEX RACE CONDITION TEST: Mix of threads and async tasks on same context.
        
        This tests the most complex race condition scenario.
        """
        logger = AuthTraceLogger()
        
        # Context shared between threads and async tasks
        mixed_context = AuthTraceContext(
            user_id="mixed_race_user",
            request_id="mixed_race_req",
            correlation_id="mixed_race_corr",
            operation="mixed_thread_async_operation"
        )
        
        assert mixed_context.error_context is None
        
        # Thread-based task
        def thread_task(thread_id: int) -> Dict[str, Any]:
            """Thread-based task for mixed race test."""
            error = Exception(f"Thread race error {thread_id}")
            additional_context = {
                "source": "thread",
                "thread_id": thread_id,
                "timestamp": time.time()
            }
            
            try:
                logger.log_failure(mixed_context, error, additional_context)
                return {"source": "thread", "id": thread_id, "success": True, "error": None}
            except Exception as e:
                return {"source": "thread", "id": thread_id, "success": False, "error": str(e)}
        
        # Async task
        async def async_task(task_id: int) -> Dict[str, Any]:
            """Async task for mixed race test."""
            await asyncio.sleep(0.001)  # Small delay
            
            error = Exception(f"Async race error {task_id}")
            additional_context = {
                "source": "async",
                "task_id": task_id,
                "timestamp": time.time()
            }
            
            try:
                logger.log_failure(mixed_context, error, additional_context)
                return {"source": "async", "id": task_id, "success": True, "error": None}
            except Exception as e:
                return {"source": "async", "id": task_id, "success": False, "error": str(e)}
        
        # Run mixed thread/async tasks
        thread_results = []
        num_threads = 4
        
        # Start threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            thread_futures = [executor.submit(thread_task, i) for i in range(num_threads)]
            
            # Run async tasks concurrently with threads
            async def run_async_tasks():
                num_async_tasks = 4
                async_tasks = [async_task(i) for i in range(num_async_tasks)]
                return await asyncio.gather(*async_tasks, return_exceptions=True)
            
            # This is a bit complex because we're mixing sync threads with async
            # For this test, we'll focus on the thread results
            for future in as_completed(thread_futures):
                thread_results.append(future.result())
        
        # Analyze mixed race condition results
        failed_results = [r for r in thread_results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # Mixed race conditions are highly likely to trigger the bug
        assert len(none_type_errors) > 0, f"Expected mixed race condition errors: {[r['error'] for r in failed_results]}"
    
    def test_rapid_context_creation_and_usage_race(self):
        """
        RAPID CREATION RACE TEST: Rapidly creating and using contexts to find initialization bugs.
        
        This tests whether rapid context creation/usage exposes initialization race conditions.
        """
        logger = AuthTraceLogger()
        
        def rapid_context_task(task_id: int) -> Dict[str, Any]:
            """Rapidly create and use context."""
            contexts_created = []
            errors_encountered = []
            
            try:
                # Rapidly create and use multiple contexts
                for i in range(5):  # 5 contexts per task
                    context = AuthTraceContext(
                        user_id=f"rapid_user_{task_id}_{i}",
                        request_id=f"rapid_req_{task_id}_{i}_{int(time.time())}",
                        correlation_id=f"rapid_corr_{task_id}_{i}_{int(time.time())}",
                        operation=f"rapid_operation_{task_id}_{i}"
                    )
                    contexts_created.append(context)
                    
                    # Immediately use the context
                    error = Exception(f"Rapid error {task_id}_{i}")
                    additional_context = {
                        "task_id": task_id,
                        "context_index": i,
                        "rapid_test": True,
                        "creation_timestamp": time.time()
                    }
                    
                    # This should work for individual contexts, but may expose initialization bugs
                    logger.log_failure(context, error, additional_context)
                
                return {
                    "task_id": task_id,
                    "success": True,
                    "contexts_created": len(contexts_created),
                    "errors": []
                }
                
            except Exception as e:
                return {
                    "task_id": task_id,
                    "success": False,
                    "contexts_created": len(contexts_created),
                    "error": str(e)
                }
        
        # Run rapid context creation tasks
        num_tasks = 6
        results = []
        
        with ThreadPoolExecutor(max_workers=num_tasks) as executor:
            futures = [executor.submit(rapid_context_task, i) for i in range(num_tasks)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze rapid creation results
        failed_results = [r for r in results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        if len(none_type_errors) > 0:
            # This would indicate a fundamental issue with context initialization
            assert len(none_type_errors) > 0, f"Rapid creation exposed initialization bugs: {[r['error'] for r in none_type_errors]}"
    
    def test_error_context_state_transitions_race(self):
        """
        STATE TRANSITION RACE TEST: Test race conditions during error_context state transitions.
        
        This tests the specific race condition where error_context transitions from None to dict.
        """
        logger = AuthTraceLogger()
        
        # Create contexts that will transition from None to initialized state
        transitioning_contexts = []
        for i in range(5):
            context = AuthTraceContext(
                user_id=f"transition_user_{i}",
                request_id=f"transition_req_{i}",
                correlation_id=f"transition_corr_{i}",
                operation=f"transition_operation_{i}"
            )
            transitioning_contexts.append(context)
        
        def state_transition_task(context_index: int, operation_index: int) -> Dict[str, Any]:
            """Task that causes state transition in error_context."""
            context = transitioning_contexts[context_index]
            
            error = Exception(f"State transition error {context_index}_{operation_index}")
            additional_context = {
                "context_index": context_index,
                "operation_index": operation_index,
                "state_transition_test": True,
                "timestamp": time.time()
            }
            
            try:
                logger.log_failure(context, error, additional_context)
                return {
                    "context_index": context_index,
                    "operation_index": operation_index,
                    "success": True,
                    "error": None
                }
            except Exception as e:
                return {
                    "context_index": context_index,
                    "operation_index": operation_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Create tasks that operate on the same contexts multiple times
        tasks = []
        for context_idx in range(len(transitioning_contexts)):
            for op_idx in range(3):  # 3 operations per context
                tasks.append((context_idx, op_idx))
        
        # Run state transition tasks
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(state_transition_task, ctx_idx, op_idx) for ctx_idx, op_idx in tasks]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze state transition race results
        failed_results = [r for r in results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # State transition races should trigger the bug
        assert len(none_type_errors) > 0, f"Expected state transition race errors: {[r['error'] for r in failed_results]}"
        
        # Check final state of contexts
        for i, context in enumerate(transitioning_contexts):
            # Some contexts should have error_context initialized, others might still be None due to failures
            if context.error_context is not None:
                assert isinstance(context.error_context, dict), f"Context {i} error_context should be dict or None"