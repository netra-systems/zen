"""Status code mapping utilities."""

from typing import Dict

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from .exceptions import ErrorCode


class StatusCodeMapper:
    """Maps error codes to HTTP status codes."""
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        status_map = self._get_complete_status_map()
        return status_map.get(error_code, HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_complete_status_map(self) -> Dict[ErrorCode, int]:
        """Get complete error code to HTTP status mapping."""
        maps = self._collect_all_status_maps()
        return self._merge_status_maps(maps)
    
    def _collect_all_status_maps(self) -> Dict[str, Dict[ErrorCode, int]]:
        """Collect all error status maps."""
        return {
            'auth': self._get_auth_error_status_map(),
            'db': self._get_db_error_status_map(),
            'validation': self._get_validation_error_status_map(),
            'service': self._get_service_error_status_map(),
            'websocket': self._get_websocket_error_status_map(),
            'file': self._get_file_error_status_map()
        }
    
    def _merge_status_maps(self, maps: Dict[str, Dict[ErrorCode, int]]) -> Dict[ErrorCode, int]:
        """Merge all status maps into one."""
        merged = {}
        for category_map in maps.values():
            merged.update(category_map)
        return merged
    
    def _get_auth_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get authentication/authorization error status mapping."""
        return {
            ErrorCode.AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHORIZATION_FAILED: HTTP_403_FORBIDDEN,
            ErrorCode.TOKEN_EXPIRED: HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID: HTTP_401_UNAUTHORIZED,
        }
    
    def _get_db_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get database error status mapping."""
        return {
            ErrorCode.RECORD_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONNECTION_FAILED: HTTP_503_SERVICE_UNAVAILABLE,
        }
    
    def _get_validation_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get validation error status mapping."""
        return {
            ErrorCode.VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
            ErrorCode.DATA_VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
        }
    
    def _get_service_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get service error status mapping."""
        return {
            ErrorCode.SERVICE_UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_TIMEOUT: HTTP_503_SERVICE_UNAVAILABLE,
        }
    
    def _get_websocket_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get WebSocket error status mapping."""
        return {
            ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
        }
    
    def _get_file_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get file error status mapping."""
        return {
            ErrorCode.FILE_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.FILE_ACCESS_DENIED: HTTP_403_FORBIDDEN,
        }