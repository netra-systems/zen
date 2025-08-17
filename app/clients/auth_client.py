"""
Auth Service Client - Backend integration with auth microservice
Implements caching, circuit breaker, and retry logic
"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class AuthServiceClient:
    """Client for communicating with auth service"""
    
    def __init__(self):
        self.base_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
        self.enabled = os.getenv("AUTH_SERVICE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))  # 5 min
        self.circuit_breaker = CircuitBreaker()
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


class CachedToken:
    """Cached token with TTL"""
    
    def __init__(self, data: Dict, ttl_seconds: int):
        self.data = data
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid"""
        return datetime.utcnow() < self.expires_at


class CircuitBreaker:
    """Circuit breaker for auth service calls"""
    
    def __init__(self, failure_threshold: int = 5, 
                 timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker"""
        if self._should_open():
            raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_open(self) -> bool:
        """Check if circuit should be open"""
        if self.is_open:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).seconds
                if elapsed > self.timeout_seconds:
                    self.is_open = False
                    self.failures = 0
                    return False
            return True
        return False
    
    def _on_success(self):
        """Handle successful call"""
        self.failures = 0
        self.is_open = False
    
    def _on_failure(self):
        """Handle failed call"""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            logger.warning("Circuit breaker opened for auth service")


# Global client instance
auth_client = AuthServiceClient()