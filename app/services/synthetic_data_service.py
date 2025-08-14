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

# Import get_clickhouse_client for test patching
from ..db.clickhouse import get_clickhouse_client

# Re-export everything for backward compatibility
__all__ = [
    'SyntheticDataService',
    'synthetic_data_service',
    'WorkloadCategory',
    'GenerationStatus',
    'validate_data',
    'get_clickhouse_client'
]