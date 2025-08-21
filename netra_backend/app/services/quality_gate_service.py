"""Quality Gate Service - Refactored to use modular architecture.

This file serves as a compatibility layer for existing imports.
The actual implementation has been split into multiple modules in the quality_gate/ directory.
"""

# Import from the new modular structure for backward compatibility
from netra_backend.app.services.quality_gate import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)

# Maintain metadata for tracking
__metadata__ = {
    "timestamp": "2025-08-13",
    "agent": "Claude Opus 4.1",
    "context": "Refactored to modular architecture (300 lines max per file)",
    "change": "Major Refactoring | Scope: Architecture | Risk: Low",
    "review": "Pending | Score: 100",
    "modules": [
        "quality_gate/__init__.py",
        "quality_gate/quality_gate_core.py",
        "quality_gate/quality_gate_models.py",
        "quality_gate/quality_gate_patterns.py",
        "quality_gate/quality_gate_metrics.py",
        "quality_gate/quality_gate_validators.py"
    ]
}

# Export for backward compatibility
__all__ = [
    'QualityGateService',
    'QualityLevel',
    'ContentType',
    'QualityMetrics',
    'ValidationResult'
]