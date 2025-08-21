"""Quality configuration helper - Weight and threshold definitions.

Extracted from interfaces_quality.py to maintain 450-line limit.
Contains all weight mappings and threshold configurations.
"""

from typing import Dict
from netra_backend.app.core.quality_types import ContentType


def get_weight_mappings() -> Dict[ContentType, Dict[str, float]]:
    """Get weight mappings for all content types."""
    return {
        ContentType.OPTIMIZATION: get_optimization_weights(),
        ContentType.DATA_ANALYSIS: get_data_analysis_weights(),
        ContentType.ACTION_PLAN: get_action_plan_weights(),
        ContentType.REPORT: get_report_weights(),
        ContentType.ERROR_MESSAGE: get_error_message_weights()
    }


def get_optimization_weights() -> Dict[str, float]:
    """Get weights for optimization content type."""
    return {
        'specificity': 0.25, 'actionability': 0.25, 'quantification': 0.20,
        'relevance': 0.15, 'completeness': 0.10, 'clarity': 0.05
    }


def get_data_analysis_weights() -> Dict[str, float]:
    """Get weights for data analysis content type."""
    return {
        'quantification': 0.30, 'specificity': 0.20, 'relevance': 0.20,
        'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.05
    }


def get_action_plan_weights() -> Dict[str, float]:
    """Get weights for action plan content type."""
    return {
        'actionability': 0.35, 'completeness': 0.25, 'specificity': 0.20,
        'clarity': 0.15, 'relevance': 0.05
    }


def get_report_weights() -> Dict[str, float]:
    """Get weights for report content type."""
    return {
        'completeness': 0.25, 'clarity': 0.20, 'specificity': 0.20,
        'quantification': 0.15, 'relevance': 0.10, 'novelty': 0.10
    }


def get_error_message_weights() -> Dict[str, float]:
    """Get weights for error message content type."""
    return {
        'specificity': 0.35, 'actionability': 0.25, 'clarity': 0.20,
        'relevance': 0.15, 'completeness': 0.05
    }


def get_default_weights() -> Dict[str, float]:
    """Get default weights for unspecified content types."""
    return {
        'specificity': 0.20, 'actionability': 0.15, 'quantification': 0.15,
        'relevance': 0.15, 'completeness': 0.15, 'clarity': 0.10, 'novelty': 0.10
    }


def initialize_content_type_thresholds() -> Dict[ContentType, Dict[str, float]]:
    """Initialize quality thresholds by content type."""
    thresholds = {}
    set_optimization_thresholds(thresholds)
    set_analysis_report_thresholds(thresholds)
    set_action_error_thresholds(thresholds)
    return thresholds


def set_optimization_thresholds(thresholds: Dict[ContentType, Dict[str, float]]) -> None:
    """Set thresholds for optimization and data analysis types."""
    thresholds[ContentType.OPTIMIZATION] = {"min_score": 0.63, "min_specificity": 0.6, "min_actionability": 0.6}
    thresholds[ContentType.DATA_ANALYSIS] = {"min_score": 0.6, "min_quantification": 0.8, "min_relevance": 0.5}


def set_analysis_report_thresholds(thresholds: Dict[ContentType, Dict[str, float]]) -> None:
    """Set thresholds for action plan and report types."""
    thresholds[ContentType.ACTION_PLAN] = {"min_score": 0.7, "min_actionability": 0.9, "min_completeness": 0.8}
    thresholds[ContentType.REPORT] = {"min_score": 0.6, "min_completeness": 0.8, "max_redundancy": 0.2}


def set_action_error_thresholds(thresholds: Dict[ContentType, Dict[str, float]]) -> None:
    """Set thresholds for error message and general types."""
    thresholds[ContentType.ERROR_MESSAGE] = {"min_score": 0.5, "min_clarity": 0.8, "min_actionability": 0.6}
    thresholds[ContentType.GENERAL] = {"min_score": 0.5, "min_clarity": 0.6, "max_generic_phrases": 3}