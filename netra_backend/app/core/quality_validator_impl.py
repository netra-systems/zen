"""Quality validator implementation.

Implementation of the QualityValidator class with all validation logic.
Part of the modular quality validation system.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.quality_content_analysis import QualityContentAnalyzer
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.factory_status.quality_metrics import (
    ContentType,
    QualityMetrics,
    ValidationResult,
)

logger = central_logger.get_logger(__name__)


class QualityValidator:
    """Unified quality validator with comprehensive validation and threshold checking."""
    
    def __init__(self, quality_gate_service=None, strict_mode: bool = False):
        """Initialize quality validator with optional quality gate service."""
        self.quality_gate_service = quality_gate_service
        self.strict_mode = strict_mode
        self.quality_stats = self._init_quality_stats()
        self.thresholds = self._init_content_type_thresholds()
        self.content_analyzer = QualityContentAnalyzer()
    
    def _init_quality_stats(self) -> Dict[str, int]:
        """Initialize quality statistics tracking."""
        return {
            'total_validations': 0, 'passed': 0, 'failed': 0,
            'retried': 0, 'fallbacks_used': 0
        }
    
    async def validate_content(self, content: str, content_type: ContentType,
                             context: Dict[str, Any], strict_mode: bool = None) -> ValidationResult:
        """Validate content with comprehensive checks and threshold validation."""
        strict_mode = self._resolve_strict_mode(strict_mode)
        metrics = await self._get_content_metrics(content, content_type)
        passed = self.check_thresholds(metrics, content_type, strict_mode)
        result = self._create_validation_result(passed, metrics)
        self._update_validation_stats(result)
        return result
    
    async def _analyze_content_quality(self, content: str, content_type: ContentType) -> QualityMetrics:
        """Analyze content quality and extract metrics."""
        metrics = QualityMetrics()
        self._analyze_basic_quality_metrics(metrics, content, content_type)
        self._analyze_additional_quality_metrics(metrics, content, content_type)
        self._analyze_quality_issues(metrics, content)
        return metrics
    
    def get_weights_for_type(self, content_type: ContentType) -> Dict[str, float]:
        """Get scoring weights based on content type."""
        weight_mappings = self._get_content_type_weight_mappings()
        return weight_mappings.get(content_type, self._get_default_weights())
    
    def calculate_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> float:
        """Calculate weighted overall score with penalties."""
        base_score, total_weight = self._calculate_base_weighted_score(metrics, weights)
        penalized_score = self._apply_quality_penalties(base_score, metrics)
        normalized_score = penalized_score / total_weight if total_weight > 0 else penalized_score
        return max(0.0, min(1.0, normalized_score))
    
    def check_thresholds(self, metrics: QualityMetrics, content_type: ContentType, strict_mode: bool) -> bool:
        """Check if metrics meet thresholds for the content type."""
        thresholds = self._get_adjusted_thresholds(content_type, strict_mode)
        
        return (self._check_overall_score_threshold(metrics, thresholds) and
                self._check_specific_metric_thresholds(metrics, thresholds) and
                self._check_maximum_thresholds(metrics, thresholds) and
                self._check_critical_failure_conditions(metrics))
    
    def generate_prompt_adjustments(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Generate prompt adjustments for retry based on quality issues."""
        adjustments = {'temperature': 0.3, 'additional_instructions': []}
        self._add_specificity_adjustments(adjustments, metrics)
        self._add_actionability_adjustments(adjustments, metrics)
        self._add_quantification_adjustments(adjustments, metrics)
        return adjustments
    
    def generate_suggestions(self, metrics: QualityMetrics, content_type: ContentType) -> List[str]:
        """Generate improvement suggestions based on metrics."""
        suggestions = []
        self._add_quality_suggestions(suggestions, metrics)
        return suggestions
    
    # Implementation helper methods ( <= 8 lines each)
    
    def _init_content_type_thresholds(self) -> Dict[ContentType, Dict[str, float]]:
        """Initialize quality thresholds by content type."""
        return {
            ContentType.OPTIMIZATION: {"min_score": 0.63, "min_specificity": 0.6, "min_actionability": 0.6},
            ContentType.DATA_ANALYSIS: {"min_score": 0.6, "min_quantification": 0.8, "min_relevance": 0.5},
            ContentType.ACTION_PLAN: {"min_score": 0.7, "min_actionability": 0.9, "min_completeness": 0.8},
            ContentType.REPORT: {"min_score": 0.6, "min_completeness": 0.8, "max_redundancy": 0.2},
            ContentType.ERROR_MESSAGE: {"min_score": 0.5, "min_clarity": 0.8, "min_actionability": 0.6},
            ContentType.GENERAL: {"min_score": 0.5, "min_clarity": 0.6, "max_generic_phrases": 3}
        }
    
    def _get_default_weights(self) -> Dict[str, float]:
        """Get default weights for unspecified content types."""
        return {
            'specificity': 0.20, 'actionability': 0.15, 'quantification': 0.15,
            'relevance': 0.15, 'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.10
        }
    
    def _calculate_base_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> Tuple[float, float]:
        """Calculate base weighted score from individual metrics."""
        metric_values = self._get_metric_values_dict(metrics)
        score = self._calculate_weighted_sum(metric_values, weights)
        total_weight = self._calculate_total_weight(metric_values, weights)
        return score, total_weight
    
    def _apply_quality_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for quality issues."""
        score = self._apply_generic_phrase_penalty(score, metrics)
        score = self._apply_reasoning_penalties(score, metrics)
        score = self._apply_redundancy_penalty(score, metrics)
        return score
    
    def _get_adjusted_thresholds(self, content_type: ContentType, strict_mode: bool) -> Dict[str, float]:
        """Get thresholds adjusted for content type and strict mode."""
        thresholds = self.thresholds.get(content_type, self.thresholds[ContentType.GENERAL]).copy()
        if strict_mode:
            thresholds = {k: v * 1.2 if k.startswith('min_') else v * 0.8 for k, v in thresholds.items()}
        return thresholds
    
    def _check_overall_score_threshold(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if overall score meets minimum threshold."""
        min_score = thresholds.get('min_score', 0.5)
        return metrics.overall_score >= min_score
    
    def _check_specific_metric_thresholds(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if specific metrics meet their thresholds."""
        checks = self._get_metric_threshold_checks(metrics)
        return self._validate_all_metric_thresholds(checks, thresholds)
    
    def _check_maximum_thresholds(self, metrics: QualityMetrics, thresholds: Dict[str, float]) -> bool:
        """Check if metrics stay within maximum thresholds."""
        if 'max_redundancy' in thresholds and metrics.redundancy_ratio > thresholds['max_redundancy']:
            return False
        if 'max_generic_phrases' in thresholds and metrics.generic_phrase_count > thresholds['max_generic_phrases']:
            return False
        return True
    
    def _check_critical_failure_conditions(self, metrics: QualityMetrics) -> bool:
        """Check for critical failure conditions."""
        return not (metrics.circular_reasoning_detected or metrics.hallucination_risk > 0.7)
    
    def _should_suggest_retry(self, metrics: QualityMetrics) -> bool:
        """Determine if retry should be suggested based on metrics."""
        return (metrics.overall_score > 0.3 and 
                not metrics.circular_reasoning_detected and 
                metrics.hallucination_risk < 0.7)
    
    def _update_validation_stats(self, result: ValidationResult) -> None:
        """Update validation statistics."""
        self.quality_stats['total_validations'] += 1
        if result.passed:
            self.quality_stats['passed'] += 1
        else:
            self.quality_stats['failed'] += 1
    
    # Helper methods for refactored functions ( <= 8 lines each)
    
    def _resolve_strict_mode(self, strict_mode: Optional[bool]) -> bool:
        """Resolve strict mode setting."""
        return self.strict_mode if strict_mode is None else strict_mode
    
    async def _get_content_metrics(self, content: str, content_type: ContentType) -> QualityMetrics:
        """Get content metrics with weighted scoring."""
        metrics = await self._analyze_content_quality(content, content_type)
        weights = self.get_weights_for_type(content_type)
        metrics.overall_score = self.calculate_weighted_score(metrics, weights)
        return metrics
    
    def _create_validation_result(self, passed: bool, metrics: QualityMetrics) -> ValidationResult:
        """Create validation result with retry suggestions if needed."""
        result = ValidationResult(passed, metrics)
        if not passed:
            result.retry_suggested = self._should_suggest_retry(metrics)
            result.retry_prompt_adjustments = self.generate_prompt_adjustments(metrics)
        return result
    
    def _analyze_basic_quality_metrics(self, metrics: QualityMetrics, content: str, content_type: ContentType) -> None:
        """Analyze basic quality metrics."""
        metrics.specificity_score = self.content_analyzer.analyze_specificity(content)
        metrics.actionability_score = self.content_analyzer.analyze_actionability(content)
        metrics.quantification_score = self.content_analyzer.analyze_quantification(content)
        metrics.relevance_score = self.content_analyzer.analyze_relevance(content, content_type)
    
    def _analyze_additional_quality_metrics(self, metrics: QualityMetrics, content: str, content_type: ContentType) -> None:
        """Analyze additional quality metrics."""
        metrics.completeness_score = self.content_analyzer.analyze_completeness(content, content_type)
        metrics.clarity_score = self.content_analyzer.analyze_clarity(content)
        metrics.novelty_score = self.content_analyzer.analyze_novelty(content)
    
    def _analyze_quality_issues(self, metrics: QualityMetrics, content: str) -> None:
        """Analyze quality issues detection."""
        metrics.generic_phrase_count = self.content_analyzer.count_generic_phrases(content)
        metrics.circular_reasoning_detected = self.content_analyzer.detect_circular_reasoning(content)
        metrics.hallucination_risk = self.content_analyzer.assess_hallucination_risk(content)
        metrics.redundancy_ratio = self.content_analyzer.calculate_redundancy_ratio(content)
    
    def _get_content_type_weight_mappings(self) -> Dict[ContentType, Dict[str, float]]:
        """Get weight mappings for all content types."""
        opt_wts = {'specificity': 0.25, 'actionability': 0.25, 'quantification': 0.20, 'relevance': 0.15, 'completeness': 0.10, 'clarity': 0.05}
        data_wts = {'quantification': 0.30, 'specificity': 0.20, 'relevance': 0.20, 'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.05}
        act_wts = {'actionability': 0.35, 'completeness': 0.25, 'specificity': 0.20, 'clarity': 0.15, 'relevance': 0.05}
        rpt_wts = {'completeness': 0.25, 'clarity': 0.20, 'specificity': 0.20, 'quantification': 0.15, 'relevance': 0.10, 'novelty': 0.10}
        err_wts = {'specificity': 0.35, 'actionability': 0.25, 'clarity': 0.20, 'relevance': 0.15, 'completeness': 0.05}
        return {ContentType.OPTIMIZATION: opt_wts, ContentType.DATA_ANALYSIS: data_wts, ContentType.ACTION_PLAN: act_wts, ContentType.REPORT: rpt_wts, ContentType.ERROR_MESSAGE: err_wts}
    
    def _add_specificity_adjustments(self, adjustments: Dict[str, Any], metrics: QualityMetrics) -> None:
        """Add specificity-related prompt adjustments."""
        if metrics.specificity_score < 0.5:
            adjustments['additional_instructions'].append(
                "Be extremely specific. Include exact parameter values, configuration settings, and metrics."
            )
    
    def _add_actionability_adjustments(self, adjustments: Dict[str, Any], metrics: QualityMetrics) -> None:
        """Add actionability-related prompt adjustments."""
        if metrics.actionability_score < 0.5:
            adjustments['additional_instructions'].append(
                "Provide step-by-step actionable instructions with specific commands or code."
            )
    
    def _add_quantification_adjustments(self, adjustments: Dict[str, Any], metrics: QualityMetrics) -> None:
        """Add quantification-related prompt adjustments."""
        if metrics.quantification_score < 0.5:
            adjustments['additional_instructions'].append(
                "Include numerical values for all claims. Show before/after metrics with percentages."
            )
    
    def _add_quality_suggestions(self, suggestions: List[str], metrics: QualityMetrics) -> None:
        """Add quality improvement suggestions based on metrics."""
        if metrics.specificity_score < 0.5:
            suggestions.append("Add specific metrics, parameters, or configuration values")
        if metrics.actionability_score < 0.5:
            suggestions.append("Include clear action steps or commands")
        if metrics.quantification_score < 0.5:
            suggestions.append("Add numerical values and measurable outcomes")
        if metrics.generic_phrase_count > 2:
            suggestions.append("Remove generic phrases and filler language")
    
    def _get_metric_values_dict(self, metrics: QualityMetrics) -> Dict[str, float]:
        """Get dictionary of metric values for scoring."""
        return {
            'specificity': metrics.specificity_score, 'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score, 'relevance': metrics.relevance_score,
            'completeness': metrics.completeness_score, 'clarity': metrics.clarity_score,
            'novelty': metrics.novelty_score
        }
    
    def _calculate_weighted_sum(self, metric_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted sum of metrics."""
        return sum(metric_values[metric] * weight for metric, weight in weights.items() if metric in metric_values)
    
    def _calculate_total_weight(self, metric_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate total weight for normalization."""
        return sum(weight for metric, weight in weights.items() if metric in metric_values)
    
    def _apply_generic_phrase_penalty(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalty for excessive generic phrases."""
        return score - 0.1 if metrics.generic_phrase_count > 2 else score
    
    def _apply_reasoning_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for reasoning issues."""
        if metrics.circular_reasoning_detected:
            score -= 0.2
        if metrics.hallucination_risk > 0.5:
            score -= 0.15
        return score
    
    def _apply_redundancy_penalty(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalty for content redundancy."""
        return score - 0.1 if metrics.redundancy_ratio > 0.3 else score
    
    def _get_metric_threshold_checks(self, metrics: QualityMetrics) -> List[Tuple[str, float]]:
        """Get metric threshold check pairs."""
        return [
            ('min_specificity', metrics.specificity_score),
            ('min_actionability', metrics.actionability_score),
            ('min_quantification', metrics.quantification_score),
            ('min_relevance', metrics.relevance_score),
            ('min_completeness', metrics.completeness_score),
            ('min_clarity', metrics.clarity_score)
        ]
    
    def _validate_all_metric_thresholds(self, checks: List[Tuple[str, float]], thresholds: Dict[str, float]) -> bool:
        """Validate all metric thresholds against requirements."""
        return all(metrics_value >= thresholds.get(threshold_key, 0) 
                  for threshold_key, metrics_value in checks if threshold_key in thresholds)
    
