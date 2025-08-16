"""Unit tests for ErrorHandler with 70%+ coverage.
Tests all error handling mechanisms, recovery strategies, and decorators.
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
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorContext(SharedTestErrorContext):
    """Test ErrorContext dataclass."""
    
    def test_error_context_creation(self):
        """Test ErrorContext creation with required fields."""
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation",
            run_id="run_123",
            timestamp=time.time()
        )
        
        assert context.agent_name == "TestAgent"
        assert context.operation_name == "test_operation"
        assert context.run_id == "run_123"
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert context.additional_data == {}
    
    def test_error_context_with_custom_values(self):
        """Test ErrorContext with custom values."""
        additional_data = {"key": "value"}
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation", 
            run_id="run_123",
            timestamp=time.time(),
            retry_count=2,
            max_retries=5,
            additional_data=additional_data
        )
        
        assert context.retry_count == 2
        assert context.max_retries == 5
        assert context.additional_data == additional_data
    
    def test_error_context_post_init(self):
        """Test ErrorContext __post_init__ method."""
        # Test with None additional_data
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_operation",
            run_id="run_123", 
            timestamp=time.time(),
            additional_data=None
        )
        
        assert context.additional_data == {}


class TestAgentErrorClasses:
    """Test custom error classes."""
    
    def test_agent_error_creation(self):
        """Test AgentError creation."""
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        error = AgentError(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PROCESSING,
            context=context,
            recoverable=False
        )
        
        assert error.message == "Test error"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.PROCESSING
        assert error.context == context
        assert error.recoverable == False
        assert isinstance(error.timestamp, float)
    
    def test_agent_error_defaults(self):
        """Test AgentError with default values."""
        error = AgentError("Default error")
        
        assert error.message == "Default error"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.UNKNOWN
        assert error.context is None
        assert error.recoverable == True
    
    def test_validation_error(self):
        """Test ValidationError specialized class."""
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="validate",
            run_id="run_123",
            timestamp=time.time()
        )
        
        error = ValidationError("Invalid input", context)
        
        assert error.message == "Invalid input"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION
        assert error.recoverable == False
        assert error.context == context
    
    def test_network_error(self):
        """Test NetworkError specialized class."""
        error = NetworkError("Connection failed")
        
        assert error.message == "Connection failed"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.NETWORK
        assert error.recoverable == True
    
    def test_database_error(self):
        """Test DatabaseError specialized class."""
        error = DatabaseError("Query failed")
        
        assert error.message == "Query failed"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.DATABASE
        assert error.recoverable == True
    
    def test_websocket_error(self):
        """Test WebSocketError specialized class."""
        error = WebSocketError("Connection lost")
        
        assert error.message == "Connection lost"
        assert error.severity == ErrorSeverity.LOW
        assert error.category == ErrorCategory.WEBSOCKET
        assert error.recoverable == True


class TestErrorRecoveryStrategy:
    """Test ErrorRecoveryStrategy static methods."""
    
    def test_get_recovery_delay_network_error(self):
        """Test recovery delay calculation for network errors."""
        error = NetworkError("Connection failed")
        
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, 0)
        assert delay == 2.0  # Base delay for network
        
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, 1)
        assert delay == 4.0  # 2.0 * 2^1
        
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, 2)
        assert delay == 8.0  # 2.0 * 2^2
    
    def test_get_recovery_delay_max_cap(self):
        """Test recovery delay maximum cap."""
        error = NetworkError("Connection failed")
        
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, 10)
        assert delay == 30.0  # Should be capped at 30 seconds
    
    def test_get_recovery_delay_different_categories(self):
        """Test recovery delays for different error categories."""
        database_error = DatabaseError("DB failed")
        websocket_error = WebSocketError("WS failed")
        
        db_delay = ErrorRecoveryStrategy.get_recovery_delay(database_error, 0)
        ws_delay = ErrorRecoveryStrategy.get_recovery_delay(websocket_error, 0)
        
        assert db_delay == 1.0  # Base delay for database
        assert ws_delay == 0.5  # Base delay for websocket
    
    def test_should_retry_validation_error(self):
        """Test should_retry returns False for validation errors."""
        error = ValidationError("Invalid input")
        
        assert ErrorRecoveryStrategy.should_retry(error) == False
    
    def test_should_retry_non_recoverable_error(self):
        """Test should_retry returns False for non-recoverable errors."""
        error = AgentError("Error", recoverable=False)
        
        assert ErrorRecoveryStrategy.should_retry(error) == False
    
    def test_should_retry_network_timeout_errors(self):
        """Test should_retry returns True for network/timeout errors."""
        network_error = NetworkError("Connection failed")
        timeout_error = AgentError("Timeout", category=ErrorCategory.TIMEOUT)
        
        assert ErrorRecoveryStrategy.should_retry(network_error) == True
        assert ErrorRecoveryStrategy.should_retry(timeout_error) == True
    
    def test_should_retry_critical_database_error(self):
        """Test should_retry returns False for critical database errors."""
        error = DatabaseError("Critical DB failure")
        error.severity = ErrorSeverity.CRITICAL
        
        assert ErrorRecoveryStrategy.should_retry(error) == False
    
    def test_should_retry_medium_severity_errors(self):
        """Test should_retry returns True for medium severity errors."""
        error = AgentError("Medium error", severity=ErrorSeverity.MEDIUM)
        
        assert ErrorRecoveryStrategy.should_retry(error) == True


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        
        assert isinstance(handler.error_history, list)
        assert len(handler.error_history) == 0
        assert isinstance(handler.recovery_strategy, ErrorRecoveryStrategy)
        assert handler.max_history == 100
    async def test_handle_error_with_agent_error(self):
        """Test handle_error with AgentError input."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=3,  # Exceed max retries to prevent retry logic
            max_retries=2
        )
        
        agent_error = ValidationError("Test error", context=context)  # Non-retryable
        
        with pytest.raises(AgentError) as exc_info:
            await handler.handle_error(agent_error, context)
        
        assert exc_info.value.message == "Test error"
        assert len(handler.error_history) == 1
    async def test_handle_error_with_generic_exception(self):
        """Test handle_error with generic Exception."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=3,  # Exceed max retries to prevent retry logic
            max_retries=2
        )
        
        generic_error = ValueError("Generic error")
        
        with pytest.raises(AgentError) as exc_info:
            await handler.handle_error(generic_error, context)
        
        assert isinstance(exc_info.value, AgentError)
        assert exc_info.value.message == "Generic error"
        assert len(handler.error_history) == 1
    async def test_handle_error_with_fallback(self):
        """Test handle_error with fallback operation."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=3,  # Exceed retry limit
            max_retries=2
        )
        
        error = ValidationError("Invalid input")  # Non-retryable
        
        async def fallback():
            return "fallback_result"
        
        result = await handler.handle_error(error, context, fallback)
        
        assert result == "fallback_result"
        assert len(handler.error_history) == 1
    async def test_handle_error_fallback_fails(self):
        """Test handle_error when fallback operation fails."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=3,
            max_retries=2
        )
        
        error = ValidationError("Invalid input")
        
        async def failing_fallback():
            raise Exception("Fallback failed")
        
        with pytest.raises(AgentError):
            await handler.handle_error(error, context, failing_fallback)
    
    def test_convert_to_agent_error_with_agent_error(self):
        """Test _convert_to_agent_error with AgentError input."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        original_error = AgentError("Test error")
        
        result = handler._convert_to_agent_error(original_error, context)
        
        assert result == original_error
        assert result.context == context
    
    def test_convert_to_agent_error_validation_error(self):
        """Test _convert_to_agent_error with validation error."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        # Create a mock class to simulate ValidationError
        class MockValidationError(Exception):
            pass
        
        validation_error = MockValidationError("Validation failed")
        
        result = handler._convert_to_agent_error(validation_error, context)
        
        assert isinstance(result, AgentError)
        # The mapping is based on the class name containing 'validation'
        # Since MockValidationError contains 'Validation', it should be treated accordingly
        assert result.severity == ErrorSeverity.HIGH
    
    def test_convert_to_agent_error_connection_error(self):
        """Test _convert_to_agent_error with connection error."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        conn_error = Exception("Connection failed")
        conn_error.__class__.__name__ = "ConnectionError"
        
        result = handler._convert_to_agent_error(conn_error, context)
        
        assert result.category == ErrorCategory.NETWORK
        assert result.recoverable == True
    
    def test_convert_to_agent_error_memory_error(self):
        """Test _convert_to_agent_error with memory error."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent", 
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        memory_error = Exception("Out of memory")
        memory_error.__class__.__name__ = "MemoryError"
        
        result = handler._convert_to_agent_error(memory_error, context)
        
        assert result.category == ErrorCategory.RESOURCE
        assert result.severity == ErrorSeverity.CRITICAL
    
    def test_log_error_different_severities(self):
        """Test _log_error with different severity levels."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time()
        )
        
        # Test critical error logging
        critical_error = AgentError("Critical", severity=ErrorSeverity.CRITICAL, context=context)
        handler._log_error(critical_error)  # Should not crash
        
        # Test high severity error logging
        high_error = AgentError("High", severity=ErrorSeverity.HIGH, context=context)
        handler._log_error(high_error)  # Should not crash
        
        # Test medium severity error logging
        medium_error = AgentError("Medium", severity=ErrorSeverity.MEDIUM, context=context)
        handler._log_error(medium_error)  # Should not crash
        
        # Test low severity error logging
        low_error = AgentError("Low", severity=ErrorSeverity.LOW, context=context)
        handler._log_error(low_error)  # Should not crash
    
    def test_store_error(self):
        """Test _store_error method."""
        handler = ErrorHandler()
        
        error = AgentError("Test error")
        
        handler._store_error(error)
        
        assert len(handler.error_history) == 1
        assert handler.error_history[0] == error
    
    def test_store_error_history_limit(self):
        """Test _store_error respects history limit."""
        handler = ErrorHandler()
        handler.max_history = 2
        
        # Add 3 errors
        for i in range(3):
            error = AgentError(f"Error {i}")
            handler._store_error(error)
        
        # Should only keep the last 2
        assert len(handler.error_history) == 2
        assert handler.error_history[0].message == "Error 1"
        assert handler.error_history[1].message == "Error 2"
    
    def test_should_retry_operation_max_retries_exceeded(self):
        """Test _should_retry_operation when max retries exceeded."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=3,
            max_retries=2
        )
        
        error = NetworkError("Connection failed")
        
        should_retry = handler._should_retry_operation(error, context)
        
        assert should_retry == False
    
    def test_should_retry_operation_within_limits(self):
        """Test _should_retry_operation when within retry limits."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=1,
            max_retries=3
        )
        
        error = NetworkError("Connection failed")
        
        should_retry = handler._should_retry_operation(error, context)
        
        assert should_retry == True
    async def test_retry_with_delay(self):
        """Test _retry_with_delay method."""
        handler = ErrorHandler()
        
        context = ErrorContext(
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_123",
            timestamp=time.time(),
            retry_count=0
        )
        
        error = NetworkError("Connection failed")
        
        with pytest.raises(AgentError) as exc_info:
            await handler._retry_with_delay(error, context)
        
        # Should raise a retry signal error
        assert "Retry required" in exc_info.value.message
        assert exc_info.value.category == ErrorCategory.PROCESSING
    
    def test_get_error_stats_empty(self):
        """Test get_error_stats with no errors."""
        handler = ErrorHandler()
        
        stats = handler.get_error_stats()
        
        assert stats["total_errors"] == 0
    
    def test_get_error_stats_with_errors(self):
        """Test get_error_stats with error history."""
        handler = ErrorHandler()
        
        # Add some test errors
        current_time = time.time()
        recent_error1 = AgentError("Recent 1", severity=ErrorSeverity.HIGH, category=ErrorCategory.NETWORK)
        recent_error1.timestamp = current_time - 1800  # 30 minutes ago
        
        recent_error2 = AgentError("Recent 2", severity=ErrorSeverity.MEDIUM, category=ErrorCategory.DATABASE)
        recent_error2.timestamp = current_time - 900  # 15 minutes ago
        
        old_error = AgentError("Old", severity=ErrorSeverity.LOW, category=ErrorCategory.VALIDATION)
        old_error.timestamp = current_time - 7200  # 2 hours ago
        
        handler.error_history = [old_error, recent_error1, recent_error2]
        
        stats = handler.get_error_stats()
        
        assert stats["total_errors"] == 3
        assert stats["recent_errors"] == 2  # Only recent ones
        assert stats["error_categories"]["network"] == 1
        assert stats["error_categories"]["database"] == 1
        assert stats["error_severities"]["high"] == 1
        assert stats["error_severities"]["medium"] == 1
        assert stats["last_error"]["message"] == "Recent 2"


class TestGlobalErrorHandler:
    """Test global error handler instance."""
    
    def test_global_error_handler_exists(self):
        """Test global_error_handler instance exists."""
        assert isinstance(global_error_handler, ErrorHandler)


class TestHandleAgentErrorDecorator:
    """Test handle_agent_error decorator."""
    async def test_decorator_successful_execution(self):
        """Test decorator with successful method execution."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
            
            @handle_agent_error("test_operation")
            async def successful_method(self, value: str, run_id: str = "test_run"):
                return f"Success: {value}"
        
        agent = TestAgent()
        result = await agent.successful_method("test_value")
        
        assert result == "Success: test_value"
    async def test_decorator_with_retries(self):
        """Test decorator with transient failures and retries."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
                self.attempt_count = 0
            
            @handle_agent_error("failing_operation")
            async def flaky_method(self, run_id: str = "test_run"):
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise NetworkError("Temporary failure")
                return "Success after retries"
        
        agent = TestAgent()
        result = await agent.flaky_method()
        
        assert result == "Success after retries"
        assert agent.attempt_count == 3
    async def test_decorator_non_retryable_error(self):
        """Test decorator with non-retryable error."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
            
            @handle_agent_error("validation_operation")
            async def validation_method(self, run_id: str = "test_run"):
                raise ValidationError("Invalid input")
        
        agent = TestAgent()
        
        with pytest.raises(AgentError):
            await agent.validation_method()
    async def test_decorator_with_fallback(self):
        """Test decorator with fallback method."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
            
            @handle_agent_error("failing_operation")
            async def failing_method(self, run_id: str = "test_run"):
                raise ValidationError("Always fails")
            
            async def _fallback_failing_operation(self):
                return "Fallback result"
        
        agent = TestAgent()
        result = await agent.failing_method()
        
        assert result == "Fallback result"
    async def test_decorator_max_retries_exceeded(self):
        """Test decorator when max retries are exceeded."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
                self.attempt_count = 0
            
            @handle_agent_error("persistent_failure")
            async def always_failing_method(self, run_id: str = "test_run"):
                self.attempt_count += 1
                raise NetworkError("Persistent failure")
        
        agent = TestAgent()
        
        with pytest.raises(AgentError):
            await agent.always_failing_method()
        
        assert agent.attempt_count == 3  # Should have tried 3 times
    async def test_decorator_with_delay_verification(self):
        """Test decorator applies appropriate delays between retries."""
        
        class TestAgent:
            def __init__(self):
                self.name = "TestAgent"
                self.call_times = []
            
            @handle_agent_error("delayed_operation")
            async def delayed_method(self, run_id: str = "test_run"):
                self.call_times.append(time.time())
                if len(self.call_times) < 3:
                    raise NetworkError("Temporary failure")
                return "Success"
        
        agent = TestAgent()
        start_time = time.time()
        
        result = await agent.delayed_method()
        
        total_time = time.time() - start_time
        
        assert result == "Success"
        assert len(agent.call_times) == 3
        # Should have taken some time due to delays
        assert total_time > 0.1  # At least some delay
    async def test_decorator_without_agent_name(self):
        """Test decorator with object without name attribute."""
        
        class TestAgent:
            # No name attribute
            pass
        
        TestAgent.test_method = handle_agent_error("test_operation")(
            lambda self, run_id="test_run": "success"
        )
        
        agent = TestAgent()
        result = await agent.test_method()
        
        assert result == "success"