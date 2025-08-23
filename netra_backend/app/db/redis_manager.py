"""Redis Manager for Database Layer

This module provides access to Redis functionality for database operations.
It imports and exposes the main RedisManager instance from the app layer.

Business Value Justification (BVJ):
- Segment: ALL (Critical infrastructure for all tiers)
- Business Goal: Provide reliable Redis access for database operations
- Value Impact: Enables session management, caching, and state persistence
- Strategic Impact: Foundation for scalable auth and data operations
"""

from netra_backend.app.redis_manager import redis_manager


def get_redis_manager():
    """
    Get the Redis manager instance.
    
    Returns:
        RedisManager: The configured Redis manager instance
        
    Note:
        This function provides access to the Redis manager for database
        operations including session management, caching, and state storage.
    """
    return redis_manager


# Export the function for easy importing
__all__ = ['get_redis_manager']