"""Validation error handling utilities."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError

from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.exceptions import ErrorCode
from netra_backend.app.logging_config import central_logger


class ValidationErrorHandler:
    """Handler for validation errors."""
    
    def __init__(self, logger):
        self._logger = logger
    
    def handle_validation_error(
        self,
        exc: ValidationError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        validation_errors = self._extract_validation_errors(exc)
        self._logger.warning(f"Validation error: {validation_errors}")
        return self._create_validation_response(validation_errors, trace_id, request_id)
    
    def _extract_validation_errors(self, exc: ValidationError) -> list:
        """Extract validation errors from Pydantic exception."""
        validation_errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(f"{field}: {error['msg']}")
        return validation_errors
    
    def _create_validation_response(
        self,
        validation_errors: list,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for validation errors."""
        details = self._create_validation_details(validation_errors)
        return self._build_response(details, trace_id, request_id)
    
    def _create_validation_details(self, validation_errors: list) -> Dict[str, Any]:
        """Create validation error details."""
        return {
            "validation_errors": validation_errors,
            "error_count": len(validation_errors)
        }
    
    def _build_response(self, details: Dict[str, Any], trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Build validation error response."""
        return ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            user_message="Please check your input and try again",
            details=details,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )