"""
Synthetic Data Generation Service - Modular Architecture
"""

from netra_backend.app.services.synthetic_data.core_service import (
    SyntheticDataService,
    synthetic_data_service,
)
from netra_backend.app.services.synthetic_data.enums import (
    GenerationStatus,
    WorkloadCategory,
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ErrorHandler
from netra_backend.app.services.synthetic_data.generation_engine import GenerationEngine
# Import stubs from core_service_base for deleted modules
from netra_backend.app.services.synthetic_data.core_service_base import (
    IngestionManager,
    JobManager
)
from netra_backend.app.services.synthetic_data.validators import validate_data

__all__ = [
    'SyntheticDataService',
    'synthetic_data_service',
    'WorkloadCategory',
    'GenerationStatus',
    'validate_data',
    'JobManager',
    'GenerationEngine', 
    'IngestionManager',
    'ErrorHandler'
]