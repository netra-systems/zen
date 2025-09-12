"""Quality validation interface - Single source of truth.

Main QualityValidator implementation with proper modular design.
Follows 450-line limit and 25-line functions.
"""

from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.quality_analysis import (
    QualityAnalyzer,
    QualityIssueDetector,
)
from netra_backend.app.core.quality_config import (
    get_default_weights,
    get_weight_mappings,
    initialize_content_type_thresholds,
)
from netra_backend.app.core.quality_types import (
    ContentType,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QualityValidator:
    """Unified quality validator with comprehensive validation and threshold checking."""
    
    def __init__(self, quality_gate_service=None, strict_mode: bool = False):
        """Initialize quality validator with optional quality gate service."""
        self.quality_gate_service = quality_gate_service
        self.strict_mode = strict_mode
        self.quality_stats = self._init_quality_stats()
        self.thresholds = initialize_content_type_thresholds()
        self.analyzer = QualityAnalyzer()
        self.issue_detector = QualityIssueDetector()
    
    def _init_quality_stats(self) -> Dict[str, int]:
        """Initialize quality statistics tracking."""
        return {
            'total_validations': 0, 'passed': 0, 'failed': 0,
            'retried': 0, 'fallbacks_used': 0
        }
    
    async def validate_content(self, content: str, content_type: ContentType,
                             context: Dict[str, Any], strict_mode: bool = None) -> ValidationResult:
        """Validate content with comprehensive checks and threshold validation."""
        strict_mode = strict_mode if strict_mode is not None else self.strict_mode
        metrics = await self._get_content_metrics(content, content_type)
        passed = self.check_thresholds(metrics, content_type, strict_mode)
        result = self._build_validation_result(metrics, passed)
        return self._finalize_validation(result)
    
    async def _analyze_content_quality(self, content: str, content_type: ContentType) -> QualityMetrics:
        """Analyze content quality and extract metrics."""
        metrics = QualityMetrics()
        self._analyze_basic_quality(metrics, content, content_type)
        self._analyze_additional_quality(metrics, content, content_type)
        self._detect_quality_issues(metrics, content)
        return metrics
    
    def get_weights_for_type(self, content_type: ContentType) -> Dict[str, float]:
        """Get scoring weights based on content type."""
        weight_mappings = get_weight_mappings()
        return weight_mappings.get(content_type, get_default_weights())
    
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
        self._add_core_suggestions(suggestions, metrics)
        self._add_language_suggestions(suggestions, metrics)
        return suggestions
    
    # Implementation helper methods ( <= 8 lines each)
    
    
    def _calculate_base_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> Tuple[float, float]:
        """Calculate base weighted score from individual metrics."""
        metric_values = self._get_metric_values(metrics)
        score = self._calculate_weighted_sum(metric_values, weights)
        total_weight = self._calculate_total_weight(metric_values, weights)
        return score, total_weight
    
    def _apply_quality_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for quality issues."""
        score = self._apply_language_penalties(score, metrics)
        score = self._apply_reasoning_penalties(score, metrics)
        score = self._apply_redundancy_penalties(score, metrics)
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
        checks = self._build_metric_threshold_checks(metrics)
        return self._validate_threshold_checks(checks, thresholds)
    
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
    
    # Additional helper methods for refactored functions
    
    async def _get_content_metrics(self, content: str, content_type: ContentType) -> QualityMetrics:
        """Get content metrics with overall score calculation."""
        metrics = await self._analyze_content_quality(content, content_type)
        weights = self.get_weights_for_type(content_type)
        metrics.overall_score = self.calculate_weighted_score(metrics, weights)
        return metrics
    
    def _build_validation_result(self, metrics: QualityMetrics, passed: bool) -> ValidationResult:
        """Build validation result with retry suggestions if needed."""
        result = ValidationResult(passed, metrics)
        if not passed:
            result.retry_suggested = self._should_suggest_retry(metrics)
            result.retry_prompt_adjustments = self.generate_prompt_adjustments(metrics)
        return result
    
    def _analyze_basic_quality(self, metrics: QualityMetrics, content: str, content_type: ContentType) -> None:
        """Analyze basic quality metrics."""
        metrics.specificity_score = self.analyzer.analyze_specificity(content)
        metrics.actionability_score = self.analyzer.analyze_actionability(content)
        metrics.quantification_score = self.analyzer.analyze_quantification(content)
        metrics.relevance_score = self.analyzer.analyze_relevance(content, content_type)
    
    def _analyze_additional_quality(self, metrics: QualityMetrics, content: str, content_type: ContentType) -> None:
        """Analyze additional quality metrics."""
        metrics.completeness_score = self.analyzer.analyze_completeness(content, content_type)
        metrics.clarity_score = self.analyzer.analyze_clarity(content)
        metrics.novelty_score = self.analyzer.analyze_novelty(content)
    
    def _detect_quality_issues(self, metrics: QualityMetrics, content: str) -> None:
        """Detect quality issues and populate metrics."""
        metrics.generic_phrase_count = self.issue_detector.count_generic_phrases(content)
        metrics.circular_reasoning_detected = self.issue_detector.detect_circular_reasoning(content)
        metrics.hallucination_risk = self.issue_detector.assess_hallucination_risk(content)
        metrics.redundancy_ratio = self.issue_detector.calculate_redundancy_ratio(content)
    
    
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
    
    def _add_core_suggestions(self, suggestions: List[str], metrics: QualityMetrics) -> None:
        """Add core improvement suggestions."""
        if metrics.specificity_score < 0.5:
            suggestions.append("Add specific metrics, parameters, or configuration values")
        if metrics.actionability_score < 0.5:
            suggestions.append("Include clear action steps or commands")
        if metrics.quantification_score < 0.5:
            suggestions.append("Add numerical values and measurable outcomes")
    
    def _add_language_suggestions(self, suggestions: List[str], metrics: QualityMetrics) -> None:
        """Add language-related improvement suggestions."""
        if metrics.generic_phrase_count > 2:
            suggestions.append("Remove generic phrases and filler language")
    
    
    def _get_metric_values(self, metrics: QualityMetrics) -> Dict[str, float]:
        """Get dictionary of metric values for calculation."""
        return {
            'specificity': metrics.specificity_score, 'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score, 'relevance': metrics.relevance_score,
            'completeness': metrics.completeness_score, 'clarity': metrics.clarity_score,
            'novelty': metrics.novelty_score
        }
    
    def _calculate_weighted_sum(self, metric_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted sum of metrics."""
        return sum(metric_values[metric] * weight 
                  for metric, weight in weights.items() 
                  if metric in metric_values)
    
    def _calculate_total_weight(self, metric_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate total weight for normalization."""
        return sum(weight for metric, weight in weights.items() 
                  if metric in metric_values)
    
    def _apply_language_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for language-related quality issues."""
        if metrics.generic_phrase_count > 2:
            score -= 0.1
        return score
    
    def _apply_reasoning_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for reasoning-related quality issues."""
        if metrics.circular_reasoning_detected:
            score -= 0.2
        if metrics.hallucination_risk > 0.5:
            score -= 0.15
        return score
    
    def _apply_redundancy_penalties(self, score: float, metrics: QualityMetrics) -> float:
        """Apply penalties for redundancy-related quality issues."""
        if metrics.redundancy_ratio > 0.3:
            score -= 0.1
        return score
    
    def _build_metric_threshold_checks(self, metrics: QualityMetrics) -> List[Tuple[str, float]]:
        """Build list of metric threshold checks."""
        return [
            ('min_specificity', metrics.specificity_score),
            ('min_actionability', metrics.actionability_score),
            ('min_quantification', metrics.quantification_score),
            ('min_relevance', metrics.relevance_score),
            ('min_completeness', metrics.completeness_score),
            ('min_clarity', metrics.clarity_score)
        ]
    
    def _validate_threshold_checks(self, checks: List[Tuple[str, float]], thresholds: Dict[str, float]) -> bool:
        """Validate metric values against their thresholds."""
        return all(metrics_value >= thresholds.get(threshold_key, 0) 
                  for threshold_key, metrics_value in checks if threshold_key in thresholds)
    
    def _finalize_validation(self, result: ValidationResult) -> ValidationResult:
        """Finalize validation by updating stats and returning result."""
        self._update_validation_stats(result)
        return result