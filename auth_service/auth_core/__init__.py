"""
Auth Service - Dedicated Authentication Microservice
Single Source of Truth for all authentication and authorization
"""

from netra_backend.app.redis_manager import RedisManager as AuthRedisManager, auth_redis_manager

__version__ = "1.0.0"
__service__ = "auth-service"

__all__ = [
    "AuthRedisManager",
    "auth_redis_manager",
]