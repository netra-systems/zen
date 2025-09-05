"""
Auth Service - Dedicated Authentication Microservice
Single Source of Truth for all authentication and authorization
"""

from auth_service.auth_core.redis_manager import AuthRedisManager, auth_redis_manager

__version__ = "1.0.0"
__service__ = "auth-service"

__all__ = [
    "AuthRedisManager",
    "auth_redis_manager",
]