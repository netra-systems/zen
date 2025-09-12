"""
Core Synthetic Data Service - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules  <= 300 lines with functions  <= 8 lines.
"""

# Import all modular components for backward compatibility
from netra_backend.app.services.synthetic_data.advanced_generators import (
    AdvancedGenerators,
)
from netra_backend.app.services.synthetic_data.analytics_reporter import (
    AnalyticsReporter,
)
from netra_backend.app.services.synthetic_data.core_service_base import CoreServiceBase
from netra_backend.app.services.synthetic_data.generation_coordinator import (
    GenerationCoordinator,
)
from netra_backend.app.services.synthetic_data.job_operations import JobOperations
from netra_backend.app.services.synthetic_data.resource_tracker import ResourceTracker
from netra_backend.app.services.synthetic_data.synthetic_data_service_main import (
    SyntheticDataService,
    synthetic_data_service,
)

# Re-export main service class and instance for backward compatibility
__all__ = [
    "SyntheticDataService",
    "synthetic_data_service",
    "ResourceTracker",
    "GenerationCoordinator",
    "JobOperations",
    "AnalyticsReporter",
    "AdvancedGenerators",
    "CoreServiceBase"
]
