"""Fallback Response Service Module

Context-aware fallback response generation for AI system failures.
This module provides intelligent, context-aware fallback responses when AI generation
fails or produces low-quality output, replacing generic error messages with helpful alternatives.
"""

from typing import Any, Dict, List

from netra_backend.app.services.fallback_response.content_processor import (
    ContentProcessor,
)
from netra_backend.app.services.fallback_response.diagnostics import DiagnosticsManager
from netra_backend.app.services.fallback_response.models import (
    FailureReason,
    FallbackContext,
)
from netra_backend.app.services.fallback_response.response_generator import (
    ResponseGenerator,
)
from netra_backend.app.services.fallback_response.templates import TemplateManager


class FallbackResponseService:
    """Service for generating context-aware fallback responses"""
    
    def __init__(self):
        """Initialize the fallback response service"""
        self.response_generator = ResponseGenerator()
    
    @property
    def response_templates(self):
        """Get response templates from template manager"""
        return self.response_generator.template_manager._templates
    
    @property  
    def diagnostic_tips(self):
        """Get diagnostic tips from diagnostics manager"""
        return self.response_generator.diagnostics_manager._diagnostic_tips
    
    @property
    def recovery_suggestions(self):
        """Get recovery suggestions from diagnostics manager"""
        return self.response_generator.diagnostics_manager._recovery_suggestions
    
    def _format_response(self, template: str, **kwargs) -> str:
        """Format template string with keyword arguments"""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Return original template if formatting fails
            return template
    
    def _get_diagnostic_tips(self, failure_reason):
        """Get diagnostic tips for failure reason"""
        return self.response_generator.diagnostics_manager.get_diagnostic_tips(failure_reason)
    
    def _get_recovery_suggestions(self, content_type, failure_reason=None):
        """Get recovery suggestions for content type"""
        suggestions = self.response_generator.diagnostics_manager.get_recovery_suggestions(content_type)
        # Return descriptions as strings for backward compatibility with tests
        return [s["description"] for s in suggestions]
    
    async def generate_fallback(
        self,
        context: FallbackContext,
        include_diagnostics: bool = True,
        include_recovery: bool = True
    ) -> Dict[str, Any]:
        """Generate a context-aware fallback response"""
        return await self.response_generator.generate_fallback(context, include_diagnostics, include_recovery)
    
    async def generate_batch_fallbacks(self, contexts: List[FallbackContext]) -> List[Dict[str, Any]]:
        """Generate fallback responses for multiple contexts"""
        return await self.response_generator.generate_batch_fallbacks(contexts)
    
    def get_fallback_for_json_error(
        self,
        agent_name: str,
        raw_response: str,
        expected_format: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fallback for JSON parsing errors"""
        return self.response_generator.get_fallback_for_json_error(agent_name, raw_response, expected_format)


__all__ = [
    "FallbackResponseService",
    "FailureReason", 
    "FallbackContext",
    "TemplateManager",
    "DiagnosticsManager",
    "ContentProcessor",
    "ResponseGenerator"
]