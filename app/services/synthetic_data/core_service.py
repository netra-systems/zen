"""
Core Synthetic Data Service - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules ≤300 lines with functions ≤8 lines.
"""

# Import all modular components for backward compatibility
from .synthetic_data_service_main import SyntheticDataService, synthetic_data_service
from .resource_tracker import ResourceTracker
from .generation_coordinator import GenerationCoordinator
from .job_operations import JobOperations
from .analytics_reporter import AnalyticsReporter
from .advanced_generators import AdvancedGenerators
from .core_service_base import CoreServiceBase

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
