# This file is deprecated - all auth types have been moved to auth_types.py
# Import from auth_types.py instead:
# from app.schemas.auth_types import GoogleUser, DevUser, DevLoginRequest, AuthEndpoints, AuthConfigResponse

# Temporary backward compatibility imports (will be removed in future version)
from .auth_types import (
    GoogleUser,
    DevUser, 
    DevLoginRequest,
    AuthEndpoints,
    AuthConfigResponse
)

# Re-export for backward compatibility
__all__ = [
    "GoogleUser",
    "DevUser",
    "DevLoginRequest", 
    "AuthEndpoints",
    "AuthConfigResponse"
]
