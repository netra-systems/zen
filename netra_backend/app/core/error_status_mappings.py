"""HTTP status code mappings for error codes."""

from typing import Dict

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from netra_backend.app.core.exceptions import ErrorCode


class ErrorStatusMapper:
    """Maps error codes to HTTP status codes."""
    
    def __init__(self):
        self._status_map = self._build_complete_status_map()
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Get HTTP status code for error code."""
        return self._status_map.get(error_code, HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _build_complete_status_map(self) -> Dict[ErrorCode, int]:
        """Build complete error code to status code mapping."""
        all_maps = self._collect_error_status_maps()
        return self._merge_status_maps(all_maps)
    
    def _collect_error_status_maps(self) -> Dict[str, Dict[ErrorCode, int]]:
        """Collect all error status mapping categories."""
        return {
            "auth": self._get_auth_error_status_map(),
            "db": self._get_db_error_status_map(),
            "validation": self._get_validation_error_status_map(),
            "service": self._get_service_error_status_map(),
            "websocket": self._get_websocket_error_status_map(),
            "file": self._get_file_error_status_map()
        }
    
    def _merge_status_maps(self, maps: Dict[str, Dict]) -> Dict[ErrorCode, int]:
        """Merge all status maps into single mapping."""
        merged = {}
        for category_map in maps.values():
            merged.update(category_map)
        return merged
    
    def _get_auth_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get authentication/authorization error status mappings."""
        return {
            ErrorCode.AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_EXPIRED: HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID: HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHORIZATION_FAILED: HTTP_403_FORBIDDEN,
        }
    
    def _get_db_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get database error status mappings."""
        return {
            ErrorCode.DATABASE_CONNECTION_ERROR: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.RECORD_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS: HTTP_409_CONFLICT,
            ErrorCode.CONSTRAINT_VIOLATION: HTTP_409_CONFLICT,
        }
    
    def _get_validation_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get validation error status mappings."""
        return {
            ErrorCode.VALIDATION_ERROR: HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.INVALID_INPUT: HTTP_400_BAD_REQUEST,
        }
    
    def _get_service_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get service error status mappings."""
        return {
            ErrorCode.SERVICE_TIMEOUT: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.INTERNAL_ERROR: HTTP_500_INTERNAL_SERVER_ERROR,
        }
    
    def _get_websocket_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get WebSocket error status mappings."""
        return {
            ErrorCode.WEBSOCKET_CONNECTION_ERROR: HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.WEBSOCKET_MESSAGE_ERROR: HTTP_400_BAD_REQUEST,
        }
    
    def _get_file_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get file operation error status mappings."""
        return {
            ErrorCode.FILE_ACCESS_DENIED: HTTP_403_FORBIDDEN,
        }


# Global mapper instance
_status_mapper = ErrorStatusMapper()


def get_http_status_code(error_code: ErrorCode) -> int:
    """Get HTTP status code for error code."""
    return _status_mapper.get_http_status_code(error_code)
