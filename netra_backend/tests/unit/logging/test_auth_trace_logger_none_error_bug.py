"""Unit tests for AuthTraceLogger NoneType error bug reproduction.

This test suite specifically targets the bug: "'NoneType' object has no attribute 'update'"
that occurs in auth_trace_logger.py:368 when context.error_context is None.

Business Value: Ensures reliable authentication debugging functionality.
Bug Reference: auth_trace_logger.py:368 - context.error_context.update(additional_context)
Root Cause: Code checks hasattr() but not if error_context is None
"""

import pytest
import threading
import asyncio
from unittest.mock import Mock
from datetime import datetime, timezone

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


@pytest.mark.unit
class TestAuthTraceLoggerNoneErrorBug:
    """Test suite to reproduce the exact NoneType error bug in AuthTraceLogger."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = AuthTraceLogger()
    
    def test_log_failure_with_none_error_context_and_additional_context_FIXED(self):
        """
        VALIDATION: Confirm the NoneType bug is now FIXED.
        
        This test validates that the previously failing scenario now works correctly.
        """
        # Create context with error_context explicitly set to None
        context = AuthTraceContext(
            user_id="test_user",
            request_id="test_request",
            correlation_id="test_correlation",
            operation="test_auth"
        )
        
        # Set error_context to None - the previously problematic condition
        context.error_context = None
        
        # Verify the state that previously caused the bug
        assert hasattr(context, 'error_context')
        assert context.error_context is None
        
        # Create additional context that previously triggered the bug
        additional_context = {"debug_info": "test_debug"}
        test_error = Exception("Test authentication failure")
        
        # Mock the logger to capture warnings
        import unittest.mock
        with unittest.mock.patch('netra_backend.app.logging.auth_trace_logger.logger.warning') as mock_warning:
            # This should now work without any exceptions
            try:
                self.logger.log_failure(context, test_error, additional_context)
                # If we get here, the fix worked!
                fix_successful = True
            except AttributeError as e:
                if "'NoneType' object has no attribute 'update'" in str(e):
                    fix_successful = False
                    pytest.fail(f"Bug still exists: {e}")
                else:
                    raise e
            except Exception as e:
                # Debug any other exceptions
                print(f"Unexpected exception: {e}")
                raise e
            
            # Check if any warnings were logged (indicating exceptions were caught)
            if mock_warning.called:
                for call in mock_warning.call_args_list:
                    print(f"Warning logged: {call[0][0]}")
        
        assert fix_successful, "The fix should prevent the NoneType error"
        
        # Debug: Print the actual error_context to understand what's happening
        print(f"Final error_context: {context.error_context}")
        print(f"Context state: auth_state={context.auth_state}")
        
        # Verify the context was properly initialized after the call
        assert context.error_context is not None
        assert isinstance(context.error_context, dict)
        
        # The fix should have added both the standard error fields AND additional_context
        expected_fields = ["error_type", "error_message", "is_auth_error", "is_permission_error"]
        for field in expected_fields:
            assert field in context.error_context, f"Expected field {field} missing from error_context"
            
        # The additional_context should also be merged in
        assert "debug_info" in context.error_context
        assert context.error_context["debug_info"] == "test_debug"
    
    def test_direct_none_error_reproduction_bypass_exception_handling(self):
        """
        DIRECT test that bypasses exception handling to prove the bug exists.
        This simulates the exact problematic code path.
        """
        # Create context with None error_context  
        context = AuthTraceContext(
            user_id="direct_test",
            request_id="direct_req",
            correlation_id="direct_corr",
            operation="direct_test"
        )
        
        # Set error_context to None - the bug condition
        context.error_context = None
        
        # Verify the bug condition
        assert hasattr(context, 'error_context')
        assert context.error_context is None
        
        # Now test the exact problematic code path
        additional_context = {"test": "data"}
        
        # This should raise the exact NoneType error
        with pytest.raises(AttributeError) as exc_info:
            # Simulate the exact failing line from auth_trace_logger.py:368
            context.error_context.update(additional_context)
        
        # Verify it's the exact error
        assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)
    
    def test_system_user_403_error_scenario(self):
        """
        VALIDATION: Confirm system user scenarios work correctly after bug fix.
        This mimics service-to-service auth failures.
        """
        context = AuthTraceContext(
            user_id="system",
            request_id="sys_req_123",
            correlation_id="sys_corr_456", 
            operation="service_auth_validation",
            error_context=None  # Common in system user scenarios
        )
        
        # 403 Not authenticated error like in production
        auth_error = Exception("403 Not authenticated - Service validation failed")
        additional_context = {
            "service_name": "agent_executor",
            "endpoint": "/api/agents/execute",
            "auth_method": "jwt_validation"
        }
        
        # Should now work correctly without exceptions
        try:
            self.logger.log_failure(context, auth_error, additional_context)
            fix_successful = True
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                fix_successful = False
                pytest.fail(f"Bug still exists: {e}")
            else:
                raise e
                
        assert fix_successful, "System user scenario should work after bug fix"
        
        # Verify error_context was properly initialized 
        assert context.error_context is not None
        assert isinstance(context.error_context, dict)
        assert "service_name" in context.error_context
        assert context.error_context["service_name"] == "agent_executor"
    
    def test_concurrent_log_failure_race_condition(self):
        """
        VALIDATION: Confirm concurrent scenarios work correctly after bug fix.
        This simulates the race condition scenario that's now fixed.
        """
        context = AuthTraceContext(
            user_id="concurrent_user",
            request_id="concurrent_req",
            correlation_id="concurrent_corr",
            operation="concurrent_auth",
            error_context=None
        )
        
        errors = []
        successes = []
        
        def log_failure_worker():
            try:
                self.logger.log_failure(
                    context, 
                    Exception("Concurrent auth failure"),
                    {"thread_id": threading.current_thread().ident}
                )
                successes.append(True)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads simultaneously
        threads = [threading.Thread(target=log_failure_worker) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should now succeed after the fix
        assert len(errors) == 0, f"No errors should occur after fix, but got: {errors}"
        assert len(successes) == 5, "All concurrent operations should succeed"
        
        # Verify context was properly initialized
        assert context.error_context is not None
        assert isinstance(context.error_context, dict)
    
    def test_log_failure_various_additional_context_types(self):
        """
        VALIDATION: Test different additional_context types work after bug fix.
        """
        context = AuthTraceContext(
            user_id="test_user", 
            request_id="var_test",
            correlation_id="var_corr",
            operation="variable_test",
            error_context=None
        )
        
        test_error = Exception("Variable context test")
        
        # Test with different additional_context types that should now work
        test_contexts = [
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"list_value": [1, 2, 3]},
            {"mixed": {"str": "test", "num": 42, "bool": True}}
        ]
        
        for i, additional_ctx in enumerate(test_contexts):
            # Reset context for each test
            context.error_context = None
            
            try:
                self.logger.log_failure(context, test_error, additional_ctx)
                fix_successful = True
            except AttributeError as e:
                if "'NoneType' object has no attribute 'update'" in str(e):
                    fix_successful = False
                    pytest.fail(f"Bug still exists for context type {i}: {e}")
                else:
                    raise e
                    
            assert fix_successful, f"Context type {i} should work after fix"
            
            # Verify all additional context was merged properly
            assert context.error_context is not None
            for key, value in additional_ctx.items():
                assert key in context.error_context
                assert context.error_context[key] == value
    
    def test_log_failure_with_empty_additional_context(self):
        """VALIDATION: Test empty additional context works after bug fix."""
        context = AuthTraceContext(
            user_id="empty_test",
            request_id="empty_req", 
            correlation_id="empty_corr",
            operation="empty_test",
            error_context=None
        )
        
        # Empty dict should now work correctly
        try:
            self.logger.log_failure(context, Exception("Empty context test"), {})
            fix_successful = True
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                fix_successful = False
                pytest.fail(f"Bug still exists with empty context: {e}")
            else:
                raise e
                
        assert fix_successful, "Empty additional context should work after fix"
        
        # Verify error_context was properly initialized
        assert context.error_context is not None
        assert isinstance(context.error_context, dict)
        # Standard error fields should be present
        assert "error_type" in context.error_context
        assert "error_message" in context.error_context
    
    @pytest.mark.asyncio
    async def test_async_concurrent_log_failure_race_condition(self):
        """
        VALIDATION: Test async race conditions work correctly after bug fix.
        """
        context = AuthTraceContext(
            user_id="async_user",
            request_id="async_req",
            correlation_id="async_corr", 
            operation="async_auth",
            error_context=None
        )
        
        async def async_log_failure():
            # Reset context for each task to test the fix thoroughly
            local_context = AuthTraceContext(
                user_id="async_user", 
                request_id=f"async_req_{id(asyncio.current_task())}",
                correlation_id="async_corr",
                operation="async_auth",
                error_context=None
            )
            self.logger.log_failure(
                local_context,
                Exception("Async auth failure"),
                {"coroutine_id": id(asyncio.current_task())}
            )
        
        # Run multiple concurrent async operations
        tasks = [async_log_failure() for _ in range(3)]
        
        # All should now succeed after the fix
        try:
            await asyncio.gather(*tasks)
            fix_successful = True
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                fix_successful = False
                pytest.fail(f"Bug still exists in async scenario: {e}")
            else:
                raise e
                
        assert fix_successful, "Async concurrent operations should work after fix"
    
    def test_websocket_connection_auth_context_scenario(self):
        """
        VALIDATION: Confirm WebSocket auth scenarios work correctly after bug fix.
        This mimics real WebSocket connection auth failures that should now work.
        """
        context = AuthTraceContext(
            user_id="websocket_user_123",
            request_id="ws_req_789",
            correlation_id="ws_corr_456",
            operation="websocket_auth_validation",
            error_context=None  # Common in WebSocket rapid connection scenarios
        )
        
        # WebSocket specific auth failure
        ws_error = Exception("WebSocket authentication failed - Invalid token")
        additional_context = {
            "connection_type": "websocket",
            "client_ip": "192.168.1.100", 
            "user_agent": "Mozilla/5.0 Test",
            "connection_id": "conn_abc123"
        }
        
        # Should now work correctly without exceptions
        try:
            self.logger.log_failure(context, ws_error, additional_context)
            fix_successful = True
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                fix_successful = False
                pytest.fail(f"Bug still exists in WebSocket scenario: {e}")
            else:
                raise e
                
        assert fix_successful, "WebSocket auth scenario should work after fix"
        
        # Verify all WebSocket context was preserved
        assert context.error_context is not None
        assert context.error_context["connection_type"] == "websocket"
        assert context.error_context["connection_id"] == "conn_abc123"
        assert context.error_context["client_ip"] == "192.168.1.100"
    
    def test_context_with_existing_none_error_context(self):
        """
        VALIDATION: Test scenario where error_context is explicitly None - core bug fix validation.
        This is the core of the bug fix - hasattr() passes but value is None.
        """
        context = AuthTraceContext(
            user_id="explicit_none",
            request_id="none_req",
            correlation_id="none_corr",
            operation="none_test"
        )
        
        # Explicitly set to None to simulate the problematic state
        context.error_context = None
        
        # Verify the problematic state that is now handled correctly
        assert hasattr(context, 'error_context')  # This passes
        assert context.error_context is None      # This is None - the fixed condition
        
        # This should now work correctly after the fix
        try:
            self.logger.log_failure(
                context,
                Exception("Explicit None test"),
                {"test": "data"}
            )
            fix_successful = True
        except AttributeError as e:
            if "'NoneType' object has no attribute 'update'" in str(e):
                fix_successful = False
                pytest.fail(f"Bug still exists for explicit None scenario: {e}")
            else:
                raise e
                
        assert fix_successful, "Explicit None error_context should work after fix"
        
        # Verify the context was properly initialized and merged
        assert context.error_context is not None
        assert isinstance(context.error_context, dict)
        assert "test" in context.error_context
        assert context.error_context["test"] == "data"
        # Standard error fields should also be present
        assert "error_type" in context.error_context
        assert "error_message" in context.error_context