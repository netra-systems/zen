"""Quality Gate Service Validators and Threshold Checking"""

from typing import Dict, List, Any

from app.logging_config import central_logger
from .quality_gate_models import ContentType, QualityLevel, QualityMetrics

logger = central_logger.get_logger(__name__)


class QualityValidator:
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
        weights = {
            ContentType.OPTIMIZATION: {
                'specificity': 0.25,
                'actionability': 0.25,
                'quantification': 0.20,
                'relevance': 0.15,
                'completeness': 0.10,
                'clarity': 0.05
            },
            ContentType.DATA_ANALYSIS: {
                'quantification': 0.30,
                'specificity': 0.20,
                'relevance': 0.20,
                'completeness': 0.15,
                'clarity': 0.10,
                'novelty': 0.05
            },
            ContentType.ACTION_PLAN: {
                'actionability': 0.35,
                'completeness': 0.25,
                'specificity': 0.20,
                'clarity': 0.15,
                'relevance': 0.05
            },
            ContentType.REPORT: {
                'completeness': 0.25,
                'clarity': 0.20,
                'specificity': 0.20,
                'quantification': 0.15,
                'relevance': 0.10,
                'novelty': 0.10
            }
        }
        
        return weights.get(content_type, {
            'specificity': 0.20,
            'actionability': 0.15,
            'quantification': 0.15,
            'relevance': 0.15,
            'completeness': 0.15,
            'clarity': 0.10,
            'novelty': 0.10
        })
    
    def calculate_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        score = 0.0
        total_weight = 0.0
        
        metric_values = {
            'specificity': metrics.specificity_score,
            'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score,
            'relevance': metrics.relevance_score,
            'completeness': metrics.completeness_score,
            'novelty': metrics.novelty_score,
            'clarity': metrics.clarity_score
        }
        
        for metric, weight in weights.items():
            if metric in metric_values:
                score += metric_values[metric] * weight
                total_weight += weight
        
        # Apply penalties
        if metrics.generic_phrase_count > 2:
            score -= 0.1
        if metrics.circular_reasoning_detected:
            score -= 0.2
        if metrics.hallucination_risk > 0.5:
            score -= 0.15
        if metrics.redundancy_ratio > 0.3:
            score -= 0.1
        
        # Normalize
        if total_weight > 0:
            score = score / total_weight
        
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
        thresholds = self.thresholds.get(content_type, self.thresholds[ContentType.GENERAL]).copy()
        
        # Apply strict mode multiplier
        if strict_mode:
            thresholds = {k: v * 1.2 if k.startswith('min_') else v * 0.8 
                         for k, v in thresholds.items()}
        
        # Check overall score
        min_score_threshold = thresholds.get('min_score', 0.5)
        if metrics.overall_score < min_score_threshold:
            logger.debug(f"Failed overall score check: {metrics.overall_score} < {min_score_threshold}")
            return False
        
        # Check specific metrics
        checks = [
            ('min_specificity', metrics.specificity_score),
            ('min_actionability', metrics.actionability_score),
            ('min_quantification', metrics.quantification_score),
            ('min_relevance', metrics.relevance_score),
            ('min_completeness', metrics.completeness_score),
            ('min_clarity', metrics.clarity_score)
        ]
        
        for threshold_key, metric_value in checks:
            if threshold_key in thresholds and metric_value < thresholds[threshold_key]:
                return False
        
        # Check maximum thresholds
        if 'max_redundancy' in thresholds and metrics.redundancy_ratio > thresholds['max_redundancy']:
            return False
        
        if 'max_generic_phrases' in thresholds and metrics.generic_phrase_count > thresholds['max_generic_phrases']:
            return False
        
        # Check for critical failures
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