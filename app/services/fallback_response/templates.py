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
        templates = {}
        self._add_all_templates(templates)
        return templates
    
    def _add_all_templates(self, templates: dict) -> None:
        """Add all template categories to templates dict."""
        templates.update(self._get_optimization_templates())
        templates.update(self._get_data_analysis_templates())
        templates.update(self._get_action_plan_templates())
        templates.update(self._get_report_templates())
        templates.update(self._get_system_templates())
    
    def _get_optimization_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get optimization-related templates."""
        return {
            **self._get_optimization_low_quality_mapping(),
            **self._get_optimization_context_mapping(),
            **self._get_optimization_circular_mapping()
        }
    
    def _get_optimization_low_quality_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get optimization low quality mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY): 
                self._get_optimization_low_quality_templates()}
    
    def _get_optimization_context_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get optimization context mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.CONTEXT_MISSING): 
                self._get_optimization_context_missing_templates()}
    
    def _get_optimization_circular_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get optimization circular mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.CIRCULAR_REASONING): 
                self._get_optimization_circular_templates()}
    
    def _get_data_analysis_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get data analysis related templates."""
        return {
            (ContentType.DATA_ANALYSIS, FailureReason.LOW_QUALITY): 
                self._get_data_analysis_low_quality_templates(),
            (ContentType.DATA_ANALYSIS, FailureReason.PARSING_ERROR): 
                self._get_data_analysis_parsing_templates()
        }
    
    def _get_action_plan_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get action plan related templates."""
        return {
            (ContentType.ACTION_PLAN, FailureReason.LOW_QUALITY): 
                self._get_action_plan_low_quality_templates(),
            (ContentType.ACTION_PLAN, FailureReason.VALIDATION_FAILED): 
                self._get_action_plan_validation_templates()
        }
    
    def _get_report_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get report related templates."""
        return {
            **self._get_report_low_quality_mapping(),
            **self._get_report_generic_mapping(),
            **self._get_triage_mapping()
        }
    
    def _get_report_low_quality_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get report low quality mapping."""
        return {(ContentType.REPORT, FailureReason.LOW_QUALITY): 
                self._get_report_low_quality_templates()}
    
    def _get_report_generic_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get report generic mapping."""
        return {(ContentType.REPORT, FailureReason.GENERIC_CONTENT): 
                self._get_report_generic_templates()}
    
    def _get_triage_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get triage mapping."""
        return {(ContentType.TRIAGE, FailureReason.LOW_QUALITY): 
                self._get_triage_low_quality_templates()}
    
    def _get_system_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get system error and general templates."""
        return {
            **self._get_error_message_mapping(),
            **self._get_timeout_mapping(),
            **self._get_rate_limit_mapping()
        }
    
    def _get_error_message_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get error message mapping."""
        return {(ContentType.ERROR_MESSAGE, FailureReason.LLM_ERROR): 
                self._get_error_message_templates()}
    
    def _get_timeout_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get timeout mapping."""
        return {(ContentType.GENERAL, FailureReason.TIMEOUT): 
                self._get_general_timeout_templates()}
    
    def _get_rate_limit_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get rate limit mapping."""
        return {(ContentType.GENERAL, FailureReason.RATE_LIMIT): 
                self._get_general_rate_limit_templates()}
    
    def _get_optimization_low_quality_templates(self) -> List[str]:
        """Get templates for optimization low quality failures"""
        return [
            self._get_optimization_info_request_template(),
            self._get_optimization_context_template(),
            self._get_optimization_stepwise_template()
        ]
    
    def _get_optimization_context_missing_templates(self) -> List[str]:
        """Get templates for optimization context missing failures"""
        return [
            self._get_optimization_key_info_template(),
            self._get_optimization_setup_template()
        ]
    
    def _get_optimization_circular_templates(self) -> List[str]:
        """Get templates for optimization circular reasoning failures"""
        return [
            self._get_concrete_optimization_template(),
            self._get_practical_optimization_template()
        ]
    
    def _get_data_analysis_low_quality_templates(self) -> List[str]:
        """Get templates for data analysis low quality failures"""
        return [
            self._get_data_analysis_parameters_template(),
            self._get_data_analysis_objectives_template()
        ]
    
    def _get_data_analysis_parsing_templates(self) -> List[str]:
        """Get templates for data analysis parsing failures"""
        return [
            self._get_data_processing_issue_template(),
            self._get_data_parsing_failure_template()
        ]
    
    def _get_action_plan_low_quality_templates(self) -> List[str]:
        """Get templates for action plan low quality failures"""
        return [
            self._get_action_plan_implementation_template(),
            self._get_action_plan_clarification_template()
        ]
    
    def _get_action_plan_implementation_template(self) -> str:
        """Get action plan implementation template."""
        return ("To create an actionable plan for {context}, I need:\n"
                "• Clear objectives and success criteria\n"
                "• Available resources and timeline\n"
                "• Current state and dependencies\n"
                "• Risk tolerance and constraints\n"
                "This enables me to provide a step-by-step implementation guide.")
    
    def _get_action_plan_clarification_template(self) -> str:
        """Get action plan clarification template."""
        return ("The action plan for {context} requires clarification:\n"
                "• What specific outcome are you targeting?\n"
                "• What's your implementation timeline?\n"
                "• What resources are available?\n"
                "• Are there any blockers or dependencies?\n"
                "With these details, I can create a detailed execution roadmap.")
    
    def _get_action_plan_validation_templates(self) -> List[str]:
        """Get templates for action plan validation failures"""
        return [
            self._get_action_plan_quality_template(),
            self._get_action_plan_refinement_template()
        ]
    
    def _get_action_plan_quality_template(self) -> str:
        """Get action plan quality template."""
        return ("The generated action plan for {context} didn't meet quality standards. "
                "Let me gather more information:\n"
                "• What's the primary goal?\n"
                "• What have you tried already?\n"
                "• What specific challenges are you facing?\n"
                "This helps me create a more targeted, practical plan.")
    
    def _get_action_plan_refinement_template(self) -> str:
        """Get action plan refinement template."""
        return ("I need to refine the action plan for {context}. Please specify:\n"
                "• Priority order of tasks\n"
                "• Technical constraints\n"
                "• Team capabilities\n"
                "• Acceptable risk level\n"
                "This ensures the plan is both achievable and valuable.")
    
    def _get_report_low_quality_templates(self) -> List[str]:
        """Get templates for report low quality failures"""
        return [
            self._get_report_comprehensive_template(),
            self._get_report_additional_input_template()
        ]
    
    def _get_report_comprehensive_template(self) -> str:
        """Get report comprehensive template."""
        return ("To generate a comprehensive report on {context}, I need:\n"
                "• Specific metrics to include\n"
                "• Reporting period and scope\n"
                "• Target audience (technical/executive)\n"
                "• Key questions to address\n"
                "This ensures the report provides valuable insights.")
    
    def _get_report_additional_input_template(self) -> str:
        """Get report additional input template."""
        return ("The report for {context} requires additional input:\n"
                "• Data sources to analyze\n"
                "• Comparison baselines\n"
                "• Success metrics\n"
                "• Stakeholder requirements\n"
                "Please provide these for a detailed, actionable report.")
    
    def _get_report_generic_templates(self) -> List[str]:
        """Get templates for report generic content failures"""
        return [
            self._get_report_specific_insights_template(),
            self._get_report_actionable_template()
        ]
    
    def _get_report_specific_insights_template(self) -> str:
        """Get report specific insights template."""
        return ("The initial report for {context} was too generic. To provide specific insights:\n"
                "• Share recent performance data\n"
                "• Highlight areas of concern\n"
                "• Specify desired report sections\n"
                "• Indicate decision points needing data\n"
                "This enables a focused, valuable analysis.")
    
    def _get_report_actionable_template(self) -> str:
        """Get report actionable template."""
        return ("Let me create a more specific report for {context}. I need:\n"
                "• Quantitative data points\n"
                "• Comparison periods\n"
                "• Business impact metrics\n"
                "• Specific recommendations needed\n"
                "This ensures the report drives actionable decisions.")
    
    def _get_triage_low_quality_templates(self) -> List[str]:
        """Get templates for triage low quality failures"""
        return [
            self._get_triage_categorization_template(),
            self._get_triage_context_template()
        ]
    
    def _get_triage_categorization_template(self) -> str:
        """Get triage categorization template."""
        return ("To properly categorize and route your request about {context}, please clarify:\n"
                "• Is this about performance, functionality, or cost?\n"
                "• What system or component is affected?\n"
                "• What's the urgency level?\n"
                "• What outcome are you seeking?\n"
                "This helps me direct you to the right optimization path.")
    
    def _get_triage_context_template(self) -> str:
        """Get triage context template."""
        return ("I need more context to triage {context} effectively:\n"
                "• Primary concern (latency/throughput/accuracy/cost)\n"
                "• Current vs. desired state\n"
                "• Available resources\n"
                "• Timeline constraints\n"
                "This ensures proper prioritization and routing.")
    
    def _get_error_message_templates(self) -> List[str]:
        """Get templates for error message failures"""
        return [
            self._get_system_unavailable_template(),
            self._get_processing_error_template()
        ]
    
    def _get_system_unavailable_template(self) -> str:
        """Get system unavailable template."""
        return ("System temporarily unable to process {context}. "
                "Alternative approach:\n"
                "• Try breaking down the request into smaller parts\n"
                "• Provide more specific parameters\n"
                "• Use our template-based optimization guides\n"
                "Error reference: {error_code}")
    
    def _get_processing_error_template(self) -> str:
        """Get processing error template."""
        return ("Processing error for {context}. Suggested workaround:\n"
                "• Simplify the request\n"
                "• Check input format and data\n"
                "• Try a different optimization approach\n"
                "• Contact support with reference: {error_code}")
    
    def _get_general_timeout_templates(self) -> List[str]:
        """Get templates for general timeout failures"""
        return [
            self._get_analysis_timeout_template(),
            self._get_request_timeout_template()
        ]
    
    def _get_analysis_timeout_template(self) -> str:
        """Get analysis timeout template."""
        return ("The analysis for {context} is taking longer than expected. "
                "You can:\n"
                "• Reduce the scope of analysis\n"
                "• Process in smaller batches\n"
                "• Use our quick optimization templates\n"
                "• Schedule for batch processing")
    
    def _get_request_timeout_template(self) -> str:
        """Get request timeout template."""
        return ("Request timeout for {context}. Options:\n"
                "• Break into smaller requests\n"
                "• Use cached optimization patterns\n"
                "• Try async processing\n"
                "• Adjust complexity parameters")
    
    def _get_general_rate_limit_templates(self) -> List[str]:
        """Get templates for general rate limit failures"""
        return [
            self._get_rate_limit_reached_template(),
            self._get_request_limit_exceeded_template()
        ]
    
    def _get_rate_limit_reached_template(self) -> str:
        """Get rate limit reached template."""
        return ("Rate limit reached while processing {context}. "
                "Please:\n"
                "• Wait {wait_time} before retry\n"
                "• Consider batching requests\n"
                "• Use our optimization templates\n"
                "• Upgrade plan for higher limits")
    
    def _get_request_limit_exceeded_template(self) -> str:
        """Get request limit exceeded template."""
        return ("Request limit exceeded for {context}. Alternatives:\n"
                "• Queue for later processing\n"
                "• Use pre-computed optimizations\n"
                "• Reduce request frequency\n"
                "• Check quota usage dashboard")
    
    def get_template(self, content_type: ContentType, failure_reason: FailureReason, retry_count: int = 0) -> str:
        """Get template for content type and failure reason"""
        templates = self._find_matching_templates(content_type, failure_reason)
        template_index = retry_count % len(templates)
        return templates[template_index]
    
    def _find_matching_templates(self, content_type: ContentType, failure_reason: FailureReason) -> List[str]:
        """Find matching templates for content type and failure reason."""
        key = (content_type, failure_reason)
        if key in self._templates:
            return self._templates[key]
        elif (ContentType.GENERAL, failure_reason) in self._templates:
            return self._templates[(ContentType.GENERAL, failure_reason)]
        return [self._get_generic_template()]
    
    def _get_generic_template(self) -> str:
        """Get a generic fallback template"""
        return self._build_generic_template_content()
    
    def _build_generic_template_content(self) -> str:
        """Build generic template content."""
        intro = "I need more information to provide a valuable response for {context}. Please provide:\n"
        requirements = self._get_generic_requirements()
        conclusion = "This will help me generate actionable recommendations."
        return intro + requirements + conclusion
    
    def _get_generic_requirements(self) -> str:
        """Get generic template requirements."""
        return ("• Specific details about your use case\n"
                "• Current metrics or configuration\n"
                "• Desired outcomes or improvements\n"
                "• Any constraints or requirements\n")
    
    def _get_optimization_info_request_template(self) -> str:
        """Get optimization info request template."""
        return self._build_optimization_info_content()
    
    def _build_optimization_info_content(self) -> str:
        """Build optimization info template content."""
        return ("I need more specific information about your {context} to provide actionable optimization recommendations. "
                "Could you provide:\n"
                "• Current performance metrics (latency, throughput)\n"
                "• Resource constraints (memory, compute)\n"
                "• Target improvements (e.g., 20% latency reduction)\n"
                "This will help me generate specific, measurable optimization strategies.")
    
    def _get_optimization_context_template(self) -> str:
        """Get optimization context template."""
        return self._build_optimization_context_content()
    
    def _build_optimization_context_content(self) -> str:
        """Build optimization context template content."""
        return ("The optimization analysis for {context} requires additional context. "
                "To provide value-driven recommendations, I need:\n"
                "• Baseline performance data\n"
                "• System architecture details\n"
                "• Specific bottlenecks you're experiencing\n"
                "With this information, I can suggest targeted optimizations with expected improvements.")
    
    def _get_optimization_stepwise_template(self) -> str:
        """Get optimization stepwise template."""
        return self._build_optimization_stepwise_content()
    
    def _build_optimization_stepwise_content(self) -> str:
        """Build optimization stepwise template content."""
        intro = "After multiple attempts to optimize {context}, let's try a different approach. Please consider:\n"
        steps = self._get_stepwise_optimization_steps()
        conclusion = "Sometimes a step-by-step approach yields better results."
        return intro + steps + conclusion
    
    def _get_stepwise_optimization_steps(self) -> str:
        """Get stepwise optimization steps."""
        return ("• Breaking the optimization into smaller, more focused tasks\n"
                "• Providing a simplified version of your requirements\n"
                "• Starting with basic performance profiling first\n"
                "• Describing the most critical performance issue only\n")
    
    def _get_optimization_key_info_template(self) -> str:
        """Get optimization key info template."""
        return self._build_optimization_key_info_content()
    
    def _build_optimization_key_info_content(self) -> str:
        """Build optimization key info template content."""
        intro = "To optimize {context} effectively, I need key information:\n"
        requirements = self._get_optimization_key_requirements()
        conclusion = "Please provide these details for targeted optimization recommendations."
        return intro + requirements + conclusion
    
    def _get_optimization_key_requirements(self) -> str:
        """Get optimization key requirements."""
        return ("• Model/system specifications\n"
                "• Current configuration parameters\n"
                "• Performance requirements\n"
                "• Available resources\n")
    
    def _get_optimization_setup_template(self) -> str:
        """Get optimization setup template."""
        return self._build_optimization_setup_content()
    
    def _build_optimization_setup_content(self) -> str:
        """Build optimization setup template content."""
        intro = "Optimization requires understanding your specific setup. For {context}, please share:\n"
        requirements = self._get_optimization_setup_requirements()
        conclusion = "This enables me to provide quantified improvement strategies."
        return intro + requirements + conclusion
    
    def _get_optimization_setup_requirements(self) -> str:
        """Get optimization setup requirements."""
        return ("• Current implementation details\n"
                "• Performance metrics you're tracking\n"
                "• Constraints or limitations\n")
    
    def _get_concrete_optimization_template(self) -> str:
        """Get concrete optimization template."""
        return self._build_concrete_optimization_content()
    
    def _build_concrete_optimization_content(self) -> str:
        """Build concrete optimization template content."""
        return ("Let me provide a more concrete optimization approach for {context}:\n"
                "1. **Measure**: First, profile your current system using tools like [specific profiler]\n"
                "2. **Identify**: Look for bottlenecks in [specific areas]\n"
                "3. **Apply**: Implement specific techniques like [concrete optimization]\n"
                "4. **Verify**: Measure improvements against baseline\n"
                "Would you like me to elaborate on any of these steps?")
    
    def _get_practical_optimization_template(self) -> str:
        """Get practical optimization template."""
        return self._build_practical_optimization_content()
    
    def _build_practical_optimization_content(self) -> str:
        """Build practical optimization template content."""
        return ("I'll be more specific about optimizing {context}. Here's a practical approach:\n"
                "• **Quick win**: [Specific easy optimization]\n"
                "• **Medium effort**: [Specific moderate optimization]\n"
                "• **Major improvement**: [Specific significant optimization]\n"
                "Each includes measurable impact. Which would you like to explore first?")
    
    def _get_data_analysis_parameters_template(self) -> str:
        """Get data analysis parameters template."""
        return self._build_data_analysis_parameters_content()
    
    def _build_data_analysis_parameters_content(self) -> str:
        """Build data analysis parameters template content."""
        return ("The data analysis for {context} needs more specific parameters:\n"
                "• Data volume and format\n"
                "• Key metrics to analyze\n"
                "• Time range or scope\n"
                "• Expected insights or patterns\n"
                "This will enable a focused, valuable analysis.")
    
    def _get_data_analysis_objectives_template(self) -> str:
        """Get data analysis objectives template."""
        return self._build_data_analysis_objectives_content()
    
    def _build_data_analysis_objectives_content(self) -> str:
        """Build data analysis objectives template content."""
        return ("To analyze {context} effectively, please provide:\n"
                "• Sample data or schema\n"
                "• Analysis objectives\n"
                "• Historical context if available\n"
                "• Specific questions to answer\n"
                "This ensures the analysis delivers actionable insights.")
    
    def _get_data_processing_issue_template(self) -> str:
        """Get data processing issue template."""
        return self._build_data_processing_issue_content()
    
    def _build_data_processing_issue_content(self) -> str:
        """Build data processing issue template content."""
        return ("I encountered an issue processing the data for {context}. "
                "This typically occurs with:\n"
                "• Inconsistent data formats\n"
                "• Missing required fields\n"
                "• Encoding issues\n"
                "Could you verify the data format and provide a sample?")
    
    def _get_data_parsing_failure_template(self) -> str:
        """Get data parsing failure template."""
        return self._build_data_parsing_failure_content()
    
    def _build_data_parsing_failure_content(self) -> str:
        """Build data parsing failure template content."""
        return ("Data parsing failed for {context}. Common causes:\n"
                "• Malformed JSON/CSV\n"
                "• Unexpected data types\n"
                "• Schema mismatches\n"
                "Please check the data structure and try again with validated input.")