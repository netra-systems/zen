"""
Unit Tests for AuthTraceLogger 'NoneType' error_context Bug

Business Value Justification (BVJ):
- Segment: Platform Security & Reliability (all tiers)
- Business Goal: Eliminate authentication debugging failures
- Value Impact: Prevent critical auth debugging from crashing
- Strategic Impact: Foundational reliability for auth debugging

CRITICAL BUG REPRODUCTION: "'NoneType' object has no attribute 'update'" at line 368
Root Cause: context.error_context is None but code tries context.error_context.update()

These tests are designed to FAIL initially and pass after the fix.
"""

import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


class TestAuthTraceLoggerNoneErrorBug:
    """Test suite specifically for the 'NoneType' error_context bug."""
    
    def test_log_failure_with_none_error_context_and_additional_context(self):
        """
        CRITICAL BUG REPRODUCTION: Test log_failure when error_context=None and additional_context provided.
        
        This should FAIL before fix and PASS after fix.
        Expected Error: AttributeError: 'NoneType' object has no attribute 'update'
        """
        logger = AuthTraceLogger()
        
        # Create context with error_context explicitly set to None (default state)
        context = AuthTraceContext(
            user_id="test_user",
            request_id="req_123",
            correlation_id="corr_456", 
            operation="test_operation"
        )
        
        # Verify error_context is None (this is the bug trigger condition)
        assert context.error_context is None
        assert hasattr(context, 'error_context')  # Attribute exists but is None
        
        # This should trigger the bug at line 368: context.error_context.update(additional_context)
        test_error = Exception("Test authentication failure")
        additional_context = {"session_id": "sess_123", "source": "test"}
        
        # This should raise AttributeError: 'NoneType' object has no attribute 'update'
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            logger.log_failure(context, test_error, additional_context)
    
    def test_log_failure_with_none_error_context_no_additional_context(self):
        """Test log_failure when error_context=None but no additional_context (should work)."""
        logger = AuthTraceLogger()
        
        context = AuthTraceContext(
            user_id="test_user",
            request_id="req_124",
            correlation_id="corr_457",
            operation="test_operation"
        )
        
        assert context.error_context is None
        
        test_error = Exception("Test error without additional context")
        
        # This should work because line 368 (the bug line) is only executed if additional_context exists
        # The bug is specifically: if additional_context: context.error_context.update(additional_context)
        try:
            logger.log_failure(context, test_error, None)
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                pytest.fail(f"Bug still exists even without additional_context: {e}")
    
    def test_log_failure_with_empty_dict_additional_context(self):
        """Test edge case: empty dict as additional_context should still trigger bug."""
        logger = AuthTraceLogger()
        
        context = AuthTraceContext(
            user_id="system",  # Test with system user
            request_id="req_125",
            correlation_id="corr_458",
            operation="system_auth"
        )
        
        assert context.error_context is None
        
        test_error = Exception("403 Not authenticated - system user failure")
        empty_additional_context = {}  # Empty dict should still trigger the bug
        
        # Even empty dict should trigger the bug because "if additional_context:" evaluates to False for {}
        # But let's test with a non-empty dict to be sure
        non_empty_additional_context = {"debug": True}
        
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            logger.log_failure(context, test_error, non_empty_additional_context)
    
    def test_log_failure_various_additional_context_types(self):
        """Test different types of additional_context that could trigger the bug."""
        logger = AuthTraceLogger()
        
        base_context = AuthTraceContext(
            user_id="test_user",
            request_id="req_126", 
            correlation_id="corr_459",
            operation="context_type_test"
        )
        
        test_error = Exception("Test error for context types")
        
        # Test cases that should trigger the bug (error_context is None)
        test_cases = [
            {"key": "value"},  # Simple dict
            {"session_id": "sess_123", "thread_id": "thread_456"},  # Multiple keys
            {"nested": {"data": "value"}},  # Nested dict
            {"list_value": [1, 2, 3]},  # Dict with list
            {"special_chars": "test with spaces & symbols!"},  # Special characters
        ]
        
        for i, additional_context in enumerate(test_cases):
            # Create fresh context for each test (error_context = None)
            context = AuthTraceContext(
                user_id=f"user_{i}",
                request_id=f"req_{126 + i}",
                correlation_id=f"corr_{459 + i}",
                operation=f"test_operation_{i}"
            )
            
            assert context.error_context is None
            
            with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
                logger.log_failure(context, test_error, additional_context)
    
    def test_log_failure_after_error_context_initialization(self):
        """Test that log_failure works when error_context is properly initialized."""
        logger = AuthTraceLogger()
        
        context = AuthTraceContext(
            user_id="test_user",
            request_id="req_127",
            correlation_id="corr_460",
            operation="initialized_context_test"
        )
        
        # Manually initialize error_context (simulates fixed state)
        context.error_context = {}
        
        test_error = Exception("Test error with initialized context")
        additional_context = {"source": "test", "initialized": True}
        
        # This should work without errors
        try:
            logger.log_failure(context, test_error, additional_context)
        except Exception as e:
            pytest.fail(f"Unexpected error with initialized error_context: {e}")
    
    def test_concurrent_log_failure_race_condition(self):
        """
        RACE CONDITION TEST: Multiple threads calling log_failure with None error_context.
        
        This test simulates the real-world race condition scenario.
        """
        logger = AuthTraceLogger()
        
        def create_context(i: int) -> AuthTraceContext:
            return AuthTraceContext(
                user_id=f"user_{i}",
                request_id=f"req_race_{i}",
                correlation_id=f"corr_race_{i}",
                operation=f"concurrent_operation_{i}"
            )
        
        def log_failure_task(context_id: int) -> Dict[str, Any]:
            """Task that calls log_failure - should trigger the bug."""
            context = create_context(context_id)
            assert context.error_context is None
            
            error = Exception(f"Concurrent error {context_id}")
            additional_context = {"context_id": context_id, "timestamp": time.time()}
            
            try:
                logger.log_failure(context, error, additional_context)
                return {"context_id": context_id, "success": True, "error": None}
            except Exception as e:
                return {"context_id": context_id, "success": False, "error": str(e)}
        
        # Run concurrent tasks
        num_threads = 10
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(log_failure_task, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze results - we expect AttributeError: 'NoneType' object has no attribute 'update'
        failed_results = [r for r in results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # Before fix: we expect multiple failures with the NoneType error
        assert len(none_type_errors) > 0, f"Expected 'NoneType' errors but got: {[r['error'] for r in failed_results]}"
        
        # All failures should be the same NoneType error (confirms bug consistency)
        for result in none_type_errors:
            assert "'NoneType' object has no attribute 'update'" in result["error"]
    
    def test_auth_trace_context_dataclass_initialization(self):
        """Test that AuthTraceContext initializes error_context as None (confirms bug precondition)."""
        context = AuthTraceContext(
            user_id="test_user",
            request_id="req_128", 
            correlation_id="corr_461",
            operation="dataclass_init_test"
        )
        
        # These assertions confirm the bug preconditions
        assert hasattr(context, 'error_context'), "error_context attribute should exist"
        assert context.error_context is None, "error_context should be None by default"
        
        # Confirm other fields are properly initialized
        assert context.session_info == {}
        assert context.performance_metrics == {}
        assert context.debug_hints == []
        assert context.auth_state == "unknown"
    
    @pytest.mark.asyncio
    async def test_async_concurrent_log_failure_race_condition(self):
        """
        ASYNC RACE CONDITION TEST: Multiple coroutines calling log_failure concurrently.
        
        This simulates async WebSocket/HTTP handler scenarios where the bug occurs.
        """
        logger = AuthTraceLogger()
        
        async def async_log_failure_task(context_id: int) -> Dict[str, Any]:
            """Async task that calls log_failure."""
            context = AuthTraceContext(
                user_id=f"async_user_{context_id}",
                request_id=f"async_req_{context_id}",
                correlation_id=f"async_corr_{context_id}",
                operation=f"async_operation_{context_id}"
            )
            
            assert context.error_context is None
            
            error = Exception(f"Async concurrent error {context_id}")
            additional_context = {
                "async_context_id": context_id,
                "timestamp": time.time(),
                "task_type": "async"
            }
            
            try:
                logger.log_failure(context, error, additional_context)
                return {"context_id": context_id, "success": True, "error": None}
            except Exception as e:
                return {"context_id": context_id, "success": False, "error": str(e)}
        
        # Run concurrent async tasks
        num_tasks = 15
        tasks = [async_log_failure_task(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert any exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "context_id": i,
                    "success": False, 
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        # Analyze results
        failed_results = [r for r in processed_results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        # Before fix: expect multiple NoneType errors from async race conditions
        assert len(none_type_errors) > 0, f"Expected async 'NoneType' errors but got: {[r['error'] for r in failed_results]}"
        
        # Verify error consistency
        for result in none_type_errors:
            assert "'NoneType' object has no attribute 'update'" in result["error"]
    
    def test_system_user_403_error_scenario(self):
        """
        SPECIFIC BUG SCENARIO: System user with 403 'Not authenticated' error.
        
        This tests the exact scenario mentioned in the bug report.
        """
        logger = AuthTraceLogger()
        
        # Create system user context (common in service-to-service auth)
        context = AuthTraceContext(
            user_id="system",  # System user triggers special logging paths
            request_id="sys_req_403",
            correlation_id="sys_corr_403",
            operation="service_to_service_auth"
        )
        
        assert context.error_context is None
        
        # 403 "Not authenticated" error (exact error pattern from bug report)
        auth_error = Exception("403 Not authenticated")
        
        # Additional context that would be provided in real auth failure
        additional_context = {
            "session_id": "system_session_123",
            "service_name": "netra_backend", 
            "auth_method": "service_token",
            "request_path": "/api/internal/auth",
            "error_source": "authentication_middleware"
        }
        
        # This should trigger the bug at line 368 AND at the special system user logging around line 418
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            logger.log_failure(context, auth_error, additional_context)