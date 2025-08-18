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
    
    async def _check_auth_service_enabled(self, token: str) -> Optional[Dict]:
        """Check if auth service is enabled, return local validation if not."""
        if not self.settings.enabled:
            return await self._local_validate(token)
        return None
    
    async def _try_cached_token(self, token: str) -> Optional[Dict]:
        """Try to get token from cache."""
        return self.token_cache.get_cached_token(token)
    
    async def _validate_with_circuit_breaker(self, token: str) -> Optional[Dict]:
        """Validate token using circuit breaker."""
        return await self.circuit_manager.call_with_breaker(
            self._validate_token_remote, token
        )
    
    async def _cache_validation_result(self, token: str, result: Optional[Dict]) -> Optional[Dict]:
        """Cache validation result if successful."""
        if result:
            self.token_cache.cache_token(token, result)
        return result
    
    async def _handle_validation_error(self, token: str, error: Exception) -> Optional[Dict]:
        """Handle validation error and fallback."""
        logger.error(f"Token validation failed: {error}")
        return await self._local_validate(token)
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate access token with caching."""
        disabled_result = await self._check_auth_service_enabled(token)
        if disabled_result is not None:
            return disabled_result
        
        cached = await self._try_cached_token(token)
        if cached:
            return cached
        
        try:
            result = await self._validate_with_circuit_breaker(token)
            return await self._cache_validation_result(token, result)
        except Exception as e:
            return await self._handle_validation_error(token, e)
    
    async def _build_validation_request(self, token: str) -> Dict:
        """Build validation request payload."""
        return {"token": token}
    
    async def _parse_validation_response(self, data: Dict) -> Dict:
        """Parse validation response data."""
        return {
            "valid": data.get("valid", False),
            "user_id": data.get("user_id"),
            "email": data.get("email"),
            "permissions": data.get("permissions", [])
        }
    
    async def _validate_token_remote(self, token: str) -> Optional[Dict]:
        """Remote token validation."""
        client = await self._get_client()
        request_data = await self._build_validation_request(token)
        
        try:
            response = await client.post("/auth/validate", json=request_data)
            if response.status_code == 200:
                return await self._parse_validation_response(response.json())
            return None
        except Exception as e:
            logger.error(f"Remote validation error: {e}")
            raise
    
    async def _build_login_request(self, email: str, password: str, provider: str) -> Dict:
        """Build login request payload."""
        return {
            "email": email,
            "password": password,
            "provider": provider
        }
    
    async def _execute_login_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute login request."""
        client = await self._get_client()
        response = await client.post("/auth/login", json=request_data)
        return response.json() if response.status_code == 200 else None
    
    async def login(self, email: str, password: str, 
                   provider: str = "local") -> Optional[Dict]:
        """User login through auth service."""
        if not self.settings.enabled:
            return None
        
        request_data = await self._build_login_request(email, password, provider)
        try:
            return await self._execute_login_request(request_data)
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None
    
    async def _build_logout_headers(self, token: str) -> Dict[str, str]:
        """Build logout request headers."""
        return {"Authorization": f"Bearer {token}"}
    
    async def _build_logout_payload(self, session_id: Optional[str]) -> Dict:
        """Build logout request payload."""
        return {"session_id": session_id} if session_id else {}
    
    async def _execute_logout_request(self, token: str, session_id: Optional[str]) -> bool:
        """Execute logout request."""
        client = await self._get_client()
        headers = await self._build_logout_headers(token)
        payload = await self._build_logout_payload(session_id)
        response = await client.post("/auth/logout", headers=headers, json=payload)
        return response.status_code == 200
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """User logout through auth service."""
        if not self.settings.enabled:
            return True
        
        try:
            result = await self._execute_logout_request(token, session_id)
            self.token_cache.invalidate_cached_token(token)
            return result
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def _build_refresh_request(self, refresh_token: str) -> Dict:
        """Build refresh token request payload."""
        return {"refresh_token": refresh_token}
    
    async def _execute_refresh_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute refresh token request."""
        client = await self._get_client()
        response = await client.post("/auth/refresh", json=request_data)
        return response.json() if response.status_code == 200 else None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token."""
        if not self.settings.enabled:
            return None
        
        request_data = await self._build_refresh_request(refresh_token)
        try:
            return await self._execute_refresh_request(request_data)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def _check_service_token_prereqs(self) -> bool:
        """Check service token prerequisites."""
        if not self.settings.enabled:
            return False
        if not self.settings.is_service_secret_configured():
            logger.warning("Service secret not configured")
            return False
        return True
    
    async def _build_service_token_request(self) -> Dict:
        """Build service token request payload."""
        service_id, service_secret = self.settings.get_service_credentials()
        return {
            "service_id": service_id,
            "service_secret": service_secret
        }
    
    async def _execute_service_token_request(self, request_data: Dict) -> Optional[str]:
        """Execute service token request."""
        client = await self._get_client()
        response = await client.post("/auth/service-token", json=request_data)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    async def create_service_token(self) -> Optional[str]:
        """Get service-to-service auth token."""
        if not await self._check_service_token_prereqs():
            return None
        
        request_data = await self._build_service_token_request()
        try:
            return await self._execute_service_token_request(request_data)
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