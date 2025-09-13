# DEPRECATED SHIM MODULE FOR BACKWARD COMPATIBILITY - SSOT COMPLIANT
# All user auth operations consolidated into auth_client SSOT
from typing import Optional, Dict, Any
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# SSOT COMPLIANCE: Single auth client instance for all operations
_auth_client = AuthServiceClient()

class UserAuthService:
    """DEPRECATED: Backward compatibility shim for UserAuthService.

    SSOT COMPLIANCE: This class delegates all operations to auth service SSOT.
    New code should import auth_client directly from netra_backend.app.clients.auth_client_core
    """

    @staticmethod
    async def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """DEPRECATED: Authenticate user through auth service SSOT."""
        try:
            # SSOT DELEGATION: Use auth service client
            result = await _auth_client.login(username, password)
            return result
        except Exception as e:
            return None

    @staticmethod
    async def validate_token(token: str) -> Optional[Dict[str, Any]]:
        """SSOT: Single validate_token implementation - delegates to auth service."""
        try:
            result = await _auth_client.validate_token(token)
            return result
        except Exception as e:
            return None

# SSOT COMPLIANCE: Single set of legacy function aliases
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """DEPRECATED: Use UserAuthService.authenticate() or auth_client directly."""
    return await UserAuthService.authenticate(username, password)

# REMOVED: Duplicate validate_token function eliminated for SSOT compliance
# Use UserAuthService.validate_token() or auth_client.validate_token() directly
