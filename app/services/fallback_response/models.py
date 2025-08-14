"""Fallback Response Models and Types

This module defines the core data models and enums used by the fallback response system.
"""

from typing import List, Optional
from enum import Enum
from dataclasses import dataclass

from app.services.quality_gate_service import ContentType, QualityMetrics


class FailureReason(Enum):
    """Reasons for needing a fallback response"""
    LOW_QUALITY = "low_quality"
    PARSING_ERROR = "parsing_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONTEXT_MISSING = "context_missing"
    LLM_ERROR = "llm_error"
    VALIDATION_FAILED = "validation_failed"
    CIRCULAR_REASONING = "circular_reasoning"
    HALLUCINATION_RISK = "hallucination_risk"
    GENERIC_CONTENT = "generic_content"


@dataclass
class FallbackContext:
    """Context for generating fallback response"""
    agent_name: str
    content_type: ContentType
    failure_reason: FailureReason
    user_request: str
    attempted_action: str
    quality_metrics: Optional[QualityMetrics] = None
    error_details: Optional[str] = None
    retry_count: int = 0
    previous_responses: List[str] = None

    def __post_init__(self):
        """Initialize default values after object creation"""
        if self.previous_responses is None:
            self.previous_responses = []