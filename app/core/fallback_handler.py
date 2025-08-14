"""
Context-Aware Fallback Handler for AI Slop Prevention
Compatibility wrapper for refactored fallback handling module
"""

from app.services.fallback_response.models import FallbackContext
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class FallbackMetadata:
    """Metadata for fallback responses"""
    error_type: str
    attempted_operation: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class FallbackHandler:
    """Handler for fallback responses"""
    
    def __init__(self):
        pass
    
    def generate_fallback(self, context: FallbackContext) -> str:
        """Generate a fallback response"""
        return f"Fallback response for {context.agent_name}"

__all__ = [
    'FallbackHandler',
    'FallbackContext', 
    'FallbackMetadata'
]