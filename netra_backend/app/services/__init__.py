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

# Core services will be imported on-demand to avoid circular import issues

# Quality analytics service
# Quality monitor service (test compatibility)
# Supply chain services
# Thread services
# New service modules
from netra_backend.app.services import (
    api_gateway,
    billing,
    llm_manager,
    quality_analytics,
    quality_monitor,
    redis,
    supplier_comparison,
    supply_catalog_service,
    supply_contract_service,
    supply_optimization,
    supply_sustainability_service,
    supply_tracking,
    thread_analytics,
)

# Alias for backward compatibility
supply_chain_service = supply_catalog_service

__all__ = [
    "quality_analytics", 
    "quality_monitor",
    "supply_optimization",
    "supply_tracking", 
    "supply_contract_service",
    "supply_sustainability_service",
    "supply_catalog_service",
    "supply_chain_service",
    "supplier_comparison",
    "thread_analytics",
    "llm_manager",
    "api_gateway",
    "redis",
    "billing"
]