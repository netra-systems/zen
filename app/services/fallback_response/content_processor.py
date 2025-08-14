"""Fallback Response Content Processing

This module handles content processing, summarization, and quality feedback generation.
"""

import re
from typing import Dict, Any

from app.services.quality_gate_service import QualityMetrics
from .models import FallbackContext


class ContentProcessor:
    """Processes and analyzes content for fallback responses"""
    
    def populate_template(self, template: str, context: FallbackContext) -> str:
        """Populate template with context values"""
        # Extract key information from user request
        request_summary = self._summarize_request(context.user_request)
        
        # Prepare substitution values
        substitutions = {
            "{context}": request_summary,
            "{error_code}": self._get_error_code(context.error_details),
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
    
    def _get_error_code(self, error_details: str) -> str:
        """Generate error code from error details"""
        if error_details:
            return error_details[:8]
        return "ERR001"
    
    def generate_quality_feedback(self, metrics: QualityMetrics) -> str:
        """Generate specific feedback based on quality metrics"""
        feedback_parts = []
        
        # Identify the main issues
        if metrics.specificity_score < 0.5:
            feedback_parts.append(
                "📊 **Specificity Issue**: The response lacked specific details and metrics."
            )
        
        if metrics.actionability_score < 0.5:
            feedback_parts.append(
                "🎯 **Actionability Issue**: The response didn't provide clear action steps."
            )
        
        if metrics.quantification_score < 0.5:
            feedback_parts.append(
                "📈 **Quantification Issue**: Missing numerical values and measurements."
            )
        
        if metrics.circular_reasoning_detected:
            feedback_parts.append(
                "🔄 **Logic Issue**: Circular reasoning detected in the response."
            )
        
        if metrics.generic_phrase_count > 3:
            feedback_parts.append(
                f"📝 **Generic Content**: Found {metrics.generic_phrase_count} generic phrases."
            )
        
        if feedback_parts:
            return "**Quality Issues Detected:**\n" + "\n".join(feedback_parts)
        
        return ""
    
    def extract_useful_content(self, raw_response: str) -> str:
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
    
    def create_json_error_fallback(
        self,
        agent_name: str,
        raw_response: str,
        expected_format: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fallback for JSON parsing errors"""
        # Try to extract useful information from raw response
        useful_parts = self.extract_useful_content(raw_response)
        
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