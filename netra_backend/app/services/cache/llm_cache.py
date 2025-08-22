"""Advanced LLM Cache Service

Implements intelligent caching with invalidation strategies.
Backward compatibility module for existing imports.
"""

# Re-export all public classes and enums for backward compatibility
from netra_backend.app.services.api_gateway.cache_manager import LLMCacheManager
from netra_backend.app.services.cache.cache_eviction import CacheEvictionManager
from netra_backend.app.services.cache.cache_models import CacheEntry, CacheStrategy
from netra_backend.app.services.cache.cache_serialization import CacheSerializer
from netra_backend.app.services.cache.cache_statistics import CacheStatistics

# Make all exports available at module level
__all__ = [
    'CacheStrategy',
    'CacheEntry',
    'CacheStatistics',
    'LLMCacheManager',
    'CacheEvictionManager',
    'CacheSerializer'
]