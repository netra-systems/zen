"""Auth Redis Manager - SSOT Compatibility Layer

DEPRECATED: Use netra_backend.app.redis_manager.redis_manager directly

This module provides backward compatibility during Redis SSOT migration.
The primary SSOT Redis manager now includes all auth functionality.

Business Value:
- Enables fast session lookups for user authentication
- Provides token blacklisting for secure logout
- Caches user permissions and roles for performance

SSOT Migration:
- All functionality has been consolidated into netra_backend.app.redis_manager
- This module provides compatibility wrappers during transition
- Future imports should use redis_manager directly
"""

from typing import Optional, Dict, Any, List
import asyncio
import warnings
from datetime import datetime, timedelta
import json
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Import SSOT Redis Manager
try:
    from netra_backend.app.redis_manager import redis_manager as ssot_redis_manager
    SSOT_AVAILABLE = True
except ImportError:
    SSOT_AVAILABLE = False
    logger.warning("SSOT Redis manager not available - falling back to standalone auth implementation")

# Issue deprecation warning
warnings.warn(
    "auth_redis_manager is deprecated. Use netra_backend.app.redis_manager.redis_manager directly",
    DeprecationWarning,
    stacklevel=2
)


class AuthRedisManager:
    """Compatibility wrapper for auth service Redis operations.
    
    DEPRECATED: Use netra_backend.app.redis_manager.redis_manager directly
    
    This class provides backward compatibility during Redis SSOT migration.
    All operations are redirected to the primary SSOT Redis manager.
    """
    
    def __init__(self):
        if SSOT_AVAILABLE:
            self._redis = ssot_redis_manager
        else:
            # Fallback initialization if SSOT not available
            self._initialize_fallback()
        
        # Auth-specific prefixes (maintained for compatibility)
        self.session_prefix = "auth:session:"
        self.token_blacklist_prefix = "auth:blacklist:"
        self.user_cache_prefix = "auth:user:"
        self.permission_prefix = "auth:perm:"
    
    def _initialize_fallback(self):
        """Fallback initialization for isolated auth service."""
        # Keep minimal fallback for auth service independence
        self.redis_client = None
        self._connection_pool = None
        self.connected = False
        self._enabled = False
    
    @property
    def enabled(self):
        """Check if Redis is enabled (redirects to SSOT)."""
        return SSOT_AVAILABLE and self._redis.is_connected
    
    def _lazy_init(self):
        """Lazy initialization of Redis configuration."""
        if self._initialized:
            return
        
        try:
            # Import here to avoid circular dependency at module level
            from auth_service.auth_core.auth_environment import get_auth_env
            
            # Get Redis configuration from SSOT AuthEnvironment
            auth_env = get_auth_env()
            self.host = auth_env.get_redis_host()
            self.port = auth_env.get_redis_port()
            
            # Extract password from Redis URL if available
            redis_url = auth_env.get_redis_url()
            if redis_url and ":" in redis_url and "@" in redis_url:
                # Parse password from redis://user:password@host:port/db format
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(redis_url)
                    self.password = parsed.password
                except Exception:
                    self.password = None
            
            # Check if Redis is enabled (for testing environments) 
            from shared.isolated_environment import get_env
            env = get_env()  # Test-specific checks can still use get_env
            self._enabled = env.get("TEST_DISABLE_REDIS", "false").lower() != "true"
            
            self._initialized = True
            logger.debug(f"AuthRedisManager initialized for {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.error(f"Failed to initialize AuthRedisManager: {e}")
            self._enabled = False
            self._initialized = True
    
    async def connect(self) -> bool:
        """Connect to Redis server (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            await self._redis.initialize()
            return self._redis.is_connected
        return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        
        self.connected = False
        logger.info("Disconnected from Redis")
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get the Redis client instance."""
        self._lazy_init()  # Ensure configuration is loaded
        return self.redis_client
    
    async def ensure_connected(self) -> bool:
        """Ensure Redis connection is active (redirects to SSOT)."""
        if not SSOT_AVAILABLE:
            return False
        if not self._redis.is_connected:
            await self._redis.initialize()
        return self._redis.is_connected
    
    # Session Management (redirected to SSOT)
    async def store_session(self, session_id: str, session_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Store user session data (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.store_session(session_id, session_data, ttl_seconds)
        return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session data (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.get_session(session_id)
        return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete user session (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.delete_session(session_id)
        return False
    
    async def extend_session(self, session_id: str, ttl_seconds: int = 3600) -> bool:
        """Extend session TTL (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.extend_session(session_id, ttl_seconds)
        return False
    
    # Token Blacklisting (redirected to SSOT)
    async def blacklist_token(self, token: str, ttl_seconds: int = 86400) -> bool:
        """Add token to blacklist (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.blacklist_token(token, ttl_seconds)
        return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.is_token_blacklisted(token)
        return False
    
    # User Caching (redirected to SSOT)
    async def cache_user_data(self, user_id: str, user_data: Dict[str, Any], ttl_seconds: int = 1800) -> bool:
        """Cache user data for fast lookup (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.cache_user_data(user_id, user_data, ttl_seconds)
        return False
    
    async def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.get_cached_user_data(user_id)
        return None
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate cached user data (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.invalidate_user_cache(user_id)
        return False
    
    # Permission Caching (redirected to SSOT)
    async def cache_user_permissions(self, user_id: str, permissions: List[str], ttl_seconds: int = 1800) -> bool:
        """Cache user permissions (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.cache_user_permissions(user_id, permissions, ttl_seconds)
        return False
    
    async def get_cached_permissions(self, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions (redirects to SSOT)."""
        if SSOT_AVAILABLE:
            return await self._redis.get_cached_permissions(user_id)
        return None
    
    # Health Check (redirected to SSOT)
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health and return status (redirects to SSOT)."""
        try:
            if not SSOT_AVAILABLE:
                return {"status": "unhealthy", "error": "SSOT Redis manager not available"}
            
            if not await self.ensure_connected():
                return {"status": "unhealthy", "error": "Cannot connect to Redis"}
            
            # Test basic auth operations using SSOT
            test_session_id = f"health_check_{int(datetime.utcnow().timestamp())}"
            test_session_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
            
            # Test session operations
            store_success = await self.store_session(test_session_id, test_session_data, 5)
            if not store_success:
                return {"status": "unhealthy", "error": "Failed to store test session"}
            
            retrieved_data = await self.get_session(test_session_id)
            if retrieved_data != test_session_data:
                return {"status": "unhealthy", "error": "Session data mismatch"}
            
            delete_success = await self.delete_session(test_session_id)
            if not delete_success:
                return {"status": "unhealthy", "error": "Failed to delete test session"}
            
            return {
                "status": "healthy",
                "connection": {
                    "ssot_available": SSOT_AVAILABLE,
                    "ssot_connected": self._redis.is_connected if SSOT_AVAILABLE else False,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    # Cleanup utilities
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (already handled by Redis TTL, but useful for monitoring)."""
        if not await self.ensure_connected():
            return 0
        
        try:
            # Get all session keys
            pattern = f"{self.session_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            # Check which ones exist (non-expired)
            active_sessions = 0
            for key in keys:
                if await self.redis_client.exists(key):
                    active_sessions += 1
            
            logger.info(f"Found {active_sessions} active sessions")
            return active_sessions
            
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0


# Global auth Redis manager instance
auth_redis_manager = AuthRedisManager()


__all__ = [
    "AuthRedisManager",
    "auth_redis_manager",
]