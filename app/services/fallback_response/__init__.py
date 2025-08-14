"""Fallback Response Service Module

Context-aware fallback response generation for AI system failures.
This module provides intelligent, context-aware fallback responses when AI generation
fails or produces low-quality output, replacing generic error messages with helpful alternatives.
"""

from .models import FailureReason, FallbackContext
from .templates import TemplateManager
from .diagnostics import DiagnosticsManager
from .content_processor import ContentProcessor
from .response_generator import ResponseGenerator


class FallbackResponseService:
    """Service for generating context-aware fallback responses"""
    
    def __init__(self):
        """Initialize the fallback response service"""
        self.response_generator = ResponseGenerator()
    
    async def generate_fallback(self, *args, **kwargs):
        """Generate a context-aware fallback response"""
        return await self.response_generator.generate_fallback(*args, **kwargs)
    
    async def generate_batch_fallbacks(self, *args, **kwargs):
        """Generate fallback responses for multiple contexts"""
        return await self.response_generator.generate_batch_fallbacks(*args, **kwargs)
    
    def get_fallback_for_json_error(self, *args, **kwargs):
        """Generate fallback for JSON parsing errors"""
        return self.response_generator.get_fallback_for_json_error(*args, **kwargs)


__all__ = [
    "FallbackResponseService",
    "FailureReason", 
    "FallbackContext",
    "TemplateManager",
    "DiagnosticsManager",
    "ContentProcessor",
    "ResponseGenerator"
]