"""Data Analysis Templates - Templates for data analysis failures and guidance.

This module provides templates for data analysis-related content types and failures
with 25-line function compliance.
"""

from typing import Dict, List, Tuple

from netra_backend.app.services.fallback_response.models import FailureReason
from netra_backend.app.services.quality_gate_service import ContentType


class DataTemplates:
    """Data analysis template provider."""
    
    def get_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get all data analysis templates."""
        return {
            **self._get_low_quality_mapping(),
            **self._get_parsing_mapping()
        }
    
    def _get_low_quality_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get low quality data analysis templates mapping."""
        return {(ContentType.DATA_ANALYSIS, FailureReason.LOW_QUALITY): 
                self._get_low_quality_templates()}
    
    def _get_parsing_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get parsing error templates mapping."""
        return {(ContentType.DATA_ANALYSIS, FailureReason.PARSING_ERROR): 
                self._get_parsing_templates()}
    
    def _get_low_quality_templates(self) -> List[str]:
        """Get templates for data analysis low quality failures."""
        return [
            self._get_parameters_template(),
            self._get_objectives_template()
        ]
    
    def _get_parsing_templates(self) -> List[str]:
        """Get templates for data analysis parsing failures."""
        return [
            self._get_processing_issue_template(),
            self._get_parsing_failure_template()
        ]
    
    def _get_parameters_template(self) -> str:
        """Get data analysis parameters template."""
        intro = "The data analysis for {context} needs more specific parameters:"
        requirements = self._build_parameters_list()
        conclusion = "This will enable a focused, valuable analysis."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_parameters_list(self) -> str:
        """Build parameters requirements list."""
        return ("[U+2022] Data volume and format\n"
                "[U+2022] Key metrics to analyze\n"
                "[U+2022] Time range or scope\n"
                "[U+2022] Expected insights or patterns\n")
    
    def _get_objectives_template(self) -> str:
        """Get data analysis objectives template."""
        intro = "To analyze {context} effectively, please provide:"
        requirements = self._build_objectives_list()
        conclusion = "This ensures the analysis delivers actionable insights."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_objectives_list(self) -> str:
        """Build objectives requirements list."""
        return ("[U+2022] Sample data or schema\n"
                "[U+2022] Analysis objectives\n"
                "[U+2022] Historical context if available\n"
                "[U+2022] Specific questions to answer\n")
    
    def _get_processing_issue_template(self) -> str:
        """Get data processing issue template."""
        intro = "I encountered an issue processing the data for {context}."
        cause = "This typically occurs with:"
        issues = self._build_processing_issues()
        question = "Could you verify the data format and provide a sample?"
        return f"{intro} {cause}\n{issues}{question}"
    
    def _build_processing_issues(self) -> str:
        """Build common processing issues list."""
        return ("[U+2022] Inconsistent data formats\n"
                "[U+2022] Missing required fields\n"
                "[U+2022] Encoding issues\n")
    
    def _get_parsing_failure_template(self) -> str:
        """Get data parsing failure template."""
        intro = "Data parsing failed for {context}."
        cause = "Common causes:"
        causes = self._build_parsing_causes()
        solution = "Please check the data structure and try again with validated input."
        return f"{intro} {cause}\n{causes}{solution}"
    
    def _build_parsing_causes(self) -> str:
        """Build common parsing failure causes."""
        return ("[U+2022] Malformed JSON/CSV\n"
                "[U+2022] Unexpected data types\n"
                "[U+2022] Schema mismatches\n")