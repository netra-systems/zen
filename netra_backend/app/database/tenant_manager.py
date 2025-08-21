"""Tenant Manager - Compatibility Module

Re-exports from the actual tenant service for backward compatibility.
"""

from netra_backend.app.services.database.tenant_service import (
    TenantService,
    TenantManager as ActualTenantManager,
    Tenant,
    TenantResource,
    Permission,
    TenantServiceError
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