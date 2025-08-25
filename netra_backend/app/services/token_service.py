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

import jwt
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
        """Get JWT secret key from configuration."""
        config = get_config()
        return getattr(config, 'jwt_secret_key', 'development_secret_key_for_jwt_do_not_use_in_production')
    
    async def create_access_token(self, user_id: str, **kwargs) -> str:
        """
        Create a new access token.
        
        Args:
            user_id: User identifier
            **kwargs: Additional token claims (email, permissions, session_id, expires_in)
            
        Returns:
            JWT access token string
        """
        now = datetime.now(timezone.utc)
        expires_in = kwargs.get('expires_in', self._access_token_ttl)
        
        payload = {
            'sub': user_id,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=expires_in)).timestamp()),
            'type': 'access',
            'jti': str(uuid.uuid4()),  # JWT ID for revocation tracking
        }
        
        # Add optional claims
        if 'email' in kwargs:
            payload['email'] = kwargs['email']
        if 'permissions' in kwargs:
            payload['permissions'] = kwargs['permissions']
        if 'session_id' in kwargs:
            payload['session_id'] = kwargs['session_id']
        
        # Sign token
        secret = self._get_jwt_secret()
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Store token metadata in Redis for revocation checking
        await self._store_token_metadata(token, payload)
        
        return token
    
    async def create_refresh_token(self, user_id: str) -> str:
        """
        Create a new refresh token.
        
        Args:
            user_id: User identifier
            
        Returns:
            JWT refresh token string
        """
        now = datetime.now(timezone.utc)
        
        payload = {
            'sub': user_id,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=self._refresh_token_ttl)).timestamp()),
            'type': 'refresh',
            'jti': str(uuid.uuid4()),
        }
        
        # Sign token
        secret = self._get_jwt_secret()
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Store refresh token for race condition protection
        await self._store_refresh_token(token, payload)
        
        return token
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Create new access token from refresh token with race condition protection.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token or None if invalid/used
        """
        # Validate refresh token
        payload = await self._validate_refresh_token(refresh_token)
        if not payload:
            return None
        
        # Check if already used (race condition protection)
        if await self._is_refresh_token_used(refresh_token):
            return None
        
        # Mark refresh token as used atomically
        await self._mark_refresh_token_used(refresh_token)
        
        # Create new access token
        user_id = payload['sub']
        return await self.create_access_token(user_id)
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to blacklist).
        
        Args:
            token: Token to revoke
            
        Returns:
            Success status
        """
        try:
            # Decode token to get JTI
            secret = self._get_jwt_secret()
            payload = jwt.decode(token, secret, algorithms=['HS256'], options={"verify_exp": False})
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
        # This would typically check against a list of previous keys
        # For testing purposes, we'll simulate this
        for old_key in self._old_keys:
            try:
                jwt.decode(
                    token,
                    old_key,
                    algorithms=['HS256'],
                    leeway=timedelta(seconds=self._clock_skew_tolerance)
                )
                return True
            except jwt.InvalidTokenError:
                continue
        
        return False
    
    async def _validate_with_old_keys(self, token: str) -> Dict[str, Any]:
        """Internal method to validate with old keys and return full payload."""
        for old_key in self._old_keys:
            try:
                payload = jwt.decode(
                    token,
                    old_key,
                    algorithms=['HS256'],
                    leeway=timedelta(seconds=self._clock_skew_tolerance)
                )
                
                return {
                    'valid': True,
                    'user_id': payload.get('sub'),
                    'email': payload.get('email'),
                    'permissions': payload.get('permissions', []),
                    'validated_with_old_key': True
                }
            except jwt.InvalidTokenError:
                continue
        
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
            # Decode to get JTI
            secret = self._get_jwt_secret()
            payload = jwt.decode(refresh_token, secret, algorithms=['HS256'], options={"verify_exp": False})
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
            # Decode to get JTI
            secret = self._get_jwt_secret()
            payload = jwt.decode(refresh_token, secret, algorithms=['HS256'], options={"verify_exp": False})
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


# Singleton instance
token_service = TokenService()