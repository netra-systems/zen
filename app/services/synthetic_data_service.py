"""
Synthetic Data Generation Service - Complete service implementation
Provides comprehensive synthetic data generation with modular architecture
"""

# Import the new modular service implementation
from .synthetic_data.core_service import SyntheticDataService, synthetic_data_service
from .synthetic_data.enums import WorkloadCategory, GenerationStatus
from .synthetic_data.validators import validate_data

# Import get_clickhouse_client for test patching compatibility
from ..db.clickhouse import get_clickhouse_client

# Advanced functionality imports
from .synthetic_data.job_manager import JobManager
from .synthetic_data.generation_engine import GenerationEngine
from .synthetic_data.ingestion_manager import IngestionManager
from .synthetic_data.error_handler import ErrorHandler

# Re-export everything for backward compatibility
__all__ = [
    'SyntheticDataService',
    'synthetic_data_service',
    'WorkloadCategory', 
    'GenerationStatus',
    'validate_data',
    'get_clickhouse_client',
    'JobManager',
    'GenerationEngine',
    'IngestionManager',
    'ErrorHandler'
]