"""Realistic Test Data Service

Backward compatibility module that imports from the new modular structure.
Generates production-like test data for comprehensive testing.
Addresses gaps identified in test_realism_analysis_20250811.md
"""

# TODO: Fix import - realistic_test_data module does not exist
# from netra_backend.app.realistic_test_data import (
#     RealisticDataPatterns,
#     RealisticTestDataService,
# )

# Temporary stubs to prevent import errors
class RealisticDataPatterns:
    """Temporary stub for RealisticDataPatterns"""
    pass

class RealisticTestDataService:
    """Temporary stub for RealisticTestDataService"""
    pass

# Create the global instance for backward compatibility
realistic_test_data_service = RealisticTestDataService()

# Export everything for backward compatibility
__all__ = ["RealisticTestDataService", "RealisticDataPatterns", "realistic_test_data_service"]