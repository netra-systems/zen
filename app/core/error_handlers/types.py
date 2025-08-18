"""Error handler type definitions and response models.

Core types for centralized error handling across the FastAPI application.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    error: bool = True
    error_code: str
    message: str
    user_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    trace_id: str
    timestamp: str
    request_id: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)


class ErrorContext:
    """Context information for error handling."""
    
    def __init__(self, trace_id: str, request_id: Optional[str] = None):
        self.trace_id = trace_id
        self.request_id = request_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def create_base_response(self, error_code: str, message: str) -> Dict[str, Any]:
        """Create base error response dict."""
        return {
            'error_code': error_code,
            'message': message,
            'trace_id': self.trace_id,
            'timestamp': self.timestamp,
            'request_id': self.request_id
        }