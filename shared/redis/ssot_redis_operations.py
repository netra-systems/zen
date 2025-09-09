"""
SSOT Redis Operations Manager - Centralized Redis operation patterns.

This module provides Single Source of Truth patterns for Redis operations,
ensuring consistent Redis 6.4.0+ compatibility and proper parameter usage.

CRITICAL: All Redis operations MUST use this SSOT manager to ensure:
- Redis 6.4.0+ compatibility with 'ex' parameter (not 'expire_seconds')
- Consistent error handling and logging
- Proper connection management
- Type safety with strongly typed operations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Eliminates Redis 6.4.0+ parameter compatibility errors in staging/production
- Strategic Impact: Single source of truth for all Redis operation patterns

Key Features:
- Automatic 'ex' parameter usage for expiration (Redis 6.4.0+ compatible)
- Consistent error handling and logging
- Connection management integration
- Type-safe operation result handling
- Session storage patterns for authentication

USAGE EXAMPLES:

# Set operations with expiration
await redis_ops.set_with_expiry(redis_manager, "key", "value", expire_seconds=300)

# Session storage
await redis_ops.set_session_data(redis_manager, "session:123", session_data, expire_seconds=3600)

# Health checks
is_healthy = await redis_ops.execute_health_check(redis_manager)

# Token blacklisting
await redis_ops.blacklist_token(redis_manager, token_jti, expire_seconds=3600)
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class SSOTRedisOperationsManager:
    """
    Single Source of Truth for Redis operation patterns.
    
    Provides centralized, Redis 6.4.0+ compatible operation execution
    with proper error handling, logging, and type safety.
    """
    
    def __init__(self):
        """Initialize SSOT Redis operations manager."""
        self.logger = logger

    async def set_with_expiry(
        self, 
        redis_manager: Any, 
        key: str, 
        value: str, 
        expire_seconds: Optional[int] = None
    ) -> bool:
        """
        Set a key-value pair with optional expiration.
        
        CRITICAL: Uses 'ex' parameter for Redis 6.4.0+ compatibility,
        not the deprecated 'expire_seconds' parameter.
        
        Args:
            redis_manager: Redis manager instance
            key: Redis key
            value: Value to store
            expire_seconds: Expiration time in seconds (uses 'ex' parameter)
            
        Returns:
            True if operation succeeded, False otherwise
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            self.logger.debug(f"Setting Redis key: {key[:50]}... (expiry: {expire_seconds}s)")
            
            # CRITICAL: Use 'ex' parameter for Redis 6.4.0+ compatibility
            if expire_seconds:
                result = await redis_manager.set(key, value, ex=expire_seconds)
            else:
                result = await redis_manager.set(key, value)
            
            success = result is not False
            self.logger.debug(f"Redis set operation result: {success}")
            
            return success
            
        except Exception as e:
            error_msg = f"Redis set operation failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="set", key=key) from e
    
    async def get_value(
        self, 
        redis_manager: Any, 
        key: str
    ) -> Optional[str]:
        """
        Get value for a Redis key.
        
        Args:
            redis_manager: Redis manager instance
            key: Redis key to retrieve
            
        Returns:
            Value if key exists, None otherwise
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            self.logger.debug(f"Getting Redis key: {key[:50]}...")
            
            result = await redis_manager.get(key)
            
            self.logger.debug(f"Redis get result: {'found' if result else 'not found'}")
            return result
            
        except Exception as e:
            error_msg = f"Redis get operation failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="get", key=key) from e
    
    async def delete_key(
        self, 
        redis_manager: Any, 
        key: str
    ) -> bool:
        """
        Delete a Redis key.
        
        Args:
            redis_manager: Redis manager instance
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            self.logger.debug(f"Deleting Redis key: {key[:50]}...")
            
            result = await redis_manager.delete(key)
            
            # Redis delete returns number of keys deleted
            success = result > 0 if isinstance(result, int) else bool(result)
            self.logger.debug(f"Redis delete result: {success}")
            
            return success
            
        except Exception as e:
            error_msg = f"Redis delete operation failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="delete", key=key) from e
    
    async def set_session_data(
        self, 
        redis_manager: Any, 
        session_key: str, 
        session_data: Dict[str, Any], 
        expire_seconds: int = 3600
    ) -> bool:
        """
        Store session data with automatic JSON serialization.
        
        Args:
            redis_manager: Redis manager instance
            session_key: Session key (e.g., 'session:user_id')
            session_data: Session data dictionary
            expire_seconds: Session expiration time (default: 1 hour)
            
        Returns:
            True if session was stored successfully
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            self.logger.debug(f"Storing session data: {session_key}")
            
            # Serialize session data to JSON
            serialized_data = json.dumps(session_data, default=str)
            
            # CRITICAL: Use 'ex' parameter for Redis 6.4.0+ compatibility
            result = await redis_manager.set(session_key, serialized_data, ex=expire_seconds)
            
            success = result is not False
            self.logger.debug(f"Session storage result: {success}")
            
            return success
            
        except Exception as e:
            error_msg = f"Session data storage failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="set_session", key=session_key) from e
    
    async def get_session_data(
        self, 
        redis_manager: Any, 
        session_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data with automatic JSON deserialization.
        
        Args:
            redis_manager: Redis manager instance
            session_key: Session key to retrieve
            
        Returns:
            Session data dictionary if found, None otherwise
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            self.logger.debug(f"Retrieving session data: {session_key}")
            
            serialized_data = await redis_manager.get(session_key)
            
            if serialized_data is None:
                self.logger.debug("Session data not found")
                return None
            
            # Deserialize JSON data
            session_data = json.loads(serialized_data)
            
            self.logger.debug(f"Session data retrieved successfully: {len(session_data)} keys")
            return session_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Session data JSON decode failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="get_session", key=session_key) from e
        except Exception as e:
            error_msg = f"Session data retrieval failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="get_session", key=session_key) from e
    
    async def blacklist_token(
        self, 
        redis_manager: Any, 
        token_jti: str, 
        expire_seconds: int = 3600
    ) -> bool:
        """
        Blacklist a JWT token by its JTI.
        
        Args:
            redis_manager: Redis manager instance
            token_jti: JWT Token ID (jti claim)
            expire_seconds: How long to keep token blacklisted
            
        Returns:
            True if token was blacklisted successfully
            
        Raises:
            RedisOperationError: If operation fails
        """
        try:
            blacklist_key = f"blacklist:{token_jti}"
            self.logger.debug(f"Blacklisting token: {token_jti[:16]}...")
            
            # CRITICAL: Use 'ex' parameter for Redis 6.4.0+ compatibility
            result = await redis_manager.set(
                blacklist_key, 
                "blacklisted", 
                ex=expire_seconds
            )
            
            success = result is not False
            self.logger.debug(f"Token blacklist result: {success}")
            
            return success
            
        except Exception as e:
            error_msg = f"Token blacklisting failed: {str(e)}"
            self.logger.error(error_msg)
            raise RedisOperationError(error_msg, operation="blacklist_token", key=token_jti) from e
    
    async def is_token_blacklisted(
        self, 
        redis_manager: Any, 
        token_jti: str
    ) -> bool:
        """
        Check if a JWT token is blacklisted.
        
        Args:
            redis_manager: Redis manager instance
            token_jti: JWT Token ID (jti claim)
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            blacklist_key = f"blacklist:{token_jti}"
            self.logger.debug(f"Checking token blacklist: {token_jti[:16]}...")
            
            result = await redis_manager.get(blacklist_key)
            
            is_blacklisted = result is not None
            self.logger.debug(f"Token blacklist status: {is_blacklisted}")
            
            return is_blacklisted
            
        except Exception as e:
            error_msg = f"Token blacklist check failed: {str(e)}"
            self.logger.error(error_msg)
            # On error, assume token is not blacklisted (fail-open for availability)
            return False
    
    async def execute_health_check(
        self, 
        redis_manager: Any, 
        timeout_seconds: float = 5.0
    ) -> bool:
        """
        Execute comprehensive Redis health check.
        
        Args:
            redis_manager: Redis manager instance
            timeout_seconds: Health check timeout
            
        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"
            
            self.logger.debug("Executing Redis health check")
            
            # Test SET operation with expiration
            set_result = await self.set_with_expiry(
                redis_manager, 
                test_key, 
                test_value, 
                expire_seconds=60
            )
            
            if not set_result:
                self.logger.warning("Redis health check: SET operation failed")
                return False
            
            # Test GET operation
            retrieved_value = await self.get_value(redis_manager, test_key)
            
            if retrieved_value != test_value:
                self.logger.warning(f"Redis health check: GET mismatch - expected '{test_value}', got '{retrieved_value}'")
                return False
            
            # Test DELETE operation (cleanup)
            delete_result = await self.delete_key(redis_manager, test_key)
            
            if not delete_result:
                self.logger.warning("Redis health check: DELETE operation failed")
                # Don't fail health check for cleanup failure
            
            self.logger.debug("Redis health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return False


class RedisOperationError(Exception):
    """Exception raised for Redis operation errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, key: Optional[str] = None):
        super().__init__(message)
        self.operation = operation
        self.key = key


# SSOT Instance for global use
ssot_redis_ops = SSOTRedisOperationsManager()