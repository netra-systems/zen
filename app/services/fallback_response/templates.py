"""Fallback Response Templates

This module manages the response templates for different content types and failure reasons.
"""

from typing import Dict, List, Tuple

from app.services.quality_gate_service import ContentType
from .models import FailureReason


class TemplateManager:
    """Manages fallback response templates"""
    
    def __init__(self):
        """Initialize the template manager"""
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Initialize response templates by content type and failure reason"""
        return {
            # Optimization fallbacks
            (ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY): 
                self._get_optimization_low_quality_templates(),
            
            (ContentType.OPTIMIZATION, FailureReason.CONTEXT_MISSING): 
                self._get_optimization_context_missing_templates(),
            
            (ContentType.OPTIMIZATION, FailureReason.CIRCULAR_REASONING): 
                self._get_optimization_circular_templates(),
            
            # Data Analysis fallbacks
            (ContentType.DATA_ANALYSIS, FailureReason.LOW_QUALITY): 
                self._get_data_analysis_low_quality_templates(),
            
            (ContentType.DATA_ANALYSIS, FailureReason.PARSING_ERROR): 
                self._get_data_analysis_parsing_templates(),
            
            # Action Plan fallbacks
            (ContentType.ACTION_PLAN, FailureReason.LOW_QUALITY): 
                self._get_action_plan_low_quality_templates(),
            
            (ContentType.ACTION_PLAN, FailureReason.VALIDATION_FAILED): 
                self._get_action_plan_validation_templates(),
            
            # Report fallbacks
            (ContentType.REPORT, FailureReason.LOW_QUALITY): 
                self._get_report_low_quality_templates(),
            
            (ContentType.REPORT, FailureReason.GENERIC_CONTENT): 
                self._get_report_generic_templates(),
            
            # Triage fallbacks
            (ContentType.TRIAGE, FailureReason.LOW_QUALITY): 
                self._get_triage_low_quality_templates(),
            
            # Error message fallbacks
            (ContentType.ERROR_MESSAGE, FailureReason.LLM_ERROR): 
                self._get_error_message_templates(),
            
            # General fallbacks
            (ContentType.GENERAL, FailureReason.TIMEOUT): 
                self._get_general_timeout_templates(),
            
            (ContentType.GENERAL, FailureReason.RATE_LIMIT): 
                self._get_general_rate_limit_templates()
        }
    
    def _get_optimization_low_quality_templates(self) -> List[str]:
        """Get templates for optimization low quality failures"""
        return [
            "I need more specific information about your {context} to provide actionable optimization recommendations. "
            "Could you provide:\n"
            "• Current performance metrics (latency, throughput)\n"
            "• Resource constraints (memory, compute)\n"
            "• Target improvements (e.g., 20% latency reduction)\n"
            "This will help me generate specific, measurable optimization strategies.",
            
            "The optimization analysis for {context} requires additional context. "
            "To provide value-driven recommendations, I need:\n"
            "• Baseline performance data\n"
            "• System architecture details\n"
            "• Specific bottlenecks you're experiencing\n"
            "With this information, I can suggest targeted optimizations with expected improvements.",
            
            "After multiple attempts to optimize {context}, let's try a different approach. "
            "Please consider:\n"
            "• Breaking the optimization into smaller, more focused tasks\n"
            "• Providing a simplified version of your requirements\n"
            "• Starting with basic performance profiling first\n"
            "• Describing the most critical performance issue only\n"
            "Sometimes a step-by-step approach yields better results."
        ]
    
    def _get_optimization_context_missing_templates(self) -> List[str]:
        """Get templates for optimization context missing failures"""
        return [
            "To optimize {context} effectively, I need key information:\n"
            "• Model/system specifications\n"
            "• Current configuration parameters\n"
            "• Performance requirements\n"
            "• Available resources\n"
            "Please provide these details for targeted optimization recommendations.",
            
            "Optimization requires understanding your specific setup. For {context}, please share:\n"
            "• Current implementation details\n"
            "• Performance metrics you're tracking\n"
            "• Constraints or limitations\n"
            "This enables me to provide quantified improvement strategies."
        ]
    
    def _get_optimization_circular_templates(self) -> List[str]:
        """Get templates for optimization circular reasoning failures"""
        return [
            "Let me provide a more concrete optimization approach for {context}:\n"
            "1. **Measure**: First, profile your current system using tools like [specific profiler]\n"
            "2. **Identify**: Look for bottlenecks in [specific areas]\n"
            "3. **Apply**: Implement specific techniques like [concrete optimization]\n"
            "4. **Verify**: Measure improvements against baseline\n"
            "Would you like me to elaborate on any of these steps?",
            
            "I'll be more specific about optimizing {context}. Here's a practical approach:\n"
            "• **Quick win**: [Specific easy optimization]\n"
            "• **Medium effort**: [Specific moderate optimization]\n"
            "• **Major improvement**: [Specific significant optimization]\n"
            "Each includes measurable impact. Which would you like to explore first?"
        ]
    
    def _get_data_analysis_low_quality_templates(self) -> List[str]:
        """Get templates for data analysis low quality failures"""
        return [
            "The data analysis for {context} needs more specific parameters:\n"
            "• Data volume and format\n"
            "• Key metrics to analyze\n"
            "• Time range or scope\n"
            "• Expected insights or patterns\n"
            "This will enable a focused, valuable analysis.",
            
            "To analyze {context} effectively, please provide:\n"
            "• Sample data or schema\n"
            "• Analysis objectives\n"
            "• Historical context if available\n"
            "• Specific questions to answer\n"
            "This ensures the analysis delivers actionable insights."
        ]
    
    def _get_data_analysis_parsing_templates(self) -> List[str]:
        """Get templates for data analysis parsing failures"""
        return [
            "I encountered an issue processing the data for {context}. "
            "This typically occurs with:\n"
            "• Inconsistent data formats\n"
            "• Missing required fields\n"
            "• Encoding issues\n"
            "Could you verify the data format and provide a sample?",
            
            "Data parsing failed for {context}. Common causes:\n"
            "• Malformed JSON/CSV\n"
            "• Unexpected data types\n"
            "• Schema mismatches\n"
            "Please check the data structure and try again with validated input."
        ]
    
    def _get_action_plan_low_quality_templates(self) -> List[str]:
        """Get templates for action plan low quality failures"""
        return [
            "To create an actionable plan for {context}, I need:\n"
            "• Clear objectives and success criteria\n"
            "• Available resources and timeline\n"
            "• Current state and dependencies\n"
            "• Risk tolerance and constraints\n"
            "This enables me to provide a step-by-step implementation guide.",
            
            "The action plan for {context} requires clarification:\n"
            "• What specific outcome are you targeting?\n"
            "• What's your implementation timeline?\n"
            "• What resources are available?\n"
            "• Are there any blockers or dependencies?\n"
            "With these details, I can create a detailed execution roadmap."
        ]
    
    def _get_action_plan_validation_templates(self) -> List[str]:
        """Get templates for action plan validation failures"""
        return [
            "The generated action plan for {context} didn't meet quality standards. "
            "Let me gather more information:\n"
            "• What's the primary goal?\n"
            "• What have you tried already?\n"
            "• What specific challenges are you facing?\n"
            "This helps me create a more targeted, practical plan.",
            
            "I need to refine the action plan for {context}. Please specify:\n"
            "• Priority order of tasks\n"
            "• Technical constraints\n"
            "• Team capabilities\n"
            "• Acceptable risk level\n"
            "This ensures the plan is both achievable and valuable."
        ]
    
    def _get_report_low_quality_templates(self) -> List[str]:
        """Get templates for report low quality failures"""
        return [
            "To generate a comprehensive report on {context}, I need:\n"
            "• Specific metrics to include\n"
            "• Reporting period and scope\n"
            "• Target audience (technical/executive)\n"
            "• Key questions to address\n"
            "This ensures the report provides valuable insights.",
            
            "The report for {context} requires additional input:\n"
            "• Data sources to analyze\n"
            "• Comparison baselines\n"
            "• Success metrics\n"
            "• Stakeholder requirements\n"
            "Please provide these for a detailed, actionable report."
        ]
    
    def _get_report_generic_templates(self) -> List[str]:
        """Get templates for report generic content failures"""
        return [
            "The initial report for {context} was too generic. To provide specific insights:\n"
            "• Share recent performance data\n"
            "• Highlight areas of concern\n"
            "• Specify desired report sections\n"
            "• Indicate decision points needing data\n"
            "This enables a focused, valuable analysis.",
            
            "Let me create a more specific report for {context}. I need:\n"
            "• Quantitative data points\n"
            "• Comparison periods\n"
            "• Business impact metrics\n"
            "• Specific recommendations needed\n"
            "This ensures the report drives actionable decisions."
        ]
    
    def _get_triage_low_quality_templates(self) -> List[str]:
        """Get templates for triage low quality failures"""
        return [
            "To properly categorize and route your request about {context}, please clarify:\n"
            "• Is this about performance, functionality, or cost?\n"
            "• What system or component is affected?\n"
            "• What's the urgency level?\n"
            "• What outcome are you seeking?\n"
            "This helps me direct you to the right optimization path.",
            
            "I need more context to triage {context} effectively:\n"
            "• Primary concern (latency/throughput/accuracy/cost)\n"
            "• Current vs. desired state\n"
            "• Available resources\n"
            "• Timeline constraints\n"
            "This ensures proper prioritization and routing."
        ]
    
    def _get_error_message_templates(self) -> List[str]:
        """Get templates for error message failures"""
        return [
            "System temporarily unable to process {context}. "
            "Alternative approach:\n"
            "• Try breaking down the request into smaller parts\n"
            "• Provide more specific parameters\n"
            "• Use our template-based optimization guides\n"
            "Error reference: {error_code}",
            
            "Processing error for {context}. Suggested workaround:\n"
            "• Simplify the request\n"
            "• Check input format and data\n"
            "• Try a different optimization approach\n"
            "• Contact support with reference: {error_code}"
        ]
    
    def _get_general_timeout_templates(self) -> List[str]:
        """Get templates for general timeout failures"""
        return [
            "The analysis for {context} is taking longer than expected. "
            "You can:\n"
            "• Reduce the scope of analysis\n"
            "• Process in smaller batches\n"
            "• Use our quick optimization templates\n"
            "• Schedule for batch processing",
            
            "Request timeout for {context}. Options:\n"
            "• Break into smaller requests\n"
            "• Use cached optimization patterns\n"
            "• Try async processing\n"
            "• Adjust complexity parameters"
        ]
    
    def _get_general_rate_limit_templates(self) -> List[str]:
        """Get templates for general rate limit failures"""
        return [
            "Rate limit reached while processing {context}. "
            "Please:\n"
            "• Wait {wait_time} before retry\n"
            "• Consider batching requests\n"
            "• Use our optimization templates\n"
            "• Upgrade plan for higher limits",
            
            "Request limit exceeded for {context}. Alternatives:\n"
            "• Queue for later processing\n"
            "• Use pre-computed optimizations\n"
            "• Reduce request frequency\n"
            "• Check quota usage dashboard"
        ]
    
    def get_template(self, content_type: ContentType, failure_reason: FailureReason, retry_count: int = 0) -> str:
        """Get template for content type and failure reason"""
        # Try specific combination first
        key = (content_type, failure_reason)
        if key in self._templates:
            templates = self._templates[key]
        # Fall back to general templates
        elif (ContentType.GENERAL, failure_reason) in self._templates:
            templates = self._templates[(ContentType.GENERAL, failure_reason)]
        else:
            # Use a generic template
            templates = [self._get_generic_template()]
        
        # Select template based on retry count (cycle through if retrying)
        template_index = retry_count % len(templates)
        return templates[template_index]
    
    def _get_generic_template(self) -> str:
        """Get a generic fallback template"""
        return (
            "I need more information to provide a valuable response for {context}. "
            "Please provide:\n"
            "• Specific details about your use case\n"
            "• Current metrics or configuration\n"
            "• Desired outcomes or improvements\n"
            "• Any constraints or requirements\n"
            "This will help me generate actionable recommendations."
        )