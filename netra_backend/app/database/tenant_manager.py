"""Tenant Manager - Compatibility Module

Re-exports from the actual tenant service for backward compatibility.
"""

from netra_backend.app.services.database.tenant_service import (
    Permission,
    Tenant,
    TenantResource,
    TenantService,
    TenantServiceError,
)
from netra_backend.app.services.database.tenant_service import (
    TenantManager as ActualTenantManager,
)

# Create alias for compatibility
TenantManager = ActualTenantManager

__all__ = [
    'TenantManager',
    'TenantService', 
    'Tenant',
    'TenantResource',
    'Permission',
    'TenantServiceError'
]