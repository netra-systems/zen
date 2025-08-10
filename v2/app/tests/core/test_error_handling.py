"""Tests for the standardized error handling system."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    ErrorDetails,
    NetraException,
    ConfigurationError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    DatabaseError,
    RecordNotFoundError,
    ServiceError,
    LLMRequestError,
    WebSocketError,
)
from app.core.error_handlers import (
    ErrorHandler,
    ErrorResponse,
    handle_exception,
    get_http_status_code,
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.core.error_context import ErrorContext, ErrorContextManager, get_enriched_error_context


class TestErrorCodes:
    """Test error code definitions."""
    
    def test_error_code_values(self):
        """Test that error codes have expected values."""
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.AUTHENTICATION_FAILED.value == "AUTH_FAILED"
        assert ErrorCode.DATABASE_CONNECTION_FAILED.value == "DB_CONNECTION_FAILED"
        assert ErrorCode.LLM_REQUEST_FAILED.value == "LLM_REQUEST_FAILED"
    
    def test_error_severity_values(self):
        """Test error severity definitions."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorDetails:
    """Test ErrorDetails model."""
    
    def test_error_details_creation(self):
        """Test creating ErrorDetails."""
        details = ErrorDetails(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test validation error",
            severity=ErrorSeverity.MEDIUM
        )
        
        assert details.code == ErrorCode.VALIDATION_ERROR.value
        assert details.message == "Test validation error"
        assert details.severity == ErrorSeverity.MEDIUM.value
        assert isinstance(details.timestamp, datetime)
    
    def test_error_details_with_context(self):
        """Test ErrorDetails with additional context."""
        context = {"user_id": "123", "request_id": "abc"}
        details = ErrorDetails(
            code=ErrorCode.DATABASE_QUERY_FAILED,
            message="Database error",
            context=context,
            trace_id="trace-123"
        )
        
        assert details.code == ErrorCode.DATABASE_QUERY_FAILED.value
        assert details.context == context
        assert details.trace_id == "trace-123"
    
    def test_error_details_serialization(self):
        """Test ErrorDetails serialization."""
        details = ErrorDetails(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Service down"
        )
        
        data = details.dict()
        assert data["code"] == "SERVICE_UNAVAILABLE"
        assert data["message"] == "Service down"
        assert "timestamp" in data


class TestNetraExceptions:
    """Test custom Netra exceptions."""
    
    def test_netra_exception_basic(self):
        """Test basic NetraException."""
        exc = NetraException("Test error")
        
        assert str(exc) == "INTERNAL_ERROR: Test error"
        assert exc.error_details.code == ErrorCode.INTERNAL_ERROR.value
        assert exc.error_details.message == "Test error"
    
    def test_netra_exception_with_code(self):
        """Test NetraException with custom error code."""
        exc = NetraException(
            message="Auth failed",
            code=ErrorCode.AUTHENTICATION_FAILED,
            severity=ErrorSeverity.HIGH
        )
        
        assert exc.error_details.code == ErrorCode.AUTHENTICATION_FAILED.value
        assert exc.error_details.severity == ErrorSeverity.HIGH.value
    
    def test_netra_exception_to_dict(self):
        """Test NetraException serialization."""
        exc = NetraException("Test error", details={"field": "value"})
        data = exc.to_dict()
        
        assert data["code"] == "INTERNAL_ERROR"
        assert data["message"] == "Test error"
        assert data["details"]["field"] == "value"
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Config missing")
        
        assert exc.error_details.code == ErrorCode.CONFIGURATION_ERROR.value
        assert exc.error_details.severity == ErrorSeverity.HIGH.value
        assert "Config missing" in exc.error_details.message
    
    def test_validation_error_with_errors(self):
        """Test ValidationError with validation errors."""
        validation_errors = ["Field required", "Invalid format"]
        exc = ValidationError(validation_errors=validation_errors)
        
        assert exc.error_details.code == ErrorCode.VALIDATION_ERROR.value
        assert exc.error_details.details["validation_errors"] == validation_errors
        assert exc.error_details.user_message == "Please check your input and try again"
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError("Invalid credentials")
        
        assert exc.error_details.code == ErrorCode.AUTHENTICATION_FAILED.value
        assert exc.error_details.severity == ErrorSeverity.HIGH.value
        assert "Invalid credentials" in exc.error_details.message
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        exc = AuthorizationError("Access denied")
        
        assert exc.error_details.code == ErrorCode.AUTHORIZATION_FAILED.value
        assert exc.error_details.user_message == "You don't have permission to perform this action"
    
    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        exc = TokenExpiredError()
        
        assert exc.error_details.code == ErrorCode.TOKEN_EXPIRED.value
        assert "expired" in exc.error_details.message.lower()
    
    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("Connection failed")
        
        assert exc.error_details.code == ErrorCode.DATABASE_QUERY_FAILED.value
        assert exc.error_details.severity == ErrorSeverity.HIGH.value
    
    def test_record_not_found_error(self):
        """Test RecordNotFoundError."""
        exc = RecordNotFoundError("User", "123")
        
        assert exc.error_details.code == ErrorCode.RECORD_NOT_FOUND.value
        assert "User not found (ID: 123)" in exc.error_details.message
        assert exc.error_details.details["resource"] == "User"
        assert exc.error_details.details["identifier"] == "123"
    
    def test_service_error(self):
        """Test ServiceError."""
        exc = ServiceError("payment", "Payment failed")
        
        assert exc.error_details.code == ErrorCode.SERVICE_UNAVAILABLE.value
        assert exc.error_details.details["service"] == "payment"
    
    def test_llm_request_error(self):
        """Test LLMRequestError."""
        exc = LLMRequestError("openai", "gpt-4")
        
        assert exc.error_details.code == ErrorCode.LLM_REQUEST_FAILED.value
        assert exc.error_details.details["provider"] == "openai"
        assert exc.error_details.details["model"] == "gpt-4"
    
    def test_websocket_error(self):
        """Test WebSocketError."""
        exc = WebSocketError("Connection lost")
        
        assert exc.error_details.code == ErrorCode.WEBSOCKET_CONNECTION_FAILED.value
        assert exc.error_details.severity == ErrorSeverity.MEDIUM.value


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def setUp(self):
        self.handler = ErrorHandler()
    
    def test_handle_netra_exception(self):
        """Test handling NetraException."""
        handler = ErrorHandler()
        exc = ValidationError("Invalid input")
        
        response = handler.handle_exception(exc)
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == "VALIDATION_ERROR"
        assert "Invalid input" in response.message
        assert response.error is True
    
    def test_handle_pydantic_validation_error(self):
        """Test handling Pydantic ValidationError."""
        handler = ErrorHandler()
        
        # Create a mock Pydantic validation error
        errors = [
            {"loc": ("field1",), "msg": "field required", "type": "value_error.missing"},
            {"loc": ("field2",), "msg": "invalid format", "type": "value_error.format"}
        ]
        exc = Mock()
        exc.errors.return_value = errors
        exc.__class__ = PydanticValidationError
        
        response = handler._handle_pydantic_validation_error(exc, "trace-123", "req-123")
        
        assert response.error_code == "VALIDATION_ERROR"
        assert response.trace_id == "trace-123"
        assert response.request_id == "req-123"
        assert len(response.details["validation_errors"]) == 2
    
    def test_handle_sqlalchemy_integrity_error(self):
        """Test handling SQLAlchemy IntegrityError."""
        handler = ErrorHandler()
        exc = IntegrityError("statement", "params", "orig")
        
        response = handler._handle_sqlalchemy_error(exc, "trace-123", "req-123")
        
        assert response.error_code == "DB_CONSTRAINT_VIOLATION"
        assert "constraint violation" in response.message.lower()
    
    def test_handle_http_exception(self):
        """Test handling HTTPException."""
        handler = ErrorHandler()
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = handler._handle_http_exception(exc, "trace-123", "req-123")
        
        assert response.error_code == "DB_RECORD_NOT_FOUND"
        assert response.message == "Not found"
        assert response.details["status_code"] == 404
    
    def test_handle_unknown_exception(self):
        """Test handling unknown exception."""
        handler = ErrorHandler()
        exc = ValueError("Unknown error")
        
        response = handler._handle_unknown_exception(exc, "trace-123", "req-123")
        
        assert response.error_code == "INTERNAL_ERROR"
        assert response.message == "An internal server error occurred"
        assert response.details["exception_type"] == "ValueError"
    
    def test_get_http_status_code_mapping(self):
        """Test HTTP status code mapping."""
        handler = ErrorHandler()
        
        assert handler.get_http_status_code(ErrorCode.AUTHENTICATION_FAILED) == 401
        assert handler.get_http_status_code(ErrorCode.AUTHORIZATION_FAILED) == 403
        assert handler.get_http_status_code(ErrorCode.RECORD_NOT_FOUND) == 404
        assert handler.get_http_status_code(ErrorCode.VALIDATION_ERROR) == 400
        assert handler.get_http_status_code(ErrorCode.SERVICE_UNAVAILABLE) == 503
        assert handler.get_http_status_code(ErrorCode.INTERNAL_ERROR) == 500


class TestErrorContext:
    """Test ErrorContext utilities."""
    
    def test_trace_id_context(self):
        """Test trace ID context management."""
        assert ErrorContext.get_trace_id() is None
        
        trace_id = ErrorContext.generate_trace_id()
        assert trace_id is not None
        assert ErrorContext.get_trace_id() == trace_id
        
        new_trace_id = "custom-trace-id"
        ErrorContext.set_trace_id(new_trace_id)
        assert ErrorContext.get_trace_id() == new_trace_id
    
    def test_request_id_context(self):
        """Test request ID context management."""
        request_id = "req-123"
        ErrorContext.set_request_id(request_id)
        assert ErrorContext.get_request_id() == request_id
    
    def test_user_id_context(self):
        """Test user ID context management."""
        user_id = "user-456"
        ErrorContext.set_user_id(user_id)
        assert ErrorContext.get_user_id() == user_id
    
    def test_custom_context(self):
        """Test custom context management."""
        ErrorContext.set_context("custom_key", "custom_value")
        assert ErrorContext.get_context("custom_key") == "custom_value"
        assert ErrorContext.get_context("missing_key", "default") == "default"
    
    def test_get_all_context(self):
        """Test getting all context information."""
        ErrorContext.set_trace_id("trace-123")
        ErrorContext.set_request_id("req-456")
        ErrorContext.set_user_id("user-789")
        ErrorContext.set_context("custom", "value")
        
        context = ErrorContext.get_all_context()
        
        assert context["trace_id"] == "trace-123"
        assert context["request_id"] == "req-456"
        assert context["user_id"] == "user-789"
        assert context["custom"] == "value"
    
    def test_clear_context(self):
        """Test clearing all context."""
        ErrorContext.set_trace_id("trace-123")
        ErrorContext.set_request_id("req-456")
        ErrorContext.set_context("custom", "value")
        
        ErrorContext.clear_context()
        
        assert ErrorContext.get_trace_id() is None
        assert ErrorContext.get_request_id() is None
        assert ErrorContext.get_all_context() == {}
    
    def test_error_context_manager(self):
        """Test ErrorContextManager."""
        with ErrorContextManager(
            trace_id="trace-123",
            request_id="req-456",
            user_id="user-789",
            custom="value"
        ):
            assert ErrorContext.get_trace_id() == "trace-123"
            assert ErrorContext.get_request_id() == "req-456"
            assert ErrorContext.get_user_id() == "user-789"
            assert ErrorContext.get_context("custom") == "value"
        
        # Context should be restored after exiting
        assert ErrorContext.get_trace_id() != "trace-123"
    
    def test_get_enriched_error_context(self):
        """Test getting enriched error context."""
        ErrorContext.set_trace_id("trace-123")
        ErrorContext.set_user_id("user-456")
        
        context = get_enriched_error_context({"additional": "data"})
        
        assert context["trace_id"] == "trace-123"
        assert context["user_id"] == "user-456"
        assert context["additional"] == "data"


class TestErrorHandlerFunctions:
    """Test error handler functions."""
    
    def test_handle_exception_function(self):
        """Test global handle_exception function."""
        exc = ValidationError("Test error")
        response = handle_exception(exc)
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == "VALIDATION_ERROR"
    
    def test_get_http_status_code_function(self):
        """Test global get_http_status_code function."""
        status_code = get_http_status_code(ErrorCode.AUTHENTICATION_FAILED)
        assert status_code == 401
    
    @pytest.mark.asyncio
    async def test_netra_exception_handler(self):
        """Test FastAPI NetraException handler."""
        request = Mock(spec=Request)
        exc = AuthenticationError("Auth failed")
        
        response = await netra_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """Test FastAPI validation exception handler."""
        request = Mock(spec=Request)
        exc = Mock()
        exc.errors.return_value = [{"loc": ("field",), "msg": "required", "type": "value_error"}]
        exc.__class__ = PydanticValidationError
        
        response = await validation_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test FastAPI HTTP exception handler."""
        request = Mock(spec=Request)
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = await http_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test FastAPI general exception handler."""
        request = Mock(spec=Request)
        exc = ValueError("Unknown error")
        
        response = await general_exception_handler(request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500


class TestErrorResponseModel:
    """Test ErrorResponse model."""
    
    def test_error_response_creation(self):
        """Test creating ErrorResponse."""
        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            trace_id="trace-123",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        assert response.error is True
        assert response.error_code == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.trace_id == "trace-123"
    
    def test_error_response_with_details(self):
        """Test ErrorResponse with additional details."""
        details = {"field": "value", "count": 5}
        response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            trace_id="trace-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details
        )
        
        assert response.details == details
    
    def test_error_response_serialization(self):
        """Test ErrorResponse serialization."""
        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            trace_id="trace-123",
            timestamp="2023-01-01T00:00:00"
        )
        
        data = response.dict()
        assert data["error"] is True
        assert data["error_code"] == "TEST_ERROR"
        assert data["trace_id"] == "trace-123"


@pytest.fixture(autouse=True)
def clear_error_context():
    """Fixture to clear error context between tests."""
    ErrorContext.clear_context()
    yield
    ErrorContext.clear_context()