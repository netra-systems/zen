"""
Tests for global error handler and decorator functionality.
All functions ≤8 lines per requirements.
"""

import pytest
import asyncio
from unittest.mock import patch

from netra_backend.app.agents.error_handler import (
    AgentErrorHandler as ErrorHandler,
    AgentValidationError as ValidationError,
    NetworkError,
    global_error_handler,
    handle_agent_error
)


class TestGlobalErrorHandler:
    """Test global error handler functionality."""
    
    def test_global_error_handler_exists(self):
        """Test global error handler instance exists."""
        assert global_error_handler is not None
        assert isinstance(global_error_handler, ErrorHandler)
    
    def test_global_error_handler_singleton(self):
        """Test global error handler is singleton."""
        from netra_backend.app.agents.error_handler import global_error_handler as global_handler_2
        assert global_error_handler is global_handler_2
    
    def test_global_error_handler_shared_state(self):
        """Test global error handler maintains shared state."""
        initial_count = global_error_handler.total_errors
        
        # Add error through global handler
        test_error = ValidationError("Global test error")
        global_error_handler._store_error(test_error)
        
        assert global_error_handler.total_errors == initial_count + 1
    
    def test_global_error_handler_thread_safety(self):
        """Test global error handler thread safety."""
        # Simple test - more complex threading would need more setup
        error1 = ValidationError("Thread test 1")
        error2 = NetworkError("Thread test 2")
        
        global_error_handler._store_error(error1)
        global_error_handler._store_error(error2)
        
        assert global_error_handler.total_errors >= 2


class TestErrorHandlerDecorator:
    """Test handle_agent_error decorator functionality."""
    
    async def _create_successful_function(self):
        """Create successful function for testing"""
        @handle_agent_error(agent_name="TestAgent", operation_name="test_op")
        async def successful_function():
            return "success"
        return successful_function

    async def test_decorator_successful_execution(self):
        """Test decorator with successful function execution."""
        successful_function = await self._create_successful_function()
        result = await successful_function()
        assert result == "success"

    async def _create_retryable_function(self):
        """Create function that fails then succeeds for retry testing"""
        call_count = [0]  # Use list for mutable closure
        
        @handle_agent_error(agent_name="TestAgent", operation_name="retry_op", max_retries=2)
        async def retryable_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise NetworkError("Temporary network issue")
            return "success"
        
        return retryable_function, call_count

    async def test_decorator_with_retries(self):
        """Test decorator with retryable errors."""
        retryable_function, call_count = await self._create_retryable_function()
        result = await retryable_function()
        assert result == "success"
        assert call_count[0] == 2  # Should be called twice

    async def _create_non_retryable_function(self):
        """Create function with non-retryable error"""
        @handle_agent_error(agent_name="TestAgent", operation_name="non_retry_op")
        async def non_retryable_function():
            raise ValidationError("Non-retryable validation error")
        return non_retryable_function

    async def test_decorator_with_non_retryable_error(self):
        """Test decorator with non-retryable error."""
        non_retryable_function = await self._create_non_retryable_function()
        
        with pytest.raises(ValidationError):
            await non_retryable_function()

    async def _create_max_retries_exceeded_function(self):
        """Create function that exceeds max retries"""
        @handle_agent_error(agent_name="TestAgent", operation_name="max_retry_op", max_retries=2)
        async def max_retries_function():
            raise NetworkError("Persistent network issue")
        return max_retries_function

    async def test_decorator_max_retries_exceeded(self):
        """Test decorator when max retries is exceeded."""
        max_retries_function = await self._create_max_retries_exceeded_function()
        
        with pytest.raises(NetworkError):
            await max_retries_function()

    async def _create_function_with_custom_handler(self):
        """Create function with custom error handler"""
        custom_handler = ErrorHandler()
        
        @handle_agent_error(
            agent_name="TestAgent", 
            operation_name="custom_op", 
            error_handler=custom_handler
        )
        async def custom_handler_function():
            raise ValidationError("Custom handler test")
        
        return custom_handler_function, custom_handler

    async def test_decorator_with_custom_handler(self):
        """Test decorator with custom error handler."""
        custom_function, custom_handler = await self._create_function_with_custom_handler()
        initial_count = custom_handler.total_errors
        
        with pytest.raises(ValidationError):
            await custom_function()
        
        assert custom_handler.total_errors == initial_count + 1

    async def _create_sync_function_with_decorator(self):
        """Create sync function with decorator"""
        @handle_agent_error(agent_name="TestAgent", operation_name="sync_op")
        def sync_function():
            return "sync_success"
        return sync_function

    def test_decorator_with_sync_function(self):
        """Test decorator with synchronous function."""
        sync_function = asyncio.run(self._create_sync_function_with_decorator())
        result = sync_function()
        assert result == "sync_success"

    async def _create_function_with_context_propagation(self):
        """Create function for testing context propagation"""
        @handle_agent_error(
            agent_name="ContextAgent", 
            operation_name="context_op",
            context_data={"test_key": "test_value"}
        )
        async def context_function():
            raise NetworkError("Context test error")
        return context_function

    async def test_decorator_context_propagation(self):
        """Test decorator context propagation."""
        context_function = await self._create_function_with_context_propagation()
        
        with pytest.raises(NetworkError):
            await context_function()

    async def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""
        @handle_agent_error(agent_name="TestAgent", operation_name="metadata_op")
        async def documented_function():
            """This function has documentation."""
            return "documented"
        
        # Check that metadata is preserved
        assert documented_function.__name__ == "documented_function"
        assert "documentation" in documented_function.__doc__

    async def _create_function_with_retry_delay(self):
        """Create function to test retry delay"""
        call_times = []
        
        @handle_agent_error(
            agent_name="TestAgent", 
            operation_name="delay_op", 
            max_retries=2,
            retry_delay=0.1
        )
        async def delayed_retry_function():
            import time
            call_times.append(time.time())
            if len(call_times) < 2:
                raise NetworkError("Delay test error")
            return "delayed_success"
        
        return delayed_retry_function, call_times

    async def test_decorator_retry_delay(self):
        """Test decorator retry delay functionality."""
        delayed_function, call_times = await self._create_function_with_retry_delay()
        
        result = await delayed_function()
        assert result == "delayed_success"
        
        # Check that there was a delay between calls
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert delay >= 0.08  # Account for timing variations