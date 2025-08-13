"""File and data exceptions - compliant with 8-line function limit."""

from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class FileError(NetraException):
    """Base class for file-related exceptions."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "File operation failed",
            code=ErrorCode.FILE_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class FileNotFoundError(FileError):
    """Raised when a file is not found."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "File not found",
            code=ErrorCode.FILE_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            user_message="The requested file was not found",
            **kwargs
        )


class FileAccessDeniedError(FileError):
    """Raised when file access is denied."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "File access denied",
            code=ErrorCode.FILE_ACCESS_DENIED,
            severity=ErrorSeverity.HIGH,
            user_message="Permission denied to access this file",
            **kwargs
        )


class DataParsingError(NetraException):
    """Raised when data parsing fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Failed to parse data",
            code=ErrorCode.DATA_PARSING_ERROR,
            severity=ErrorSeverity.MEDIUM,
            user_message="Invalid data format",
            **kwargs
        )


class DataValidationError(NetraException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Data validation failed",
            code=ErrorCode.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            user_message="The provided data is invalid",
            **kwargs
        )