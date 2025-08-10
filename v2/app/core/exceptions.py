"""Standardized exception hierarchy and error handling patterns for the Netra application."""

import traceback
from typing import Any, Dict, Optional, Union, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class ErrorCode(Enum):
    """Standardized error codes for consistent error classification."""
    
    # General errors (1000-1999)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Authentication errors (2000-2999)
    AUTHENTICATION_FAILED = "AUTH_FAILED"
    AUTHORIZATION_FAILED = "AUTH_UNAUTHORIZED"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    
    # Database errors (3000-3999)
    DATABASE_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "DB_QUERY_FAILED"
    DATABASE_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"
    RECORD_NOT_FOUND = "DB_RECORD_NOT_FOUND"
    RECORD_ALREADY_EXISTS = "DB_RECORD_EXISTS"
    
    # Service errors (4000-4999)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    
    # Agent/LLM errors (5000-5999)
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    LLM_RATE_LIMIT_EXCEEDED = "LLM_RATE_LIMIT_EXCEEDED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    
    # WebSocket errors (6000-6999)
    WEBSOCKET_CONNECTION_FAILED = "WS_CONNECTION_FAILED"
    WEBSOCKET_MESSAGE_INVALID = "WS_MESSAGE_INVALID"
    WEBSOCKET_AUTHENTICATION_FAILED = "WS_AUTH_FAILED"
    
    # File/Data errors (7000-7999)
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"
    DATA_PARSING_ERROR = "DATA_PARSING_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"


class ErrorSeverity(Enum):
    """Error severity levels for logging and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorDetails(BaseModel):
    """Detailed error information for structured error responses."""
    
    code: ErrorCode
    message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    details: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    trace_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


# Base Exceptions

class NetraException(Exception):
    """Base exception class for all Netra application exceptions."""
    
    def __init__(
        self, 
        message: str = None,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        trace_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.error_details = ErrorDetails(
            code=code,
            message=message or "An internal error occurred",
            severity=severity,
            details=details or {},
            user_message=user_message,
            trace_id=trace_id,
            context=context or {}
        )
        super().__init__(self.error_details.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return self.error_details.dict()
    
    def __str__(self) -> str:
        return f"{self.error_details.code.value}: {self.error_details.message}"


# Configuration Exceptions

class ConfigurationError(NetraException):
    """Raised when configuration issues are encountered."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Configuration error occurred",
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ValidationError(NetraException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str = None, validation_errors: List[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if validation_errors:
            details['validation_errors'] = validation_errors
            
        super().__init__(
            message=message or "Data validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            user_message="Please check your input and try again",
            **kwargs
        )


# Authentication Exceptions

class AuthenticationError(NetraException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication failed",
            code=ErrorCode.AUTHENTICATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="Please check your credentials and try again",
            **kwargs
        )


class AuthorizationError(NetraException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Access denied",
            code=ErrorCode.AUTHORIZATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="You don't have permission to perform this action",
            **kwargs
        )


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication token has expired",
            code=ErrorCode.TOKEN_EXPIRED,
            user_message="Your session has expired. Please log in again",
            **kwargs
        )


class TokenInvalidError(AuthenticationError):
    """Raised when authentication token is invalid."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication token is invalid",
            code=ErrorCode.TOKEN_INVALID,
            user_message="Invalid authentication token. Please log in again",
            **kwargs
        )


# Database Exceptions

class DatabaseError(NetraException):
    """Base class for database-related errors."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Database error occurred",
            code=ErrorCode.DATABASE_QUERY_FAILED,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Failed to connect to database",
            code=ErrorCode.DATABASE_CONNECTION_FAILED,
            severity=ErrorSeverity.CRITICAL,
            user_message="Service temporarily unavailable. Please try again later",
            **kwargs
        )


class RecordNotFoundError(DatabaseError):
    """Raised when a requested record is not found."""
    
    def __init__(self, resource: str = None, identifier: Any = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"
            
        super().__init__(
            message=message,
            code=ErrorCode.RECORD_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            details={"resource": resource, "identifier": str(identifier) if identifier else None},
            user_message="The requested item was not found",
            **kwargs
        )


class RecordAlreadyExistsError(DatabaseError):
    """Raised when trying to create a record that already exists."""
    
    def __init__(self, resource: str = None, identifier: Any = None, **kwargs):
        message = f"{resource} already exists"
        if identifier:
            message += f" (ID: {identifier})"
            
        super().__init__(
            message=message,
            code=ErrorCode.RECORD_ALREADY_EXISTS,
            severity=ErrorSeverity.MEDIUM,
            details={"resource": resource, "identifier": str(identifier) if identifier else None},
            user_message="This item already exists",
            **kwargs
        )


class ConstraintViolationError(DatabaseError):
    """Raised when database constraint is violated."""
    
    def __init__(self, constraint: str = None, **kwargs):
        super().__init__(
            message=f"Database constraint violation: {constraint}" if constraint else "Database constraint violation",
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            severity=ErrorSeverity.MEDIUM,
            details={"constraint": constraint},
            user_message="The operation could not be completed due to data constraints",
            **kwargs
        )


# Service Exceptions

class ServiceError(NetraException):
    """Base class for service-related errors."""
    
    def __init__(self, service_name: str = None, message: str = None, **kwargs):
        super().__init__(
            message=message or f"Service error occurred{f' in {service_name}' if service_name else ''}",
            code=ErrorCode.SERVICE_UNAVAILABLE,
            severity=ErrorSeverity.HIGH,
            details={"service": service_name},
            **kwargs
        )


class ServiceTimeoutError(ServiceError):
    """Raised when a service operation times out."""
    
    def __init__(self, service_name: str = None, timeout_seconds: float = None, **kwargs):
        details = {"service": service_name}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
            
        super().__init__(
            service_name=service_name,
            message=f"Service operation timed out{f' after {timeout_seconds}s' if timeout_seconds else ''}",
            code=ErrorCode.SERVICE_TIMEOUT,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="The operation is taking longer than expected. Please try again",
            **kwargs
        )


class ExternalServiceError(ServiceError):
    """Raised when an external service call fails."""
    
    def __init__(self, service_name: str = None, status_code: int = None, **kwargs):
        details = {"service": service_name}
        if status_code:
            details["status_code"] = status_code
            
        super().__init__(
            service_name=service_name,
            message=f"External service call failed{f' (status: {status_code})' if status_code else ''}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=details,
            user_message="An external service is currently unavailable. Please try again later",
            **kwargs
        )


# Agent/LLM Exceptions

class AgentError(NetraException):
    """Base class for agent-related errors."""
    
    def __init__(self, agent_name: str = None, message: str = None, **kwargs):
        super().__init__(
            message=message or f"Agent error occurred{f' in {agent_name}' if agent_name else ''}",
            code=ErrorCode.AGENT_EXECUTION_FAILED,
            severity=ErrorSeverity.HIGH,
            details={"agent": agent_name},
            **kwargs
        )


class LLMRequestError(AgentError):
    """Raised when LLM API request fails."""
    
    def __init__(self, provider: str = None, model: str = None, **kwargs):
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
            
        super().__init__(
            message=f"LLM request failed{f' ({provider}/{model})' if provider and model else ''}",
            code=ErrorCode.LLM_REQUEST_FAILED,
            details=details,
            user_message="AI service is temporarily unavailable. Please try again",
            **kwargs
        )


class LLMRateLimitError(LLMRequestError):
    """Raised when LLM API rate limit is exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
            
        super().__init__(
            message=f"LLM rate limit exceeded{f'. Retry after {retry_after}s' if retry_after else ''}",
            code=ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            details=details,
            user_message="Service is busy. Please wait a moment and try again",
            **kwargs
        )


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""
    
    def __init__(self, agent_name: str = None, timeout_seconds: float = None, **kwargs):
        details = {"agent": agent_name}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
            
        super().__init__(
            agent_name=agent_name,
            message=f"Agent execution timed out{f' after {timeout_seconds}s' if timeout_seconds else ''}",
            code=ErrorCode.AGENT_TIMEOUT,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="The AI operation is taking longer than expected. Please try again",
            **kwargs
        )


# WebSocket Exceptions

class WebSocketError(NetraException):
    """Base class for WebSocket-related errors."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "WebSocket error occurred",
            code=ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection fails."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="WebSocket connection failed",
            code=ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            user_message="Connection failed. Please refresh the page and try again",
            **kwargs
        )


class WebSocketMessageError(WebSocketError):
    """Raised when WebSocket message is invalid."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="Invalid WebSocket message",
            code=ErrorCode.WEBSOCKET_MESSAGE_INVALID,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class WebSocketAuthenticationError(WebSocketError):
    """Raised when WebSocket authentication fails."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="WebSocket authentication failed",
            code=ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="Authentication failed. Please refresh the page and log in again",
            **kwargs
        )


# File/Data Exceptions

class FileError(NetraException):
    """Base class for file-related errors."""
    
    def __init__(self, file_path: str = None, message: str = None, **kwargs):
        super().__init__(
            message=message or f"File error occurred{f': {file_path}' if file_path else ''}",
            details={"file_path": file_path},
            **kwargs
        )


class FileNotFoundError(FileError):
    """Raised when a required file is not found."""
    
    def __init__(self, file_path: str = None, **kwargs):
        super().__init__(
            file_path=file_path,
            message=f"File not found{f': {file_path}' if file_path else ''}",
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="The requested file was not found",
            **kwargs
        )


class FileAccessDeniedError(FileError):
    """Raised when file access is denied."""
    
    def __init__(self, file_path: str = None, **kwargs):
        super().__init__(
            file_path=file_path,
            message=f"File access denied{f': {file_path}' if file_path else ''}",
            code=ErrorCode.FILE_ACCESS_DENIED,
            severity=ErrorSeverity.HIGH,
            user_message="Access to the file is denied",
            **kwargs
        )


class DataParsingError(NetraException):
    """Raised when data parsing fails."""
    
    def __init__(self, data_type: str = None, **kwargs):
        super().__init__(
            message=f"Data parsing error{f' ({data_type})' if data_type else ''}",
            code=ErrorCode.DATA_PARSING_ERROR,
            details={"data_type": data_type},
            user_message="The data format is invalid or corrupted",
            **kwargs
        )


class DataValidationError(ValidationError):
    """Raised when data validation fails."""
    
    def __init__(self, field: str = None, value: Any = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
            
        super().__init__(
            message=f"Data validation error{f' for field {field}' if field else ''}",
            code=ErrorCode.DATA_VALIDATION_ERROR,
            details=details,
            **kwargs
        )