"""Error response model."""

from typing import Dict, Any, Optional
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