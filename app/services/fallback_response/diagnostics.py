"""Fallback Response Diagnostics

This module provides diagnostic tips and recovery suggestions for different failure scenarios.
"""

from typing import Dict, List

from app.services.quality_gate_service import ContentType
from .models import FailureReason


class DiagnosticsManager:
    """Manages diagnostic tips and recovery suggestions"""
    
    def __init__(self):
        """Initialize the diagnostics manager"""
        self._diagnostic_tips = self._initialize_diagnostic_tips()
        self._recovery_suggestions = self._initialize_recovery_suggestions()
    
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
    
    def get_diagnostic_tips(self, failure_reason: FailureReason) -> List[str]:
        """Get diagnostic tips for the failure reason"""
        if failure_reason in self._diagnostic_tips:
            return self._diagnostic_tips[failure_reason]
        return ["Tip: Provide more specific details about your request"]
    
    def get_recovery_suggestions(self, content_type: ContentType) -> List[Dict[str, str]]:
        """Get recovery suggestions for the content type"""
        if content_type in self._recovery_suggestions:
            return self._recovery_suggestions[content_type]
        
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