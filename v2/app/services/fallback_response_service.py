"""Context-Aware Fallback Response Service

This service provides intelligent, context-aware fallback responses when AI generation
fails or produces low-quality output, replacing generic error messages with helpful alternatives.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import json
import re

from app.logging_config import central_logger
from app.services.quality_gate_service import ContentType, QualityMetrics

logger = central_logger.get_logger(__name__)


class FailureReason(Enum):
    """Reasons for needing a fallback response"""
    LOW_QUALITY = "low_quality"
    PARSING_ERROR = "parsing_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONTEXT_MISSING = "context_missing"
    LLM_ERROR = "llm_error"
    VALIDATION_FAILED = "validation_failed"
    CIRCULAR_REASONING = "circular_reasoning"
    HALLUCINATION_RISK = "hallucination_risk"
    GENERIC_CONTENT = "generic_content"


@dataclass
class FallbackContext:
    """Context for generating fallback response"""
    agent_name: str
    content_type: ContentType
    failure_reason: FailureReason
    user_request: str
    attempted_action: str
    quality_metrics: Optional[QualityMetrics] = None
    error_details: Optional[str] = None
    retry_count: int = 0
    previous_responses: List[str] = None


class FallbackResponseService:
    """Service for generating context-aware fallback responses"""
    
    def __init__(self):
        """Initialize the fallback response service"""
        self.response_templates = self._initialize_templates()
        self.diagnostic_tips = self._initialize_diagnostic_tips()
        self.recovery_suggestions = self._initialize_recovery_suggestions()
        logger.info("Fallback Response Service initialized")
    
    def _initialize_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Initialize response templates by content type and failure reason"""
        return {
            # Optimization fallbacks
            (ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY): [
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
                "With this information, I can suggest targeted optimizations with expected improvements."
            ],
            
            (ContentType.OPTIMIZATION, FailureReason.CONTEXT_MISSING): [
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
            ],
            
            (ContentType.OPTIMIZATION, FailureReason.CIRCULAR_REASONING): [
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
            ],
            
            # Data Analysis fallbacks
            (ContentType.DATA_ANALYSIS, FailureReason.LOW_QUALITY): [
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
            ],
            
            (ContentType.DATA_ANALYSIS, FailureReason.PARSING_ERROR): [
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
            ],
            
            # Action Plan fallbacks
            (ContentType.ACTION_PLAN, FailureReason.LOW_QUALITY): [
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
            ],
            
            (ContentType.ACTION_PLAN, FailureReason.VALIDATION_FAILED): [
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
            ],
            
            # Report fallbacks
            (ContentType.REPORT, FailureReason.LOW_QUALITY): [
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
            ],
            
            (ContentType.REPORT, FailureReason.GENERIC_CONTENT): [
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
            ],
            
            # Triage fallbacks
            (ContentType.TRIAGE, FailureReason.LOW_QUALITY): [
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
            ],
            
            # Error message fallbacks
            (ContentType.ERROR_MESSAGE, FailureReason.LLM_ERROR): [
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
            ],
            
            # General fallbacks for any content type
            (ContentType.GENERAL, FailureReason.TIMEOUT): [
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
            ],
            
            (ContentType.GENERAL, FailureReason.RATE_LIMIT): [
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
        }
    
    def _initialize_diagnostic_tips(self) -> Dict[FailureReason, List[str]]:
        """Initialize diagnostic tips for each failure reason"""
        return {
            FailureReason.LOW_QUALITY: [
                "Tip: Provide specific metrics and constraints for better recommendations",
                "Tip: Include current performance baselines for targeted optimization",
                "Tip: Specify measurable goals (e.g., '20% latency reduction')"
            ],
            FailureReason.PARSING_ERROR: [
                "Tip: Validate JSON structure before submission",
                "Tip: Check for special characters in input data",
                "Tip: Ensure consistent data types across fields"
            ],
            FailureReason.CONTEXT_MISSING: [
                "Tip: Include system specifications in your request",
                "Tip: Provide current configuration details",
                "Tip: Share relevant performance metrics"
            ],
            FailureReason.CIRCULAR_REASONING: [
                "Tip: Ask for specific optimization techniques",
                "Tip: Request quantified recommendations",
                "Tip: Focus on measurable improvements"
            ],
            FailureReason.HALLUCINATION_RISK: [
                "Tip: Verify all metrics against your actual data",
                "Tip: Cross-reference recommendations with documentation",
                "Tip: Start with small-scale testing"
            ],
            FailureReason.GENERIC_CONTENT: [
                "Tip: Provide domain-specific context",
                "Tip: Include technical constraints",
                "Tip: Specify your optimization priorities"
            ]
        }
    
    def _initialize_recovery_suggestions(self) -> Dict[ContentType, List[Dict[str, str]]]:
        """Initialize recovery suggestions by content type"""
        return {
            ContentType.OPTIMIZATION: [
                {
                    "action": "Use Optimization Template",
                    "description": "Start with our proven optimization patterns",
                    "link": "/templates/optimization"
                },
                {
                    "action": "Run Diagnostics",
                    "description": "Analyze your system to identify bottlenecks",
                    "link": "/tools/diagnostics"
                },
                {
                    "action": "Schedule Consultation",
                    "description": "Get expert help for complex optimizations",
                    "link": "/support/consultation"
                }
            ],
            ContentType.DATA_ANALYSIS: [
                {
                    "action": "Data Validation Tool",
                    "description": "Check and fix data format issues",
                    "link": "/tools/data-validator"
                },
                {
                    "action": "Sample Analysis",
                    "description": "Try with a smaller data sample first",
                    "link": "/tools/sample-analysis"
                },
                {
                    "action": "Analysis Templates",
                    "description": "Use pre-built analysis patterns",
                    "link": "/templates/analysis"
                }
            ],
            ContentType.ACTION_PLAN: [
                {
                    "action": "Planning Wizard",
                    "description": "Guided process for action plan creation",
                    "link": "/tools/planning-wizard"
                },
                {
                    "action": "Best Practices",
                    "description": "Review proven implementation patterns",
                    "link": "/docs/best-practices"
                },
                {
                    "action": "Example Plans",
                    "description": "See successful optimization plans",
                    "link": "/examples/action-plans"
                }
            ],
            ContentType.REPORT: [
                {
                    "action": "Report Builder",
                    "description": "Interactive report generation tool",
                    "link": "/tools/report-builder"
                },
                {
                    "action": "Metrics Dashboard",
                    "description": "View real-time metrics and trends",
                    "link": "/dashboard/metrics"
                },
                {
                    "action": "Export Templates",
                    "description": "Download report templates",
                    "link": "/templates/reports"
                }
            ]
        }
    
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
            # Get appropriate template
            template = self._select_template(context)
            
            # Populate template with context
            response_text = self._populate_template(template, context)
            
            # Add quality-specific feedback if available
            if context.quality_metrics:
                quality_feedback = self._generate_quality_feedback(context.quality_metrics)
                response_text += f"\n\n{quality_feedback}"
            
            # Add diagnostic tips
            diagnostics = []
            if include_diagnostics:
                diagnostics = self._get_diagnostic_tips(context.failure_reason)
            
            # Add recovery suggestions
            recovery_options = []
            if include_recovery:
                recovery_options = self._get_recovery_suggestions(context.content_type)
            
            # Build complete response
            response = {
                "response": response_text,
                "metadata": {
                    "is_fallback": True,
                    "failure_reason": context.failure_reason.value,
                    "content_type": context.content_type.value,
                    "agent": context.agent_name,
                    "retry_count": context.retry_count,
                    "can_retry": context.retry_count < 3 and context.failure_reason != FailureReason.RATE_LIMIT
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
                response["retry_info"] = {
                    "attempts": context.retry_count,
                    "max_attempts": 3,
                    "next_action": "Consider alternative approach" if context.retry_count >= 2 else "Retry with more context"
                }
            
            # Log fallback generation
            logger.info(
                f"Generated fallback for {context.agent_name} - "
                f"Reason: {context.failure_reason.value} - "
                f"Type: {context.content_type.value}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating fallback response: {str(e)}")
            # Return a safe default fallback
            return self._get_emergency_fallback(context)
    
    def _select_template(self, context: FallbackContext) -> str:
        """Select the most appropriate template based on context"""
        # Try specific combination first
        key = (context.content_type, context.failure_reason)
        if key in self.response_templates:
            templates = self.response_templates[key]
        # Fall back to general templates
        elif (ContentType.GENERAL, context.failure_reason) in self.response_templates:
            templates = self.response_templates[(ContentType.GENERAL, context.failure_reason)]
        else:
            # Use a generic template
            templates = [self._get_generic_template()]
        
        # Select template based on retry count (cycle through if retrying)
        template_index = context.retry_count % len(templates)
        return templates[template_index]
    
    def _populate_template(self, template: str, context: FallbackContext) -> str:
        """Populate template with context values"""
        # Extract key information from user request
        request_summary = self._summarize_request(context.user_request)
        
        # Prepare substitution values
        substitutions = {
            "{context}": request_summary,
            "{error_code}": context.error_details[:8] if context.error_details else "ERR001",
            "{wait_time}": "30 seconds",
            "{attempted_action}": context.attempted_action
        }
        
        # Perform substitutions
        result = template
        for key, value in substitutions.items():
            result = result.replace(key, value)
        
        return result
    
    def _summarize_request(self, user_request: str) -> str:
        """Create a brief summary of the user request"""
        # Truncate long requests
        if len(user_request) > 50:
            # Try to find a natural break point
            summary = user_request[:47]
            if ' ' in summary:
                summary = summary[:summary.rfind(' ')]
            summary += "..."
        else:
            summary = user_request
        
        return summary
    
    def _generate_quality_feedback(self, metrics: QualityMetrics) -> str:
        """Generate specific feedback based on quality metrics"""
        feedback_parts = []
        
        # Identify the main issues
        if metrics.specificity_score < 0.5:
            feedback_parts.append("📊 **Specificity Issue**: The response lacked specific details and metrics.")
        
        if metrics.actionability_score < 0.5:
            feedback_parts.append("🎯 **Actionability Issue**: The response didn't provide clear action steps.")
        
        if metrics.quantification_score < 0.5:
            feedback_parts.append("📈 **Quantification Issue**: Missing numerical values and measurements.")
        
        if metrics.circular_reasoning_detected:
            feedback_parts.append("🔄 **Logic Issue**: Circular reasoning detected in the response.")
        
        if metrics.generic_phrase_count > 3:
            feedback_parts.append(f"📝 **Generic Content**: Found {metrics.generic_phrase_count} generic phrases.")
        
        if feedback_parts:
            return "**Quality Issues Detected:**\n" + "\n".join(feedback_parts)
        
        return ""
    
    def _get_diagnostic_tips(self, failure_reason: FailureReason) -> List[str]:
        """Get diagnostic tips for the failure reason"""
        if failure_reason in self.diagnostic_tips:
            return self.diagnostic_tips[failure_reason]
        return ["Tip: Provide more specific details about your request"]
    
    def _get_recovery_suggestions(self, content_type: ContentType) -> List[Dict[str, str]]:
        """Get recovery suggestions for the content type"""
        if content_type in self.recovery_suggestions:
            return self.recovery_suggestions[content_type]
        
        # Generic recovery suggestions
        return [
            {
                "action": "Refine Request",
                "description": "Add more specific details and constraints",
                "link": "/help/requests"
            },
            {
                "action": "View Examples",
                "description": "See successful request examples",
                "link": "/examples"
            },
            {
                "action": "Get Help",
                "description": "Contact support for assistance",
                "link": "/support"
            }
        ]
    
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
        # Try to extract useful information from raw response
        useful_parts = self._extract_useful_content(raw_response)
        
        response = {
            "response": (
                f"The {agent_name} encountered a formatting issue. "
                f"Here's what I found:\n\n"
                f"{useful_parts}\n\n"
                f"Let me retry with a more structured approach. "
                f"Please provide any additional context that might help."
            ),
            "partial_data": useful_parts,
            "expected_format": expected_format,
            "metadata": {
                "is_fallback": True,
                "failure_reason": "parsing_error",
                "agent": agent_name,
                "can_retry": True
            }
        }
        
        return response
    
    def _extract_useful_content(self, raw_response: str) -> str:
        """Extract useful content from a malformed response"""
        # Try to find bullet points or numbered lists
        list_pattern = r'[•\-\*\d+\.]\s+(.+)'
        matches = re.findall(list_pattern, raw_response)
        
        if matches:
            return "\n".join(f"• {match}" for match in matches[:5])
        
        # Try to find key-value pairs
        kv_pattern = r'(\w+):\s*([^\n]+)'
        kv_matches = re.findall(kv_pattern, raw_response)
        
        if kv_matches:
            return "\n".join(f"• {k}: {v}" for k, v in kv_matches[:5])
        
        # Return first few sentences as fallback
        sentences = re.split(r'[.!?]+', raw_response)
        useful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
        
        if useful_sentences:
            return "\n".join(f"• {s}" for s in useful_sentences)
        
        return "Unable to extract structured information. Please rephrase your request."