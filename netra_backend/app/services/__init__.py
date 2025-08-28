"""
Services package exports for Netra Apex
Provides access to core business services and utilities.
"""

# Configuration manager for unified config system
class ServiceConfigManager:
    """Service configuration manager for unified config system."""
    
    def populate_service_config(self, config):
        """Populate service configuration."""
        pass
    
    def validate_service_consistency(self, config):
        """Validate service configuration consistency."""
        return []
    
    def get_enabled_services_count(self):
        """Get count of enabled services."""
        return 0

# Core services available for import
# Services are imported by specific modules to avoid circular imports
# Import services directly from their modules when needed:
#   from netra_backend.app.services.cost_calculator import CostCalculatorService
#   from netra_backend.app.services.thread_service import ThreadService
#   etc.

# Service configuration manager remains here for backward compatibility

__all__ = [
    "ServiceConfigManager",
]