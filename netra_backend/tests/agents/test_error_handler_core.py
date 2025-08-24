"""
Tests for AgentErrorHandler core functionality.
All functions ≤8 lines per requirements.
"""

import sys
from pathlib import Path

# Add netra_backend to path  

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.error_handler import (
    AgentError,
    DatabaseError,
    NetworkError,
)

from netra_backend.app.agents.error_handler import (
    AgentErrorHandler as ErrorHandler,
)
from netra_backend.app.agents.error_handler import (
    AgentValidationError as ValidationError,
)
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.shared_types import ErrorContext

class TestErrorHandler:
    """Test AgentErrorHandler functionality."""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return ErrorHandler()
    
    @pytest.fixture
    def sample_context(self):
        """Create sample error context for testing."""
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation",
            run_id="test_run",
            timestamp=time.time()
        )
    
    def _assert_error_handler_initialization(self, handler):
        """Assert error handler initialization"""
        assert handler.max_history_size == 1000
        assert len(handler.error_history) == 0
        assert handler.total_errors == 0

    def test_error_handler_initialization(self, error_handler):
        """Test ErrorHandler initialization."""
        self._assert_error_handler_initialization(error_handler)

    async def _test_handle_error_with_agent_error_helper(self, error_handler, sample_context):
        """Helper for testing handle_error with agent error"""
        error = ValidationError("Validation failed")
        result = await error_handler.handle_error(error, sample_context)
        return result, error

    @pytest.mark.asyncio

    async def test_handle_error_with_agent_error(self, error_handler, sample_context):
        """Test handle_error with AgentError."""
        result, error = await self._test_handle_error_with_agent_error_helper(error_handler, sample_context)
        assert result == error
        assert len(error_handler.error_history) == 1

    async def _test_handle_error_with_generic_exception_helper(self, error_handler, sample_context):
        """Helper for testing handle_error with generic exception"""
        original_error = ValueError("Generic error")
        result = await error_handler.handle_error(original_error, sample_context)
        return result, original_error

    @pytest.mark.asyncio

    async def test_handle_error_with_generic_exception(self, error_handler, sample_context):
        """Test handle_error with generic exception."""
        result, original_error = await self._test_handle_error_with_generic_exception_helper(error_handler, sample_context)
        assert isinstance(result, AgentError)
        assert result.original_error == original_error

    def _create_mock_async_operation(self):
        """Create mock async operation"""
        async def operation():
            await asyncio.sleep(0.01)
            raise NetworkError("Network failure")
        return operation

    @pytest.mark.asyncio

    async def test_handle_error_with_retry_context(self, error_handler, sample_context):
        """Test handle_error with retry context."""
        error = NetworkError("Temporary failure")
        sample_context.retry_count = 1
        sample_context.max_retries = 3
        
        result = await error_handler.handle_error(error, sample_context)
        assert result == error

    def _create_websocket_error_for_handling_test(self):
        """Create WebSocket error for handling test"""
        from netra_backend.app.core.exceptions_websocket import WebSocketError
        return WebSocketError("WebSocket connection lost")

    @pytest.mark.asyncio

    async def test_handle_websocket_error(self, error_handler, sample_context):
        """Test handling WebSocket-specific errors."""
        error = self._create_websocket_error_for_handling_test()
        result = await error_handler.handle_error(error, sample_context)
        
        assert isinstance(result, AgentError)
        assert "WebSocket" in result.message

    def test_get_error_statistics(self, error_handler):
        """Test error statistics retrieval."""
        # Add some errors
        errors = [
            ValidationError("Error 1"),
            NetworkError("Error 2"),
            DatabaseError("Error 3")
        ]
        
        for error in errors:
            error_handler._store_error(error)
        
        stats = error_handler.get_error_statistics()
        _assert_error_statistics_format(stats)

    def _create_errors_for_logging_test(self):
        """Create errors for logging test"""
        return [
            ValidationError("Validation error"),
            NetworkError("Network error"),
            AgentError("Critical error", severity=ErrorSeverity.CRITICAL)
        ]

    def test_log_error_different_severities(self, error_handler):
        """Test log_error with different severity levels."""
        errors = self._create_errors_for_logging_test()
        with patch('app.agents.error_handler.central_logger') as mock_logger:
            for error in errors:
                error_handler._log_error(error)
            assert mock_logger.get_logger.return_value.error.call_count >= 1

    def _create_error_for_storage_test(self):
        """Create error for storage testing"""
        return ValidationError("Test error for storage")

    def test_store_error(self, error_handler):
        """Test error storage functionality."""
        error = self._create_error_for_storage_test()
        error_handler._store_error(error)
        assert len(error_handler.error_history) == 1
        assert error_handler.total_errors == 1

    def _fill_error_history_to_limit(self, error_handler):
        """Fill error history to test limit"""
        for i in range(1005):  # Exceed limit
            error = AgentError(f"Error {i}")
            error_handler._store_error(error)

    def test_store_error_history_limit(self, error_handler):
        """Test error history size limit."""
        self._fill_error_history_to_limit(error_handler)
        assert len(error_handler.error_history) == 1000  # Should be capped

    def _create_context_with_max_retries_exceeded(self):
        """Create context with max retries exceeded"""
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="test_run",
            timestamp=time.time(),
            retry_count=5,
            max_retries=3
        )

    def test_should_retry_operation_max_retries_exceeded(self, error_handler):
        """Test should_retry_operation when max retries exceeded."""
        context = self._create_context_with_max_retries_exceeded()
        error = NetworkError("Network error")
        should_retry = error_handler._should_retry_operation(error, context)
        assert should_retry is False

    def _create_retryable_network_error(self):
        """Create retryable network error"""
        return NetworkError("Temporary network issue")

    def test_should_retry_operation_retryable_error(self, error_handler, sample_context):
        """Test should_retry_operation with retryable error."""
        error = self._create_retryable_network_error()
        sample_context.retry_count = 1
        sample_context.max_retries = 3
        
        should_retry = error_handler._should_retry_operation(error, sample_context)
        assert should_retry is True

    def test_error_handler_memory_usage(self, error_handler):
        """Test error handler memory usage with many errors."""
        # Add many errors to test memory management
        for i in range(2000):
            error = AgentError(f"Memory test error {i}")
            error_handler._store_error(error)
        
        # Should maintain reasonable memory usage
        assert len(error_handler.error_history) <= 1000

def _assert_error_statistics_format(stats: dict) -> None:
    """Assert error statistics have correct format"""
    expected_keys = ['total_errors', 'errors_by_category', 'errors_by_severity']
    for key in expected_keys:
        assert key in stats
    
    assert isinstance(stats['total_errors'], int)
    assert isinstance(stats['errors_by_category'], dict)
    assert isinstance(stats['errors_by_severity'], dict)