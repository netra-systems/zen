"""
Quality Validation Models and Configuration
Defines all data models, enums, and configuration for quality validation
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class QualityLevel(Enum):
    """Quality level classifications"""
    EXCELLENT = "excellent"  # Score >= 0.9
    GOOD = "good"           # Score >= 0.75
    ACCEPTABLE = "acceptable"  # Score >= 0.6
    POOR = "poor"           # Score >= 0.4
    UNACCEPTABLE = "unacceptable"  # Score < 0.4


class QualityMetrics(BaseModel):
    """Detailed quality metrics for an output"""
    overall_score: float = Field(ge=0, le=1)
    specificity_score: float = Field(ge=0, le=1)
    actionability_score: float = Field(ge=0, le=1)
    quantification_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    domain_relevance_score: float = Field(ge=0, le=1)
    quality_level: QualityLevel
    issues_detected: List[str] = Field(default_factory=list)
    improvements_suggested: List[str] = Field(default_factory=list)


@dataclass
class ValidationConfig:
    """Configuration for quality validation"""
    min_length: int = 100
    min_quality_score: float = 0.7
    min_specificity: float = 0.7
    min_actionability: float = 0.6
    require_metrics: bool = True
    require_concrete_steps: bool = True
    max_generic_phrase_ratio: float = 0.1