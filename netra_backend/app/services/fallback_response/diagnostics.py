"""Diagnostics Manager for Fallback Response Service

Provides diagnostic information and recovery suggestions for various failure scenarios.
"""

from typing import Dict, List, Any
from netra_backend.app.services.fallback_response.models import FailureReason


class DiagnosticsManager:
    """Manages diagnostic tips and recovery suggestions for failures."""
    
    def __init__(self):
        """Initialize the diagnostics manager with tips and suggestions."""
        self._diagnostic_tips = {
            FailureReason.LOW_QUALITY: [
                "Response quality score below acceptable threshold",
                "Consider refining the prompt for better clarity",
                "Check if the context provided is sufficient"
            ],
            FailureReason.TIMEOUT: [
                "Request exceeded maximum processing time",
                "System may be experiencing high load",
                "Consider breaking down complex requests"
            ],
            FailureReason.RATE_LIMIT: [
                "API rate limit has been reached",
                "Consider implementing request queuing",
                "Upgrade to a higher tier for increased limits"
            ],
            FailureReason.CONTEXT_MISSING: [
                "Input context exceeds model's maximum token limit",
                "Consider summarizing or chunking the input",
                "Remove unnecessary context information"
            ],
            FailureReason.VALIDATION_FAILED: [
                "Response failed validation checks",
                "Output format doesn't match expected schema",
                "Check data type requirements"
            ],
            FailureReason.LLM_ERROR: [
                "Network connectivity issue detected",
                "Check internet connection stability",
                "Verify API endpoint accessibility"
            ],
            FailureReason.PARSING_ERROR: [
                "Model encountered an internal error",
                "Temporary model unavailability",
                "Consider fallback to alternative model"
            ],
            FailureReason.GENERIC_CONTENT: [
                "Unexpected error occurred",
                "Check system logs for details",
                "Contact support if issue persists"
            ]
        }
        
        self._recovery_suggestions = {
            "optimization": [
                {
                    "description": "Retry with simplified parameters",
                    "action": "retry_simplified"
                },
                {
                    "description": "Use cached results if available",
                    "action": "use_cache"
                },
                {
                    "description": "Switch to faster model variant",
                    "action": "switch_model"
                }
            ],
            "data": [
                {
                    "description": "Validate input data format",
                    "action": "validate_input"
                },
                {
                    "description": "Clean and preprocess data",
                    "action": "preprocess"
                },
                {
                    "description": "Check data source availability",
                    "action": "check_source"
                }
            ],
            "report": [
                {
                    "description": "Generate simplified report",
                    "action": "simplify_report"
                },
                {
                    "description": "Use template-based response",
                    "action": "use_template"
                },
                {
                    "description": "Provide partial results",
                    "action": "partial_results"
                }
            ],
            "default": [
                {
                    "description": "Retry the request",
                    "action": "retry"
                },
                {
                    "description": "Check system status",
                    "action": "check_status"
                },
                {
                    "description": "Contact support",
                    "action": "contact_support"
                }
            ]
        }
    
    def get_diagnostic_tips(self, failure_reason: FailureReason) -> List[str]:
        """Get diagnostic tips for a specific failure reason.
        
        Args:
            failure_reason: The reason for the failure
            
        Returns:
            List of diagnostic tips
        """
        return self._diagnostic_tips.get(failure_reason, self._diagnostic_tips[FailureReason.GENERIC_CONTENT])
    
    def get_recovery_suggestions(self, content_type: str) -> List[Dict[str, str]]:
        """Get recovery suggestions for a content type.
        
        Args:
            content_type: Type of content (optimization, data, report, etc.)
            
        Returns:
            List of recovery suggestion dictionaries
        """
        return self._recovery_suggestions.get(content_type, self._recovery_suggestions["default"])
    
    def analyze_failure(self, failure_reason: FailureReason, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a failure and provide comprehensive diagnostics.
        
        Args:
            failure_reason: The reason for the failure
            context: Additional context about the failure
            
        Returns:
            Dictionary with diagnostic analysis
        """
        return {
            "failure_reason": failure_reason.value,
            "diagnostic_tips": self.get_diagnostic_tips(failure_reason),
            "recovery_suggestions": self.get_recovery_suggestions(
                context.get("content_type", "default")
            ),
            "severity": self._get_severity(failure_reason),
            "retry_recommended": self._should_retry(failure_reason)
        }
    
    def _get_severity(self, failure_reason: FailureReason) -> str:
        """Determine severity level of the failure.
        
        Args:
            failure_reason: The reason for the failure
            
        Returns:
            Severity level (low, medium, high, critical)
        """
        severity_map = {
            FailureReason.LOW_QUALITY: "low",
            FailureReason.TIMEOUT: "medium",
            FailureReason.RATE_LIMIT: "medium",
            FailureReason.CONTEXT_MISSING: "medium",
            FailureReason.VALIDATION_FAILED: "low",
            FailureReason.LLM_ERROR: "high",
            FailureReason.PARSING_ERROR: "critical",
            FailureReason.GENERIC_CONTENT: "high",
            FailureReason.HALLUCINATION_RISK: "critical",
            FailureReason.CIRCULAR_REASONING: "high"
        }
        return severity_map.get(failure_reason, "medium")
    
    def _should_retry(self, failure_reason: FailureReason) -> bool:
        """Determine if retry is recommended for the failure.
        
        Args:
            failure_reason: The reason for the failure
            
        Returns:
            True if retry is recommended, False otherwise
        """
        retry_recommended = {
            FailureReason.LOW_QUALITY: False,
            FailureReason.TIMEOUT: True,
            FailureReason.RATE_LIMIT: False,
            FailureReason.CONTEXT_MISSING: False,
            FailureReason.VALIDATION_FAILED: False,
            FailureReason.LLM_ERROR: True,
            FailureReason.PARSING_ERROR: True,
            FailureReason.GENERIC_CONTENT: True,
            FailureReason.HALLUCINATION_RISK: False,
            FailureReason.CIRCULAR_REASONING: False
        }
        return retry_recommended.get(failure_reason, False)