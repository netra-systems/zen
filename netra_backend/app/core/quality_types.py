"""Quality validation types - Single source of truth.

Contains core types and enums used across quality validation system.
"""

from typing import Dict, List, Any
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ContentType(Enum):
    """Content types for quality validation."""
    OPTIMIZATION = "optimization"
    DATA_ANALYSIS = "data_analysis"
    ACTION_PLAN = "action_plan"
    REPORT = "report"
    TRIAGE = "triage"
    ERROR_MESSAGE = "error_message"
    GENERAL = "general"


class QualityLevel(Enum):
    """Quality levels based on scoring."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class QualityMetrics:
    """Quality metrics structure for validation."""
    
    def __init__(self):
        self.overall_score: float = 0.0
        self.specificity_score: float = 0.0
        self.actionability_score: float = 0.0
        self.quantification_score: float = 0.0
        self.relevance_score: float = 0.0
        self.completeness_score: float = 0.0
        self.clarity_score: float = 0.0
        self.novelty_score: float = 0.0
        self.generic_phrase_count: int = 0
        self.circular_reasoning_detected: bool = False
        self.hallucination_risk: float = 0.0
        self.redundancy_ratio: float = 0.0
        self.issues: List[str] = []


class ValidationResult:
    """Result of quality validation."""
    
    def __init__(self, passed: bool, metrics: QualityMetrics):
        self.passed = passed
        self.metrics = metrics
        self.retry_suggested: bool = False
        self.retry_prompt_adjustments: Dict[str, Any] = {}