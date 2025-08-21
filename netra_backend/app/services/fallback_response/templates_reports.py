"""Report Templates - Templates for report generation failures and guidance.

This module provides templates for report-related content types and failures
with 25-line function compliance.
"""

from typing import Dict, List, Tuple

from app.services.quality_gate_service import ContentType
from netra_backend.app.models import FailureReason


class ReportTemplates:
    """Report generation template provider."""
    
    def get_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get all report templates."""
        return {
            **self._get_low_quality_mapping(),
            **self._get_generic_mapping(),
            **self._get_action_plan_mapping(),
            **self._get_triage_mapping()
        }
    
    def _get_low_quality_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get report low quality templates mapping."""
        return {(ContentType.REPORT, FailureReason.LOW_QUALITY): 
                self._get_report_low_quality_templates()}
    
    def _get_generic_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get report generic content templates mapping."""
        return {(ContentType.REPORT, FailureReason.GENERIC_CONTENT): 
                self._get_generic_templates()}
    
    def _get_action_plan_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get action plan templates mapping."""
        return {
            (ContentType.ACTION_PLAN, FailureReason.LOW_QUALITY): 
                self._get_action_plan_low_quality_templates(),
            (ContentType.ACTION_PLAN, FailureReason.VALIDATION_FAILED): 
                self._get_action_plan_validation_templates()
        }
    
    def _get_triage_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get triage templates mapping."""
        return {(ContentType.TRIAGE, FailureReason.LOW_QUALITY): 
                self._get_triage_templates()}
    
    def _get_report_low_quality_templates(self) -> List[str]:
        """Get templates for report low quality failures."""
        return [
            self._get_comprehensive_template(),
            self._get_additional_input_template()
        ]
    
    def _get_generic_templates(self) -> List[str]:
        """Get templates for report generic content failures."""
        return [
            self._get_specific_insights_template(),
            self._get_actionable_template()
        ]
    
    def _get_action_plan_low_quality_templates(self) -> List[str]:
        """Get templates for action plan low quality failures."""
        return [
            self._get_implementation_template(),
            self._get_clarification_template()
        ]
    
    def _get_action_plan_validation_templates(self) -> List[str]:
        """Get templates for action plan validation failures."""
        return [
            self._get_quality_template(),
            self._get_refinement_template()
        ]
    
    def _get_triage_templates(self) -> List[str]:
        """Get templates for triage low quality failures."""
        return [
            self._get_categorization_template(),
            self._get_context_template()
        ]
    
    def _get_comprehensive_template(self) -> str:
        """Get report comprehensive template."""
        intro = "To generate a comprehensive report on {context}, I need:"
        requirements = self._build_comprehensive_requirements()
        conclusion = "This ensures the report provides valuable insights."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_comprehensive_requirements(self) -> str:
        """Build comprehensive report requirements."""
        return ("• Specific metrics to include\n"
                "• Reporting period and scope\n"
                "• Target audience (technical/executive)\n"
                "• Key questions to address\n")
    
    def _get_additional_input_template(self) -> str:
        """Get report additional input template."""
        intro = "The report for {context} requires additional input:"
        requirements = self._build_additional_requirements()
        conclusion = "Please provide these for a detailed, actionable report."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_additional_requirements(self) -> str:
        """Build additional input requirements."""
        return ("• Data sources to analyze\n"
                "• Comparison baselines\n"
                "• Success metrics\n"
                "• Stakeholder requirements\n")
    
    def _get_specific_insights_template(self) -> str:
        """Get report specific insights template."""
        intro = "The initial report for {context} was too generic."
        purpose = "To provide specific insights:"
        requirements = self._build_insights_requirements()
        conclusion = "This enables a focused, valuable analysis."
        return f"{intro} {purpose}\n{requirements}{conclusion}"
    
    def _build_insights_requirements(self) -> str:
        """Build specific insights requirements."""
        return ("• Share recent performance data\n"
                "• Highlight areas of concern\n"
                "• Specify desired report sections\n"
                "• Indicate decision points needing data\n")
    
    def _get_actionable_template(self) -> str:
        """Get report actionable template."""
        intro = "Let me create a more specific report for {context}."
        request = "I need:"
        requirements = self._build_actionable_requirements()
        conclusion = "This ensures the report drives actionable decisions."
        return f"{intro} {request}\n{requirements}{conclusion}"
    
    def _build_actionable_requirements(self) -> str:
        """Build actionable report requirements."""
        return ("• Quantitative data points\n"
                "• Comparison periods\n"
                "• Business impact metrics\n"
                "• Specific recommendations needed\n")
    
    def _get_implementation_template(self) -> str:
        """Get action plan implementation template."""
        intro = "To create an actionable plan for {context}, I need:"
        requirements = self._build_implementation_requirements()
        conclusion = "This enables me to provide a step-by-step implementation guide."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_implementation_requirements(self) -> str:
        """Build implementation requirements."""
        return ("• Clear objectives and success criteria\n"
                "• Available resources and timeline\n"
                "• Current state and dependencies\n"
                "• Risk tolerance and constraints\n")
    
    def _get_clarification_template(self) -> str:
        """Get action plan clarification template."""
        intro = "The action plan for {context} requires clarification:"
        questions = self._build_clarification_questions()
        conclusion = "With these details, I can create a detailed execution roadmap."
        return f"{intro}\n{questions}{conclusion}"
    
    def _build_clarification_questions(self) -> str:
        """Build clarification questions."""
        return ("• What specific outcome are you targeting?\n"
                "• What's your implementation timeline?\n"
                "• What resources are available?\n"
                "• Are there any blockers or dependencies?\n")
    
    def _get_quality_template(self) -> str:
        """Get action plan quality template."""
        intro = "The generated action plan for {context} didn't meet quality standards."
        request = "Let me gather more information:"
        questions = self._build_quality_questions()
        conclusion = "This helps me create a more targeted, practical plan."
        return f"{intro} {request}\n{questions}{conclusion}"
    
    def _build_quality_questions(self) -> str:
        """Build quality assessment questions."""
        return ("• What's the primary goal?\n"
                "• What have you tried already?\n"
                "• What specific challenges are you facing?\n")
    
    def _get_refinement_template(self) -> str:
        """Get action plan refinement template."""
        intro = "I need to refine the action plan for {context}."
        request = "Please specify:"
        requirements = self._build_refinement_requirements()
        conclusion = "This ensures the plan is both achievable and valuable."
        return f"{intro} {request}\n{requirements}{conclusion}"
    
    def _build_refinement_requirements(self) -> str:
        """Build refinement requirements."""
        return ("• Priority order of tasks\n"
                "• Technical constraints\n"
                "• Team capabilities\n"
                "• Acceptable risk level\n")
    
    def _get_categorization_template(self) -> str:
        """Get triage categorization template."""
        intro = "To properly categorize and route your request about {context}, please clarify:"
        questions = self._build_categorization_questions()
        conclusion = "This helps me direct you to the right optimization path."
        return f"{intro}\n{questions}{conclusion}"
    
    def _build_categorization_questions(self) -> str:
        """Build categorization questions."""
        return ("• Is this about performance, functionality, or cost?\n"
                "• What system or component is affected?\n"
                "• What's the urgency level?\n"
                "• What outcome are you seeking?\n")
    
    def _get_context_template(self) -> str:
        """Get triage context template."""
        intro = "I need more context to triage {context} effectively:"
        requirements = self._build_context_requirements()
        conclusion = "This ensures proper prioritization and routing."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_context_requirements(self) -> str:
        """Build context requirements."""
        return ("• Primary concern (latency/throughput/accuracy/cost)\n"
                "• Current vs. desired state\n"
                "• Available resources\n"
                "• Timeline constraints\n")