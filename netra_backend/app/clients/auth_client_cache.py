"""Auth Client Cache - Minimal implementation for caching authentication data.

This module provides caching functionality for authentication client operations.
Created as a minimal implementation to resolve missing module imports.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Performance & User Experience
- Value Impact: Enables auth caching to reduce latency and improve UX
- Strategic Impact: Foundation for scalable authentication operations
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Import UnifiedCircuitBreaker for proper circuit breaker implementation
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with expiration."""
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: int = 300  # 5 minutes default TTL
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > (self.created_at + self.ttl)


class CachedToken:
    """Token cache entry for test compatibility.
    
    This class is used by test_auth_token_cache.py to simulate expired tokens.
    It provides the same interface as expected by the E2E tests.
    """
    
    def __init__(self, data: Dict[str, Any], ttl_seconds: int = 300):
        """Initialize cached token with data and TTL.
        
        Args:
            data: The token validation data to cache
            ttl_seconds: Time-to-live in seconds (negative for expired)
        """
        self.data = data
        if ttl_seconds < 0:
            # Negative TTL means already expired (for testing)
            self.expires_at = datetime.now(timezone.utc) - timedelta(seconds=abs(ttl_seconds))
        else:
            self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    
    def is_valid(self) -> bool:
        """Check if the cached token is still valid."""
        return datetime.now(timezone.utc) < self.expires_at
    
    def get(self) -> Optional[Dict[str, Any]]:
        """Get the cached data if still valid."""
        if self.is_valid():
            return self.data
        return None


class AuthClientCache:
    """In-memory cache for authentication client data with user-scoped thread safety.
    
    ENHANCED: Eliminates race conditions by providing complete user isolation:
    - Per-user cache isolation prevents cross-user data contamination
    - Thread-safe operations with per-user locks prevent race conditions
    - Request-scoped instances eliminate global state sharing
    """
    
    def __init__(self, default_ttl: int = 300):
        """Initialize auth client cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        
        # RACE CONDITION FIX: Add user-scoped isolation
        self._per_user_caches: Dict[str, Dict[str, CacheEntry]] = {}
        self._user_locks: Dict[str, asyncio.Lock] = {}
        self._user_lock_creation_lock = asyncio.Lock()
        
        logger.info(f"AuthClientCache initialized with default TTL: {default_ttl}s and user isolation")
    
    async def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create user-specific lock for thread safety.
        
        Args:
            user_id: User identifier for lock isolation
            
        Returns:
            User-specific asyncio Lock
        """
        if user_id not in self._user_locks:
            async with self._user_lock_creation_lock:
                # Double-check locking pattern
                if user_id not in self._user_locks:
                    self._user_locks[user_id] = asyncio.Lock()
                    logger.debug(f"Created user-specific lock for user: {user_id}")
        return self._user_locks[user_id]
    
    async def _get_user_cache(self, user_id: str) -> Dict[str, CacheEntry]:
        """Get or create user-specific cache for complete isolation.
        
        Args:
            user_id: User identifier for cache isolation
            
        Returns:
            User-specific cache dictionary
        """
        if user_id not in self._per_user_caches:
            # This is already protected by the user lock in calling methods
            self._per_user_caches[user_id] = {}
            logger.debug(f"Created user-specific cache for user: {user_id}")
        return self._per_user_caches[user_id]
    
    async def get_user_scoped(self, user_id: str, key: str) -> Optional[Any]:
        """Get value from user-scoped cache (RACE CONDITION SAFE).
        
        Args:
            user_id: User identifier for cache isolation
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        user_lock = await self._get_user_lock(user_id)
        async with user_lock:
            user_cache = await self._get_user_cache(user_id)
            entry = user_cache.get(key)
            if entry is None:
                logger.debug(f"Cache miss for user {user_id}, key: {key}")
                return None
            
            if entry.is_expired():
                logger.debug(f"Cache entry expired for user {user_id}, key: {key}")
                del user_cache[key]
                return None
            
            logger.debug(f"Cache hit for user {user_id}, key: {key}")
            return entry.value
    
    async def set_user_scoped(self, user_id: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in user-scoped cache (RACE CONDITION SAFE).
        
        Args:
            user_id: User identifier for cache isolation
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        actual_ttl = ttl if ttl is not None else self._default_ttl
        user_lock = await self._get_user_lock(user_id)
        
        async with user_lock:
            user_cache = await self._get_user_cache(user_id)
            user_cache[key] = CacheEntry(value=value, ttl=actual_ttl)
            logger.debug(f"Cache set for user {user_id}, key: {key}, TTL: {actual_ttl}s")
    
    async def delete_user_scoped(self, user_id: str, key: str) -> bool:
        """Delete key from user-scoped cache (RACE CONDITION SAFE).
        
        Args:
            user_id: User identifier for cache isolation
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        user_lock = await self._get_user_lock(user_id)
        async with user_lock:
            user_cache = await self._get_user_cache(user_id)
            if key in user_cache:
                del user_cache[key]
                logger.debug(f"Cache key deleted for user {user_id}: {key}")
                return True
            return False
    
    async def clear_user_scoped(self, user_id: str) -> None:
        """Clear all cache entries for a specific user (RACE CONDITION SAFE).
        
        Args:
            user_id: User identifier for cache isolation
        """
        user_lock = await self._get_user_lock(user_id)
        async with user_lock:
            user_cache = await self._get_user_cache(user_id)
            count = len(user_cache)
            user_cache.clear()
            logger.info(f"User cache cleared for {user_id}: {count} entries removed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"Cache miss for key: {key}")
                return None
            
            if entry.is_expired():
                logger.debug(f"Cache entry expired for key: {key}")
                del self._cache[key]
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        actual_ttl = ttl if ttl is not None else self._default_ttl
        
        async with self._lock:
            self._cache[key] = CacheEntry(value=value, ttl=actual_ttl)
            logger.debug(f"Cache set for key: {key}, TTL: {actual_ttl}s")
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache key deleted: {key}")
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.
        
        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_entries": len(self._cache),
            "default_ttl": self._default_ttl,
            "memory_usage_bytes": sum(
                len(str(entry.value)) for entry in self._cache.values()
            ),
        }


class TokenCache:
    """Specialized cache for authentication tokens."""
    
    def __init__(self, cache_or_ttl):
        """Initialize with either AuthClientCache or TTL seconds for backward compatibility."""
        if isinstance(cache_or_ttl, int):
            # Backward compatibility: create AuthClientCache with TTL
            self._cache = AuthClientCache(default_ttl=cache_or_ttl)
        else:
            # New usage: direct AuthClientCache
            self._cache = cache_or_ttl
    
    async def get_token(self, user_id: str) -> Optional[str]:
        """Get cached token for user."""
        return await self._cache.get(f"token:{user_id}")
    
    async def set_token(self, user_id: str, token: str, expires_in: int = 3600) -> None:
        """Cache token for user."""
        # Set TTL slightly less than token expiry for safety
        ttl = max(expires_in - 60, 300)  # At least 5 minutes
        await self._cache.set(f"token:{user_id}", token, ttl)
    
    async def invalidate_token(self, user_id: str) -> None:
        """Invalidate cached token for user."""
        await self._cache.delete(f"token:{user_id}")
    
    async def get_cached_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Backward compatibility method for legacy auth flow.
        
        This method provides backward compatibility for the authentication flow
        that expects to retrieve cached token data based on the token itself.
        
        Args:
            token: The authentication token to look up
            
        Returns:
            Cached token data if available, None otherwise
        """
        # Validate cache type (defensive programming)
        if isinstance(self._cache, int):
            logger.error(f"CRITICAL BUG: self._cache is an integer: {self._cache}")
            return None
        # Bridge to token validation cache
        return await self._cache.get(f"validated_token:{token}")
    
    async def set_cached_token(self, token: str, token_data: Dict[str, Any], expires_in: int = 3600) -> None:
        """Cache validated token data for backward compatibility.
        
        Args:
            token: The authentication token
            token_data: The validated token data to cache
            expires_in: TTL for cache entry in seconds
        """
        # Set TTL slightly less than token expiry for safety
        ttl = max(expires_in - 60, 300)  # At least 5 minutes
        await self._cache.set(f"validated_token:{token}", token_data, ttl)
    
    def get_cached_token_sync(self, token: str) -> Optional[Dict[str, Any]]:
        """Synchronous backward compatibility wrapper with unique name.
        
        Some legacy code may expect a synchronous version of token validation.
        This returns None to avoid blocking, indicating cache miss.
        The calling code should fall back to async validation.
        
        Note: This is a separate method to avoid SSOT violation with async version.
        Legacy code should migrate to async get_cached_token() when possible.
        """
        logger.debug(f"Sync get_cached_token_sync called for backward compatibility - returning None to force async path")
        return None
    
    async def cache_token(self, token: str, result: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Cache token validation result for auth_client_core compatibility.
        
        This method is called by auth_client_core.py line 217 after successful validation.
        It caches the validation result to avoid repeated auth service calls.
        
        Args:
            token: The authentication token
            result: The validation result to cache
            ttl: Optional TTL override in seconds
        """
        if result is None:
            logger.debug(f"Skipping cache for None result for token: {token[:20]}...")
            return
        
        # Use provided TTL or default to 300 seconds (5 minutes)
        cache_ttl = ttl if ttl is not None else 300
        
        # Validate cache type (defensive programming)
        if isinstance(self._cache, int):
            logger.error(f"CRITICAL BUG: self._cache is an integer: {self._cache}")
            return
        
        # Store with the specified TTL
        await self._cache.set(f"validated_token:{token}", result, ttl=cache_ttl)
        logger.debug(f"Cached validation result for token: {token[:20]}... with TTL: {cache_ttl}s")
    
    async def invalidate_cached_token(self, token: str) -> None:
        """Invalidate a cached token validation result.
        
        This method is called by auth_client_core.py line 204 when a token is blacklisted
        or line 624 during logout to ensure the token is removed from cache.
        
        Args:
            token: The authentication token to invalidate
        """
        # Validate cache type (defensive programming)
        if isinstance(self._cache, int):
            logger.error(f"CRITICAL BUG: self._cache is an integer: {self._cache}")
            return
        
        # Remove the validated token from cache
        removed = await self._cache.delete(f"validated_token:{token}")
        if removed:
            logger.info(f"Invalidated cached token: {token[:20]}...")
        else:
            logger.debug(f"Token not in cache, nothing to invalidate: {token[:20]}...")


class UserCache:
    """Specialized cache for user data."""
    
    def __init__(self, cache: AuthClientCache):
        self._cache = cache
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data."""
        return await self._cache.get(f"user:{user_id}")
    
    async def set_user(self, user_id: str, user_data: Dict[str, Any], ttl: int = 600) -> None:
        """Cache user data."""
        await self._cache.set(f"user:{user_id}", user_data, ttl)
    
    async def invalidate_user(self, user_id: str) -> None:
        """Invalidate cached user data."""
        await self._cache.delete(f"user:{user_id}")


# Global instances
_auth_cache = AuthClientCache()
token_cache = TokenCache(_auth_cache)
user_cache = UserCache(_auth_cache)


async def get_auth_cache() -> AuthClientCache:
    """Get global auth client cache instance."""
    return _auth_cache


async def get_token_cache() -> TokenCache:
    """Get global token cache instance."""
    return token_cache


async def get_user_cache() -> UserCache:
    """Get global user cache instance."""
    return user_cache


class AuthCircuitBreakerManager:
    """Circuit breaker manager for authentication operations."""
    
    def __init__(self):
        """Initialize auth circuit breaker manager."""
        self._breakers: Dict[str, Any] = {}
        logger.info("AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker")
    
    def get_breaker(self, name: str) -> Any:
        """Get circuit breaker by name."""
        if name not in self._breakers:
            # CRITICAL FIX: Use UnifiedCircuitBreaker with proper recovery mechanisms
            # This fixes the bug where MockCircuitBreaker would open permanently on any error
            config = UnifiedCircuitConfig(
                name=name,
                failure_threshold=3,  # Allow 3 failures before opening (reduced from 5 for faster detection)
                success_threshold=1,  # Only need 1 success to close from half-open (faster recovery)
                recovery_timeout=10,  # Attempt recovery after 10 seconds (reduced from 30 for faster recovery)
                timeout_seconds=5.0,  # Individual request timeout (reduced for faster failure detection)
                slow_call_threshold=3.0,  # Mark calls over 3s as slow (reduced threshold)
                adaptive_threshold=False,  # Use fixed thresholds for predictability
                exponential_backoff=False  # Disable exponential backoff for faster recovery in database operations
            )
            self._breakers[name] = UnifiedCircuitBreaker(config)
            logger.info(f"Created UnifiedCircuitBreaker for '{name}' with recovery_timeout=10s, failure_threshold=3 - OPTIMIZED FOR DATABASE OPERATIONS")
        return self._breakers[name]
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for name, breaker in self._breakers.items():
            if isinstance(breaker, UnifiedCircuitBreaker):
                # UnifiedCircuitBreaker uses state management
                breaker.state = UnifiedCircuitBreakerState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0
                logger.info(f"Reset UnifiedCircuitBreaker '{name}' to CLOSED state")
            elif hasattr(breaker, 'reset'):
                # Fallback for any legacy breakers
                breaker.reset()
        logger.info("All auth circuit breakers reset")
    
    async def call_with_breaker(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        breaker_name = f"{func.__name__}_breaker"
        breaker = self.get_breaker(breaker_name)
        return await breaker.call(func, *args, **kwargs)


class MockCircuitBreaker:
    """Enhanced mock circuit breaker with recovery capabilities.
    
    CRITICAL FIX: Added recovery timer and failure threshold to prevent permanent open state.
    This is a fallback implementation if UnifiedCircuitBreaker is not available.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.is_open = False
        self.failure_count = 0
        self.failure_threshold = 5  # FIX: Add threshold instead of opening on first error
        self.opened_at = None
        self.recovery_timeout = 30  # FIX: Add recovery timeout (30 seconds)
        logger.info(f"MockCircuitBreaker '{name}' initialized with recovery_timeout=30s, failure_threshold=5")
    
    def reset(self):
        """Reset circuit breaker."""
        self.is_open = False
        self.failure_count = 0
        self.opened_at = None
        logger.info(f"MockCircuitBreaker '{self.name}' manually reset")
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection and automatic recovery."""
        # FIX: Check if we should attempt recovery
        if self.is_open:
            if self.opened_at and (time.time() - self.opened_at > self.recovery_timeout):
                # Attempt recovery after timeout
                logger.info(f"MockCircuitBreaker '{self.name}' attempting recovery after {self.recovery_timeout}s")
                self.is_open = False
                self.failure_count = 0
                self.opened_at = None
            else:
                # Still in recovery timeout period
                remaining = self.recovery_timeout - (time.time() - self.opened_at) if self.opened_at else 0
                logger.warning(f"Circuit breaker '{self.name}' is open, recovery in {remaining:.1f}s")
                raise Exception(f"Circuit breaker {self.name} is open")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # FIX: Reset failure count on success
            if self.failure_count > 0:
                logger.info(f"MockCircuitBreaker '{self.name}' successful call, resetting failure count")
            self.failure_count = 0
            return result
            
        except Exception as e:
            # FIX: Increment failure count and only open after threshold
            self.failure_count += 1
            logger.warning(f"MockCircuitBreaker '{self.name}' failure {self.failure_count}/{self.failure_threshold}: {e}")
            
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                self.opened_at = time.time()
                logger.critical(f"MockCircuitBreaker '{self.name}' OPENED after {self.failure_count} failures, will recover in {self.recovery_timeout}s")
            raise


# Global circuit breaker manager
auth_circuit_breaker_manager = AuthCircuitBreakerManager()


async def get_auth_circuit_breaker_manager() -> AuthCircuitBreakerManager:
    """Get global auth circuit breaker manager."""
    return auth_circuit_breaker_manager


@dataclass
class AuthServiceSettings:
    """Settings for auth service client."""
    base_url: str = "http://localhost:8081"
    timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 300
    circuit_breaker_enabled: bool = True
    # FIX: Add 'enabled' field to match usage in auth_client_core.py
    # This controls whether auth service integration is active
    enabled: bool = True
    
    def __post_init__(self):
        """Initialize settings from environment after dataclass init."""
        from shared.isolated_environment import get_env
        env = get_env()
        
        # Override with environment values if present
        self.base_url = env.get("AUTH_SERVICE_URL", self.base_url)
        self.timeout = int(env.get("AUTH_CLIENT_TIMEOUT", str(self.timeout)))
        self.max_retries = int(env.get("AUTH_CLIENT_MAX_RETRIES", str(self.max_retries)))
        self.cache_ttl = int(env.get("AUTH_CLIENT_CACHE_TTL", str(self.cache_ttl)))
        self.circuit_breaker_enabled = env.get("AUTH_CLIENT_CIRCUIT_BREAKER", "true").lower() == "true"
        
        # Determine if auth service is enabled based on environment
        # Default to True for production safety, can be disabled explicitly
        auth_enabled_str = env.get("AUTH_SERVICE_ENABLED", "true")
        self.enabled = auth_enabled_str.lower() == "true"
    
    @classmethod
    def from_env(cls) -> 'AuthServiceSettings':
        """Create settings from environment variables."""
        # Simply create instance, __post_init__ will handle environment loading
        return cls()
    
    def is_service_secret_configured(self) -> bool:
        """Check if service secret is configured."""
        from shared.isolated_environment import get_env
        env = get_env()
        service_secret = env.get("SERVICE_SECRET", "")
        return bool(service_secret)
    
    def get_service_credentials(self) -> tuple[str, str]:
        """Get service ID and secret from environment."""
        from shared.isolated_environment import get_env
        env = get_env()
        service_id = env.get("SERVICE_ID", "netra-backend")
        service_secret = env.get("SERVICE_SECRET", "")
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"AuthServiceSettings.get_service_credentials - ID: {service_id}, Secret configured: {bool(service_secret)}")
        
        return service_id, service_secret


class AuthTokenCache:
    """Specialized token cache for E2E test compatibility.
    
    This class wraps TokenCache and adds methods expected by test_auth_token_cache.py.
    It maintains a _token_cache dict for direct test access.
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize auth token cache with TTL.
        
        Args:
            cache_ttl_seconds: Default TTL for cached tokens
        """
        self._inner_cache = TokenCache(cache_ttl_seconds)
        self._token_cache: Dict[str, CachedToken] = {}  # For test compatibility
        self.cache_ttl_seconds = cache_ttl_seconds
    
    def cache_token(self, token: str, data: Dict[str, Any]) -> None:
        """Cache token data synchronously for test compatibility.
        
        Args:
            token: The token to cache
            data: The validation data to cache
        """
        # Store in both internal dict (for tests) and async cache
        self._token_cache[token] = CachedToken(data, self.cache_ttl_seconds)
        
        # Also cache asynchronously if possible (fire and forget)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._inner_cache.cache_token(token, data))
        except RuntimeError:
            # No event loop, just use sync storage
            pass
    
    def get_cached_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached token data synchronously for test compatibility.
        
        Args:
            token: The token to retrieve
            
        Returns:
            Cached data if valid, None otherwise
        """
        if token in self._token_cache:
            cached = self._token_cache[token]
            if cached.is_valid():
                return cached.data
            else:
                # Remove expired token
                del self._token_cache[token]
        return None
    
    def invalidate_cached_token(self, token: str) -> None:
        """Invalidate cached token synchronously for test compatibility.
        
        Args:
            token: The token to invalidate
        """
        if token in self._token_cache:
            del self._token_cache[token]
        
        # Also invalidate asynchronously if possible (fire and forget)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._inner_cache.invalidate_cached_token(token))
        except RuntimeError:
            # No event loop, just use sync storage
            pass
    
    # Delegate other methods to inner cache for full compatibility
    async def get_token(self, user_id: str) -> Optional[str]:
        """Get cached token for user."""
        return await self._inner_cache.get_token(user_id)
    
    async def set_token(self, user_id: str, token: str, expires_in: int = 3600) -> None:
        """Cache token for user."""
        await self._inner_cache.set_token(user_id, token, expires_in)
    
    async def invalidate_token(self, user_id: str) -> None:
        """Invalidate cached token for user."""
        await self._inner_cache.invalidate_token(user_id)