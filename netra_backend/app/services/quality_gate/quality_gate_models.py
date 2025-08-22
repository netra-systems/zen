"""Quality Gate Service Models and Data Classes"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QualityLevel(Enum):
    """Quality level classifications"""
    EXCELLENT = "excellent"  # Score >= 0.9
    GOOD = "good"           # Score >= 0.7
    ACCEPTABLE = "acceptable"  # Score >= 0.5
    POOR = "poor"           # Score >= 0.3
    UNACCEPTABLE = "unacceptable"  # Score < 0.3


class ContentType(Enum):
    """Types of content to validate"""
    OPTIMIZATION = "optimization"
    DATA_ANALYSIS = "data_analysis"
    ACTION_PLAN = "action_plan"
    REPORT = "report"
    TRIAGE = "triage"
    ERROR_MESSAGE = "error_message"
    GENERAL = "general"


@dataclass
class QualityMetrics:
    """Quality metrics for a piece of content"""
    specificity_score: float = 0.0
    actionability_score: float = 0.0
    quantification_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    novelty_score: float = 0.0
    clarity_score: float = 0.0
    
    # Negative indicators
    generic_phrase_count: int = 0
    circular_reasoning_detected: bool = False
    hallucination_risk: float = 0.0
    redundancy_ratio: float = 0.0
    
    # Meta information
    word_count: int = 0
    sentence_count: int = 0
    numeric_values_count: int = 0
    specific_terms_count: int = 0
    
    # Overall score
    overall_score: float = 0.0
    quality_level: QualityLevel = QualityLevel.UNACCEPTABLE
    
    # Detailed feedback
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of quality validation"""
    passed: bool
    metrics: QualityMetrics
    retry_suggested: bool = False
    retry_prompt_adjustments: Optional[Dict[str, Any]] = None
    fallback_response: Optional[str] = None