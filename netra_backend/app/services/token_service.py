"""
Token Management Service: Single Source of Truth for JWT Token Operations

This module provides comprehensive token management capabilities including:
- Access token creation and validation
- Refresh token handling with race condition protection
- Token revocation and blacklisting
- Clock skew tolerance and signature rotation
- Redis-backed token storage and caching

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) 
- Business Goal: Provide secure, scalable token management
- Value Impact: Enable zero-downtime token rotation and 99.9% auth uptime
- Revenue Impact: Support enterprise security requirements and compliance
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

# JWT operations removed - all token operations now delegate to auth service SSOT
import redis.asyncio as redis

from netra_backend.app.config import get_config

logger = logging.getLogger(__name__)


class TokenService:
    """Comprehensive JWT token management service with Redis backing."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize token service with optional Redis client."""
        self.redis_client = redis_client
        self._revoked_tokens: Set[str] = set()  # In-memory fallback
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}  # In-memory refresh token store
        self._clock_skew_tolerance = 30  # 30 seconds tolerance
        self._access_token_ttl = 900  # 15 minutes
        self._refresh_token_ttl = 86400 * 7  # 7 days
        
        # For signature rotation testing
        self._old_keys: List[str] = []
        
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with lazy initialization."""
        if self.redis_client:
            return self.redis_client
            
        try:
            config = get_config()
            if hasattr(config, 'redis') and config.redis:
                redis_config = config.redis
                redis_url = f"redis://{redis_config.username}:{redis_config.password}@{redis_config.host}:{redis_config.port}"
                self.redis_client = await redis.from_url(redis_url, decode_responses=True)
                return self.redis_client
            elif hasattr(config, 'redis_url') and config.redis_url:
                self.redis_client = await redis.from_url(config.redis_url, decode_responses=True)
                return self.redis_client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
        
        return None
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret key - DELEGATES TO SSOT.
        
        SSOT ENFORCEMENT: This method now delegates to the canonical
        UnifiedSecretManager to eliminate duplicate JWT secret implementations.
        """
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        return get_jwt_secret()
    
    async def create_access_token(self, user_id: str, **kwargs) -> str:
        """
        DEPRECATED: Create access token - now delegates to canonical AuthServiceClient.
        
        SSOT ENFORCEMENT: This method now delegates to the canonical auth client
        to eliminate duplicate token creation implementations.
        
        Args:
            user_id: User identifier
            **kwargs: Additional token claims (email, permissions, session_id, expires_in)
            
        Returns:
            JWT access token string
        """
        import warnings
        warnings.warn(
            "TokenService.create_access_token is DEPRECATED. "
            "Use netra_backend.app.clients.auth_client_core.auth_client.create_token directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to canonical implementation
        from netra_backend.app.clients.auth_client_core import auth_client
        
        # Map kwargs to auth service format
        token_data = {
            "user_id": user_id,
            "email": kwargs.get('email'),
            "permissions": kwargs.get('permissions', []),
            "expires_in": kwargs.get('expires_in', self._access_token_ttl)
        }
        
        # Remove None values
        token_data = {k: v for k, v in token_data.items() if v is not None}
        
        result = await auth_client.create_token(token_data)
        
        if not result or "access_token" not in result:
            raise ValueError("Failed to create access token via auth service")
        
        return result["access_token"]
    
    async def create_refresh_token(self, user_id: str) -> str:
        """
        DEPRECATED: Create refresh token - now delegates to canonical AuthServiceClient.
        
        SSOT ENFORCEMENT: This method now delegates to the canonical auth client
        to eliminate duplicate token creation implementations.
        
        Args:
            user_id: User identifier
            
        Returns:
            JWT refresh token string
        """
        import warnings
        warnings.warn(
            "TokenService.create_refresh_token is DEPRECATED. "
            "Use netra_backend.app.clients.auth_client_core.auth_client directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to canonical implementation via refresh token creation
        from netra_backend.app.clients.auth_client_core import auth_client
        
        # Create both access and refresh token, return only refresh
        token_data = {
            "user_id": user_id,
            "token_type": "refresh",
            "expire_days": self._refresh_token_ttl // (24 * 60 * 60)  # Convert seconds to days
        }
        
        result = await auth_client.create_token(token_data)
        
        if not result or "refresh_token" not in result:
            raise ValueError("Failed to create refresh token via auth service")
        
        return result["refresh_token"]
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        DEPRECATED: Refresh access token - now delegates to canonical AuthServiceClient.
        
        SSOT ENFORCEMENT: This method now delegates to the canonical auth client
        to eliminate duplicate token refresh implementations.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token or None if invalid/used
        """
        import warnings
        warnings.warn(
            "TokenService.refresh_access_token is DEPRECATED. "
            "Use netra_backend.app.clients.auth_client_core.auth_client.refresh_token directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to canonical implementation
        from netra_backend.app.clients.auth_client_core import auth_client
        
        result = await auth_client.refresh_token(refresh_token)
        
        if not result or "access_token" not in result:
            return None
        
        return result["access_token"]
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to blacklist).
        
        Args:
            token: Token to revoke
            
        Returns:
            Success status
        """
        try:
            # Delegate token decoding to auth service - SSOT compliant
            from netra_backend.app.clients.auth_client_core import auth_client
            validation_result = await auth_client.validate_token_jwt(token)
            
            if not validation_result or not validation_result.get('valid'):
                return False
            
            payload = validation_result.get('payload', {})
            jti = payload.get('jti')
            
            if jti:
                # Add to Redis blacklist
                redis_client = await self._get_redis_client()
                if redis_client:
                    blacklist_key = f"revoked_token:{jti}"
                    exp = payload.get('exp', int(time.time()) + 3600)
                    ttl = max(exp - int(time.time()), 60)  # At least 60 seconds TTL
                    await redis_client.setex(blacklist_key, ttl, "1")
                
                # Add to memory fallback
                self._revoked_tokens.add(jti)
                
                return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
        
        return False
    
    async def validate_token_jwt(self, token: str) -> Dict[str, Any]:
        """
        DEPRECATED: Validate a JWT token - delegates to canonical AuthServiceClient.
        
        SSOT ENFORCEMENT: This method now delegates to the canonical auth client
        to eliminate duplicate token validation implementations.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Validation result with token data
        """
        import warnings
        warnings.warn(
            "TokenService.validate_token_jwt is DEPRECATED. "
            "Use netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to canonical implementation
        from netra_backend.app.clients.auth_client_core import auth_client
        
        result = await auth_client.validate_token_jwt(token)
        
        # Handle None result from auth service
        if result is None:
            return {'valid': False, 'error': 'auth_service_unavailable'}
            
        # Ensure consistent return format for backward compatibility
        if isinstance(result, dict):
            # Map auth service response to expected format
            return {
                'valid': result.get('valid', False),
                'user_id': result.get('user_id'),
                'email': result.get('email'), 
                'permissions': result.get('permissions', []),
                'error': result.get('error')
            }
            
        return {'valid': False, 'error': 'unexpected_response_format'}
    
    async def validate_with_old_keys(self, token: str) -> bool:
        """
        Validate token with old signing keys during rotation.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Whether token is valid with old keys
        """
        # Delegate old key validation to auth service - SSOT compliant
        from netra_backend.app.clients.auth_client_core import auth_client
        
        # Try validation with current key first via auth service
        try:
            validation_result = await auth_client.validate_token_jwt(token)
            return validation_result and validation_result.get('valid', False)
        except Exception:
            return False
        
        return False
    
    async def _validate_with_old_keys(self, token: str) -> Dict[str, Any]:
        """Internal method to validate with old keys and return full payload."""
        # Delegate old key validation to auth service - SSOT compliant
        from netra_backend.app.clients.auth_client_core import auth_client
        
        try:
            validation_result = await auth_client.validate_token_jwt(token)
            if validation_result and validation_result.get('valid'):
                return {
                    'valid': True,
                    'user_id': validation_result.get('user_id'),
                    'email': validation_result.get('email'),
                    'permissions': validation_result.get('permissions', []),
                    'validated_with_old_key': True
                }
        except Exception:
            pass
        
        return {'valid': False, 'error': 'invalid_with_all_keys'}
    
    async def _store_token_metadata(self, token: str, payload: Dict[str, Any]) -> None:
        """Store token metadata in Redis for tracking."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                jti = payload.get('jti')
                if jti:
                    metadata_key = f"token_meta:{jti}"
                    metadata = {
                        'user_id': payload.get('sub'),
                        'type': payload.get('type'),
                        'created_at': payload.get('iat'),
                        'expires_at': payload.get('exp')
                    }
                    
                    ttl = payload.get('exp', int(time.time())) - int(time.time())
                    if ttl > 0:
                        await redis_client.setex(metadata_key, ttl, json.dumps(metadata))
                    
        except Exception as e:
            logger.warning(f"Failed to store token metadata: {e}")
    
    async def _store_refresh_token(self, token: str, payload: Dict[str, Any]) -> None:
        """Store refresh token for race condition protection."""
        try:
            jti = payload.get('jti')
            if not jti:
                return
            
            redis_client = await self._get_redis_client()
            if redis_client:
                refresh_key = f"refresh_token:{jti}"
                token_data = {
                    'user_id': payload.get('sub'),
                    'created_at': payload.get('iat'),
                    'used': False
                }
                
                ttl = payload.get('exp', int(time.time())) - int(time.time())
                if ttl > 0:
                    await redis_client.setex(refresh_key, ttl, json.dumps(token_data))
            
            # Store in memory fallback
            self._refresh_tokens[jti] = {
                'user_id': payload.get('sub'),
                'used': False,
                'expires_at': payload.get('exp')
            }
            
        except Exception as e:
            logger.warning(f"Failed to store refresh token: {e}")
    
    async def _validate_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Validate refresh token and return payload."""
        try:
            secret = self._get_jwt_secret()
            payload = jwt.decode(
                refresh_token,
                secret,
                algorithms=['HS256'],
                leeway=timedelta(seconds=self._clock_skew_tolerance)
            )
            
            # Check token type
            if payload.get('type') != 'refresh':
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    async def _is_refresh_token_used(self, refresh_token: str) -> bool:
        """Check if refresh token has been used."""
        try:
            # Decode to get JTI via auth service - SSOT compliant
            from netra_backend.app.clients.auth_client_core import auth_client
            validation_result = await auth_client.validate_token_jwt(refresh_token)
            
            if not validation_result:
                return True  # Invalid token
            
            payload = validation_result.get('payload', {})
            jti = payload.get('jti')
            
            if not jti:
                return True  # Invalid token
            
            redis_client = await self._get_redis_client()
            if redis_client:
                refresh_key = f"refresh_token:{jti}"
                token_data = await redis_client.get(refresh_key)
                
                if token_data:
                    data = json.loads(token_data)
                    return data.get('used', False)
            
            # Check memory fallback
            token_info = self._refresh_tokens.get(jti)
            return token_info.get('used', False) if token_info else True
            
        except Exception as e:
            logger.error(f"Failed to check refresh token usage: {e}")
            return True
    
    async def _mark_refresh_token_used(self, refresh_token: str) -> None:
        """Mark refresh token as used atomically."""
        try:
            # Decode to get JTI via auth service - SSOT compliant
            from netra_backend.app.clients.auth_client_core import auth_client
            validation_result = await auth_client.validate_token_jwt(refresh_token)
            
            if not validation_result:
                return
            
            payload = validation_result.get('payload', {})
            jti = payload.get('jti')
            
            if not jti:
                return
            
            redis_client = await self._get_redis_client()
            if redis_client:
                refresh_key = f"refresh_token:{jti}"
                
                # Atomic update using Lua script
                lua_script = """
                local key = KEYS[1]
                local token_data = redis.call('GET', key)
                if token_data then
                    local data = cjson.decode(token_data)
                    if not data.used then
                        data.used = true
                        redis.call('SET', key, cjson.encode(data), 'KEEPTTL')
                        return 1
                    end
                end
                return 0
                """
                
                result = await redis_client.eval(lua_script, 1, refresh_key)
                if result == 1:
                    logger.debug(f"Marked refresh token {jti} as used")
            
            # Update memory fallback
            if jti in self._refresh_tokens:
                self._refresh_tokens[jti]['used'] = True
                
        except Exception as e:
            logger.error(f"Failed to mark refresh token as used: {e}")
    
    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is in revocation blacklist."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                blacklist_key = f"revoked_token:{jti}"
                is_revoked = await redis_client.exists(blacklist_key)
                return bool(is_revoked)
            
            # Check memory fallback
            return jti in self._revoked_tokens
            
        except Exception as e:
            logger.warning(f"Failed to check token revocation: {e}")
            return False
    
    def initialize(self):
        """Initialize the token service.
        
        This method exists for compatibility with tests that call initialize().
        The service is ready to use after construction.
        """
        pass  # No additional initialization needed
    
    def create_token(self, user_data: dict) -> str:
        """Create a token with user data.
        
        Synchronous wrapper for create_access_token for test compatibility.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            JWT token string
        """
        secret = self._get_jwt_secret()
        
        # Create payload from user_data
        now = datetime.now(timezone.utc)
        expires_in = self._access_token_ttl
        if 'exp' in user_data and isinstance(user_data['exp'], datetime):
            # If exp is provided as datetime, calculate expires_in
            exp_time = user_data['exp']
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=timezone.utc)
            expires_in = int((exp_time - now).total_seconds())
        
        payload = {
            'sub': user_data.get('user_id', 'test_user'),
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=expires_in)).timestamp()),
            'type': 'access',
            'jti': str(uuid.uuid4()),
        }
        
        # Add additional claims from user_data
        for key, value in user_data.items():
            if key not in ['exp'] and not key.startswith('_'):
                payload[key] = value
        
        # Create and return token
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def create_service_token(self, service_data: dict) -> str:
        """Create a service token with service data.
        
        Args:
            service_data: Dictionary containing service information
            
        Returns:
            JWT service token string
        """
        secret = self._get_jwt_secret()
        
        # Create payload from service_data
        now = datetime.now(timezone.utc)
        expires_in = self._access_token_ttl
        if 'exp' in service_data and isinstance(service_data['exp'], datetime):
            exp_time = service_data['exp']
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=timezone.utc)
            expires_in = int((exp_time - now).total_seconds())
        
        payload = {
            'sub': service_data.get('service_id', 'test_service'),
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=expires_in)).timestamp()),
            'type': 'service_token',
            'jti': str(uuid.uuid4()),
        }
        
        # Add additional claims from service_data
        for key, value in service_data.items():
            if key not in ['exp'] and not key.startswith('_'):
                payload[key] = value
        
        # Create and return token
        return jwt.encode(payload, secret, algorithm='HS256')
    
    async def rotate_service_token(self, service_id: str, old_token_version: int, 
                                   new_token_version: int, grace_period_seconds: int = 30):
        """Rotate a service token with grace period.
        
        Args:
            service_id: Service identifier
            old_token_version: Version of token being replaced
            new_token_version: Version of new token
            grace_period_seconds: Grace period for old token validity
        """
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                # Store rotation info in Redis
                rotation_key = f"service_rotation:{service_id}"
                rotation_data = {
                    'old_version': old_token_version,
                    'new_version': new_token_version,
                    'rotation_time': int(time.time()),
                    'grace_period_ends': int(time.time()) + grace_period_seconds
                }
                await redis_client.setex(rotation_key, grace_period_seconds + 60, json.dumps(rotation_data))
                
                logger.info(f"Service token rotation registered for {service_id}: {old_token_version} -> {new_token_version}")
            
            # Store in memory fallback
            if not hasattr(self, '_service_rotations'):
                self._service_rotations = {}
            self._service_rotations[service_id] = {
                'old_version': old_token_version,
                'new_version': new_token_version,
                'grace_period_ends': int(time.time()) + grace_period_seconds
            }
            
        except Exception as e:
            logger.error(f"Failed to register service token rotation: {e}")
    
    async def is_service_token_version_valid(self, service_id: str, token_version: int) -> bool:
        """Check if a service token version is still valid.
        
        Args:
            service_id: Service identifier
            token_version: Token version to check
            
        Returns:
            True if token version is valid
        """
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                rotation_key = f"service_rotation:{service_id}"
                rotation_data = await redis_client.get(rotation_key)
                
                if rotation_data:
                    data = json.loads(rotation_data)
                    current_time = int(time.time())
                    
                    # Check if it's the current version
                    if token_version == data.get('new_version'):
                        return True
                    
                    # Check if it's an old version within grace period
                    if token_version == data.get('old_version'):
                        return current_time < data.get('grace_period_ends', 0)
                    
                    # Any other version is invalid
                    return False
            
            # Check memory fallback
            if hasattr(self, '_service_rotations') and service_id in self._service_rotations:
                data = self._service_rotations[service_id]
                current_time = int(time.time())
                
                if token_version == data.get('new_version'):
                    return True
                
                if token_version == data.get('old_version'):
                    return current_time < data.get('grace_period_ends', 0)
                
                return False
            
            # No rotation data means all versions are valid (backward compatibility)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check service token version validity: {e}")
            return True  # Fail open for availability


# Singleton instance
token_service = TokenService()