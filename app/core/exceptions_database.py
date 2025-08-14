"""Database exceptions - compliant with 8-line function limit."""

from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class DatabaseError(NetraException):
    """Base class for database-related exceptions."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Database operation failed",
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
            **kwargs
        )


class RecordNotFoundError(DatabaseError):
    """Raised when a database record is not found."""
    
    def __init__(self, resource: str = None, identifier: str = None, message: str = None, **kwargs):
        # Support both old and new calling patterns
        if resource is not None and identifier is not None:
            formatted_message = f"{resource} not found (ID: {identifier})"
            details = {"resource": resource, "identifier": str(identifier)}
        else:
            formatted_message = message or "Record not found"
            details = {}
        
        # Call NetraException directly to avoid code conflict
        NetraException.__init__(
            self,
            message=formatted_message,
            code=ErrorCode.RECORD_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            user_message="The requested item was not found",
            details=details,
            **kwargs
        )


class RecordAlreadyExistsError(DatabaseError):
    """Raised when attempting to create a duplicate record."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Record already exists",
            code=ErrorCode.RECORD_ALREADY_EXISTS,
            severity=ErrorSeverity.MEDIUM,
            user_message="This item already exists",
            **kwargs
        )


class DatabaseConstraintError(DatabaseError):
    """Raised when a database constraint is violated."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Database constraint violation",
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )