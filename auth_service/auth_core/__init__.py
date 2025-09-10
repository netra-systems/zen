"""
Auth Service - Dedicated Authentication Microservice
Single Source of Truth for all authentication and authorization
"""

# Auth service operates independently without backend dependencies
# Redis functionality is handled internally by auth_core.redis_manager

__version__ = "1.0.0"
__service__ = "auth-service"

__all__ = [
]