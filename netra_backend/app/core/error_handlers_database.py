"""Database error handling utilities."""

from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from netra_backend.app.core.exceptions import ErrorCode
from netra_backend.app.core.error_response import ErrorResponse


class DatabaseErrorHandler:
    """Handler for database errors."""
    
    def __init__(self, logger):
        self._logger = logger
    
    def handle_database_error(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle SQLAlchemy database errors."""
        if isinstance(exc, IntegrityError):
            return self._handle_integrity_error(exc, trace_id, request_id)
        return self._handle_general_db_error(exc, trace_id, request_id)
    
    def _handle_integrity_error(
        self,
        exc: IntegrityError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle database integrity constraint violations."""
        self._logger.warning(f"Database integrity error: {exc}")
        return self._create_integrity_error_response(trace_id, request_id)
    
    def _handle_general_db_error(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle general SQLAlchemy database errors."""
        self._logger.error(f"Database error: {str(exc)}", exc_info=True)
        return self._create_general_db_error_response(exc, trace_id, request_id)
    
    def _create_integrity_error_response(self, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Create integrity error response."""
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value,
            message="Database constraint violation",
            user_message="The operation could not be completed due to data constraints",
            details={"error_type": "constraint_violation"},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _create_general_db_error_response(self, exc: SQLAlchemyError, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Create general database error response."""
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_QUERY_FAILED.value,
            message="Database operation failed",
            user_message="A database error occurred. Please try again",
            details={"error_type": type(exc).__name__},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )