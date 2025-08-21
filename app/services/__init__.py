"""
Services package exports for Netra Apex
Provides access to core business services and utilities.
"""

# Core services will be imported on-demand to avoid circular import issues

# Quality analytics service
from . import quality_analytics

# Quality monitor service (test compatibility)
from . import quality_monitor

# Supply chain services
from . import supply_optimization
from . import supply_tracking
from . import supply_contract_service
from . import supply_sustainability_service
from . import supply_catalog_service
from . import supplier_comparison

# Thread services
from . import thread_analytics

# New service modules
from . import llm_manager
from . import api_gateway
from . import redis
from . import billing

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