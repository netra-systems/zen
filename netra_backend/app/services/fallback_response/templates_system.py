"""System Templates - Templates for system errors, timeouts, and general failures.

This module provides templates for system-related errors and general fallback
scenarios with 25-line function compliance.
"""

from typing import Dict, List, Tuple

from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.app.services.fallback_response.models import FailureReason


class SystemTemplates:
    """System error and general template provider."""
    
    def get_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get all system templates."""
        return {
            **self._get_error_mapping(),
            **self._get_timeout_mapping(),
            **self._get_rate_limit_mapping()
        }
    
    def _get_error_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get error message templates mapping."""
        return {(ContentType.ERROR_MESSAGE, FailureReason.LLM_ERROR): 
                self._get_error_templates()}
    
    def _get_timeout_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get timeout templates mapping."""
        return {(ContentType.GENERAL, FailureReason.TIMEOUT): 
                self._get_timeout_templates()}
    
    def _get_rate_limit_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get rate limit templates mapping."""
        return {(ContentType.GENERAL, FailureReason.RATE_LIMIT): 
                self._get_rate_limit_templates()}
    
    def _get_error_templates(self) -> List[str]:
        """Get templates for error message failures."""
        return [
            self._get_system_unavailable_template(),
            self._get_processing_error_template()
        ]
    
    def _get_timeout_templates(self) -> List[str]:
        """Get templates for general timeout failures."""
        return [
            self._get_analysis_timeout_template(),
            self._get_request_timeout_template()
        ]
    
    def _get_rate_limit_templates(self) -> List[str]:
        """Get templates for general rate limit failures."""
        return [
            self._get_rate_limit_reached_template(),
            self._get_request_limit_exceeded_template()
        ]
    
    def _get_system_unavailable_template(self) -> str:
        """Get system unavailable template."""
        intro = "System temporarily unable to process {context}."
        approach = "Alternative approach:"
        options = self._build_system_options()
        reference = "Error reference: {error_code}"
        return f"{intro} {approach}\n{options}{reference}"
    
    def _build_system_options(self) -> str:
        """Build system unavailable options."""
        return ("• Try breaking down the request into smaller parts\n"
                "• Provide more specific parameters\n"
                "• Use our template-based optimization guides\n")
    
    def _get_processing_error_template(self) -> str:
        """Get processing error template."""
        intro = "Processing error for {context}."
        workaround = "Suggested workaround:"
        options = self._build_processing_options()
        reference = "• Contact support with reference: {error_code}"
        return f"{intro} {workaround}\n{options}{reference}"
    
    def _build_processing_options(self) -> str:
        """Build processing error options."""
        return ("• Simplify the request\n"
                "• Check input format and data\n"
                "• Try a different optimization approach\n")
    
    def _get_analysis_timeout_template(self) -> str:
        """Get analysis timeout template."""
        intro = "The analysis for {context} is taking longer than expected."
        options = "You can:"
        actions = self._build_analysis_actions()
        return f"{intro} {options}\n{actions}"
    
    def _build_analysis_actions(self) -> str:
        """Build analysis timeout actions."""
        return ("• Reduce the scope of analysis\n"
                "• Process in smaller batches\n"
                "• Use our quick optimization templates\n"
                "• Schedule for batch processing")
    
    def _get_request_timeout_template(self) -> str:
        """Get request timeout template."""
        intro = "Request timeout for {context}."
        options = "Options:"
        actions = self._build_request_actions()
        return f"{intro} {options}\n{actions}"
    
    def _build_request_actions(self) -> str:
        """Build request timeout actions."""
        return ("• Break into smaller requests\n"
                "• Use cached optimization patterns\n"
                "• Try async processing\n"
                "• Adjust complexity parameters")
    
    def _get_rate_limit_reached_template(self) -> str:
        """Get rate limit reached template."""
        intro = "Rate limit reached while processing {context}."
        request = "Please:"
        actions = self._build_rate_limit_actions()
        return f"{intro} {request}\n{actions}"
    
    def _build_rate_limit_actions(self) -> str:
        """Build rate limit actions."""
        return ("• Wait {wait_time} before retry\n"
                "• Consider batching requests\n"
                "• Use our optimization templates\n"
                "• Upgrade plan for higher limits")
    
    def _get_request_limit_exceeded_template(self) -> str:
        """Get request limit exceeded template."""
        intro = "Request limit exceeded for {context}."
        alternatives = "Alternatives:"
        actions = self._build_limit_actions()
        return f"{intro} {alternatives}\n{actions}"
    
    def _build_limit_actions(self) -> str:
        """Build request limit actions."""
        return ("• Queue for later processing\n"
                "• Use pre-computed optimizations\n"
                "• Reduce request frequency\n"
                "• Check quota usage dashboard")
    
    def get_generic_template(self) -> str:
        """Get a generic fallback template."""
        intro = "I need more information to provide a valuable response for {context}."
        request = "Please provide:"
        requirements = self._build_generic_requirements()
        conclusion = "This will help me generate actionable recommendations."
        return f"{intro} {request}\n{requirements}{conclusion}"
    
    def _build_generic_requirements(self) -> str:
        """Build generic template requirements."""
        return ("• Specific details about your use case\n"
                "• Current metrics or configuration\n"
                "• Desired outcomes or improvements\n"
                "• Any constraints or requirements\n")