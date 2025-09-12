"""Core Template Manager for Fallback Response Service

Manages fallback response templates for various content types and failure scenarios.
"""

from typing import Dict, List, Tuple, Any
from netra_backend.app.services.fallback_response.models import FailureReason
from netra_backend.app.services.quality_gate_service import ContentType


class TemplateManager:
    """Manages templates for generating fallback responses."""
    
    def __init__(self):
        """Initialize the template manager with default templates."""
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Initialize default templates for various content types and failure reasons."""
        return {
            (ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY): [
                "The optimization analysis for {context} requires additional refinement. Consider:\n"
                "[U+2022] Reviewing input parameters for completeness\n"
                "[U+2022] Ensuring all constraints are properly defined\n"
                "[U+2022] Validating the objective function",
                
                "Unable to generate high-quality optimization results for {context}. "
                "Please verify the problem formulation and constraints."
            ],
            
            (ContentType.DATA_ANALYSIS, FailureReason.LOW_QUALITY): [
                "The data analysis for {context} needs more specific parameters:\n"
                "[U+2022] Dataset characteristics and size\n"
                "[U+2022] Analysis objectives and key metrics\n"
                "[U+2022] Expected output format",
                
                "Data analysis incomplete for {context}. "
                "Consider providing more context or breaking down the analysis into smaller steps."
            ],
            
            (ContentType.REPORT, FailureReason.LOW_QUALITY): [
                "Report generation for {context} requires clarification:\n"
                "[U+2022] Report scope and intended audience\n"
                "[U+2022] Key metrics to include\n"
                "[U+2022] Preferred format and structure",
                
                "Unable to generate comprehensive report for {context}. "
                "Please specify the reporting requirements more clearly."
            ],
            
            (ContentType.OPTIMIZATION, FailureReason.TIMEOUT): [
                "Optimization process for {context} exceeded time limit. "
                "Consider simplifying constraints or reducing problem complexity.",
                
                "The optimization for {context} is taking longer than expected. "
                "You may want to try with a smaller dataset or relaxed constraints."
            ],
            
            (ContentType.DATA_ANALYSIS, FailureReason.TIMEOUT): [
                "Data analysis for {context} timed out. "
                "Try processing a smaller subset of data or simplifying the analysis.",
                
                "Analysis timeout for {context}. "
                "Consider breaking the analysis into smaller, incremental steps."
            ],
            
            (ContentType.REPORT, FailureReason.TIMEOUT): [
                "Report generation for {context} exceeded time limit. "
                "Try generating a summary report or focusing on key sections.",
                
                "Report timeout for {context}. "
                "Consider generating individual sections separately."
            ],
            
            # Generic fallback templates
            (ContentType.OPTIMIZATION, FailureReason.LLM_ERROR): [
                "An unexpected issue occurred while processing optimization for {context}. "
                "Please review the input and try again."
            ],
            
            (ContentType.DATA_ANALYSIS, FailureReason.LLM_ERROR): [
                "An unexpected issue occurred during data analysis for {context}. "
                "Please verify the data format and try again."
            ],
            
            (ContentType.REPORT, FailureReason.LLM_ERROR): [
                "An unexpected issue occurred while generating the report for {context}. "
                "Please check the input data and try again."
            ]
        }
    
    def get_template(
        self, 
        content_type: ContentType, 
        failure_reason: FailureReason,
        index: int = 0
    ) -> str:
        """Get a specific template for content type and failure reason.
        
        Args:
            content_type: Type of content being generated
            failure_reason: Reason for the failure
            index: Index of the template to retrieve (default: 0)
            
        Returns:
            Template string or default message if not found
        """
        templates = self._templates.get((content_type, failure_reason), [])
        
        if templates and 0 <= index < len(templates):
            return templates[index]
        
        # Return generic fallback if specific template not found
        return self._get_generic_template(content_type, failure_reason)
    
    def get_all_templates(
        self, 
        content_type: ContentType, 
        failure_reason: FailureReason
    ) -> List[str]:
        """Get all templates for content type and failure reason.
        
        Args:
            content_type: Type of content being generated
            failure_reason: Reason for the failure
            
        Returns:
            List of template strings
        """
        templates = self._templates.get((content_type, failure_reason), [])
        
        if not templates:
            # Return generic template as list if no specific templates found
            templates = [self._get_generic_template(content_type, failure_reason)]
        
        return templates
    
    def _get_generic_template(
        self, 
        content_type: ContentType, 
        failure_reason: FailureReason
    ) -> str:
        """Generate a generic fallback template.
        
        Args:
            content_type: Type of content being generated
            failure_reason: Reason for the failure
            
        Returns:
            Generic template string
        """
        content_type_str = content_type.value if hasattr(content_type, 'value') else str(content_type)
        failure_reason_str = failure_reason.value if hasattr(failure_reason, 'value') else str(failure_reason)
        
        return (
            f"Unable to complete {content_type_str} for {{context}} "
            f"due to {failure_reason_str}. Please review the input and try again "
            f"with adjusted parameters."
        )
    
    def add_template(
        self,
        content_type: ContentType,
        failure_reason: FailureReason,
        template: str
    ) -> None:
        """Add a new template for a content type and failure reason.
        
        Args:
            content_type: Type of content being generated
            failure_reason: Reason for the failure
            template: Template string to add
        """
        key = (content_type, failure_reason)
        
        if key not in self._templates:
            self._templates[key] = []
        
        self._templates[key].append(template)
    
    def format_template(self, template: str, **kwargs) -> str:
        """Format a template with provided keyword arguments.
        
        Args:
            template: Template string with placeholders
            **kwargs: Keyword arguments for formatting
            
        Returns:
            Formatted template string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Return template with error indication if formatting fails
            return f"{template} [Formatting error: missing {e}]"
        except Exception:
            # Return original template if any other error occurs
            return template