"""
Auth Client Unified Shim - Backward Compatibility Layer
DEPRECATION NOTICE: This module provides backward compatibility while services migrate to unified auth.

Business Value Justification:
- Segment: Platform/Migration
- Business Goal: Zero-downtime migration to unified auth
- Value Impact: Prevents breaking existing authentication flows during consolidation
- Strategic Impact: Enables safe migration to single source of truth architecture

ALL NEW CODE should use netra_backend.app.clients.auth_client_core directly.
This shim will be removed after migration is complete.
"""
import logging
from typing import Dict, List, Optional

# Using HTTP-based auth client for microservice independence
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = logging.getLogger(__name__)


class AuthClientUnifiedShim:
    """
    DEPRECATED: Backward compatibility shim for existing auth_client usage.
    This delegates all calls to the HTTP-based auth client.
    
    MIGRATION PATH:
    OLD: from netra_backend.app.clients.auth_client import auth_client
         result = await auth_client.validate_token(token)
    
    NEW: from netra_backend.app.clients.auth_client_core import auth_client
         result = await auth_client.validate_token(token)
    """
    
    def __init__(self):
        logger.warning(
            "AuthClientUnifiedShim is DEPRECATED. "
            "Use netra_backend.app.clients.auth_client_core instead"
        )
        self._auth_client = AuthServiceClient()
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """DEPRECATED: Use auth_client.validate_token instead"""
        logger.warning("validate_token via shim is DEPRECATED. Use auth_client_core directly")
        return await self._auth_client.validate_token(token)
    
    async def validate_token_jwt(self, token: str) -> Optional[Dict]:
        """DEPRECATED: Use auth_client.validate_token instead"""
        logger.warning("validate_token_jwt via shim is DEPRECATED. Use auth_client_core directly")
        return await self._auth_client.validate_token(token)
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """DEPRECATED: Use auth_client.logout instead"""
        logger.warning("logout via shim is DEPRECATED. Use auth_client_core directly")
        return await self._auth_client.logout(token, session_id)
    
    def blacklist_token(self, token: str) -> bool:
        """DEPRECATED: Use auth_client.blacklist_token instead"""
        logger.warning("blacklist_token via shim is DEPRECATED. Use auth_client_core directly")
        return self._auth_client.blacklist_token(token)
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """DEPRECATED: Get user permissions (placeholder implementation)"""
        logger.warning("get_user_permissions via shim is DEPRECATED. Use auth_client_core directly")
        return await self._auth_client.get_user_permissions(user_id)
    
    async def revoke_user_sessions(self, user_id: str) -> Dict[str, bool]:
        """DEPRECATED: Use auth_client.revoke_user_sessions instead"""
        logger.warning("revoke_user_sessions via shim is DEPRECATED. Use auth_client_core directly")
        return await self._auth_client.revoke_user_sessions(user_id)
    
    def health_check(self) -> bool:
        """DEPRECATED: Use auth_client.health_check instead"""
        logger.warning("health_check via shim is DEPRECATED. Use auth_client_core directly")
        return self._auth_client.health_check()
    
    def detect_environment(self):
        """DEPRECATED: Use auth_client.detect_environment instead"""
        logger.warning("detect_environment via shim is DEPRECATED. Use auth_client_core directly")
        return self._auth_client.detect_environment()


# Global instance for backward compatibility
_auth_client_shim = None

def get_auth_client_shim() -> AuthClientUnifiedShim:
    """Get the global auth client shim for backward compatibility"""
    global _auth_client_shim
    if _auth_client_shim is None:
        _auth_client_shim = AuthClientUnifiedShim()
    return _auth_client_shim


# Create a singleton instance that acts like the old auth_client
auth_client_unified_shim = get_auth_client_shim()


# Export for backward compatibility
__all__ = [
    'AuthClientUnifiedShim',
    'get_auth_client_shim', 
    'auth_client_unified_shim'
]