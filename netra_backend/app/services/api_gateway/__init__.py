"""
API Gateway services module.

This module provides API gateway functionality including routing, rate limiting,
caching, and circuit breaking capabilities.
"""

# Import from existing files only
from netra_backend.app.services.api_gateway.cache_strategies import CacheStrategy
from netra_backend.app.services.api_gateway.transformation_engine import (
    TransformationEngine,
)
from netra_backend.app.services.api_gateway.rate_limiter import (
    ApiGatewayRateLimiter,
    RateLimitConfig,
    RateLimitResult,
)

# Stubs for deleted modules
class ApiCacheManager:
    """Stub for deleted ApiCacheManager"""
    def __init__(self):
        pass

class ApiCircuitBreaker:
    """Stub for deleted ApiCircuitBreaker"""
    def __init__(self):
        pass

# ApiGatewayRateLimiter is now imported from rate_limiter module above

class ApiGatewayRouter:
    """Stub for deleted ApiGatewayRouter"""
    def __init__(self):
        pass

__all__ = [
    'ApiGatewayRouter',
    'ApiGatewayRateLimiter',
    'RateLimitConfig',
    'RateLimitResult',
    'ApiCacheManager',
    'ApiCircuitBreaker',
    'CacheStrategy',
    'TransformationEngine'
]