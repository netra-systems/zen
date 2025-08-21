"""Realistic Test Data Service

Backward compatibility module that imports from the new modular structure.
Generates production-like test data for comprehensive testing.
Addresses gaps identified in test_realism_analysis_20250811.md
"""

from netra_backend.app.realistic_test_data import (
    RealisticTestDataService,
    RealisticDataPatterns
)

# Create the global instance for backward compatibility
realistic_test_data_service = RealisticTestDataService()

# Export everything for backward compatibility
__all__ = ["RealisticTestDataService", "RealisticDataPatterns", "realistic_test_data_service"]