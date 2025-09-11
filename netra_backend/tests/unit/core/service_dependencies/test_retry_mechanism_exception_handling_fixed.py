"""
Test suite validating the fixed exception handling in retry_mechanism.py.

This test suite validates that the Python 3.11+ exception handling fix
works correctly for all types of exceptions, including complex constructors
that previously caused TypeError failures.

Business Impact:
- Validates critical reliability fix for service error reporting
- Ensures proper error propagation in production systems
- Confirms debugging and monitoring capabilities are preserved

Test Focus:
- Validates safe exception construction approach
- Confirms fallback to RuntimeError for complex exceptions
- Verifies exception chain preservation
- Tests defensive programming approach
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from typing import Any, Dict

from netra_backend.app.core.service_dependencies.retry_mechanism import (
    RetryMechanism,
    CircuitBreakerState
)
from netra_backend.app.core.service_dependencies.models import (
    ServiceType,
    EnvironmentType
)


class TestRetryMechanismExceptionHandlingFixed:
    """Test suite validating the fixed exception handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_mechanism = RetryMechanism(EnvironmentType.TESTING)
        self.service_type = ServiceType.DATABASE_POSTGRES
        self.operation_name = "test_operation"
    
    def test_simple_exception_handling_works(self):
        """Test that simple exceptions (ValueError, TypeError) work correctly."""
        
        async def failing_operation():
            raise ValueError("Simple error message")
        
        # Should work fine with enhanced error message
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        assert "test_operation failed for database_postgres after" in error_msg
        assert "Simple error message" in error_msg
        # Verify exception chain is preserved
        assert exc_info.value.__cause__ is not None
    
    def test_oserror_with_dynamic_construction_succeeds(self):
        """
        Test that OSError with simple constructor works with dynamic construction.
        """
        
        async def failing_operation():
            # Simple OSError - should work with dynamic construction
            raise OSError("File operation failed")
        
        # Should successfully create OSError with enhanced message
        with pytest.raises(OSError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        assert "test_operation failed for database_postgres after" in error_msg
        assert "File operation failed" in error_msg
        # Verify exception chain is preserved
        assert exc_info.value.__cause__ is not None
    
    def test_complex_oserror_falls_back_to_runtime_error(self):
        """
        Test that complex OSError falls back to RuntimeError gracefully.
        """
        
        async def failing_operation():
            # Complex OSError with errno, strerror, filename - should trigger fallback
            raise OSError(2, "No such file or directory", "/nonexistent/path")
        
        # Should fall back to RuntimeError with all original info preserved
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        # Verify retry context is included
        assert "test_operation failed for database_postgres after" in error_msg
        # Verify original exception info is preserved
        assert "No such file or directory" in error_msg
        assert "FileNotFoundError" in error_msg or "OSError" in error_msg
        # Verify exception chain is preserved
        assert exc_info.value.__cause__ is not None
    
    def test_unicode_decode_error_falls_back_gracefully(self):
        """
        Test that UnicodeDecodeError falls back to RuntimeError with full context.
        """
        
        async def failing_operation():
            # UnicodeDecodeError with complex constructor - should trigger fallback
            raise UnicodeDecodeError(
                "utf-8",
                b'\xff\xfe',
                0,
                2,
                "invalid start byte"
            )
        
        # Should fall back to RuntimeError with comprehensive error info
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        # Verify retry context
        assert "test_operation failed for database_postgres after" in error_msg
        # Verify original exception details preserved
        assert "invalid start byte" in error_msg
        assert "UnicodeDecodeError" in error_msg
        # Verify original exception is in the chain
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, UnicodeDecodeError)
    
    def test_permission_error_falls_back_gracefully(self):
        """
        Test that PermissionError falls back to RuntimeError with context preservation.
        """
        
        async def failing_operation():
            # PermissionError with errno - should trigger fallback
            raise PermissionError(13, "Permission denied", "/protected/file")
        
        # Should fall back to RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        assert "test_operation failed for database_postgres after" in error_msg
        assert "Permission denied" in error_msg
        assert "PermissionError" in error_msg
        # Verify exception chain preservation
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, PermissionError)
    
    def test_custom_exception_with_complex_constructor_fallback(self):
        """Test custom exception with complex constructor falls back properly."""
        
        class DatabaseConnectionError(Exception):
            def __init__(self, host: str, port: int, error_code: int):
                self.host = host
                self.port = port
                self.error_code = error_code
                super().__init__(f"Failed to connect to {host}:{port} (error {error_code})")
        
        async def failing_operation():
            raise DatabaseConnectionError("localhost", 5432, 1001)
        
        # Should fall back to RuntimeError while preserving all context
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        error_msg = str(exc_info.value)
        # Verify comprehensive error context
        assert "test_operation failed for database_postgres after" in error_msg
        assert "Failed to connect to localhost:5432" in error_msg
        assert "DatabaseConnectionError" in error_msg
        # Verify original exception attributes are accessible via chain
        assert exc_info.value.__cause__ is not None
        original_exc = exc_info.value.__cause__
        assert hasattr(original_exc, 'host')
        assert hasattr(original_exc, 'port')
        assert hasattr(original_exc, 'error_code')
        assert original_exc.host == "localhost"
        assert original_exc.port == 5432
        assert original_exc.error_code == 1001
    
    def test_exception_chain_preservation_with_nested_exceptions(self):
        """
        Test that exception chains are preserved even with nested exception scenarios.
        """
        
        async def failing_operation():
            try:
                # Create nested exception scenario
                raise ValueError("Root cause error")
            except ValueError as e:
                # Complex OSError with context - should trigger fallback but preserve full chain
                raise OSError(2, "File operation failed") from e
        
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        # Verify the immediate exception
        error_msg = str(exc_info.value)
        assert "test_operation failed for database_postgres after" in error_msg
        assert "File operation failed" in error_msg
        
        # Verify exception chain: RuntimeError -> OSError -> ValueError
        assert exc_info.value.__cause__ is not None
        oserror = exc_info.value.__cause__
        assert isinstance(oserror, OSError)
        
        # Verify the original nested chain is preserved
        assert oserror.__cause__ is not None
        original_cause = oserror.__cause__
        assert isinstance(original_cause, ValueError)
        assert str(original_cause) == "Root cause error"
    
    def test_logging_behavior_for_fallback_cases(self):
        """Test that proper logging occurs when fallback is triggered."""
        
        async def failing_operation():
            # This should trigger the fallback mechanism
            raise UnicodeDecodeError("utf-8", b'\xff\xfe', 0, 2, "invalid start byte")
        
        # Capture logs to verify debug logging occurs
        with patch.object(self.retry_mechanism.logger, 'debug') as mock_debug:
            with pytest.raises(RuntimeError):
                asyncio.run(
                    self.retry_mechanism.execute_with_retry(
                        failing_operation,
                        self.service_type,
                        self.operation_name
                    )
                )
        
        # Verify that logging occurred for the fallback
        mock_debug.assert_called()
        debug_calls = [call[0][0] for call in mock_debug.call_args_list]
        fallback_logged = any("Failed to construct" in call and "Using RuntimeError wrapper" in call 
                             for call in debug_calls)
        assert fallback_logged, f"Expected fallback logging not found in: {debug_calls}"
    
    def test_successful_operation_still_works(self):
        """Test that successful operations work correctly (regression test)."""
        
        call_count = 0
        
        async def eventually_succeeding_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:  # Fail once, then succeed
                raise ValueError("Temporary failure")
            return "success"
        
        result = asyncio.run(
            self.retry_mechanism.execute_with_retry(
                eventually_succeeding_operation,
                self.service_type,
                self.operation_name
            )
        )
        
        assert result == "success"
        assert call_count == 2  # Failed once, succeeded on second attempt
    
    def test_retry_statistics_work_with_fixed_exceptions(self):
        """Test that retry statistics tracking works with the fixed exception handling."""
        
        async def failing_operation():
            # Use complex exception that triggers fallback
            raise OSError(2, "No such file or directory", "/nonexistent/path")
        
        # Clear any existing stats
        self.retry_mechanism._retry_stats.clear()
        
        with pytest.raises(RuntimeError):
            asyncio.run(
                self.retry_mechanism.execute_with_retry(
                    failing_operation,
                    self.service_type,
                    self.operation_name
                )
            )
        
        # Verify statistics were recorded properly
        stats = self.retry_mechanism.get_retry_statistics(self.service_type)
        assert stats["failure_count"] == 1
        assert stats["total_attempts"] > 1  # Should have retried
        assert stats["total_retries"] > 0


class TestExceptionConstructorSafety:
    """Test suite validating the safety mechanisms in exception construction."""
    
    def test_safe_construction_attempt_patterns(self):
        """Test the specific patterns used in the safe construction approach."""
        
        # Test simple exceptions that should work with dynamic construction
        simple_exceptions = [
            ValueError("test"),
            TypeError("test"), 
            RuntimeError("test"),
            KeyError("test"),
            AttributeError("test"),
        ]
        
        for original_exc in simple_exceptions:
            try:
                # This is what the fix attempts first
                reconstructed = type(original_exc)("Enhanced message")
                assert isinstance(reconstructed, type(original_exc))
                assert str(reconstructed) == "Enhanced message"
            except (TypeError, ValueError) as e:
                pytest.fail(f"Simple exception {type(original_exc).__name__} should work: {e}")
    
    def test_complex_exception_construction_detection(self):
        """Test detection of complex exception constructors that require fallback."""
        
        complex_exceptions = [
            OSError(2, "No such file", "/path"),
            UnicodeDecodeError("utf-8", b'\xff\xfe', 0, 2, "invalid"),
            PermissionError(13, "Permission denied", "/protected"),
        ]
        
        for original_exc in complex_exceptions:
            # These should fail with TypeError when attempting simple string construction
            with pytest.raises(TypeError):
                type(original_exc)("Enhanced message")
    
    def test_runtime_error_fallback_construction(self):
        """Test that RuntimeError fallback always works as expected."""
        
        # RuntimeError should always work with string constructor
        test_messages = [
            "Simple message",
            "Message with (parentheses) and special chars: @#$%",
            "Multi-line\nmessage\nwith\nbreaks",
            "Unicode message with émojis: 🚀🔥⚠️",
            "",  # Empty message
            "Very " + "long " * 100 + "message",  # Long message
        ]
        
        for message in test_messages:
            try:
                runtime_error = RuntimeError(message)
                assert isinstance(runtime_error, RuntimeError)
                assert str(runtime_error) == message
            except Exception as e:
                pytest.fail(f"RuntimeError should always work with any string: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])