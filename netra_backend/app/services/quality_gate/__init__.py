"""Quality Gate Service Module

This module provides comprehensive quality validation for all AI-generated outputs
to prevent generic, low-value, or meaningless responses (AI slop).
"""

from netra_backend.app.services.quality_gate.quality_gate_core import QualityGateService
from netra_backend.app.services.quality_gate.quality_gate_models import (
    ContentType,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)

__all__ = [
    'QualityGateService',
    'QualityLevel',
    'ContentType',
    'QualityMetrics',
    'ValidationResult'
]