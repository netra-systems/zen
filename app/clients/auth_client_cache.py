"""
Auth client caching and circuit breaker functionality.
Handles token caching and resilience patterns for auth service calls.
"""

import os
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.core.circuit_breaker_core import CircuitBreaker
from app.core.circuit_breaker_types import CircuitConfig


@dataclass
class CachedToken:
    """Cached token with TTL."""
    
    data: Dict
    expires_at: datetime
    
    def __init__(self, data: Dict, ttl_seconds: int):
        self.data = data
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return datetime.utcnow() < self.expires_at


class AuthTokenCache:
    """Manages token caching with TTL support."""
    
    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl = cache_ttl_seconds
        self._token_cache: Dict[str, CachedToken] = {}
    
    def _remove_expired_token(self, token: str) -> None:
        """Remove expired token from cache."""
        if token in self._token_cache:
            del self._token_cache[token]
    
    def get_cached_token(self, token: str) -> Optional[Dict]:
        """Get token from cache if valid."""
        if token not in self._token_cache:
            return None
        
        cached = self._token_cache[token]
        if cached.is_valid():
            return cached.data
        
        self._remove_expired_token(token)
        return None
    
    def cache_token(self, token: str, data: Dict) -> None:
        """Cache validated token."""
        self._token_cache[token] = CachedToken(data, self.cache_ttl)
    
    def invalidate_cached_token(self, token: str) -> None:
        """Remove token from cache."""
        if token in self._token_cache:
            del self._token_cache[token]
    
    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        self._token_cache.clear()


class AuthCircuitBreakerManager:
    """Manages circuit breaker for auth service calls."""
    
    def __init__(self):
        self.circuit_breaker = self._create_circuit_breaker()
    
    def _create_circuit_breaker(self) -> CircuitBreaker:
        """Create circuit breaker for auth service."""
        config = CircuitConfig(
            name="auth_service",
            failure_threshold=5,
            recovery_timeout=60,
            timeout_seconds=30
        )
        return CircuitBreaker(config)
    
    async def call_with_breaker(self, func, *args, **kwargs):
        """Execute function call through circuit breaker."""
        async def wrapped_func():
            return await func(*args, **kwargs)
        return await self.circuit_breaker.call(wrapped_func)


class AuthServiceSettings:
    """Manages auth service configuration settings."""
    
    def __init__(self):
        self.base_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
        self.enabled = os.getenv("AUTH_SERVICE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))  # 5 min
        self.service_id = os.getenv("SERVICE_ID", "backend")
        self.service_secret = os.getenv("SERVICE_SECRET")
    
    def is_service_secret_configured(self) -> bool:
        """Check if service secret is configured."""
        return bool(self.service_secret)
    
    def get_service_credentials(self) -> tuple[str, str]:
        """Get service ID and secret."""
        return self.service_id, self.service_secret