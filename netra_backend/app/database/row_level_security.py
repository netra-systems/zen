"""Row Level Security - Compatibility Module

Re-exports from the actual tenant service for backward compatibility.
"""

from netra_backend.app.services.database.tenant_service import RowLevelSecurityManager

__all__ = [
    'RowLevelSecurityManager'
]