"""
Context-Aware Fallback Handler for AI Slop Prevention
Compatibility wrapper for refactored fallback handling module
"""

from netra_backend.app.services.fallback_response.models import FallbackContext
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
        """Initialize the FallbackHandler with default templates."""
        self.fallback_templates = {
            "agent_error": "I encountered an issue while processing your request for {agent_name}. Please try again or contact support if the issue persists.",
            "timeout": "The operation timed out for {agent_name}. Please try again with a simpler request.",
            "validation_error": "There was a validation error in your request to {agent_name}. Please check your input and try again.",
            "default": "I'm unable to process your request for {agent_name} at the moment. Please try again later."
        }
    
    def generate_fallback(self, context: FallbackContext) -> str:
        """Generate a fallback response based on context."""
        error_type = getattr(context, 'error_type', 'default')
        template = self.fallback_templates.get(error_type, self.fallback_templates['default'])
        
        return template.format(
            agent_name=getattr(context, 'agent_name', 'the system'),
            error_type=error_type
        )

__all__ = [
    'FallbackHandler',
    'FallbackContext', 
    'FallbackMetadata'
]