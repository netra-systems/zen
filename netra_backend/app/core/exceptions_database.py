"""Database exceptions - compliant with 25-line function limit."""

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException

class DatabaseError(NetraException):
    """Base class for database-related exceptions."""
    
    def __init__(self, message: str = None, query: str = None, **kwargs):
        from netra_backend.app.schemas.core_enums import ErrorCategory
        
        self.query = query
        self._category = ErrorCategory.DATABASE
        
        super().__init__(
            message=message or "Database operation failed",
            code=ErrorCode.DATABASE_QUERY_FAILED,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
    
    @property
    def message(self):
        """Get error message."""
        return self.error_details.message
    
    @property
    def category(self):
        """Get error category."""
        return self._category


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
        formatted_message, details = self._build_record_info(resource, identifier, message)
        NetraException.__init__(
            self, message=formatted_message, code=ErrorCode.RECORD_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM, user_message="The requested item was not found",
            details=details, **kwargs
        )
    
    def _build_record_info(self, resource: str, identifier: str, message: str) -> tuple:
        """Build record info for not found errors."""
        if resource is not None and identifier is not None:
            return f"{resource} not found (ID: {identifier})", {"resource": resource, "identifier": str(identifier)}
        return message or "Record not found", {}


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