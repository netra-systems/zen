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

# Stubs for deleted modules
class ApiCacheManager:
    """Stub for deleted ApiCacheManager"""
    def __init__(self):
        pass

class ApiCircuitBreaker:
    """Stub for deleted ApiCircuitBreaker"""
    def __init__(self):
        pass

class ApiGatewayRateLimiter:
    """Stub for deleted ApiGatewayRateLimiter"""
    def __init__(self):
        pass

class ApiGatewayRouter:
    """Stub for deleted ApiGatewayRouter"""
    def __init__(self):
        pass

__all__ = [
    'ApiGatewayRouter',
    'ApiGatewayRateLimiter', 
    'ApiCacheManager',
    'ApiCircuitBreaker',
    'CacheStrategy',
    'TransformationEngine'
]