"""Fallback Response Generation Core

This module handles the core logic for generating context-aware fallback responses.
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.fallback_response.content_processor import (
    ContentProcessor,
)
from netra_backend.app.services.fallback_response.diagnostics import DiagnosticsManager
from netra_backend.app.services.fallback_response.models import (
    FailureReason,
    FallbackContext,
)
from netra_backend.app.services.fallback_response.templates import TemplateManager

logger = central_logger.get_logger(__name__)


class ResponseGenerator:
    """Core response generator for fallback responses"""
    
    def __init__(self):
        """Initialize the response generator"""
        self.template_manager = TemplateManager()
        self.diagnostics_manager = DiagnosticsManager()
        self.content_processor = ContentProcessor()
        logger.info("Response Generator initialized")
    
    async def generate_fallback(
        self,
        context: FallbackContext,
        include_diagnostics: bool = True,
        include_recovery: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a context-aware fallback response
        
        Args:
            context: Context for generating the fallback
            include_diagnostics: Whether to include diagnostic tips
            include_recovery: Whether to include recovery suggestions
            
        Returns:
            Dict containing the fallback response and metadata
        """
        try:
            response_text = await self._create_response_text(context)
            diagnostics, recovery_options = self._collect_support_options(context, include_diagnostics, include_recovery)
            response = self._build_response(response_text, context, diagnostics, recovery_options)
            self._log_fallback_generation(context)
            return response
        except Exception as e:
            logger.error(f"Error generating fallback response: {str(e)}")
            return self._get_emergency_fallback(context)
    
    async def _create_response_text(self, context: FallbackContext) -> str:
        """Create the main response text with template and quality feedback"""
        template = self.template_manager.get_template(context.content_type, context.failure_reason, context.retry_count)
        response_text = self.content_processor.populate_template(template, context)
        quality_feedback = self._get_quality_feedback(context)
        if quality_feedback:
            response_text += f"\n\n{quality_feedback}"
        return response_text
    
    def _get_quality_feedback(self, context: FallbackContext) -> Optional[str]:
        """Get quality feedback if available"""
        if not context.quality_metrics:
            return None
        return self.content_processor.generate_quality_feedback(context.quality_metrics)
    
    def _collect_support_options(self, context: FallbackContext, include_diagnostics: bool, include_recovery: bool) -> tuple[List[str], List[Dict[str, str]]]:
        """Collect diagnostic tips and recovery suggestions"""
        diagnostics = self._get_diagnostics(context, include_diagnostics)
        recovery_options = self._get_recovery_options(context, include_recovery)
        return diagnostics, recovery_options
    
    def _get_diagnostics(self, context: FallbackContext, include_diagnostics: bool) -> List[str]:
        """Get diagnostic tips if requested"""
        if not include_diagnostics:
            return []
        return self.diagnostics_manager.get_diagnostic_tips(context.failure_reason)
    
    def _get_recovery_options(self, context: FallbackContext, include_recovery: bool) -> List[Dict[str, str]]:
        """Get recovery suggestions if requested"""
        if not include_recovery:
            return []
        return self.diagnostics_manager.get_recovery_suggestions(context.content_type)
    
    def _log_fallback_generation(self, context: FallbackContext) -> None:
        """Log fallback generation details"""
        logger.info(
            f"Generated fallback for {context.agent_name} - "
            f"Reason: {context.failure_reason.value} - "
            f"Type: {context.content_type.value}"
        )
    
    def _build_response(
        self,
        response_text: str,
        context: FallbackContext,
        diagnostics: List[str],
        recovery_options: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Build the complete response structure"""
        response = {
            "response": response_text,
            "metadata": {
                "is_fallback": True,
                "failure_reason": context.failure_reason.value,
                "content_type": context.content_type.value,
                "agent": context.agent_name,
                "retry_count": context.retry_count,
                "can_retry": self._can_retry(context)
            }
        }
        
        # Add diagnostics if included
        if diagnostics:
            response["diagnostics"] = diagnostics
        
        # Add recovery options if included
        if recovery_options:
            response["recovery_options"] = recovery_options
        
        # Add retry information if applicable
        if context.retry_count > 0:
            response["retry_info"] = self._build_retry_info(context)
        
        return response
    
    def _can_retry(self, context: FallbackContext) -> bool:
        """Determine if the request can be retried"""
        return (
            context.retry_count < 3 and 
            context.failure_reason != FailureReason.RATE_LIMIT
        )
    
    def _build_retry_info(self, context: FallbackContext) -> Dict[str, Any]:
        """Build retry information for the response"""
        next_action = (
            "Consider alternative approach" if context.retry_count >= 2 
            else "Retry with more context"
        )
        
        return {
            "attempts": context.retry_count,
            "max_attempts": 3,
            "next_action": next_action
        }
    
    def _get_emergency_fallback(self, context: FallbackContext) -> Dict[str, Any]:
        """Get emergency fallback when normal fallback generation fails"""
        return {
            "response": (
                f"I encountered an issue processing your request about '{context.attempted_action}'. "
                f"Please try:\n"
                f"1. Simplifying your request\n"
                f"2. Providing more specific details\n"
                f"3. Breaking it into smaller parts\n"
                f"If the issue persists, please contact support."
            ),
            "metadata": {
                "is_fallback": True,
                "is_emergency": True,
                "failure_reason": context.failure_reason.value,
                "agent": context.agent_name
            }
        }
    
    async def generate_batch_fallbacks(
        self,
        contexts: List[FallbackContext]
    ) -> List[Dict[str, Any]]:
        """Generate fallback responses for multiple contexts"""
        responses = []
        for context in contexts:
            response = await self.generate_fallback(context)
            responses.append(response)
        return responses
    
    def get_fallback_for_json_error(
        self,
        agent_name: str,
        raw_response: str,
        expected_format: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fallback for JSON parsing errors"""
        return self.content_processor.create_json_error_fallback(
            agent_name,
            raw_response,
            expected_format
        )