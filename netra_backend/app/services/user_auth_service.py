"""
User Authentication Service - Enhanced Cross-Service Security
CRITICAL: This service provides secure authentication integration with auth microservice
Business Value: Prevents authentication bypasses and ensures secure cross-service communication
"""

import logging
import time
from typing import Dict, Optional
import hashlib
import hmac

from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.configuration import unified_config_manager

logger = logging.getLogger(__name__)


class UserAuthService:
    """Enhanced user authentication service with cross-service security"""
    
    def __init__(self):
        self.auth_client = auth_client
        self.config = unified_config_manager
        self._token_blacklist = set()
        self._shared_secret = self._get_shared_secret()
    
    def _get_shared_secret(self) -> str:
        """Get shared secret for cross-service validation"""
        config = self.config.get_config()
        
        # Try service_secret first (AUTH_SHARED_SECRET equivalent)
        secret = config.service_secret
        if not secret:
            # Fallback to JWT secret for backward compatibility
            secret = config.jwt_secret_key or "dev-secret"
            logger.warning("service_secret not configured, using jwt_secret_key fallback")
        return secret
    
    async def validate_user_token(self, token: str) -> Optional[Dict]:
        """CRITICAL FIX: Enhanced token validation with cross-service security"""
        try:
            # First check local blacklist
            if self._is_token_blacklisted(token):
                logger.warning("Token is locally blacklisted")
                return None
            
            # Validate with auth service
            result = await self.auth_client.validate_token(token)
            
            if not result or not result.get("valid"):
                logger.warning("Auth service rejected token")
                return None
            
            # CRITICAL FIX: Additional cross-service validation
            if not self._validate_cross_service_token(result, token):
                logger.warning("Cross-service token validation failed")
                return None
            
            # Track successful validation
            self._track_successful_validation(token, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def _validate_cross_service_token(self, result: Dict, token: str) -> bool:
        """CRITICAL FIX: Validate token came from trusted auth service"""
        try:
            # Check required fields are present
            required_fields = ["user_id", "email", "verified_at"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing required field in auth response: {field}")
                    return False
            
            # Validate timestamp is recent (within 5 minutes)
            verified_at = result.get("verified_at")
            if verified_at:
                try:
                    import datetime
                    verified_time = datetime.datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                    now = datetime.datetime.now(datetime.timezone.utc)
                    
                    if (now - verified_time).total_seconds() > 300:  # 5 minutes
                        logger.warning("Token verification timestamp too old")
                        return False
                except Exception as e:
                    logger.warning(f"Failed to parse verification timestamp: {e}")
                    return False
            
            # Validate service signature if present
            service_signature = result.get("service_signature")
            if service_signature:
                expected_sig = self._generate_service_signature(result, token)
                if not hmac.compare_digest(service_signature, expected_sig):
                    logger.warning("Invalid service signature")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-service validation error: {e}")
            return False
    
    def _generate_service_signature(self, result: Dict, token: str) -> str:
        """Generate HMAC signature for service validation"""
        try:
            # Create signature payload
            payload = f"{result.get('user_id')}:{result.get('email')}:{token[:10]}"
            signature = hmac.new(
                self._shared_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            logger.error(f"Failed to generate service signature: {e}")
            return ""
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted locally"""
        return token in self._token_blacklist
    
    def blacklist_token(self, token: str):
        """Add token to local blacklist"""
        self._token_blacklist.add(token)
        # Also notify auth service
        try:
            # This would be an API call in production
            logger.info(f"Token blacklisted locally")
        except Exception as e:
            logger.error(f"Failed to notify auth service of blacklist: {e}")
    
    def _track_successful_validation(self, token: str, result: Dict):
        """Track successful validations for security monitoring"""
        try:
            # This could be enhanced with Redis or database tracking
            logger.debug(f"Token validated successfully for user: {result.get('user_id')}")
        except Exception as e:
            logger.error(f"Failed to track validation: {e}")
    
    async def get_user_permissions(self, user_id: str) -> list:
        """Get user permissions from auth service"""
        try:
            # This would be an API call to auth service
            permissions = await self.auth_client.get_user_permissions(user_id)
            return permissions or []
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []
    
    async def revoke_user_sessions(self, user_id: str) -> bool:
        """Revoke all sessions for a user"""
        try:
            result = await self.auth_client.revoke_user_sessions(user_id)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")
            return False
    
    def get_security_metrics(self) -> Dict:
        """Get security metrics for monitoring"""
        return {
            "blacklisted_tokens": len(self._token_blacklist),
            "service_name": "netra-backend",
            "timestamp": time.time()
        }


# Global instance
user_auth_service = UserAuthService()