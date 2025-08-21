"""HTTP error handling utilities."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.exceptions import ErrorCode


class HttpErrorHandler:
    """Handler for HTTP errors."""
    
    def __init__(self, logger):
        self._logger = logger
    
    def handle_http_error(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle FastAPI HTTP exceptions."""
        error_code = self._map_http_status_to_error_code(exc.status_code)
        self._logger.warning(f"HTTP exception {exc.status_code}: {exc.detail}")
        return self._create_http_error_response(exc, error_code, trace_id, request_id)
    
    def _map_http_status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to internal error codes."""
        status_mapping = self._get_status_mapping()
        return status_mapping.get(status_code, ErrorCode.INTERNAL_ERROR)
    
    def _get_status_mapping(self) -> dict:
        """Get HTTP status code mapping."""
        return {
            HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_FAILED,
            HTTP_403_FORBIDDEN: ErrorCode.AUTHORIZATION_FAILED,
            HTTP_404_NOT_FOUND: ErrorCode.RECORD_NOT_FOUND,
            HTTP_409_CONFLICT: ErrorCode.RECORD_ALREADY_EXISTS,
            HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
        }
    
    def _create_http_error_response(
        self,
        exc: HTTPException,
        error_code: ErrorCode,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for HTTP exceptions."""
        details = self._build_http_details(exc)
        return self._build_http_response(exc, error_code, details, trace_id, request_id)
    
    def _build_http_details(self, exc: HTTPException) -> dict:
        """Build details for HTTP error."""
        return {
            "status_code": exc.status_code,
            "headers": dict(exc.headers) if exc.headers else None
        }
    
    def _build_http_response(self, exc: HTTPException, error_code: ErrorCode, details: dict, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Build HTTP error response."""
        return ErrorResponse(
            error_code=error_code.value,
            message=str(exc.detail),
            user_message=str(exc.detail),
            details=details,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )