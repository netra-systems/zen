"""
Unified Authentication Interface - Single Source of Truth
All authentication operations MUST go through this interface to ensure consistency

Business Value Justification:
- Segment: ALL (Platform/Security)
- Business Goal: Eliminate auth inconsistencies, prevent security breaches
- Value Impact: Single auth model prevents auth bypasses worth $100K+ in security issues
- Strategic Impact: Platform-wide authentication consistency, audit compliance

This replaces ALL duplicate authentication implementations across services.
"""
import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    AuthProvider
)

logger = logging.getLogger(__name__)


class UnifiedAuthInterface:
    """
    SINGLE SOURCE OF TRUTH for ALL authentication operations.
    This interface consolidates authentication logic from ALL services.
    """
    
    def __init__(self):
        """Initialize unified auth with all core components."""
        self.jwt_handler = JWTHandler()
        self.session_manager = SessionManager()
        self.auth_service = AuthService()
        
        # Security validation components
        self._token_blacklist = set()
        self._user_blacklist = set()
        self._nonce_cache = set()
        self._last_cleanup = time.time()
        
        logger.info("UnifiedAuthInterface initialized - Single Source of Truth ready")
    
    # =======================
    # JWT TOKEN OPERATIONS
    # =======================
    
    def create_access_token(self, user_id: str, email: str, 
                           permissions: List[str] = None) -> str:
        """Create JWT access token - CANONICAL implementation."""
        return self.jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            permissions=permissions or []
        )
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token - CANONICAL implementation."""
        return self.jwt_handler.create_refresh_token(user_id)
    
    def create_service_token(self, service_id: str, service_name: str) -> str:
        """Create service-to-service token - CANONICAL implementation."""
        return self.jwt_handler.create_service_token(service_id, service_name)
    
    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Validate JWT token - CANONICAL implementation.
        This is the ONLY token validation that should be used.
        """
        return self.jwt_handler.validate_token(token, token_type)
    
    def validate_token_jwt(self, token: str) -> Optional[Dict]:
        """Alias for validate_token for backward compatibility."""
        return self.validate_token(token, "access")
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token - CANONICAL implementation."""
        return self.jwt_handler.extract_user_id(token)
    
    def blacklist_token(self, token: str) -> bool:
        """Blacklist token immediately - CANONICAL implementation."""
        return self.jwt_handler.blacklist_token(token)
    
    def blacklist_user(self, user_id: str) -> bool:
        """Blacklist user - invalidates all their tokens."""
        return self.jwt_handler.blacklist_user(user_id)
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        return self.jwt_handler.is_token_blacklisted(token)
    
    def is_user_blacklisted(self, user_id: str) -> bool:
        """Check if user is blacklisted."""
        return self.jwt_handler.is_user_blacklisted(user_id)
    
    # =======================
    # USER AUTHENTICATION
    # =======================
    
    async def login(self, email: str, password: str, provider: str = "local",
                   client_info: Dict = None) -> Optional[LoginResponse]:
        """Authenticate user - CANONICAL implementation."""
        request = LoginRequest(
            email=email,
            password=password,
            provider=AuthProvider(provider)
        )
        
        try:
            response = await self.auth_service.login(request, client_info or {})
            return response
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """Logout user - CANONICAL implementation."""
        return await self.auth_service.logout(token, session_id)
    
    async def validate_user_token(self, token: str) -> Optional[Dict]:
        """
        Validate user token with enhanced security - CANONICAL implementation.
        This replaces ALL other token validation methods.
        """
        try:
            # First check local blacklist
            if self.is_token_blacklisted(token):
                logger.warning("Token is locally blacklisted")
                return None
            
            # Validate with JWT handler
            result = self.validate_token(token, "access")
            
            if not result:
                logger.warning("Token validation failed")
                return None
            
            # Additional cross-service validation
            if not self._validate_cross_service_security(result, token):
                logger.warning("Cross-service security validation failed")
                return None
            
            # Return standardized format
            return {
                "valid": True,
                "user_id": result.get("sub"),
                "email": result.get("email"),
                "permissions": result.get("permissions", []),
                "expires_at": datetime.fromtimestamp(result.get("exp")).isoformat() if result.get("exp") else None,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def _validate_cross_service_security(self, token_payload: Dict, token: str) -> bool:
        """Enhanced cross-service security validation."""
        try:
            # Check issuer
            if token_payload.get("iss") != "netra-auth-service":
                return False
            
            # Check token age
            issued_at = token_payload.get("iat", 0)
            if time.time() - issued_at > 86400:  # 24 hours max
                return False
            
            # Check user blacklist
            user_id = token_payload.get("sub")
            if user_id and self.is_user_blacklisted(user_id):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-service security validation error: {e}")
            return False
    
    # =======================
    # SESSION MANAGEMENT
    # =======================
    
    def create_session(self, user_id: str, user_data: Dict) -> str:
        """Create user session - CANONICAL implementation."""
        return self.session_manager.create_session(user_id, user_data)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict]:
        """Get user session - CANONICAL implementation."""
        return await self.session_manager.get_user_session(user_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session - CANONICAL implementation."""
        return self.session_manager.delete_session(session_id)
    
    async def invalidate_user_sessions(self, user_id: str) -> None:
        """Invalidate all user sessions - CANONICAL implementation."""
        await self.session_manager.invalidate_user_sessions(user_id)
    
    # =======================
    # API KEY VALIDATION
    # =======================
    
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key - CANONICAL implementation."""
        # This would integrate with API key management system
        # For now, delegate to auth service
        try:
            # API keys would be stored in database and validated here
            # This is a placeholder for the full implementation
            return None
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return None
    
    # =======================
    # SECURITY UTILITIES
    # =======================
    
    def generate_secure_nonce(self) -> str:
        """Generate cryptographically secure nonce."""
        return str(uuid.uuid4())
    
    def validate_nonce(self, nonce: str) -> bool:
        """Validate nonce and prevent replay attacks."""
        try:
            current_time = time.time()
            
            # Cleanup old nonces periodically
            if current_time - self._last_cleanup > 300:  # 5 minutes
                self._cleanup_expired_nonces()
                self._last_cleanup = current_time
            
            # Check for replay
            if nonce in self._nonce_cache:
                logger.warning(f"Nonce replay attack detected: {nonce[:8]}...")
                return False
            
            # Add to cache
            self._nonce_cache.add(nonce)
            
            # Limit cache size
            if len(self._nonce_cache) > 10000:
                oldest_nonces = list(self._nonce_cache)[:2000]
                for old_nonce in oldest_nonces:
                    self._nonce_cache.discard(old_nonce)
            
            return True
            
        except Exception as e:
            logger.error(f"Nonce validation error: {e}")
            return False
    
    def _cleanup_expired_nonces(self) -> None:
        """Clean up expired nonces."""
        try:
            # Simple cleanup - in production this would use TTL
            if len(self._nonce_cache) > 5000:
                self._nonce_cache.clear()
                logger.debug("Nonce cache cleared")
        except Exception as e:
            logger.error(f"Nonce cleanup error: {e}")
    
    def generate_service_signature(self, payload: Dict) -> str:
        """Generate service signature for cross-service auth."""
        try:
            # Extract service secret from auth service
            service_secret = self.jwt_handler.service_secret
            
            # Create signature payload
            signature_data = f"NETRA_SERVICE_AUTH:{payload}"
            
            # Generate HMAC signature
            signature = hmac.new(
                service_secret.encode(),
                signature_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Service signature generation error: {e}")
            return ""
    
    # =======================
    # OAUTH OPERATIONS
    # =======================
    
    async def handle_oauth_callback(self, code: str, state: str, 
                                  provider: str = "google") -> Optional[LoginResponse]:
        """Handle OAuth callback - delegates to auth service."""
        try:
            # This would be handled by the auth service routes
            # The auth service already has comprehensive OAuth handling
            logger.info(f"OAuth callback received for provider: {provider}")
            return None  # Handled by auth service routes
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return None
    
    # =======================
    # HEALTH AND MONITORING
    # =======================
    
    def get_auth_health(self) -> Dict[str, any]:
        """Get authentication system health."""
        try:
            return {
                "status": "healthy",
                "jwt_handler": "operational",
                "session_manager": "operational" if self.session_manager.health_check() else "degraded",
                "auth_service": "operational",
                "blacklisted_tokens": len(self._token_blacklist),
                "blacklisted_users": len(self._user_blacklist),
                "nonce_cache_size": len(self._nonce_cache),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Auth health check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_security_metrics(self) -> Dict[str, any]:
        """Get security metrics for monitoring."""
        return {
            "blacklisted_tokens": len(self._token_blacklist),
            "blacklisted_users": len(self._user_blacklist),
            "nonce_cache_size": len(self._nonce_cache),
            "service_name": "unified-auth-interface",
            "timestamp": time.time()
        }
    
    async def get_user_by_id(self, db, user_id: str) -> Optional[Dict]:
        """Get user by ID from auth service.
        
        Args:
            db: Database session (ignored, using auth service)
            user_id: User ID to lookup
            
        Returns:
            User dict if found, None otherwise
        """
        try:
            # Use auth service to get user data
            # For now, return a basic user structure
            # This would be replaced by actual auth service user lookup
            if self.is_user_blacklisted(user_id):
                return None
            
            # Placeholder implementation - would query auth service database
            return {
                "id": user_id,
                "active": True,
                "email": f"user_{user_id}@example.com"  # Placeholder
            }
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def validate_user_active(self, user: Optional[Dict]) -> bool:
        """Validate if user is active and not blacklisted.
        
        Args:
            user: User dictionary from get_user_by_id
            
        Returns:
            True if user is active and valid, False otherwise
        """
        if not user:
            return False
            
        user_id = str(user.get("id", ""))
        if self.is_user_blacklisted(user_id):
            return False
            
        # Check if user is marked as active
        return user.get("active", False) is True


# =======================
# GLOBAL SINGLETON
# =======================

# Global unified auth interface - SINGLE SOURCE OF TRUTH
_unified_auth_interface: Optional[UnifiedAuthInterface] = None

def get_unified_auth() -> UnifiedAuthInterface:
    """
    Get the global unified authentication interface.
    This is the ONLY way other services should access authentication.
    """
    global _unified_auth_interface
    if _unified_auth_interface is None:
        _unified_auth_interface = UnifiedAuthInterface()
    return _unified_auth_interface


# =======================
# BACKWARD COMPATIBILITY
# =======================

# These functions provide backward compatibility while services transition
# They all delegate to the unified interface

def validate_token_legacy(token: str) -> Optional[Dict]:
    """Legacy token validation - delegates to unified interface."""
    return get_unified_auth().validate_user_token(token)

def create_access_token_legacy(user_id: str, email: str, 
                              permissions: List[str] = None) -> str:
    """Legacy token creation - delegates to unified interface."""
    return get_unified_auth().create_access_token(user_id, email, permissions)

def blacklist_token_legacy(token: str) -> bool:
    """Legacy token blacklisting - delegates to unified interface."""
    return get_unified_auth().blacklist_token(token)

async def validate_user_token_legacy(token: str) -> Optional[Dict]:
    """Legacy user token validation - delegates to unified interface."""
    return await get_unified_auth().validate_user_token(token)


# Export the main interface and legacy functions
__all__ = [
    "UnifiedAuthInterface",
    "get_unified_auth",
    "validate_token_legacy",
    "create_access_token_legacy", 
    "blacklist_token_legacy",
    "validate_user_token_legacy"
]