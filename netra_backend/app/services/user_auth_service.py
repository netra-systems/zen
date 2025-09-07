# Shim module for backward compatibility
# User auth consolidated into auth_client
from typing import Optional, Dict, Any
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.services.auth_failover_service import AuthFailoverService

# Create auth client instance
_auth_client = AuthServiceClient()

class UserAuthService:
    """Backward compatibility shim for UserAuthService."""
    
    @staticmethod
    async def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user through auth service."""
        try:
            # FIX: Call the correct method - login() instead of authenticate()
            # AuthServiceClient has login() method, not authenticate()
            result = await _auth_client.login(username, password)
            return result
        except Exception as e:
            return None
    
    @staticmethod
    async def validate_token(token: str) -> Optional[Dict[str, Any]]:
        """Validate token through auth service."""
        try:
            result = await _auth_client.validate_token(token)
            return result
        except Exception as e:
            return None

# Legacy function aliases
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Legacy authenticate function."""
    return await UserAuthService.authenticate(username, password)

async def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Legacy validate token function."""  
    return await UserAuthService.validate_token(token)
