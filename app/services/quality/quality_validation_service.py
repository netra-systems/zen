"""
Quality Validation Service for AI Slop Prevention
Main service class for validating AI output quality with comprehensive metrics
"""

import json
from typing import Dict, Any, Tuple, Optional

from .quality_models import ValidationConfig, QualityMetrics
from .quality_score_calculators import QualityScoreCalculators
from .quality_validators import QualityValidators


class QualityValidationService:
    """Service for validating AI output quality and detecting slop"""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize the quality validation service"""
        self.config = config or ValidationConfig()
        
    def validate_output(self, 
                       output: str, 
                       output_type: str = "general",
                       context: Optional[Dict[str, Any]] = None) -> Tuple[bool, QualityMetrics]:
        """
        Validate the quality of an AI-generated output
        
        Args:
            output: The text output to validate
            output_type: Type of output (e.g., "report", "recommendation", "analysis")
            context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, quality_metrics)
        """
        metrics = self._calculate_metrics(output, output_type)
        is_valid = QualityValidators.determine_validity(metrics, self.config)
        return is_valid, metrics
    
    def _calculate_metrics(self, output: str, output_type: str) -> QualityMetrics:
        """Calculate all quality metrics for the output"""
        individual_scores = self._calculate_individual_scores(output, output_type)
        overall_score = self._calculate_weighted_score(**individual_scores)
        quality_level = QualityValidators.determine_quality_level(overall_score)
        issues, improvements = self._analyze_quality_issues(output, individual_scores)
        return self._build_quality_metrics(individual_scores, overall_score, quality_level, issues, improvements)
    
    def _calculate_weighted_score(self, specificity: float, actionability: float,
                                 quantification: float, novelty: float,
                                 completeness: float, domain_relevance: float) -> float:
        """Calculate weighted overall score from individual metrics"""
        weights = self._get_quality_weights()
        scores = {
            'specificity': specificity, 'actionability': actionability,
            'quantification': quantification, 'novelty': novelty,
            'completeness': completeness, 'domain_relevance': domain_relevance
        }
        return sum(scores[metric] * weight for metric, weight in weights.items())
    
    def validate_agent_output(self, 
                             agent_name: str,
                             output: Dict[str, Any]) -> Tuple[bool, QualityMetrics]:
        """
        Validate output from a specific agent
        
        Args:
            agent_name: Name of the agent
            output: Agent's output dictionary
            
        Returns:
            Tuple of (is_valid, quality_metrics)
        """
        text_content = self._extract_text_content(output)
        output_type = self._get_output_type_for_agent(agent_name)
        return self.validate_output(text_content, output_type)
    
    def _extract_text_content(self, output: Dict[str, Any]) -> str:
        """Extract text content from agent output"""
        if isinstance(output, dict):
            content = self._try_common_content_keys(output)
            return content or json.dumps(output)
        else:
            return str(output)
    
    def _get_output_type_for_agent(self, agent_name: str) -> str:
        """Get output type based on agent name"""
        output_type_map = self._get_agent_output_mapping()
        return output_type_map.get(agent_name, 'general')
    
    def get_quality_report(self, metrics: QualityMetrics) -> str:
        """Generate a human-readable quality report"""
        header = self._build_report_header(metrics)
        scores = self._build_detailed_scores_section(metrics)
        issues = self._build_issues_section(metrics)
        improvements = self._build_improvements_section(metrics)
        return f"{header}\n\n{scores}\n\n{issues}\n\n{improvements}"
    
    def _calculate_individual_scores(self, output: str, output_type: str) -> Dict[str, float]:
        """Calculate all individual quality scores."""
        return {
            'specificity': QualityScoreCalculators.calculate_specificity_score(output),
            'actionability': QualityScoreCalculators.calculate_actionability_score(output),
            'quantification': QualityScoreCalculators.calculate_quantification_score(output),
            'novelty': QualityScoreCalculators.calculate_novelty_score(output),
            'completeness': QualityScoreCalculators.calculate_completeness_score(output, output_type),
            'domain_relevance': QualityScoreCalculators.calculate_domain_relevance_score(output)
        }
    
    def _analyze_quality_issues(self, output: str, scores: Dict[str, float]) -> Tuple[List[str], List[str]]:
        """Analyze quality issues and suggest improvements."""
        scores_subset = {k: v for k, v in scores.items() if k in ['specificity', 'actionability', 'quantification']}
        issues = QualityValidators.detect_issues(output, scores_subset, self.config)
        improvements = QualityValidators.suggest_improvements(scores_subset)
        return issues, improvements
    
    def _build_quality_metrics(self, scores: Dict[str, float], overall_score: float, 
                              quality_level, issues: List[str], improvements: List[str]) -> QualityMetrics:
        """Build QualityMetrics object from components."""
        return QualityMetrics(
            overall_score=overall_score, **scores, quality_level=quality_level,
            issues_detected=issues, improvements_suggested=improvements
        )
    
    def _get_quality_weights(self) -> Dict[str, float]:
        """Get quality metric weights."""
        return {
            'specificity': 0.25, 'actionability': 0.20, 'quantification': 0.20,
            'novelty': 0.10, 'completeness': 0.15, 'domain_relevance': 0.10
        }
    
    def _try_common_content_keys(self, output: Dict[str, Any]) -> str:
        """Try common keys for text content extraction."""
        content_keys = ['report', 'analysis', 'recommendations', 'data']
        for key in content_keys:
            if content := output.get(key, ''):
                return content
        return ''
    
    def _get_agent_output_mapping(self) -> Dict[str, str]:
        """Get agent name to output type mapping."""
        return {
            'TriageSubAgent': 'analysis', 'DataSubAgent': 'analysis',
            'OptimizationsCoreSubAgent': 'recommendation', 'ActionsToMeetGoalsSubAgent': 'recommendation',
            'ReportingSubAgent': 'report'
        }
    
    def _build_report_header(self, metrics: QualityMetrics) -> str:
        """Build report header section."""
        return f"Quality Assessment Report\n========================\nOverall Score: {metrics.overall_score:.2f} ({metrics.quality_level.value.upper()})"
    
    def _build_detailed_scores_section(self, metrics: QualityMetrics) -> str:
        """Build detailed scores section."""
        return f"Detailed Scores:\n- Specificity: {metrics.specificity_score:.2f}\n- Actionability: {metrics.actionability_score:.2f}\n- Quantification: {metrics.quantification_score:.2f}\n- Novelty: {metrics.novelty_score:.2f}\n- Completeness: {metrics.completeness_score:.2f}\n- Domain Relevance: {metrics.domain_relevance_score:.2f}"
    
    def _build_issues_section(self, metrics: QualityMetrics) -> str:
        """Build issues section."""
        issues_text = chr(10).join(f'  - {issue}' for issue in metrics.issues_detected) if metrics.issues_detected else '  None'
        return f"Issues Detected: {len(metrics.issues_detected)}\n{issues_text}"
    
    def _build_improvements_section(self, metrics: QualityMetrics) -> str:
        """Build improvements section."""
        improvements_text = chr(10).join(f'  - {improvement}' for improvement in metrics.improvements_suggested) if metrics.improvements_suggested else '  None'
        return f"Suggested Improvements: {len(metrics.improvements_suggested)}\n{improvements_text}"