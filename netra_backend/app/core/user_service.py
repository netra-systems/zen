"""Shim module for backward compatibility with UserService imports.

This module redirects imports to the actual user service implementation.
All imports should be updated to use the new location directly.
"""

# Import from the actual location
from netra_backend.app.services.auth_failover_service import (
    AuthFailoverService as UserService,
    auth_failover_service as user_service,
)

# Re-export for backward compatibility
__all__ = ["UserService", "user_service"]