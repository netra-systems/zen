"""Redis manager for auth service.

Uses SSOT AuthEnvironment for all configuration access.

Provides Redis connection and management functionality specifically for
authentication operations like session storage, token blacklisting, and
cache management.

Business Value:
- Enables fast session lookups for user authentication
- Provides token blacklisting for secure logout
- Caches user permissions and roles for performance
"""

from typing import Optional, Dict, Any, List
import asyncio
import redis.asyncio as redis
from datetime import datetime, timedelta
import json
import logging

from auth_service.auth_core.auth_environment import get_auth_env

logger = logging.getLogger(__name__)


class AuthRedisManager:
    """Redis manager specifically for authentication operations."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self.connected = False
        
        # Get Redis configuration from SSOT AuthEnvironment
        auth_env = get_auth_env()
        self.host = auth_env.get_redis_host()
        self.port = auth_env.get_redis_port()
        self.db = 1  # Use separate DB for auth (default from AuthEnvironment Redis URL)
        
        # Extract password from Redis URL if available
        redis_url = auth_env.get_redis_url()
        self.password = None
        if redis_url and ":" in redis_url and "@" in redis_url:
            # Parse password from redis://user:password@host:port/db format
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(redis_url)
                self.password = parsed.password
            except Exception:
                self.password = None
        
        self.ssl = False  # Default to no SSL unless explicitly configured
        
        # Check if Redis is enabled (for testing environments) 
        from shared.isolated_environment import get_env
        env = get_env()  # Test-specific checks can still use get_env
        self.enabled = env.get("TEST_DISABLE_REDIS", "false").lower() != "true"
        
        # Auth-specific prefixes
        self.session_prefix = "auth:session:"
        self.token_blacklist_prefix = "auth:blacklist:"
        self.user_cache_prefix = "auth:user:"
        self.permission_prefix = "auth:perm:"
        
        logger.debug(f"AuthRedisManager initialized for {self.host}:{self.port}/{self.db}")
    
    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            self._connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
            )
            
            self.redis_client = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        
        self.connected = False
        logger.info("Disconnected from Redis")
    
    async def ensure_connected(self) -> bool:
        """Ensure Redis connection is active."""
        if not self.enabled:
            logger.debug("Redis is disabled for testing")
            return False
        
        if not self.connected or not self.redis_client:
            return await self.connect()
        
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}")
            return await self.connect()
    
    # Session Management
    async def store_session(self, session_id: str, session_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Store user session data."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.session_prefix}{session_id}"
            session_json = json.dumps(session_data, default=str)
            
            await self.redis_client.setex(key, ttl_seconds, session_json)
            logger.debug(f"Stored session {session_id} with TTL {ttl_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session data."""
        if not await self.ensure_connected():
            return None
        
        try:
            key = f"{self.session_prefix}{session_id}"
            session_json = await self.redis_client.get(key)
            
            if session_json:
                return json.loads(session_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete user session."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.session_prefix}{session_id}"
            result = await self.redis_client.delete(key)
            logger.debug(f"Deleted session {session_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def extend_session(self, session_id: str, ttl_seconds: int = 3600) -> bool:
        """Extend session TTL."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.session_prefix}{session_id}"
            result = await self.redis_client.expire(key, ttl_seconds)
            logger.debug(f"Extended session {session_id} TTL to {ttl_seconds}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False
    
    # Token Blacklisting
    async def blacklist_token(self, token: str, ttl_seconds: int = 86400) -> bool:
        """Add token to blacklist."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.token_blacklist_prefix}{token}"
            await self.redis_client.setex(key, ttl_seconds, "blacklisted")
            logger.debug(f"Blacklisted token with TTL {ttl_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.token_blacklist_prefix}{token}"
            result = await self.redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False
    
    # User Caching
    async def cache_user_data(self, user_id: str, user_data: Dict[str, Any], ttl_seconds: int = 1800) -> bool:
        """Cache user data for fast lookup."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.user_cache_prefix}{user_id}"
            user_json = json.dumps(user_data, default=str)
            
            await self.redis_client.setex(key, ttl_seconds, user_json)
            logger.debug(f"Cached user data for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache user data for {user_id}: {e}")
            return False
    
    async def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data."""
        if not await self.ensure_connected():
            return None
        
        try:
            key = f"{self.user_cache_prefix}{user_id}"
            user_json = await self.redis_client.get(key)
            
            if user_json:
                return json.loads(user_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached user data for {user_id}: {e}")
            return None
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate cached user data."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.user_cache_prefix}{user_id}"
            result = await self.redis_client.delete(key)
            logger.debug(f"Invalidated user cache for {user_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to invalidate user cache for {user_id}: {e}")
            return False
    
    # Permission Caching
    async def cache_user_permissions(self, user_id: str, permissions: List[str], ttl_seconds: int = 1800) -> bool:
        """Cache user permissions."""
        if not await self.ensure_connected():
            return False
        
        try:
            key = f"{self.permission_prefix}{user_id}"
            permissions_json = json.dumps(permissions)
            
            await self.redis_client.setex(key, ttl_seconds, permissions_json)
            logger.debug(f"Cached permissions for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache permissions for {user_id}: {e}")
            return False
    
    async def get_cached_permissions(self, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions."""
        if not await self.ensure_connected():
            return None
        
        try:
            key = f"{self.permission_prefix}{user_id}"
            permissions_json = await self.redis_client.get(key)
            
            if permissions_json:
                return json.loads(permissions_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached permissions for {user_id}: {e}")
            return None
    
    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health and return status."""
        try:
            if not await self.ensure_connected():
                return {"status": "unhealthy", "error": "Cannot connect to Redis"}
            
            # Test basic operations
            test_key = "auth:health:test"
            await self.redis_client.set(test_key, "test", ex=5)
            test_value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)
            
            if test_value != "test":
                return {"status": "unhealthy", "error": "Basic operations failed"}
            
            # Get connection info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "connection": {
                    "host": self.host,
                    "port": self.port,
                    "db": self.db,
                },
                "server_info": {
                    "version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
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