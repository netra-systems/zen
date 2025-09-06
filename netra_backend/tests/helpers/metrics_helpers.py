"""Metrics creation helper functions for Quality Gate Service tests"""

from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityLevel,
    QualityMetrics,
)

def create_all_penalties_metrics():
    """Create metrics with all penalties applied"""
    return QualityMetrics(
        specificity_score = 0.8,
        actionability_score = 0.8,
        generic_phrase_count = 10,  # High penalty
        circular_reasoning_detected = True,  # -0.2
        hallucination_risk = 0.8,  # -0.15
        redundancy_ratio = 0.5  # -0.1,
)

def create_all_specific_checks_metrics():
    """Create metrics that fail all specific threshold checks"""
    return QualityMetrics(
        overall_score = 0.4,
        specificity_score = 0.4,
        actionability_score = 0.4,
        quantification_score = 0.4,
        relevance_score = 0.4,
        completeness_score = 0.4,
        clarity_score = 0.4,
        redundancy_ratio = 0.5,
        generic_phrase_count = 10,
)

def create_all_issues_metrics():
    """Create metrics with all possible issues"""
    return QualityMetrics(
        specificity_score = 0.3,
        actionability_score = 0.3,
        quantification_score = 0.3,
        generic_phrase_count = 5,
        circular_reasoning_detected = True,
        redundancy_ratio = 0.4,
        completeness_score = 0.3,
)

def create_prompt_adjustment_metrics():
    """Create metrics for prompt adjustment testing"""
    return QualityMetrics(
        specificity_score = 0.2,
        actionability_score = 0.2,
        quantification_score = 0.2,
        generic_phrase_count = 8,
        circular_reasoning_detected = True,
)

def create_borderline_optimization_metrics():
    """Create borderline metrics for optimization suggestions"""
    return QualityMetrics(
        quantification_score = 0.3,
        completeness_score = 0.8,
)

def create_borderline_action_plan_metrics():
    """Create borderline metrics for action plan suggestions"""
    return QualityMetrics(
        completeness_score = 0.3,
        actionability_score = 0.8,
)

def create_high_hallucination_metrics():
    """Create metrics with high hallucination risk"""
    return QualityMetrics(
        overall_score = 0.9,
        hallucination_risk = 0.8  # Above 0.7 threshold,
)

def add_quality_distribution_metrics(quality_service):
    """Add metrics with different quality levels for distribution testing"""
    levels_scores = [
        (QualityLevel.EXCELLENT, 0.95),
        (QualityLevel.GOOD, 0.75),
        (QualityLevel.ACCEPTABLE, 0.55),
        (QualityLevel.POOR, 0.35),
        (QualityLevel.UNACCEPTABLE, 0.25),
]
    for level, score in levels_scores:
        quality_service.metrics_history[ContentType.REPORT].append({
            'timestamp': '2024-01-01',
            'overall_score': score,
            'quality_level': level.value,
})

def add_recent_metrics_overflow(quality_service, count = 150):
    """Add metrics that exceed recent entry limits"""
    for i in range(count):
        quality_service.metrics_history[ContentType.TRIAGE].append({
            'timestamp': f'2024-01-{i+1:03d}',
            'overall_score': 0.5 + (i * 0.001),
            'quality_level': 'acceptable',
})

def add_metrics_to_memory_limit(quality_service, count = 1000):
    """Add metrics up to memory limit"""
    for i in range(count):
        quality_service.metrics_history[ContentType.OPTIMIZATION].append({
            'timestamp': f'2024-01-01T{i:04d}',
            'overall_score': 0.5,
})