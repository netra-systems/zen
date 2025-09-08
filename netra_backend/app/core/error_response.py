"""Error response model."""

from typing import Any, Dict, Optional, List

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
    
    # Debug fields - ONLY included in non-production environments for security
    line_number: Optional[int] = None
    source_file: Optional[str] = None
    stack_trace: Optional[List[str]] = None
    debug_info: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)