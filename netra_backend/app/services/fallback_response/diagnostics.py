"""Fallback Response Diagnostics

This module provides diagnostic tips and recovery suggestions for different failure scenarios.
"""

from typing import Dict, List

from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.app.services.apex_optimizer_agent.models import FailureReason


class DiagnosticsManager:
    """Manages diagnostic tips and recovery suggestions"""
    
    def __init__(self):
        """Initialize the diagnostics manager"""
        self._diagnostic_tips = self._initialize_diagnostic_tips()
        self._recovery_suggestions = self._initialize_recovery_suggestions()
    
    def _initialize_diagnostic_tips(self) -> Dict[FailureReason, List[str]]:
        """Initialize diagnostic tips for each failure reason"""
        return {
            FailureReason.LOW_QUALITY: self._get_low_quality_tips(),
            FailureReason.PARSING_ERROR: self._get_parsing_error_tips(),
            FailureReason.CONTEXT_MISSING: self._get_context_missing_tips(),
            FailureReason.CIRCULAR_REASONING: self._get_circular_reasoning_tips(),
            FailureReason.HALLUCINATION_RISK: self._get_hallucination_risk_tips(),
            FailureReason.GENERIC_CONTENT: self._get_generic_content_tips()
        }
    
    def _get_low_quality_tips(self) -> List[str]:
        """Get diagnostic tips for low quality failures"""
        return [
            "Tip: Provide specific metrics and constraints for better recommendations",
            "Tip: Include current performance baselines for targeted optimization",
            "Tip: Specify measurable goals (e.g., '20% latency reduction')"
        ]
    
    def _get_parsing_error_tips(self) -> List[str]:
        """Get diagnostic tips for parsing error failures"""
        return [
            "Tip: Validate JSON structure before submission",
            "Tip: Check for special characters in input data",
            "Tip: Ensure consistent data types across fields"
        ]
    
    def _get_context_missing_tips(self) -> List[str]:
        """Get diagnostic tips for context missing failures"""
        return [
            "Tip: Include system specifications in your request",
            "Tip: Provide current configuration details",
            "Tip: Share relevant performance metrics"
        ]
    
    def _get_circular_reasoning_tips(self) -> List[str]:
        """Get diagnostic tips for circular reasoning failures"""
        return [
            "Tip: Ask for specific optimization techniques",
            "Tip: Request quantified recommendations",
            "Tip: Focus on measurable improvements"
        ]
    
    def _get_hallucination_risk_tips(self) -> List[str]:
        """Get diagnostic tips for hallucination risk failures"""
        return [
            "Tip: Verify all metrics against your actual data",
            "Tip: Cross-reference recommendations with documentation",
            "Tip: Start with small-scale testing"
        ]
    
    def _get_generic_content_tips(self) -> List[str]:
        """Get diagnostic tips for generic content failures"""
        return [
            "Tip: Provide domain-specific context",
            "Tip: Include technical constraints",
            "Tip: Specify your optimization priorities"
        ]
    
    def _initialize_recovery_suggestions(self) -> Dict[ContentType, List[Dict[str, str]]]:
        """Initialize recovery suggestions by content type"""
        return {
            ContentType.OPTIMIZATION: self._create_optimization_suggestions(),
            ContentType.DATA_ANALYSIS: self._create_data_analysis_suggestions(),
            ContentType.ACTION_PLAN: self._create_action_plan_suggestions(),
            ContentType.REPORT: self._create_report_suggestions()
        }
    
    def _create_optimization_suggestions(self) -> List[Dict[str, str]]:
        """Create recovery suggestions for optimization content"""
        return [
            self._create_suggestion("Use Optimization Template", "Provide specific optimization patterns and metrics", "/templates/optimization"),
            self._create_suggestion("Run Diagnostics", "Analyze your system to identify specific bottlenecks", "/tools/diagnostics"),
            self._create_suggestion("Schedule Consultation", "Get expert help with specific optimization requirements", "/support/consultation")
        ]
    
    def _create_data_analysis_suggestions(self) -> List[Dict[str, str]]:
        """Create recovery suggestions for data analysis content"""
        return [
            self._create_suggestion("Data Validation Tool", "Check and fix data format issues", "/tools/data-validator"),
            self._create_suggestion("Sample Analysis", "Try with a smaller data sample first", "/tools/sample-analysis"),
            self._create_suggestion("Analysis Templates", "Use pre-built analysis patterns", "/templates/analysis")
        ]
    
    def _create_action_plan_suggestions(self) -> List[Dict[str, str]]:
        """Create recovery suggestions for action plan content"""
        return [
            self._create_suggestion("Planning Wizard", "Guided process for action plan creation", "/tools/planning-wizard"),
            self._create_suggestion("Best Practices", "Review proven implementation patterns", "/docs/best-practices"),
            self._create_suggestion("Example Plans", "See successful optimization plans", "/examples/action-plans")
        ]
    
    def _create_report_suggestions(self) -> List[Dict[str, str]]:
        """Create recovery suggestions for report content"""
        return [
            self._create_suggestion("Report Builder", "Interactive report generation tool", "/tools/report-builder"),
            self._create_suggestion("Metrics Dashboard", "View real-time metrics and trends", "/dashboard/metrics"),
            self._create_suggestion("Export Templates", "Download report templates", "/templates/reports")
        ]
    
    def _create_suggestion(self, action: str, description: str, link: str) -> Dict[str, str]:
        """Create a single recovery suggestion"""
        return {
            "action": action,
            "description": description,
            "link": link
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
                "description": "Provide more specific details and constraints",
                "link": "/help/requests"
            },
            {
                "action": "View Examples",
                "description": "See successful request examples with specific patterns",
                "link": "/examples"
            },
            {
                "action": "Get Help",
                "description": "Contact support to provide tailored assistance",
                "link": "/support"
            }
        ]