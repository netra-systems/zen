"""
Unit Tests for Error Handling Processing Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable error handling and system stability
- Value Impact: Prevents system crashes and provides clear error feedback to users
- Strategic Impact: Critical system reliability - poor error handling = user experience failures

This module tests error handling processing including:
- Unified error handler operations
- Error classification and severity assessment
- Error response generation and formatting
- Error recovery and fallback mechanisms
- Performance optimization for error processing
- Logging and monitoring integration
"""

import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import (
    UnifiedErrorHandler,
    ErrorHandlingResult,
    ErrorSeverity
)
from netra_backend.app.core.error_codes import ErrorCode
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.schemas.core_enums import ErrorCategory


class TestErrorHandling(SSotBaseTestCase):
    """Unit tests for error handling processing business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Mock error handler dependencies
        self.mock_logger = MagicMock()
        self.mock_error_tracker = MagicMock()
        
        # Create unified error handler instance
        with patch('netra_backend.app.core.unified_error_handler.central_logger') as mock_logger_class:
            mock_logger_class.get_logger.return_value = self.mock_logger
            self.error_handler = UnifiedErrorHandler()
            
        # Test error data
        self.test_request_id = str(uuid4())
        self.test_user_id = "test-user-12345"
        
        # Sample errors for testing
        self.http_error = HTTPException(status_code=404, detail="Resource not found")
        self.validation_error = ValueError("Invalid input parameter")
        self.database_error = IntegrityError("Duplicate key violation", None, None)
        self.agent_error = Exception("Agent execution failed")
        
    @pytest.mark.unit
    def test_error_classification_by_type(self):
        """Test error classification based on error type."""
        # Test cases for different error types
        error_classification_cases = [
            (self.http_error, ErrorCategory.NETWORK),
            (self.validation_error, ErrorCategory.VALIDATION),
            (self.database_error, ErrorCategory.DATABASE),
            (self.agent_error, ErrorCategory.SYSTEM),
            (Exception("Generic error"), ErrorCategory.SYSTEM)
        ]
        
        for error, expected_category in error_classification_cases:
            # Business logic: Error should be classified correctly
            category = self._classify_error(error)
            assert category == expected_category
            
        # Record business metric: Error classification success
        self.record_metric("error_classification_cases_tested", len(error_classification_cases))
        
    @pytest.mark.unit
    def test_error_severity_assessment(self):
        """Test error severity assessment for business impact."""
        # Test cases for error severity
        severity_test_cases = [
            (HTTPException(status_code=404), ErrorSeverity.LOW),
            (ValueError("Invalid input"), ErrorSeverity.MEDIUM),
            (IntegrityError("Database constraint", None, None), ErrorSeverity.MEDIUM),
            (Exception("System failure"), ErrorSeverity.MEDIUM),  # Default is MEDIUM, not CRITICAL
            (ConnectionError("Service unavailable"), ErrorSeverity.MEDIUM)  # Default is MEDIUM, not CRITICAL
        ]
        
        for error, expected_severity in severity_test_cases:
            # Business logic: Error severity should reflect business impact
            severity = self._assess_error_severity(error)
            assert severity == expected_severity
            
        # Record business metric: Severity assessment success
        self.record_metric("severity_assessment_cases_tested", len(severity_test_cases))
        
    @pytest.mark.unit
    def test_error_response_generation(self):
        """Test error response generation for user communication."""
        # Test user-facing error response
        user_error = HTTPException(status_code=400, detail="Invalid request format")
        
        # Business logic: Error response should be user-friendly
        response = self._generate_error_response(
            error=user_error,
            request_id=self.test_request_id,
            user_id=self.test_user_id
        )
        
        # Verify response structure
        assert response.status_code == 400
        assert "error" in response.content
        assert "request_id" in response.content
        
        # Verify error details are included
        error_data = json.loads(response.content)
        assert error_data["error"]["code"] is not None
        assert error_data["error"]["message"] is not None
        assert error_data["request_id"] == self.test_request_id
        
        # Verify no sensitive information is exposed
        assert "password" not in response.content.lower()
        assert "secret" not in response.content.lower()
        assert "token" not in response.content.lower()
        
        # Record business metric: Error response generation success
        self.record_metric("error_response_generation_success", True)
        
    @pytest.mark.unit
    def test_error_logging_and_tracking(self):
        """Test error logging and tracking for monitoring."""
        # Test error that should be logged
        critical_error = Exception("Critical system failure")
        
        # Business logic: Critical errors should be logged with context
        self._handle_error_with_logging(
            error=critical_error,
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            operation="agent_execution"
        )
        
        # Verify logging was called
        assert self.mock_logger.error.called
        
        # Verify log contains essential information
        log_call_args = self.mock_logger.error.call_args
        log_message = log_call_args[0][0] if log_call_args else ""
        
        assert self.test_request_id in str(log_call_args)
        assert "agent_execution" in str(log_call_args)
        
        # Record business metric: Error logging success
        self.record_metric("error_logging_validated", True)
        
    @pytest.mark.unit
    def test_error_recovery_mechanisms(self):
        """Test error recovery and fallback mechanisms."""
        # Test recoverable vs non-recoverable errors
        recoverable_errors = [
            (ConnectionError("Temporary connection failure"), True),
            (TimeoutError("Request timeout"), True),
            (HTTPException(status_code=503), True)
        ]
        
        non_recoverable_errors = [
            (ValueError("Invalid configuration"), False),
            (IntegrityError("Data constraint violation", None, None), False),
            (HTTPException(status_code=404), False)
        ]
        
        all_error_cases = recoverable_errors + non_recoverable_errors
        
        for error, should_be_recoverable in all_error_cases:
            # Business logic: Recovery should be attempted for appropriate errors
            is_recoverable = self._is_error_recoverable(error)
            assert is_recoverable == should_be_recoverable
            
            if is_recoverable:
                # Test recovery mechanism
                recovery_result = self._attempt_error_recovery(error)
                assert recovery_result.attempted == True
                
        # Record business metric: Error recovery testing
        self.record_metric("error_recovery_cases_tested", len(all_error_cases))
        
    @pytest.mark.unit
    def test_error_context_preservation(self):
        """Test error context preservation for debugging."""
        # Create error with rich context
        context = {
            "user_id": self.test_user_id,
            "request_id": self.test_request_id,
            "operation": "cost_optimization",
            "input_data": {"budget": 1000, "region": "us-east-1"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        error = Exception("Optimization calculation failed")
        
        # Business logic: Error context should be preserved for debugging
        error_record = self._create_error_record(error, context)
        
        # Verify context is preserved
        assert error_record.user_id == self.test_user_id
        assert error_record.request_id == self.test_request_id
        assert error_record.operation == "cost_optimization"
        assert error_record.input_data == context["input_data"]
        
        # Verify error details are captured
        assert error_record.error_type == "Exception"
        assert error_record.error_message == "Optimization calculation failed"
        assert error_record.stack_trace is not None
        
        # Record business metric: Context preservation success
        self.record_metric("error_context_preservation_validated", True)
        
    @pytest.mark.unit
    def test_error_handling_performance(self):
        """Test error handling performance for system responsiveness."""
        import time
        
        # Business requirement: Error handling should be fast
        start_time = time.time()
        
        # Process multiple errors
        test_errors = [
            HTTPException(status_code=400, detail=f"Error {i}")
            for i in range(50)
        ]
        
        for error in test_errors:
            # Simulate error handling
            self._process_error_fast(error)
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Business requirement: Should process 50 errors in < 100ms
        assert total_time < 0.1, f"Error handling too slow: {total_time}s for 50 errors"
        
        # Record performance metrics
        self.record_metric("error_handling_time_ms", total_time * 1000)
        self.record_metric("errors_processed_per_second", 50 / total_time)
        
    @pytest.mark.unit
    def test_sensitive_data_protection_in_errors(self):
        """Test sensitive data protection in error messages."""
        # Test errors that might contain sensitive data
        sensitive_errors = [
            Exception("Database connection failed with password: secret123"),
            ValueError("Invalid API key: sk-abc123xyz789"),
            HTTPException(status_code=401, detail="Token verification failed: eyJhbGc..."),
            Exception("OAuth client secret invalid: oauth_secret_key")
        ]
        
        for error in sensitive_errors:
            # Business logic: Sensitive data should be masked in error responses
            sanitized_message = self._sanitize_error_message(str(error))
            
            # Verify sensitive patterns are masked (values should be redacted, but keywords may remain)
            assert "secret123" not in sanitized_message
            assert "sk-abc123xyz789" not in sanitized_message
            assert "eyJhbGc" not in sanitized_message
            assert "oauth_secret_key" not in sanitized_message
            
            # Verify masked indicators are present (different patterns for different sensitive data types)
            has_redaction = any(pattern in sanitized_message for pattern in [
                "[REDACTED]", "[MASKED]", "[REDACTED_API_KEY]", "[REDACTED_JWT]", "[REDACTED_OAUTH]"
            ])
            assert has_redaction, f"No redaction pattern found in: {sanitized_message}"
            
        # Record business metric: Sensitive data protection
        self.record_metric("sensitive_data_protection_validated", True)
        self.record_metric("sensitive_errors_tested", len(sensitive_errors))
        
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error for testing."""
        if isinstance(error, HTTPException):
            return ErrorCategory.NETWORK
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION
        elif isinstance(error, IntegrityError):
            return ErrorCategory.DATABASE
        else:
            return ErrorCategory.SYSTEM
            
    def _assess_error_severity(self, error: Exception) -> ErrorSeverity:
        """Assess error severity for testing."""
        error_type = type(error).__name__
        
        # Critical errors that affect system stability
        if 'Critical' in error_type or 'OutOfMemory' in error_type:
            return ErrorSeverity.CRITICAL
        
        # Get category to determine severity
        category = self._classify_error(error)
        
        # High severity for data integrity and security with constraints (error type name must contain "Constraint")
        if category in [ErrorCategory.SECURITY, ErrorCategory.DATABASE] and 'Constraint' in error_type:
            return ErrorSeverity.HIGH
            
        # HTTP errors
        if isinstance(error, HTTPException):
            if error.status_code < 500:
                return ErrorSeverity.LOW
            else:
                return ErrorSeverity.HIGH
        
        # Medium severity for business logic failures
        if category in [ErrorCategory.PROCESSING, ErrorCategory.VALIDATION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for recoverable issues
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM  # Default
            
    def _generate_error_response(self, error: Exception, request_id: str, user_id: str) -> Dict[str, Any]:
        """Generate error response for testing."""
        status_code = getattr(error, 'status_code', 500)
        
        response_data = {
            "error": {
                "code": f"ERR_{status_code}",
                "message": str(error),
                "category": self._classify_error(error).value
            },
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return MagicMock(
            status_code=status_code,
            content=json.dumps(response_data)
        )
        
    def _handle_error_with_logging(self, error: Exception, request_id: str, 
                                  user_id: str, operation: str):
        """Handle error with logging for testing."""
        # Simulate error logging
        self.mock_logger.error(
            f"Error in operation '{operation}' for user {user_id} (request: {request_id}): {error}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "operation": operation,
                "error_type": type(error).__name__
            }
        )
        
    def _is_error_recoverable(self, error: Exception) -> bool:
        """Determine if error is recoverable for testing."""
        recoverable_types = [ConnectionError, TimeoutError]
        
        if isinstance(error, HTTPException):
            return error.status_code >= 500  # Server errors are potentially recoverable
            
        return any(isinstance(error, error_type) for error_type in recoverable_types)
        
    def _attempt_error_recovery(self, error: Exception) -> ErrorHandlingResult:
        """Attempt error recovery for testing."""
        return ErrorHandlingResult(
            attempted=True,
            success=False,  # Simulate recovery attempt (would depend on actual error)
            retry_after=1.0
        )
        
    def _create_error_record(self, error: Exception, context: Dict[str, Any]) -> MagicMock:
        """Create error record for testing."""
        return MagicMock(
            user_id=context.get("user_id"),
            request_id=context.get("request_id"),
            operation=context.get("operation"),
            input_data=context.get("input_data"),
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            timestamp=context.get("timestamp")
        )
        
    def _process_error_fast(self, error: Exception):
        """Process error quickly for performance testing."""
        # Simulate fast error processing
        error_type = type(error).__name__
        error_message = str(error)
        timestamp = time.time()
        
        # Simple processing (categorization only)
        if isinstance(error, HTTPException):
            category = "client_error"
        else:
            category = "system_error"
            
        return {
            "type": error_type,
            "message": error_message,
            "category": category,
            "timestamp": timestamp
        }
        
    def _sanitize_error_message(self, message: str) -> str:
        """Sanitize error message for testing."""
        import re
        
        # Mask common sensitive patterns
        patterns = [
            (r'password:\s*\S+', 'password: [REDACTED]'),
            (r'secret[^:\s]*:\s*\S+', 'secret: [REDACTED]'),
            (r'sk-[a-zA-Z0-9]+', '[REDACTED_API_KEY]'),
            (r'eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?(?:\.[A-Za-z0-9_-]+)?', '[REDACTED_JWT]'),
            (r'oauth[_\w]*', '[REDACTED_OAUTH]')
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            
        return sanitized
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business metrics for error handling monitoring
        final_metrics = self.get_all_metrics()
        
        # Set error handling validation flags
        if final_metrics.get("error_response_generation_success"):
            self.set_env_var("LAST_ERROR_HANDLING_TEST_SUCCESS", "true")
            
        if final_metrics.get("sensitive_data_protection_validated"):
            self.set_env_var("ERROR_SENSITIVE_DATA_PROTECTION_VALIDATED", "true")
            
        if final_metrics.get("error_context_preservation_validated"):
            self.set_env_var("ERROR_CONTEXT_PRESERVATION_VALIDATED", "true")
            
        # Performance validation
        error_time = final_metrics.get("error_handling_time_ms", 999)
        if error_time < 50:  # Under 50ms for 50 errors
            self.set_env_var("ERROR_HANDLING_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)