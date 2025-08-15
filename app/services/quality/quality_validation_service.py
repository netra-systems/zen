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
        # Calculate individual scores
        specificity = QualityScoreCalculators.calculate_specificity_score(output)
        actionability = QualityScoreCalculators.calculate_actionability_score(output)
        quantification = QualityScoreCalculators.calculate_quantification_score(output)
        novelty = QualityScoreCalculators.calculate_novelty_score(output)
        completeness = QualityScoreCalculators.calculate_completeness_score(output, output_type)
        domain_relevance = QualityScoreCalculators.calculate_domain_relevance_score(output)
        
        # Calculate weighted overall score
        overall_score = self._calculate_weighted_score(
            specificity, actionability, quantification,
            novelty, completeness, domain_relevance
        )
        
        # Determine quality level
        quality_level = QualityValidators.determine_quality_level(overall_score)
        
        # Detect issues
        scores_dict = {
            'specificity': specificity,
            'actionability': actionability,
            'quantification': quantification
        }
        issues = QualityValidators.detect_issues(output, scores_dict, self.config)
        
        # Suggest improvements
        improvements = QualityValidators.suggest_improvements(scores_dict)
        
        return QualityMetrics(
            overall_score=overall_score,
            specificity_score=specificity,
            actionability_score=actionability,
            quantification_score=quantification,
            novelty_score=novelty,
            completeness_score=completeness,
            domain_relevance_score=domain_relevance,
            quality_level=quality_level,
            issues_detected=issues,
            improvements_suggested=improvements
        )
    
    def _calculate_weighted_score(self, specificity: float, actionability: float,
                                 quantification: float, novelty: float,
                                 completeness: float, domain_relevance: float) -> float:
        """Calculate weighted overall score from individual metrics"""
        weights = {
            'specificity': 0.25,
            'actionability': 0.20,
            'quantification': 0.20,
            'novelty': 0.10,
            'completeness': 0.15,
            'domain_relevance': 0.10
        }
        
        return (
            specificity * weights['specificity'] +
            actionability * weights['actionability'] +
            quantification * weights['quantification'] +
            novelty * weights['novelty'] +
            completeness * weights['completeness'] +
            domain_relevance * weights['domain_relevance']
        )
    
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
        # Extract text content from agent output
        text_content = self._extract_text_content(output)
        
        # Determine output type based on agent
        output_type = self._get_output_type_for_agent(agent_name)
        
        return self.validate_output(text_content, output_type)
    
    def _extract_text_content(self, output: Dict[str, Any]) -> str:
        """Extract text content from agent output"""
        if isinstance(output, dict):
            # Try common keys
            return (
                output.get('report', '') or
                output.get('analysis', '') or 
                output.get('recommendations', '') or
                output.get('data', '') or
                json.dumps(output)
            )
        else:
            return str(output)
    
    def _get_output_type_for_agent(self, agent_name: str) -> str:
        """Get output type based on agent name"""
        output_type_map = {
            'TriageSubAgent': 'analysis',
            'DataSubAgent': 'analysis',
            'OptimizationsCoreSubAgent': 'recommendation',
            'ActionsToMeetGoalsSubAgent': 'recommendation',
            'ReportingSubAgent': 'report'
        }
        
        return output_type_map.get(agent_name, 'general')
    
    def get_quality_report(self, metrics: QualityMetrics) -> str:
        """Generate a human-readable quality report"""
        return f"""
Quality Assessment Report
========================
Overall Score: {metrics.overall_score:.2f} ({metrics.quality_level.value.upper()})

Detailed Scores:
- Specificity: {metrics.specificity_score:.2f}
- Actionability: {metrics.actionability_score:.2f}
- Quantification: {metrics.quantification_score:.2f}
- Novelty: {metrics.novelty_score:.2f}
- Completeness: {metrics.completeness_score:.2f}
- Domain Relevance: {metrics.domain_relevance_score:.2f}

Issues Detected: {len(metrics.issues_detected)}
{chr(10).join(f'  - {issue}' for issue in metrics.issues_detected) if metrics.issues_detected else '  None'}

Suggested Improvements: {len(metrics.improvements_suggested)}
{chr(10).join(f'  - {improvement}' for improvement in metrics.improvements_suggested) if metrics.improvements_suggested else '  None'}
"""