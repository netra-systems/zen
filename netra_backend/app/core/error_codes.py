"""Error codes and severity levels - compliant with 25-line function limit."""

from enum import Enum


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
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    
    # Database errors (3000-3999)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "DB_QUERY_FAILED"
    DATABASE_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"
    RECORD_NOT_FOUND = "DB_RECORD_NOT_FOUND"
    RECORD_ALREADY_EXISTS = "DB_RECORD_EXISTS"
    
    # Service errors (4000-4999)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    
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


class ErrorCodeMap:
    """Maps error codes to severity levels and HTTP status codes."""
    
    _ERROR_SEVERITY_MAP = {
        # General errors
        ErrorCode.INTERNAL_ERROR: ErrorSeverity.CRITICAL,
        ErrorCode.CONFIGURATION_ERROR: ErrorSeverity.HIGH,
        ErrorCode.VALIDATION_ERROR: ErrorSeverity.MEDIUM,
        
        # Authentication errors
        ErrorCode.AUTHENTICATION_FAILED: ErrorSeverity.HIGH,
        ErrorCode.AUTHORIZATION_FAILED: ErrorSeverity.HIGH,
        ErrorCode.TOKEN_EXPIRED: ErrorSeverity.MEDIUM,
        ErrorCode.TOKEN_INVALID: ErrorSeverity.MEDIUM,
        ErrorCode.SECURITY_VIOLATION: ErrorSeverity.CRITICAL,
        
        # Database errors
        ErrorCode.DATABASE_ERROR: ErrorSeverity.CRITICAL,
        ErrorCode.DATABASE_CONNECTION_FAILED: ErrorSeverity.CRITICAL,
        ErrorCode.DATABASE_QUERY_FAILED: ErrorSeverity.HIGH,
        ErrorCode.DATABASE_CONSTRAINT_VIOLATION: ErrorSeverity.MEDIUM,
        ErrorCode.RECORD_NOT_FOUND: ErrorSeverity.LOW,
        ErrorCode.RECORD_ALREADY_EXISTS: ErrorSeverity.MEDIUM,
        
        # Service errors
        ErrorCode.SERVICE_UNAVAILABLE: ErrorSeverity.HIGH,
        ErrorCode.SERVICE_TIMEOUT: ErrorSeverity.MEDIUM,
        ErrorCode.EXTERNAL_SERVICE_ERROR: ErrorSeverity.MEDIUM,
        ErrorCode.HTTP_ERROR: ErrorSeverity.MEDIUM,
        
        # Agent/LLM errors
        ErrorCode.AGENT_EXECUTION_FAILED: ErrorSeverity.HIGH,
        ErrorCode.LLM_REQUEST_FAILED: ErrorSeverity.MEDIUM,
        ErrorCode.LLM_RATE_LIMIT_EXCEEDED: ErrorSeverity.MEDIUM,
        ErrorCode.AGENT_TIMEOUT: ErrorSeverity.MEDIUM,
        
        # WebSocket errors
        ErrorCode.WEBSOCKET_CONNECTION_FAILED: ErrorSeverity.MEDIUM,
        ErrorCode.WEBSOCKET_MESSAGE_INVALID: ErrorSeverity.LOW,
        ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED: ErrorSeverity.HIGH,
        
        # File/Data errors
        ErrorCode.FILE_NOT_FOUND: ErrorSeverity.LOW,
        ErrorCode.FILE_ACCESS_DENIED: ErrorSeverity.MEDIUM,
        ErrorCode.DATA_PARSING_ERROR: ErrorSeverity.MEDIUM,
        ErrorCode.DATA_VALIDATION_ERROR: ErrorSeverity.MEDIUM,
    }
    
    @classmethod
    def get_severity(cls, error_code: ErrorCode) -> ErrorSeverity:
        """Get severity level for an error code."""
        return cls._ERROR_SEVERITY_MAP.get(error_code, ErrorSeverity.MEDIUM)