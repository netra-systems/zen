"""
Core auth service client functionality.
Handles token validation, authentication, and service-to-service communication.
"""

import httpx
import logging
from typing import Optional, Dict

from .auth_client_cache import AuthTokenCache, AuthCircuitBreakerManager, AuthServiceSettings
from .auth_client_config import EnvironmentDetector, OAuthConfigGenerator, OAuthConfig

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for communicating with auth service."""
    
    def __init__(self):
        self.settings = AuthServiceSettings()
        self.token_cache = AuthTokenCache(self.settings.cache_ttl)
        self.circuit_manager = AuthCircuitBreakerManager()
        self.environment_detector = EnvironmentDetector()
        self.oauth_generator = OAuthConfigGenerator()
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.settings.base_url,
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_keepalive_connections=5)
            )
        return self._client
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate access token with caching."""
        if not self.settings.enabled:
            return await self._local_validate(token)
        
        # Check cache first
        cached = self.token_cache.get_cached_token(token)
        if cached:
            return cached
        
        # Call auth service with circuit breaker
        try:
            result = await self.circuit_manager.call_with_breaker(
                self._validate_token_remote, token
            )
            if result:
                self.token_cache.cache_token(token, result)
            return result
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return await self._local_validate(token)
    
    async def _validate_token_remote(self, token: str) -> Optional[Dict]:
        """Remote token validation."""
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/auth/validate",
                json={"token": token}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": data.get("valid", False),
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "permissions": data.get("permissions", [])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Remote validation error: {e}")
            raise
    
    async def login(self, email: str, password: str, 
                   provider: str = "local") -> Optional[Dict]:
        """User login through auth service."""
        if not self.settings.enabled:
            return None
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "provider": provider
                }
            )
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
        
        return None
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """User logout through auth service."""
        if not self.settings.enabled:
            return True
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                json={"session_id": session_id} if session_id else {}
            )
            
            # Clear token from cache
            self.token_cache.invalidate_cached_token(token)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token."""
        if not self.settings.enabled:
            return None
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
        
        return None
    
    async def create_service_token(self) -> Optional[str]:
        """Get service-to-service auth token."""
        if not self.settings.enabled:
            return None
        
        if not self.settings.is_service_secret_configured():
            logger.warning("Service secret not configured")
            return None
        
        client = await self._get_client()
        service_id, service_secret = self.settings.get_service_credentials()
        
        try:
            response = await client.post(
                "/auth/service-token",
                json={
                    "service_id": service_id,
                    "service_secret": service_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
            
        except Exception as e:
            logger.error(f"Service token creation failed: {e}")
        
        return None
    
    async def _local_validate(self, token: str) -> Optional[Dict]:
        """Local token validation fallback."""
        # In production, this should always fail if auth service is down
        logger.warning("Auth service unavailable, rejecting token")
        return {"valid": False}
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def detect_environment(self):
        """Detect current environment from environment variables."""
        return self.environment_detector.detect_environment()
    
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        environment = self.detect_environment()
        return self.oauth_generator.get_oauth_config(environment)


# Global client instance
auth_client = AuthServiceClient()