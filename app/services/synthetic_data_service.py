"""
Synthetic Data Generation Service - Compatibility wrapper
This file maintains backward compatibility by re-exporting from the refactored modules
"""

from .synthetic_data import (
    SyntheticDataService,
    synthetic_data_service,
    WorkloadCategory,
    GenerationStatus,
    validate_data
)

# Re-export everything for backward compatibility
__all__ = [
    'SyntheticDataService',
    'synthetic_data_service',
    'WorkloadCategory',
    'GenerationStatus',
    'validate_data'
]