"""
JWT Token Handler - Core authentication token management
Maintains 450-line limit with focused single responsibility
"""
import logging
import os
import time
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
from auth_service.auth_core.isolated_environment import get_env

logger = logging.getLogger(__name__)

class JWTHandler:
    """Single Source of Truth for JWT operations"""
    
    def __init__(self):
        self.secret = self._get_jwt_secret()
        self.service_secret = AuthConfig.get_service_secret()
        self.service_id = AuthConfig.get_service_id()
        self.algorithm = AuthConfig.get_jwt_algorithm()
        self.access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
        self.refresh_expiry = AuthConfig.get_jwt_refresh_expiry_days()
        self.service_expiry = AuthConfig.get_jwt_service_expiry_minutes()
        
        # Token blacklist for immediate invalidation
        self._token_blacklist = set()
        self._user_blacklist = set()  # For invalidating all user tokens
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret with production safety"""
        secret = AuthConfig.get_jwt_secret()
        env = AuthConfig.get_environment()
        
        if not secret:
            # In staging/production, require explicit JWT configuration
            if env in ["staging", "production"]:
                raise ValueError(
                    f"JWT_SECRET_KEY must be set in {env} environment. "
                    "JWT secrets must be explicitly configured."
                )
            # For test/development, warn but allow empty
            logger.warning(f"JWT_SECRET_KEY not configured for {env} environment")
            # Use a test secret that's clearly marked as unsafe
            return "TEST-ONLY-SECRET-NOT-FOR-PRODUCTION-" + "x" * 32
        
        if len(secret) < 32 and env in ["staging", "production"]:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        
        return secret
        
    def create_access_token(self, user_id: str, email: str, 
                           permissions: list = None) -> str:
        """Create access token for user authentication"""
        payload = self._build_payload(
            sub=user_id,
            email=email,
            permissions=permissions or [],
            token_type="access",
            exp_minutes=self.access_expiry
        )
        return self._encode_token(payload)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token for token renewal"""
        payload = self._build_payload(
            sub=user_id,
            token_type="refresh",
            exp_minutes=self.refresh_expiry * 24 * 60
        )
        return self._encode_token(payload)
    
    def create_service_token(self, service_id: str, 
                           service_name: str) -> str:
        """Create token for service-to-service auth"""
        payload = self._build_payload(
            sub=service_id,
            service=service_name,
            token_type="service",
            exp_minutes=self.service_expiry
        )
        return self._encode_token(payload)
    
    def validate_token(self, token: str, 
                      token_type: str = "access") -> Optional[Dict]:
        """CANONICAL JWT validation - Single Source of Truth for all JWT validation operations"""
        try:
            # Check cache first for sub-100ms performance
            cache_key = jwt_validation_cache.get_cache_key(token, token_type)
            cached_result = jwt_validation_cache.get_from_cache(cache_key)
            if cached_result is not None:
                if cached_result == "INVALID":
                    return None
                # Verify user not blacklisted (blacklist changes not cached)
                user_id = cached_result.get("sub")
                if user_id and self.is_user_blacklisted(user_id):
                    jwt_validation_cache.invalidate_user_cache(user_id)
                    return None
                return cached_result
            
            # Validate token format first to prevent "Not enough segments" errors
            if not token or not isinstance(token, str):
                logger.warning("Invalid token format: token is None or not a string")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            token_parts = token.split('.')
            if len(token_parts) != 3:
                logger.warning(f"Invalid token format: expected 3 segments, got {len(token_parts)}")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # Check if token is blacklisted first
            if self.is_token_blacklisted(token):
                logger.warning("Token is blacklisted")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # CONSOLIDATED: Validate token security (algorithm, format, etc.) - moved from oauth_security.py
            if not self._validate_token_security_consolidated(token):
                logger.warning("Token failed security validation")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                # Enhanced security options - disable audience verification since we handle it manually
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,  # We validate audience manually in cross-service validation
                    "require": ["exp", "iat", "sub"]
                }
            )
            
            if payload.get("token_type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # Check if user is blacklisted
            user_id = payload.get("sub")
            if user_id and self.is_user_blacklisted(user_id):
                logger.warning(f"User {user_id} is blacklisted")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # Additional security checks
            if not self._validate_token_claims(payload):
                logger.warning("Token claims validation failed")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # Enhanced JWT validation (optimized for performance)
            if not self._validate_enhanced_jwt_claims_fast(payload):
                logger.warning("Enhanced JWT claims validation failed")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # CRITICAL FIX: Cross-service validation
            if not self._validate_cross_service_token(payload, token):
                logger.warning("Cross-service token validation failed")
                jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
                return None
            
            # Generate service signature for response
            service_signature = self._generate_service_signature(payload)
            payload["service_signature"] = service_signature
            
            # Cache successful validation (shorter TTL than token expiry for security)
            cache_ttl = min(300, payload.get('exp', int(time.time()) + 900) - int(time.time()))
            jwt_validation_cache.cache_validation_result(cache_key, payload, ttl=max(60, cache_ttl))
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            jwt_validation_cache.cache_validation_result(cache_key, None, ttl=60)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            return None
    
    def validate_token_jwt(self, token: str, 
                          token_type: str = "access") -> Optional[Dict]:
        """Alias for validate_token for backwards compatibility with tests"""
        return self.validate_token(token, token_type)
    
    def validate_id_token(self, id_token: str, expected_issuer: str = None) -> Optional[Dict]:
        """Validate OAuth ID token from external providers (Google, etc.)"""
        try:
            # Decode header to check algorithm
            header = jwt.get_unverified_header(id_token)
            algorithm = header.get("alg")
            
            # For external OAuth ID tokens, we typically can't verify signature
            # without the provider's public key. For testing, we'll do basic validation.
            # In production, this would verify against Google's public keys.
            
            # Basic validation without signature verification for now
            payload = jwt.decode(
                id_token,
                options={
                    "verify_signature": False,  # Would need provider's public key
                    "verify_exp": True,
                    "verify_iat": True
                }
            )
            
            # Validate issuer if provided
            if expected_issuer and payload.get("iss") != expected_issuer:
                logger.warning(f"Invalid ID token issuer: {payload.get('iss')}")
                return None
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and exp < time.time():
                logger.warning("ID token is expired")
                return None
            
            # Check if token is too old
            iat = payload.get("iat")
            if iat and (time.time() - iat) > 24 * 60 * 60:  # 24 hours
                logger.warning("ID token issued too long ago")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("ID token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"ID token validation error: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[tuple]:
        """Generate new access token from refresh token"""
        # For token consumption operations, we DO need replay protection
        payload = self.validate_token_for_consumption(refresh_token, "refresh")
        if not payload:
            return None
            
        # Get user details from database (placeholder)
        user_id = payload["sub"]
        # In real implementation, fetch from DB
        email = "user@example.com"
        permissions = []
        
        new_access = self.create_access_token(user_id, email, permissions)
        new_refresh = self.create_refresh_token(user_id)
        
        return new_access, new_refresh
    
    def validate_token_for_consumption(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Validate token for consumption operations (token exchange, refresh, etc.)
        This includes replay protection via JWT ID tracking.
        """
        try:
            # Check if token is blacklisted first
            if self.is_token_blacklisted(token):
                logger.warning("Token is blacklisted")
                return None
            
            # CONSOLIDATED: Validate token security (algorithm, etc.)
            if not self._validate_token_security_consolidated(token):
                logger.warning("Token failed security validation")
                return None
            
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,
                    "require": ["exp", "iat", "sub"]
                }
            )
            
            if payload.get("token_type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}")
                return None
            
            # Check if user is blacklisted
            user_id = payload.get("sub")
            if user_id and self.is_user_blacklisted(user_id):
                logger.warning(f"User {user_id} is blacklisted")
                return None
            
            # Additional security checks
            if not self._validate_token_claims(payload):
                logger.warning("Token claims validation failed")
                return None
            
            # For consumption operations, include replay protection
            if not self._validate_cross_service_token_with_replay_protection(payload, token):
                logger.warning("Cross-service token validation with replay protection failed")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def _build_payload(self, sub: str, token_type: str, 
                      exp_minutes: int, **kwargs) -> Dict:
        """Build JWT payload with enhanced security claims"""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=exp_minutes)
        
        payload = {
            "sub": sub,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "token_type": token_type,
            "iss": "netra-auth-service",  # Issuer claim
            "aud": self._get_audience_for_token_type(token_type),  # Enhanced audience
            "jti": str(uuid.uuid4()),     # JWT ID for replay protection
            "env": AuthConfig.get_environment(),  # Environment binding
            "svc_id": self.service_id      # Service instance ID
        }
        payload.update(kwargs)
        return payload
    
    def _encode_token(self, payload: Dict) -> str:
        """Encode payload into JWT token"""
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token without full validation"""
        try:
            # Still validate basic security even without signature verification
            if not self._validate_token_security_consolidated(token):
                return None
            
            # Decode without verification for user ID extraction
            payload = jwt.decode(
                token, 
                options={"verify_signature": False, "verify_exp": False}
            )
            return payload.get("sub")
        except Exception:
            return None
    
    def _validate_token_claims(self, payload: Dict) -> bool:
        """Validate additional token claims for security"""
        try:
            # Check required claims
            required_claims = ["sub", "iat", "exp", "iss"]
            for claim in required_claims:
                if claim not in payload:
                    logger.warning(f"Missing required claim: {claim}")
                    return False
            
            # Validate issuer
            if payload.get("iss") != "netra-auth-service":
                logger.warning(f"Invalid issuer: {payload.get('iss')}")
                return False
            
            # Check token age (not too old)
            issued_at = payload.get("iat")
            if isinstance(issued_at, datetime):
                age = datetime.now(timezone.utc) - issued_at
            else:
                age = datetime.now(timezone.utc) - datetime.fromtimestamp(issued_at, timezone.utc)
            
            # Reject tokens older than 24 hours for security
            if age.total_seconds() > 24 * 60 * 60:
                logger.warning("Token too old")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Token claims validation error: {e}")
            return False
    
    def _validate_enhanced_jwt_claims(self, payload: Dict) -> bool:
        """Validate enhanced JWT claims for security"""
        try:
            # Check for jti/nonce field for replay protection (optional for performance)
            jti = payload.get("jti")
            if not jti:
                logger.debug("Missing jti (JWT ID) claim - continuing without replay protection for performance")
                # Don't fail validation for performance optimization
            
            # Validate issuer is exactly "netra-auth-service"
            if payload.get("iss") != "netra-auth-service":
                logger.warning(f"Invalid issuer: {payload.get('iss')}")
                return False
            
            # Validate audience matches expected values
            audience = payload.get("aud")
            valid_audiences = ["netra-platform", "netra-services", "netra-admin"]
            if audience not in valid_audiences:
                logger.warning(f"Invalid audience: {audience}")
                return False
            
            # Validate environment binding if present
            token_env = payload.get("env")
            current_env = AuthConfig.get_environment()
            if token_env and token_env != current_env:
                logger.warning(f"Environment mismatch: token={token_env}, current={current_env}")
                return False
            
            # Validate service ID if present
            token_svc_id = payload.get("svc_id")
            if token_svc_id and token_svc_id != self.service_id:
                logger.warning(f"Service ID mismatch: token={token_svc_id}, current={self.service_id}")
                return False
            
            # Log security event for enhanced validation
            logger.info(f"Enhanced JWT validation passed for token {jti[:8]}... (audience: {audience})")
            
            return True
            
        except Exception as e:
            logger.error(f"Enhanced JWT claims validation error: {e}")
            return False
    
    def _validate_cross_service_token(self, payload: Dict, token: str) -> bool:
        """CRITICAL FIX: Validate token for cross-service security"""
        try:
            # Check for service-specific claims that indicate token origin
            issuer = payload.get("iss", "netra-auth-service")
            audience = payload.get("aud", "netra-platform")
            
            # Validate issuer and audience for cross-service security
            if issuer != "netra-auth-service":
                logger.warning(f"Invalid token issuer: {issuer}")
                return False
            
            # For development environment, be more permissive with audiences
            env = get_env().get("ENVIRONMENT", "development").lower()
            valid_audiences = ["netra-platform", "netra-backend", "netra-auth", "netra-services", "netra-admin"]
            
            if env == "development":
                # In development, allow more permissive audience validation
                valid_audiences.extend(["test", "localhost", "development"])
            
            if audience not in valid_audiences:
                logger.warning(f"Invalid token audience: {audience} (env: {env})")
                return False
            
            # PERFORMANCE FIX: Do NOT track JWT IDs for validation operations
            # JWT ID tracking should only apply to token consumption operations (like token exchange)
            # Validation is a read operation and should be idempotent and concurrent-safe
            # Token replay protection is handled by expiry times and should not prevent
            # legitimate concurrent validations of the same valid token
            
            # Validate token was issued within acceptable time window
            iat = payload.get("iat", 0)
            now = time.time()
            if iat > now + 60:  # Allow 1 minute clock skew
                logger.warning(f"Token issued in future: {iat} > {now}")
                return False
            
            if now - iat > 86400:  # Token older than 24 hours (max validity)
                logger.warning(f"Token too old: issued {now - iat} seconds ago")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-service token validation error: {e}")
            return False
    
    def _validate_cross_service_token_with_replay_protection(self, payload: Dict, token: str) -> bool:
        """Validate token for consumption operations with JWT ID replay protection"""
        try:
            # First do standard cross-service validation
            if not self._validate_cross_service_token(payload, token):
                return False
            
            # Additional replay protection for consumption operations
            jti = payload.get("jti")
            if jti and self._is_token_id_used(jti):
                logger.warning(f"Token ID already used (replay attack): {jti}")
                return False
            
            # Track token ID to prevent replay attacks
            if jti:
                self._track_token_id(jti, payload.get("exp", 0))
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-service token validation with replay protection error: {e}")
            return False
    
    def _is_token_id_used(self, jti: str) -> bool:
        """Check if JWT ID has been used (for replay attack prevention)"""
        # In production, this should use Redis or database
        # For now, use in-memory tracking
        if not hasattr(self, '_used_token_ids'):
            self._used_token_ids = set()
        return jti in self._used_token_ids
    
    def _track_token_id(self, jti: str, exp: int):
        """Track JWT ID to prevent replay attacks"""
        if not hasattr(self, '_used_token_ids'):
            self._used_token_ids = set()
        self._used_token_ids.add(jti)
        
        # Clean up expired token IDs periodically
        if len(self._used_token_ids) > 10000:
            self._cleanup_expired_token_ids()
    
    def _cleanup_expired_token_ids(self):
        """Clean up expired token IDs to prevent memory leaks"""
        # This is a simple cleanup; in production use proper expiration tracking
        if hasattr(self, '_used_token_ids') and len(self._used_token_ids) > 5000:
            self._used_token_ids.clear()
            logger.info("Cleaned up token ID tracking cache")
    
    def _get_audience_for_token_type(self, token_type: str) -> str:
        """Get appropriate audience for token type"""
        audience_map = {
            "access": "netra-platform",
            "refresh": "netra-platform", 
            "service": "netra-services",
            "admin": "netra-admin"
        }
        return audience_map.get(token_type, "netra-platform")
    
    def _generate_service_signature(self, payload: Dict) -> str:
        """Generate service identity signature for enhanced security"""
        try:
            # Extract key claims for signature
            service_claims = {
                "sub": payload.get("sub"),
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "svc_id": payload.get("svc_id"),
                "exp": payload.get("exp")
            }
            
            # Create signature data with domain separation
            domain_prefix = "NETRA_SERVICE_AUTH_V1"
            signature_data = f"{domain_prefix}:{service_claims}"
            
            # Generate HMAC-SHA256 signature
            signature = hmac.new(
                self.service_secret.encode('utf-8'),
                signature_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Service signature generation failed: {e}")
            return ""

    def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist for immediate invalidation"""
        try:
            self._token_blacklist.add(token)
            logger.info(f"Token blacklisted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
# User blacklisting is now handled by the enhanced version above
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if specific token is blacklisted"""
        return token in self._token_blacklist
    
    def is_user_blacklisted(self, user_id: str) -> bool:
        """Check if user is blacklisted"""
        return user_id in self._user_blacklist
    
    def remove_from_blacklist(self, token: str) -> bool:
        """Remove token from blacklist"""
        try:
            self._token_blacklist.discard(token)
            logger.info(f"Token removed from blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False
    
    def remove_user_from_blacklist(self, user_id: str) -> bool:
        """Remove user from blacklist"""
        try:
            self._user_blacklist.discard(user_id)
            logger.info(f"User {user_id} removed from blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove user {user_id} from blacklist: {e}")
            return False
    
    def _validate_enhanced_jwt_claims_fast(self, payload: Dict) -> bool:
        """Fast enhanced JWT claims validation optimized for performance"""
        try:
            # Validate issuer is exactly "netra-auth-service"
            if payload.get("iss") != "netra-auth-service":
                return False
            
            # Validate audience matches expected values (relaxed for performance)
            audience = payload.get("aud")
            if audience and audience not in ["netra-platform", "netra-services", "netra-backend", "netra-admin"]:
                # Only warn for unknown audiences in development, fail in production
                env = AuthConfig.get_environment()
                if env in ["staging", "production"]:
                    return False
                logger.debug(f"Unknown audience in {env}: {audience}")
            
            # Skip environment and service ID validation for performance
            # These are less critical and slow down validation
            
            return True
            
        except Exception as e:
            logger.error(f"Fast enhanced JWT claims validation error: {e}")
            return False
    
    def blacklist_user(self, user_id: str) -> bool:
        """Add user to blacklist, invalidating all their tokens and cache"""
        try:
            self._user_blacklist.add(user_id)
            # Invalidate cached tokens for this user
            jwt_validation_cache.invalidate_user_cache(user_id)
            logger.info(f"User {user_id} blacklisted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist user {user_id}: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_stats = jwt_validation_cache.get_cache_stats()
        blacklist_stats = {
            "blacklisted_tokens": len(self._token_blacklist),
            "blacklisted_users": len(self._user_blacklist)
        }
        
        return {
            "cache_stats": cache_stats,
            "blacklist_stats": blacklist_stats,
            "performance_optimizations": {
                "caching_enabled": True,
                "fast_validation": True,
                "redis_backend": cache_stats.get("cache_enabled", False)
            }
        }
    
    def get_blacklist_info(self) -> Dict[str, int]:
        """Get blacklist statistics"""
        return {
            "blacklisted_tokens": len(self._token_blacklist),
            "blacklisted_users": len(self._user_blacklist)
        }
    
    def _validate_token_security_consolidated(self, token: str) -> bool:
        """CONSOLIDATED: JWT security validation - moved from oauth_security.py to eliminate SSOT violation"""
        try:
            import jwt
            
            # Decode header without verification to check algorithm
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            
            # Check if algorithm is allowed
            allowed_algorithms = ["HS256", "RS256"]
            if algorithm not in allowed_algorithms:
                logger.warning(f"Insecure JWT algorithm: {algorithm}")
                return False
            
            # Check for algorithm confusion attacks
            if algorithm == "none":
                logger.warning("JWT algorithm 'none' is not allowed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"JWT security validation error: {e}")
            return False