"""
Test suite for retry mechanism exception handling issues.

This test reproduces and validates the Python 3.11+ exception handling bug
in retry_mechanism.py line 191 where complex exceptions fail to construct
properly when retry attempts are exhausted.

Business Impact:
- Critical reliability issue affecting service error reporting
- Prevents proper error propagation in production systems
- Affects debugging and monitoring capabilities

Test Focus:
- Exception constructor compatibility issues
- Complex exception types (OSError, UnicodeDecodeError, etc.)
- Error context preservation during retry exhaustion
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict, List

from netra_backend.app.core.service_dependencies.retry_mechanism import (
    ServiceRetryManager,
    ServiceType,
    RetryConfig,
    RetryContext,
    CircuitBreakerState
)


class TestRetryMechanismExceptionHandling:
    """Test suite for exception handling in retry mechanism."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_manager = ServiceRetryManager()
        self.service_type = ServiceType.DATABASE
        self.operation_name = "test_operation"
    
    def test_simple_exception_handling_works(self):
        """Test that simple exceptions (ValueError, TypeError) work correctly."""
        
        async def failing_operation():
            raise ValueError("Simple error message")
        
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Should work fine - ValueError accepts single string argument
        assert "test_operation failed for DATABASE after 2 attempts" in str(exc_info.value)
        assert "Simple error message" in str(exc_info.value)
    
    def test_oserror_exception_handling_fails(self):
        """Test that OSError fails with current exception handling approach."""
        
        async def failing_operation():
            # OSError with errno, strerror arguments
            raise OSError(2, "No such file or directory", "/nonexistent/path")
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Current code fails because OSError constructor doesn't accept single string
        assert "OSError" in str(exc_info.value) or "__init__" in str(exc_info.value)
    
    def test_unicode_decode_error_handling_fails(self):
        """Test that UnicodeDecodeError fails with current exception handling."""
        
        async def failing_operation():
            # UnicodeDecodeError with specific constructor signature
            raise UnicodeDecodeError(
                "utf-8",           # encoding
                b'\xff\xfe',       # object
                0,                 # start
                2,                 # end
                "invalid start byte"  # reason
            )
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Current code fails because UnicodeDecodeError has complex constructor
        assert "UnicodeDecodeError" in str(exc_info.value) or "__init__" in str(exc_info.value)
    
    def test_connection_error_with_args_fails(self):
        """Test that ConnectionError with multiple args fails."""
        
        async def failing_operation():
            # ConnectionError with multiple arguments
            raise ConnectionError("Connection failed", 111, "Connection refused")
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Should fail with current approach
        error_msg = str(exc_info.value)
        assert "ConnectionError" in error_msg or "__init__" in error_msg
    
    def test_key_error_handling_works(self):
        """Test that KeyError works (single argument constructor)."""
        
        async def failing_operation():
            raise KeyError("missing_key")
        
        with pytest.raises(KeyError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # KeyError should work fine
        assert "test_operation failed for DATABASE after 2 attempts" in str(exc_info.value)
    
    def test_custom_exception_with_complex_constructor_fails(self):
        """Test custom exception with complex constructor fails."""
        
        class ComplexCustomException(Exception):
            def __init__(self, code: int, message: str, details: Dict[str, Any]):
                self.code = code
                self.message = message
                self.details = details
                super().__init__(f"Code {code}: {message}")
        
        async def failing_operation():
            raise ComplexCustomException(
                500, 
                "Internal server error", 
                {"timestamp": time.time(), "context": "test"}
            )
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Should fail because ComplexCustomException doesn't accept single string
        error_msg = str(exc_info.value)
        assert "ComplexCustomException" in error_msg or "__init__" in error_msg
    
    def test_exception_with_no_args_constructor_fails(self):
        """Test exception that requires no arguments fails."""
        
        class NoArgsException(Exception):
            def __init__(self):
                super().__init__("Fixed message")
        
        async def failing_operation():
            raise NoArgsException()
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # Should fail because NoArgsException doesn't accept arguments
        error_msg = str(exc_info.value)
        assert "NoArgsException" in error_msg or "__init__" in error_msg
    
    def test_exception_context_preservation_issue(self):
        """Test that exception context is preserved but constructor fails."""
        
        async def failing_operation():
            try:
                # Simulate nested exception scenario
                raise ValueError("Original error")
            except ValueError as e:
                # Create OSError with context
                raise OSError(2, "File not found") from e
        
        with pytest.raises(TypeError) as exc_info:
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
        
        # The __cause__ chain is lost due to constructor failure
        error_msg = str(exc_info.value)
        assert "OSError" in error_msg or "__init__" in error_msg
    
    def test_successful_operation_after_retries(self):
        """Test that successful operations work correctly (control test)."""
        call_count = 0
        
        async def eventually_succeeding_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = asyncio.run(
            self.retry_manager.retry_with_backoff(
                eventually_succeeding_operation,
                self.service_type,
                self.operation_name,
                max_retries=3
            )
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_different_exception_types_compatibility(self):
        """Test matrix of different exception types and their constructor compatibility."""
        
        # Exception types that should work (single string constructor)
        working_exceptions = [
            ValueError("test"),
            TypeError("test"),
            RuntimeError("test"),
            KeyError("test"),
            AttributeError("test"),
        ]
        
        # Exception types that fail (complex constructors)
        failing_exceptions = [
            OSError(2, "No such file"),
            UnicodeDecodeError("utf-8", b'\xff', 0, 1, "invalid"),
            ConnectionError("failed", 111),
        ]
        
        # Test working exceptions
        for exc in working_exceptions:
            async def failing_op():
                raise exc
            
            with pytest.raises(type(exc)):
                asyncio.run(
                    self.retry_manager.retry_with_backoff(
                        failing_op,
                        self.service_type,
                        f"test_{type(exc).__name__}",
                        max_retries=1
                    )
                )
        
        # Test failing exceptions
        for exc in failing_exceptions:
            async def failing_op():
                raise exc
            
            with pytest.raises(TypeError):
                asyncio.run(
                    self.retry_manager.retry_with_backoff(
                        failing_op,
                        self.service_type,
                        f"test_{type(exc).__name__}",
                        max_retries=1
                    )
                )
    
    def test_exception_args_preservation_issue(self):
        """Test that original exception args are lost in current implementation."""
        
        async def failing_operation():
            exc = OSError(2, "No such file or directory", "/path/to/file")
            exc.filename = "/path/to/file"  # Additional attribute
            raise exc
        
        # Current implementation will fail to construct OSError properly
        with pytest.raises(TypeError):
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=1
                )
            )
    
    @patch('netra_backend.app.core.service_dependencies.retry_mechanism.logger')
    def test_logging_during_exception_reconstruction_failure(self, mock_logger):
        """Test that logging still works even when exception reconstruction fails."""
        
        async def failing_operation():
            raise OSError(2, "File not found")
        
        with pytest.raises(TypeError):
            asyncio.run(
                self.retry_manager.retry_with_backoff(
                    failing_operation,
                    self.service_type,
                    self.operation_name,
                    max_retries=2
                )
            )
        
        # Verify retry logging still occurred before failure
        assert mock_logger.warning.call_count >= 2  # At least 2 retry attempts
        assert mock_logger.error.call_count >= 1     # Final exhaustion message


class TestExceptionConstructorAnalysis:
    """Detailed analysis of exception constructor patterns."""
    
    def test_builtin_exception_constructor_signatures(self):
        """Analyze constructor signatures of common builtin exceptions."""
        
        # Test different constructor patterns
        constructor_tests = [
            # (Exception class, works_with_single_string, example_args)
            (ValueError, True, ("message",)),
            (TypeError, True, ("message",)),
            (RuntimeError, True, ("message",)),
            (KeyError, True, ("key",)),
            (AttributeError, True, ("message",)),
            (OSError, False, (2, "No such file")),
            (ConnectionError, True, ("Connection failed",)),  # Inherits from OSError but works
            (UnicodeDecodeError, False, ("utf-8", b'\xff', 0, 1, "invalid")),
            (PermissionError, False, (13, "Permission denied")),
            (FileNotFoundError, False, (2, "File not found")),
        ]
        
        for exc_class, should_work, example_args in constructor_tests:
            # Test if single string constructor works
            try:
                reconstructed = exc_class("test message")
                works_with_string = True
            except (TypeError, ValueError):
                works_with_string = False
            
            assert works_with_string == should_work, (
                f"{exc_class.__name__} string constructor expectation mismatch: "
                f"expected {should_work}, got {works_with_string}"
            )
    
    def test_exception_attribute_preservation(self):
        """Test which exception attributes are preserved or lost."""
        
        # Create OSError with specific attributes
        original_exc = OSError(2, "No such file or directory", "/nonexistent")
        original_exc.filename = "/nonexistent"
        
        # Try current approach (will fail)
        try:
            reconstructed = type(original_exc)("New message")
            # This won't be reached due to TypeError
            assert False, "Should have failed with TypeError"
        except TypeError:
            # Expected - OSError constructor doesn't accept single string
            pass
        
        # Show what's lost
        assert hasattr(original_exc, 'errno')
        assert hasattr(original_exc, 'strerror') 
        assert hasattr(original_exc, 'filename')
        assert original_exc.errno == 2
        assert original_exc.strerror == "No such file or directory"
        assert original_exc.filename == "/nonexistent"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])