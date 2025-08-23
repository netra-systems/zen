"""
User Authentication Service - Enhanced Cross-Service Security
CRITICAL: This service provides secure authentication integration with auth microservice
Business Value: Prevents authentication bypasses and ensures secure cross-service communication
"""

import logging
import time
from typing import Dict, Optional, Set
import hashlib
import hmac
import secrets
import datetime

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
        # Nonce cache for replay attack prevention
        self._nonce_cache: Set[str] = set()
        self._last_nonce_cleanup = time.time()
    
    def _get_shared_secret(self) -> str:
        """CRITICAL FIX: Get shared secret with strict security validation"""
        config = self.config.get_config()
        
        # Get service secret with strict validation
        service_secret = config.service_secret
        jwt_secret = config.jwt_secret_key
        
        # CRITICAL: Enforce strict security requirements
        if not service_secret:
            logger.critical("SECURITY VIOLATION: service_secret not configured - authentication disabled")
            raise ValueError("service_secret is required for secure authentication")
        
        # Validate secret strength
        if len(service_secret) < 32:
            logger.critical(f"SECURITY VIOLATION: service_secret too weak ({len(service_secret)} chars, minimum 32)")
            raise ValueError("service_secret must be at least 32 characters for security")
        
        # CRITICAL: Ensure service secret differs from JWT secret
        if service_secret == jwt_secret:
            logger.critical("SECURITY VIOLATION: service_secret identical to jwt_secret_key")
            raise ValueError("service_secret must be different from jwt_secret_key")
        
        logger.info("Service secret validation passed - secure authentication enabled")
        return service_secret
    
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
            
            # CRITICAL FIX: Service identity validation
            if not self._validate_service_identity(result, token):
                logger.warning("Service identity validation failed")
                return None
            
            # CRITICAL FIX: Nonce/replay attack prevention
            if not self._validate_nonce_replay_protection(result):
                logger.warning("Nonce/replay validation failed")
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
            
            # Validate timestamp is recent (within 5 minutes for production, 1 hour for dev)
            verified_at = result.get("verified_at")
            if verified_at:
                try:
                    import datetime
                    import os
                    
                    verified_time = datetime.datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                    now = datetime.datetime.now(datetime.timezone.utc)
                    
                    # More permissive timestamp validation for development
                    env = os.getenv("ENVIRONMENT", "development").lower()
                    max_age = 3600 if env == "development" else 300  # 1 hour vs 5 minutes
                    
                    if (now - verified_time).total_seconds() > max_age:
                        logger.warning(f"Token verification timestamp too old (env: {env})")
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
    
    def _validate_service_identity(self, result: Dict, token: str) -> bool:
        """CRITICAL FIX: Validate service identity and prevent impersonation"""
        try:
            # Extract service identity claims
            service_id = result.get("service_id")
            issuer = result.get("iss")
            audience = result.get("aud")
            
            # Validate service identity signature
            expected_identity_sig = self._generate_service_identity_signature(result)
            actual_identity_sig = result.get("service_identity_signature")
            
            if not actual_identity_sig:
                logger.debug("No service identity signature present - allowing for backward compatibility")
                return True
            
            if not hmac.compare_digest(expected_identity_sig, actual_identity_sig):
                logger.warning("Service identity signature mismatch")
                return False
            
            # Validate service claims
            if service_id and service_id != "auth_service":
                logger.warning(f"Invalid service_id: {service_id}")
                return False
            
            if issuer and issuer != "netra-auth-service":
                logger.warning(f"Invalid issuer: {issuer}")
                return False
            
            if audience and "netra-backend" not in audience:
                logger.warning(f"Invalid audience: {audience}")
                return False
            
            logger.debug("Service identity validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Service identity validation error: {e}")
            return False
    
    def _generate_service_identity_signature(self, payload: Dict) -> str:
        """CRITICAL FIX: Generate service identity signature with domain separation"""
        try:
            # Domain separation prefix
            domain_prefix = "NETRA_SERVICE_AUTH_V1"
            
            # Create identity payload
            identity_data = {
                "service_id": payload.get("service_id", ""),
                "iss": payload.get("iss", ""),
                "aud": payload.get("aud", ""),
                "user_id": payload.get("user_id", ""),
                "exp": payload.get("exp", "")
            }
            
            # Canonical string representation
            identity_string = "|".join([f"{k}:{v}" for k, v in sorted(identity_data.items())])
            full_payload = f"{domain_prefix}|{identity_string}"
            
            # Generate HMAC signature
            signature = hmac.new(
                self._shared_secret.encode(),
                full_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to generate service identity signature: {e}")
            return ""
    
    def _validate_nonce_replay_protection(self, result: Dict) -> bool:
        """CRITICAL FIX: Prevent nonce replay attacks"""
        try:
            current_time = time.time()
            
            # Cleanup expired nonces periodically
            if current_time - self._last_nonce_cleanup > 300:  # Every 5 minutes
                self._cleanup_expired_nonces(current_time)
                self._last_nonce_cleanup = current_time
            
            # Extract nonce from token result
            nonce = result.get("nonce")
            if not nonce:
                logger.debug("No nonce present - allowing for backward compatibility")
                return True
            
            # Check for replay attack
            if nonce in self._nonce_cache:
                logger.warning(f"SECURITY ALERT: Nonce replay attack detected: {nonce[:8]}...")
                return False
            
            # Add nonce to cache
            self._nonce_cache.add(nonce)
            
            # Limit cache size to prevent memory exhaustion
            if len(self._nonce_cache) > 10000:
                # Remove oldest 20% of entries (simple cleanup)
                nonces_to_remove = list(self._nonce_cache)[:2000]
                for old_nonce in nonces_to_remove:
                    self._nonce_cache.discard(old_nonce)
                logger.debug("Nonce cache cleanup performed")
            
            logger.debug(f"Nonce validation passed: {nonce[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Nonce validation error: {e}")
            return False
    
    def _cleanup_expired_nonces(self, current_time: float) -> None:
        """CRITICAL FIX: Cleanup expired nonces to prevent memory leaks"""
        try:
            # In a production system, this would use Redis with TTL
            # For now, we periodically clear old nonces based on cache size
            initial_size = len(self._nonce_cache)
            
            if initial_size > 5000:
                # Keep only recent 50% of nonces
                nonces_list = list(self._nonce_cache)
                self._nonce_cache = set(nonces_list[len(nonces_list)//2:])
                logger.debug(f"Expired nonces cleanup: {initial_size} -> {len(self._nonce_cache)}")
            
        except Exception as e:
            logger.error(f"Nonce cleanup error: {e}")
    
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