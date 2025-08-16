"""Unit tests for ErrorHandler with 70%+ coverage.
Tests all error handling mechanisms, recovery strategies, and decorators.
REFACTORED VERSION: All functions ≤8 lines
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import asdict

from app.agents.error_handler import (
    AgentErrorHandler as ErrorHandler, 
    AgentError,
    AgentValidationError as ValidationError,
    NetworkError,
    DatabaseError, 
    ErrorCategory,
    ErrorRecoveryStrategy,
    global_error_handler,
    handle_agent_error
)
from app.core.exceptions_websocket import WebSocketError
from app.core.error_codes import ErrorSeverity
from app.schemas.shared_types import ErrorContext
from app.tests.helpers.shared_test_types import TestErrorContext as SharedTestErrorContext


class TestErrorEnums:
    """Test error enumerations."""
    
    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.PROCESSING.value == "processing"
        assert ErrorCategory.WEBSOCKET.value == "websocket"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.RESOURCE.value == "resource"


class TestErrorContext(SharedTestErrorContext):
    """Test ErrorContext dataclass."""
    
    def _create_basic_error_context(self):
        """Create basic error context for testing"""
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation",
            run_id="run_123",
            timestamp=time.time()
        )

    def _assert_basic_error_context(self, context):
        """Assert basic error context properties"""
        assert context.agent_name == "TestAgent"
        assert context.operation_name == "test_operation"
        assert context.run_id == "run_123"
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert context.additional_data == {}

    def test_error_context_creation(self):
        """Test ErrorContext creation with required fields."""
        context = self._create_basic_error_context()
        self._assert_basic_error_context(context)

    def _create_custom_error_context(self):
        """Create error context with custom values"""
        additional_data = {"key": "value"}
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation", 
            run_id="run_123",
            timestamp=time.time(),
            retry_count=2,
            max_retries=5,
            additional_data=additional_data
        )

    def test_error_context_with_custom_values(self):
        """Test ErrorContext with custom values."""
        context = self._create_custom_error_context()
        assert context.retry_count == 2
        assert context.max_retries == 5
        assert context.additional_data == {"key": "value"}

    def _create_none_additional_data_context(self):
        """Create error context with None additional_data"""
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation",
            run_id="run_123", 
            timestamp=time.time(),
            additional_data=None
        )

    def test_error_context_post_init(self):
        """Test ErrorContext __post_init__ method."""
        context = self._create_none_additional_data_context()
        assert context.additional_data == {}


class TestAgentErrors:
    """Test custom agent error classes."""
    
    def _create_basic_agent_error(self):
        """Create basic agent error for testing"""
        return AgentError(
            message="Test error message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            original_error=ValueError("Original error")
        )

    def _assert_basic_agent_error(self, error):
        """Assert basic agent error properties"""
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert isinstance(error.original_error, ValueError)

    def test_agent_error_creation(self):
        """Test AgentError creation with all parameters."""
        error = self._create_basic_agent_error()
        self._assert_basic_agent_error(error)

    def _create_default_agent_error(self):
        """Create agent error with defaults"""
        return AgentError("Default error")

    def test_agent_error_defaults(self):
        """Test AgentError with default values."""
        error = self._create_default_agent_error()
        assert error.message == "Default error"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM

    def _create_validation_error(self):
        """Create validation error for testing"""
        return ValidationError("Invalid input", field_name="test_field")

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = self._create_validation_error()
        assert error.message == "Invalid input"
        assert error.category == ErrorCategory.VALIDATION
        assert error.field_name == "test_field"

    def _create_network_error(self):
        """Create network error for testing"""
        return NetworkError("Connection failed", endpoint="http://test.com")

    def test_network_error(self):
        """Test NetworkError creation."""
        error = self._create_network_error()
        assert error.message == "Connection failed"
        assert error.category == ErrorCategory.NETWORK

    def _create_database_error(self):
        """Create database error for testing"""
        return DatabaseError("Query failed", operation="SELECT")

    def test_database_error(self):
        """Test DatabaseError creation."""
        error = self._create_database_error()
        assert error.message == "Query failed"
        assert error.category == ErrorCategory.DATABASE

    def _create_websocket_error(self):
        """Create websocket error for testing"""
        return WebSocketError("WebSocket connection lost", code=1006)

    def test_websocket_error(self):
        """Test WebSocketError creation."""
        error = self._create_websocket_error()
        assert "WebSocket connection lost" in str(error)


class TestErrorRecoveryStrategy:
    """Test error recovery strategy logic."""
    
    def _create_network_error_for_delay_test(self):
        """Create network error for delay testing"""
        return NetworkError("Network timeout", severity=ErrorSeverity.MEDIUM)

    def test_get_recovery_delay_network_error(self):
        """Test recovery delay calculation for network errors."""
        error = self._create_network_error_for_delay_test()
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=1)
        assert 0.5 <= delay <= 4.0  # Base 2^1 * 1.0 with jitter

    def _create_high_severity_error_for_max_cap_test(self):
        """Create high severity error for max cap testing"""
        return AgentError("Test", severity=ErrorSeverity.HIGH)

    def test_get_recovery_delay_max_cap(self):
        """Test recovery delay maximum cap."""
        error = self._create_high_severity_error_for_max_cap_test()
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=10)
        assert delay <= 30.0  # Should not exceed max delay

    def _create_errors_for_category_test(self):
        """Create different error categories for testing"""
        return [
            ValidationError("Validation failed"),
            DatabaseError("DB error"),
            NetworkError("Network error")
        ]

    def test_get_recovery_delay_different_categories(self):
        """Test recovery delay for different error categories."""
        errors = self._create_errors_for_category_test()
        delays = [ErrorRecoveryStrategy.get_recovery_delay(err, 1) for err in errors]
        assert all(delay >= 0 for delay in delays)

    def _create_validation_error_for_retry_test(self):
        """Create validation error for retry testing"""
        return ValidationError("Invalid data")

    def test_should_retry_validation_error(self):
        """Test should_retry for validation errors."""
        error = self._create_validation_error_for_retry_test()
        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
        assert should_retry is False  # Validation errors shouldn't retry

    def test_should_retry_non_recoverable_error(self):
        """Test should_retry for non-recoverable errors."""
        error = AgentError("Fatal error", severity=ErrorSeverity.CRITICAL)
        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
        assert should_retry is False

    def _create_network_timeout_error(self):
        """Create network timeout error for testing"""
        return NetworkError("Timeout", severity=ErrorSeverity.MEDIUM)

    def test_should_retry_network_timeout_errors(self):
        """Test should_retry for network timeout errors."""
        error = self._create_network_timeout_error()
        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
        assert should_retry is True

    def _create_critical_database_error(self):
        """Create critical database error for testing"""
        return DatabaseError("Connection lost", severity=ErrorSeverity.CRITICAL)

    def test_should_retry_critical_database_error(self):
        """Test should_retry for critical database errors."""
        error = self._create_critical_database_error()
        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
        assert should_retry is False

    def _create_medium_severity_error(self):
        """Create medium severity error for testing"""
        return AgentError("Recoverable error", severity=ErrorSeverity.MEDIUM)

    def test_should_retry_medium_severity_errors(self):
        """Test should_retry for medium severity errors."""
        error = self._create_medium_severity_error()
        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
        assert should_retry is True


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

    async def test_handle_error_with_generic_exception(self, error_handler, sample_context):
        """Test handle_error with generic exception."""
        result, original_error = await self._test_handle_error_with_generic_exception_helper(error_handler, sample_context)
        assert isinstance(result, AgentError)
        assert result.original_error == original_error

    async def _create_fallback_function(self):
        """Create fallback function for testing"""
        async def fallback_func(error, context):
            return "fallback_result"
        return fallback_func

    async def test_handle_error_with_fallback(self, error_handler, sample_context):
        """Test handle_error with fallback function."""
        error = NetworkError("Network failed")
        fallback = await self._create_fallback_function()
        result = await error_handler.handle_error(error, sample_context, fallback)
        assert result == "fallback_result"

    async def _create_failing_fallback(self):
        """Create failing fallback function for testing"""
        async def failing_fallback(error, context):
            raise RuntimeError("Fallback failed")
        return failing_fallback

    async def test_handle_error_fallback_fails(self, error_handler, sample_context):
        """Test handle_error when fallback also fails."""
        error = NetworkError("Network failed")
        failing_fallback = await self._create_failing_fallback()
        result = await error_handler.handle_error(error, sample_context, failing_fallback)
        assert isinstance(result, AgentError)

    def _create_existing_agent_error(self):
        """Create existing agent error for testing"""
        return ValidationError("Existing error")

    def test_convert_to_agent_error_with_agent_error(self, error_handler):
        """Test convert_to_agent_error with existing AgentError."""
        existing_error = self._create_existing_agent_error()
        result = error_handler._convert_to_agent_error(existing_error)
        assert result == existing_error

    def _create_validation_error_for_conversion(self):
        """Create validation error for conversion testing"""
        return ValueError("Invalid value")

    def test_convert_to_agent_error_validation_error(self, error_handler):
        """Test convert_to_agent_error with ValueError."""
        value_error = self._create_validation_error_for_conversion()
        result = error_handler._convert_to_agent_error(value_error)
        assert isinstance(result, ValidationError)
        assert result.original_error == value_error

    def _create_connection_error_for_conversion(self):
        """Create connection error for conversion testing"""
        return ConnectionError("Connection failed")

    def test_convert_to_agent_error_connection_error(self, error_handler):
        """Test convert_to_agent_error with ConnectionError."""
        conn_error = self._create_connection_error_for_conversion()
        result = error_handler._convert_to_agent_error(conn_error)
        assert isinstance(result, NetworkError)
        assert result.original_error == conn_error

    def _create_memory_error_for_conversion(self):
        """Create memory error for conversion testing"""
        return MemoryError("Out of memory")

    def test_convert_to_agent_error_memory_error(self, error_handler):
        """Test convert_to_agent_error with MemoryError."""
        mem_error = self._create_memory_error_for_conversion()
        result = error_handler._convert_to_agent_error(mem_error)
        assert isinstance(result, AgentError)
        assert result.category == ErrorCategory.RESOURCE

    def _create_errors_for_logging_test(self):
        """Create errors with different severities for logging test"""
        return [
            AgentError("Low error", severity=ErrorSeverity.LOW),
            AgentError("Medium error", severity=ErrorSeverity.MEDIUM),
            AgentError("High error", severity=ErrorSeverity.HIGH),
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

    def _create_context_within_retry_limits(self):
        """Create context within retry limits"""
        return ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="test_run",
            timestamp=time.time(),
            retry_count=1,
            max_retries=3
        )

    def test_should_retry_operation_within_limits(self, error_handler):
        """Test should_retry_operation within retry limits."""
        context = self._create_context_within_retry_limits()
        error = NetworkError("Network error")
        should_retry = error_handler._should_retry_operation(error, context)
        assert should_retry is True

    async def _test_retry_with_delay_helper(self, error_handler):
        """Helper for testing retry with delay"""
        start_time = time.time()
        await error_handler._retry_with_delay(0.1)  # 100ms delay
        end_time = time.time()
        return end_time - start_time

    async def test_retry_with_delay(self, error_handler):
        """Test retry delay functionality."""
        elapsed_time = await self._test_retry_with_delay_helper(error_handler)
        assert elapsed_time >= 0.1  # Should wait at least 100ms

    def test_get_error_stats_empty(self, error_handler):
        """Test get_error_stats with no errors."""
        stats = error_handler.get_error_stats()
        assert stats['total_errors'] == 0
        assert stats['by_category'] == {}

    def _add_errors_for_stats_test(self, error_handler):
        """Add various errors for stats testing"""
        errors = [
            ValidationError("Validation error"),
            NetworkError("Network error"),
            NetworkError("Another network error")
        ]
        for error in errors:
            error_handler._store_error(error)

    def test_get_error_stats_with_errors(self, error_handler):
        """Test get_error_stats with stored errors."""
        self._add_errors_for_stats_test(error_handler)
        stats = error_handler.get_error_stats()
        assert stats['total_errors'] == 3
        assert stats['by_category']['validation'] == 1
        assert stats['by_category']['network'] == 2


class TestGlobalErrorHandler:
    """Test global error handler functionality."""
    
    def test_global_error_handler_exists(self):
        """Test global error handler instance exists."""
        assert global_error_handler is not None
        assert isinstance(global_error_handler, ErrorHandler)


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

    async def test_decorator_non_retryable_error(self):
        """Test decorator with non-retryable errors."""
        non_retryable_function = await self._create_non_retryable_function()
        result = await non_retryable_function()
        assert isinstance(result, ValidationError)

    async def _create_fallback_function_for_decorator(self):
        """Create function with fallback for decorator testing"""
        async def fallback_func(error, context):
            return "fallback_executed"
        
        @handle_agent_error(agent_name="TestAgent", operation_name="fallback_op", fallback=fallback_func)
        async def function_with_fallback():
            raise NetworkError("Network error")
        
        return function_with_fallback

    async def test_decorator_with_fallback(self):
        """Test decorator with fallback function."""
        function_with_fallback = await self._create_fallback_function_for_decorator()
        result = await function_with_fallback()
        assert result == "fallback_executed"

    async def _create_max_retries_function(self):
        """Create function that always fails for max retries testing"""
        @handle_agent_error(agent_name="TestAgent", operation_name="always_fail", max_retries=2)
        async def always_failing_function():
            raise NetworkError("Always fails")
        return always_failing_function

    async def test_decorator_max_retries_exceeded(self):
        """Test decorator when max retries exceeded."""
        always_failing_function = await self._create_max_retries_function()
        result = await always_failing_function()
        assert isinstance(result, NetworkError)

    async def _create_delay_verification_function(self):
        """Create function for delay verification testing"""
        call_times = []
        
        @handle_agent_error(agent_name="TestAgent", operation_name="delay_test", max_retries=2)
        async def function_with_delay():
            call_times.append(time.time())
            if len(call_times) < 2:
                raise NetworkError("Retry with delay")
            return "success"
        
        return function_with_delay, call_times

    async def test_decorator_with_delay_verification(self):
        """Test decorator retry delay functionality."""
        function_with_delay, call_times = await self._create_delay_verification_function()
        await function_with_delay()
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert delay >= 0.5  # Should have some delay between retries

    async def _create_function_without_agent_name(self):
        """Create function without agent name for testing"""
        @handle_agent_error(operation_name="no_agent_op")
        async def function_without_agent():
            return "no_agent_success"
        return function_without_agent

    async def test_decorator_without_agent_name(self):
        """Test decorator without agent_name parameter."""
        function_without_agent = await self._create_function_without_agent_name()
        result = await function_without_agent()
        assert result == "no_agent_success"