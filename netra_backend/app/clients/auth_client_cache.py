"""
Auth client caching and circuit breaker functionality.
Handles token caching and resilience patterns for auth service calls.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from netra_backend.app.config import get_config
from netra_backend.app.core.circuit_breaker_core import CircuitBreaker
from netra_backend.app.core.circuit_breaker_types import CircuitConfig


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
        
        return self._validate_and_return_cached_token(token)
    
    def _validate_and_return_cached_token(self, token: str) -> Optional[Dict]:
        """Validate cached token and return if valid."""
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
        config = self._get_circuit_config()
        return CircuitBreaker(config)
    
    def _get_circuit_config(self) -> CircuitConfig:
        """Get circuit breaker configuration."""
        return CircuitConfig(
            name="auth_service",
            failure_threshold=5,
            recovery_timeout=60,
            timeout_seconds=30
        )
    
    async def call_with_breaker(self, func, *args, **kwargs):
        """Execute function call through circuit breaker."""
        async def wrapped_func():
            return await func(*args, **kwargs)
        return await self.circuit_breaker.call(wrapped_func)


class AuthServiceSettings:
    """Manages auth service configuration settings."""
    
    def __init__(self):
        config = get_config()
        
        # Use 127.0.0.1 instead of localhost for Windows compatibility
        self.base_url = config.auth_service_url
        # If localhost is in the URL, replace with 127.0.0.1 for Windows
        if "localhost" in self.base_url:
            self.base_url = self.base_url.replace("localhost", "127.0.0.1")
        
        # Check environment and test mode for auth service enabling
        fast_test_mode = config.auth_fast_test_mode.lower() == "true"
        
        # Disable auth service in fast test mode or test environment
        if fast_test_mode or config.environment == "test":
            self.enabled = False
        else:
            self.enabled = config.auth_service_enabled.lower() == "true"
        
        self.cache_ttl = int(config.auth_cache_ttl_seconds)  # 5 min
        self.service_id = config.service_id
        self.service_secret = config.service_secret
    
    def is_service_secret_configured(self) -> bool:
        """Check if service secret is configured."""
        return bool(self.service_secret)
    
    def get_service_credentials(self) -> tuple[str, str]:
        """Get service ID and secret."""
        return self.service_id, self.service_secret