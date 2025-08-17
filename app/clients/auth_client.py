"""
Auth Service Client - Backend integration with auth microservice
Implements caching, circuit breaker, and retry logic
"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache
from enum import Enum
from dataclasses import dataclass
import logging

from app.core.circuit_breaker_core import CircuitBreaker
from app.core.circuit_breaker_types import CircuitConfig

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types for auth configuration."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class OAuthConfig:
    """OAuth configuration for environment."""
    client_id: str = ""
    client_secret: str = ""
    redirect_uris: List[str] = None
    javascript_origins: List[str] = None
    allow_dev_login: bool = False
    allow_mock_auth: bool = False
    use_proxy: bool = False
    proxy_url: str = ""

    def __post_init__(self):
        """Initialize lists if None."""
        if self.redirect_uris is None:
            self.redirect_uris = []
        if self.javascript_origins is None:
            self.javascript_origins = []


class AuthServiceClient:
    """Client for communicating with auth service"""
    
    def __init__(self):
        self.base_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
        self.enabled = os.getenv("AUTH_SERVICE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))  # 5 min
        self.circuit_breaker = CircuitBreaker(CircuitConfig(
            name="auth_service",
            failure_threshold=5,
            recovery_timeout=60,
            timeout_seconds=30
        ))
        self._token_cache: Dict[str, CachedToken] = {}
        self._client = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_keepalive_connections=5)
            )
        return self._client
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate access token with caching"""
        if not self.enabled:
            # Fallback to local validation if service disabled
            return await self._local_validate(token)
        
        # Check cache first
        cached = self._get_cached_token(token)
        if cached:
            return cached
        
        # Call auth service with circuit breaker
        try:
            result = await self.circuit_breaker.call(
                self._validate_token_remote, token
            )
            if result:
                self._cache_token(token, result)
            return result
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            # Fallback to local validation
            return await self._local_validate(token)
    
    async def _validate_token_remote(self, token: str) -> Optional[Dict]:
        """Remote token validation"""
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
        """User login through auth service"""
        if not self.enabled:
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
        """User logout through auth service"""
        if not self.enabled:
            return True
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                "/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                json={"session_id": session_id} if session_id else {}
            )
            
            # Clear token from cache
            self._invalidate_cached_token(token)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token"""
        if not self.enabled:
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
        """Get service-to-service auth token"""
        if not self.enabled:
            return None
        
        service_id = os.getenv("SERVICE_ID", "backend")
        service_secret = os.getenv("SERVICE_SECRET")
        
        if not service_secret:
            logger.warning("Service secret not configured")
            return None
        
        client = await self._get_client()
        
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
    
    def _get_cached_token(self, token: str) -> Optional[Dict]:
        """Get token from cache if valid"""
        if token in self._token_cache:
            cached = self._token_cache[token]
            if cached.is_valid():
                return cached.data
            else:
                del self._token_cache[token]
        return None
    
    def _cache_token(self, token: str, data: Dict):
        """Cache validated token"""
        self._token_cache[token] = CachedToken(data, self.cache_ttl)
    
    def _invalidate_cached_token(self, token: str):
        """Remove token from cache"""
        if token in self._token_cache:
            del self._token_cache[token]
    
    async def _local_validate(self, token: str) -> Optional[Dict]:
        """Local token validation fallback"""
        # In production, this should always fail if auth service is down
        # Consider implementing JWT validation directly here if needed
        logger.warning("Auth service unavailable, rejecting token")
        return {"valid": False}
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
    
    def detect_environment(self) -> Environment:
        """Detect current environment from environment variables."""
        env_override = os.getenv("ENVIRONMENT", "").lower()
        if env_override:
            return self._parse_environment(env_override)
        if self._check_testing_flag():
            return Environment.TESTING
        return self._detect_from_cloud_run()
    
    def _parse_environment(self, env_str: str) -> Environment:
        """Parse environment string to enum."""
        env_map = {
            "development": Environment.DEVELOPMENT,
            "testing": Environment.TESTING,
            "staging": Environment.STAGING,
            "production": Environment.PRODUCTION,
        }
        if env_str in env_map:
            return env_map[env_str]
        logger.warning(f"Unknown environment '{env_str}', defaulting to development")
        return Environment.DEVELOPMENT
    
    def _check_testing_flag(self) -> bool:
        """Check if TESTING flag is set."""
        return os.getenv("TESTING") in ["true", "1"]
    
    def _detect_from_cloud_run(self) -> Environment:
        """Detect environment from Cloud Run variables."""
        k_service = os.getenv("K_SERVICE", "")
        k_revision = os.getenv("K_REVISION", "")
        if k_service or k_revision:
            return self._detect_cloud_run_environment(k_service, k_revision)
        return Environment.DEVELOPMENT
    
    def _detect_cloud_run_environment(self, k_service: str, k_revision: str) -> Environment:
        """Detect environment from Cloud Run service names."""
        if self._is_production_service(k_service) or self._is_production_service(k_revision):
            return Environment.PRODUCTION
        if self._is_staging_service(k_service) or self._is_staging_service(k_revision):
            return Environment.STAGING
        return Environment.STAGING
    
    def _is_production_service(self, name: str) -> bool:
        """Check if service name indicates production."""
        name_lower = name.lower()
        return any(prod in name_lower for prod in ["prod", "backend"])
    
    def _is_staging_service(self, name: str) -> bool:
        """Check if service name indicates staging."""
        return "staging" in name.lower()
    
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        environment = self.detect_environment()
        config_map = {
            Environment.DEVELOPMENT: self._get_dev_oauth_config,
            Environment.TESTING: self._get_test_oauth_config,
            Environment.STAGING: self._get_staging_oauth_config,
            Environment.PRODUCTION: self._get_prod_oauth_config,
        }
        return config_map.get(environment, lambda: OAuthConfig())()
    
    def _get_dev_oauth_config(self) -> OAuthConfig:
        """Get development OAuth configuration."""
        client_id = self._get_oauth_credential("DEV", "CLIENT_ID")
        client_secret = self._get_oauth_credential("DEV", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_dev_redirect_uris(),
            javascript_origins=self._get_dev_js_origins(),
            allow_dev_login=True, allow_mock_auth=True, use_proxy=False
        )
    
    def _get_test_oauth_config(self) -> OAuthConfig:
        """Get testing OAuth configuration."""
        client_id = self._get_oauth_credential("TEST", "CLIENT_ID")
        client_secret = self._get_oauth_credential("TEST", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=["http://test.local:8000/api/auth/callback"],
            javascript_origins=["http://test.local:3000"],
            allow_dev_login=False, allow_mock_auth=True, use_proxy=False
        )
    
    def _get_staging_oauth_config(self) -> OAuthConfig:
        """Get staging OAuth configuration."""
        client_id = self._get_oauth_credential("STAGING", "CLIENT_ID")
        client_secret = self._get_oauth_credential("STAGING", "CLIENT_SECRET")
        is_pr_environment = bool(os.getenv("PR_NUMBER"))
        if is_pr_environment:
            return self._get_pr_oauth_config(client_id, client_secret)
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_staging_redirect_uris(),
            javascript_origins=self._get_staging_js_origins(),
            allow_dev_login=False, allow_mock_auth=False, use_proxy=False
        )
    
    def _get_prod_oauth_config(self) -> OAuthConfig:
        """Get production OAuth configuration."""
        client_id = self._get_oauth_credential("PROD", "CLIENT_ID")
        client_secret = self._get_oauth_credential("PROD", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_prod_redirect_uris(),
            javascript_origins=self._get_prod_js_origins(),
            allow_dev_login=False, allow_mock_auth=False, use_proxy=False
        )
    
    def _get_pr_oauth_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Get PR environment OAuth configuration with proxy."""
        pr_number = os.getenv("PR_NUMBER", "")
        proxy_url = "https://auth.staging.netrasystems.ai"
        origins = [proxy_url]
        if pr_number:
            origins.append(f"https://pr-{pr_number}.staging.netrasystems.ai")
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=[f"{proxy_url}/callback"], javascript_origins=origins,
            allow_dev_login=False, allow_mock_auth=False,
            use_proxy=True, proxy_url=proxy_url
        )
    
    def _get_oauth_credential(self, env_suffix: str, cred_type: str) -> str:
        """Get OAuth credential with fallback chain."""
        env_var = f"GOOGLE_OAUTH_CLIENT_{cred_type}_{env_suffix}"
        credential = os.getenv(env_var, "")
        if not credential:
            credential = self._get_fallback_credential(cred_type)
        if not credential:
            logger.error(f"Missing OAuth credential: {env_var}")
        return credential
    
    def _get_fallback_credential(self, cred_type: str) -> str:
        """Get fallback OAuth credential."""
        if cred_type == "CLIENT_ID":
            fallback_var = "GOOGLE_CLIENT_ID"
        else:
            fallback_var = f"GOOGLE_CLIENT_{cred_type}"
        return os.getenv(fallback_var, "")
    
    def _get_dev_redirect_uris(self) -> List[str]:
        """Get development redirect URIs."""
        base_uris = ["http://localhost:8000/api/auth/callback",
                     "http://localhost:3000/api/auth/callback",
                     "http://localhost:3010/api/auth/callback"]
        auth_uris = ["http://localhost:3000/auth/callback",
                     "http://localhost:3010/auth/callback"]
        return base_uris + auth_uris
    
    def _get_dev_js_origins(self) -> List[str]:
        """Get development JavaScript origins."""
        return ["http://localhost:3000", "http://localhost:3010", "http://localhost:8000"]
    
    def _get_staging_redirect_uris(self) -> List[str]:
        """Get staging redirect URIs."""
        return ["https://staging.netrasystems.ai/api/auth/callback",
                "https://app.staging.netrasystems.ai/callback"]
    
    def _get_staging_js_origins(self) -> List[str]:
        """Get staging JavaScript origins."""
        return ["https://staging.netrasystems.ai", "https://app.staging.netrasystems.ai"]
    
    def _get_prod_redirect_uris(self) -> List[str]:
        """Get production redirect URIs."""
        return ["https://api.netrasystems.ai/api/auth/callback",
                "https://netrasystems.ai/callback"]
    
    def _get_prod_js_origins(self) -> List[str]:
        """Get production JavaScript origins."""
        return ["https://netrasystems.ai", "https://api.netrasystems.ai"]


class CachedToken:
    """Cached token with TTL"""
    
    def __init__(self, data: Dict, ttl_seconds: int):
        self.data = data
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid"""
        return datetime.utcnow() < self.expires_at


# CircuitBreaker class removed - now using core implementation


# Global client instance
auth_client = AuthServiceClient()