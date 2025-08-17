"""Quality Gate Service Validators and Threshold Checking"""

from typing import Dict, List, Any, Tuple, Optional

from app.logging_config import central_logger
from app.schemas.quality_types import QualityValidatorInterface, QualityValidationResult
from .quality_gate_models import ContentType, QualityLevel, QualityMetrics

logger = central_logger.get_logger(__name__)


class QualityValidator(QualityValidatorInterface):
    """Validate content quality against thresholds"""
    
    def __init__(self):
        # Quality thresholds by content type
        self.thresholds = {
            ContentType.OPTIMIZATION: {
                "min_score": 0.63,
                "min_specificity": 0.6,
                "min_actionability": 0.6,
                "min_quantification": 0.6
            },
            ContentType.DATA_ANALYSIS: {
                "min_score": 0.6,
                "min_specificity": 0.6,
                "min_quantification": 0.8,
                "min_relevance": 0.5
            },
            ContentType.ACTION_PLAN: {
                "min_score": 0.7,
                "min_actionability": 0.9,
                "min_specificity": 0.7,
                "min_completeness": 0.8
            },
            ContentType.REPORT: {
                "min_score": 0.6,
                "min_completeness": 0.8,
                "min_clarity": 0.7,
                "max_redundancy": 0.2
            },
            ContentType.TRIAGE: {
                "min_score": 0.5,
                "min_specificity": 0.6,
                "min_relevance": 0.8
            },
            ContentType.ERROR_MESSAGE: {
                "min_score": 0.5,
                "min_clarity": 0.8,
                "min_actionability": 0.6,
                "min_specificity": 0.7
            },
            ContentType.GENERAL: {
                "min_score": 0.5,
                "min_clarity": 0.6,
                "max_generic_phrases": 3
            }
        }
    
    def get_weights_for_type(self, content_type: ContentType) -> Dict[str, float]:
        """Get scoring weights based on content type"""
        weight_mappings = self._get_content_type_weight_mappings()
        return weight_mappings.get(content_type, self._get_default_weights())
    
    def _get_content_type_weight_mappings(self) -> Dict[ContentType, Dict[str, float]]:
        """Get all content type weight mappings."""
        return {
            ContentType.OPTIMIZATION: self._get_optimization_weights(),
            ContentType.DATA_ANALYSIS: self._get_data_analysis_weights(),
            ContentType.ACTION_PLAN: self._get_action_plan_weights(),
            ContentType.REPORT: self._get_report_weights(),
            ContentType.ERROR_MESSAGE: self._get_error_message_weights()
        }
    
    def _get_optimization_weights(self) -> Dict[str, float]:
        """Get weights for optimization content type."""
        return {
            'specificity': 0.25, 'actionability': 0.25, 'quantification': 0.20,
            'relevance': 0.15, 'completeness': 0.10, 'clarity': 0.05
        }
    
    def _get_data_analysis_weights(self) -> Dict[str, float]:
        """Get weights for data analysis content type."""
        return {
            'quantification': 0.30, 'specificity': 0.20, 'relevance': 0.20,
            'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.05
        }
    
    def _get_action_plan_weights(self) -> Dict[str, float]:
        """Get weights for action plan content type."""
        return {
            'actionability': 0.35, 'completeness': 0.25, 'specificity': 0.20,
            'clarity': 0.15, 'relevance': 0.05
        }
    
    def _get_report_weights(self) -> Dict[str, float]:
        """Get weights for report content type."""
        return {
            'completeness': 0.25, 'clarity': 0.20, 'specificity': 0.20,
            'quantification': 0.15, 'relevance': 0.10, 'novelty': 0.10
        }
    
    def _get_error_message_weights(self) -> Dict[str, float]:
        """Get weights for error message content type."""
        return {
            'specificity': 0.35, 'actionability': 0.25, 'clarity': 0.20,
            'relevance': 0.15, 'completeness': 0.05
        }
    
    def _get_default_weights(self) -> Dict[str, float]:
        """Get default weights for unspecified content types."""
        return {
            'specificity': 0.20, 'actionability': 0.15, 'quantification': 0.15,
            'relevance': 0.15, 'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.10
        }
    
    def calculate_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        base_score, total_weight = self._calculate_base_weighted_score(metrics, weights)
        penalized_score = self._apply_quality_penalties(base_score, metrics)
        normalized_score = self._normalize_score(penalized_score, total_weight)
        return self._clamp_score(normalized_score)
    
    def _calculate_base_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> Tuple[float, float]:
        """Calculate base weighted score from individual metrics."""
        metric_values = self._get_metric_values_dict(metrics)
        score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in metric_values:
                score += metric_values[metric] * weight
                total_weight += weight
        return score, total_weight
    
    def _get_metric_values_dict(self, metrics: QualityMetrics) -> Dict[str, float]:
        """Get dictionary mapping metric names to their values."""
        return {
            'specificity': metrics.specificity_score,
            'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score,
            'relevance': metrics.relevance_score,
            'completeness': metrics.completeness_score,
            'novelty': metrics.novelty_score,
            'clarity': metrics.clarity_score
        }
    
    def _apply_quality_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for quality issues."""
        if metrics.generic_phrase_count > 2:
            score -= 0.1
        if metrics.circular_reasoning_detected:
            score -= 0.2
        if metrics.hallucination_risk > 0.5:
            score -= 0.15
        if metrics.redundancy_ratio > 0.3:
            score -= 0.1
        return score
    
    def _normalize_score(self, score: float, total_weight: float) -> float:
        """Normalize score by total weight."""
        if total_weight > 0:
            return score / total_weight
        return score
    
    def _clamp_score(self, score: float) -> float:
        """Clamp score to valid range [0.0, 1.0]."""
        return max(0.0, min(1.0, score))
    
    def determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def check_thresholds(
        self,
        metrics: QualityMetrics,
        content_type: ContentType,
        strict_mode: bool
    ) -> bool:
        """Check if metrics meet thresholds for the content type"""
        thresholds = self._get_adjusted_thresholds(content_type, strict_mode)
        
        return (self._check_overall_score_threshold(metrics, thresholds) and
                self._check_specific_metric_thresholds(metrics, thresholds) and
                self._check_maximum_thresholds(metrics, thresholds) and
                self._check_critical_failure_conditions(metrics))
    
    def _get_adjusted_thresholds(self, content_type: ContentType, strict_mode: bool) -> Dict[str, float]:
        """Get thresholds adjusted for content type and strict mode."""
        thresholds = self.thresholds.get(content_type, self.thresholds[ContentType.GENERAL]).copy()
        if strict_mode:
            thresholds = {k: v * 1.2 if k.startswith('min_') else v * 0.8 
                         for k, v in thresholds.items()}
        return thresholds
    
    def _check_overall_score_threshold(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if overall score meets minimum threshold."""
        min_score_threshold = thresholds.get('min_score', 0.5)
        if metrics.overall_score < min_score_threshold:
            logger.debug(f"Failed overall score check: {metrics.overall_score} < {min_score_threshold}")
            return False
        return True
    
    def _check_specific_metric_thresholds(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if specific metrics meet their thresholds."""
        checks = self._get_metric_threshold_checks(metrics)
        for threshold_key, metric_value in checks:
            if threshold_key in thresholds and metric_value < thresholds[threshold_key]:
                return False
        return True
    
    def _get_metric_threshold_checks(self, metrics: QualityMetrics) -> List[Tuple[str, float]]:
        """Get list of metric threshold checks to perform."""
        return [
            ('min_specificity', metrics.specificity_score),
            ('min_actionability', metrics.actionability_score),
            ('min_quantification', metrics.quantification_score),
            ('min_relevance', metrics.relevance_score),
            ('min_completeness', metrics.completeness_score),
            ('min_clarity', metrics.clarity_score)
        ]
    
    def _check_maximum_thresholds(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if metrics stay within maximum thresholds."""
        if 'max_redundancy' in thresholds and metrics.redundancy_ratio > thresholds['max_redundancy']:
            return False
        if 'max_generic_phrases' in thresholds and metrics.generic_phrase_count > thresholds['max_generic_phrases']:
            return False
        return True
    
    def _check_critical_failure_conditions(self, metrics: QualityMetrics) -> bool:
        """Check for critical failure conditions that always fail validation."""
        if metrics.circular_reasoning_detected:
            return False
        if metrics.hallucination_risk > 0.7:
            return False
        return True
    
    def generate_suggestions(self, metrics: QualityMetrics, content_type: ContentType) -> List[str]:
        """Generate improvement suggestions based on metrics"""
        suggestions = []
        
        if metrics.specificity_score < 0.5:
            suggestions.append("Add specific metrics, parameters, or configuration values")
        
        if metrics.actionability_score < 0.5:
            suggestions.append("Include clear action steps or commands")
        
        if metrics.quantification_score < 0.5:
            suggestions.append("Add numerical values and measurable outcomes")
        
        if metrics.generic_phrase_count > 2:
            suggestions.append("Remove generic phrases and filler language")
        
        if metrics.circular_reasoning_detected:
            suggestions.append("Avoid circular reasoning - provide concrete solutions")
        
        if metrics.redundancy_ratio > 0.2:
            suggestions.append("Reduce redundant information")
        
        if content_type == ContentType.OPTIMIZATION and metrics.quantification_score < 0.7:
            suggestions.append("Include before/after performance metrics")
        
        if content_type == ContentType.ACTION_PLAN and metrics.completeness_score < 0.7:
            suggestions.append("Add verification steps and success criteria")
        
        return suggestions
    
    def generate_prompt_adjustments(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Generate prompt adjustments for retry based on quality issues"""
        adjustments = {
            'temperature': 0.3,  # Lower temperature for more focused output
            'additional_instructions': []
        }
        
        if metrics.specificity_score < 0.5:
            adjustments['additional_instructions'].append(
                "Be extremely specific. Include exact parameter values, configuration settings, and metrics."
            )
        
        if metrics.actionability_score < 0.5:
            adjustments['additional_instructions'].append(
                "Provide step-by-step actionable instructions with specific commands or code."
            )
        
        if metrics.quantification_score < 0.5:
            adjustments['additional_instructions'].append(
                "Include numerical values for all claims. Show before/after metrics with percentages."
            )
        
        if metrics.generic_phrase_count > 2:
            adjustments['additional_instructions'].append(
                "Avoid generic phrases. Be direct and specific without filler language."
            )
        
        if metrics.circular_reasoning_detected:
            adjustments['additional_instructions'].append(
                "Provide concrete solutions, not circular logic. Explain HOW, not just WHAT."
            )
        
        return adjustments
    
    # Interface Implementation Methods
    async def validate_content(
        self, 
        content: str, 
        content_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityValidationResult:
        """Validate content and return detailed quality results"""
        from datetime import datetime, UTC
        from ..quality_gate_service import QualityGateService
        
        # Convert string content_type to ContentType enum
        content_type_enum = self._convert_content_type(content_type)
        
        # Create QualityGateService instance to perform full validation
        service = QualityGateService()
        validation_result = await service.validate_content(
            content=content,
            content_type=content_type_enum,
            context=context or {},
            strict_mode=False
        )
        
        return validation_result
    
    def _convert_content_type(self, content_type: Optional[str]) -> ContentType:
        """Convert string content type to ContentType enum"""
        if not content_type:
            return ContentType.GENERAL
        
        try:
            return ContentType(content_type.lower())
        except ValueError:
            return ContentType.GENERAL
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "validator_type": "QualityGateValidator",
            "threshold_count": len(self.thresholds),
            "supported_content_types": [ct.value for ct in ContentType],
            "validation_capabilities": [
                "threshold_checking", "scoring", "improvement_suggestions",
                "prompt_adjustments", "quality_level_determination"
            ]
        }