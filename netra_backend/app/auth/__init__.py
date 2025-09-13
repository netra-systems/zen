"""
Authentication Package - SSOT Implementation

This package provides authentication functionality for the Netra platform.
Following SSOT principles, this consolidates authentication logic from app/services/auth.

Business Value: Security/Internal - System Security & User Management
Ensures secure authentication and authorization across all platform operations.

CRITICAL: This is a minimal SSOT-compliant stub to resolve import errors.
Re-exports from the canonical auth service implementation.

NOTE: Tests expect this location (app.auth) instead of app.services.auth.
This package provides compatibility imports.
"""

from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


class AuthMethodType(Enum):
    """Authentication method types."""
    JWT_BEARER = "jwt_bearer"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    SESSION = "session"


@dataclass
class SecurityAuditEvent:
    """Security audit event for logging authentication activities."""
    event_type: str
    user_id: Optional[str] = None
    method: Optional[str] = None
    timestamp: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Import from the canonical auth service implementation
try:
    from netra_backend.app.services.auth import *
    from netra_backend.app.services.unified_authentication_service import (
        UnifiedAuthenticationService,
        AuthResult as AuthenticationResult,
    )
    # Import AuthenticationError from auth client where it actually exists
    from netra_backend.app.clients.auth_client_core import AuthServiceError as AuthenticationError
except ImportError:
    # Fallback minimal implementations if services not available
    from typing import Dict, Optional, Any
    from dataclasses import dataclass
    from enum import Enum
    
    @dataclass
    class AuthenticationResult:
        """Basic authentication result."""
        success: bool
        user_id: Optional[str] = None
        token: Optional[str] = None
        error_message: Optional[str] = None
    
    class AuthenticationError(Exception):
        """Basic authentication error."""
        pass
    
    
    class UnifiedAuthenticationService:
        """Basic authentication service."""
        
        def __init__(self):
            self.is_initialized = False
        
        async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationResult:
            """Basic authentication method."""
            return AuthenticationResult(
                success=False,
                error_message="Authentication service not fully initialized"
            )

# Export common auth interfaces
__all__ = [
    "UnifiedAuthenticationService",
    "AuthenticationResult", 
    "AuthenticationError",
]