"""Quality Gate Service Module

This module provides comprehensive quality validation for all AI-generated outputs
to prevent generic, low-value, or meaningless responses (AI slop).
"""

from .quality_gate_models import (
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from .quality_gate_core import QualityGateService

__all__ = [
    'QualityGateService',
    'QualityLevel',
    'ContentType',
    'QualityMetrics',
    'ValidationResult'
]