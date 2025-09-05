"""Advanced LLM Cache Service

Implements intelligent caching with invalidation strategies.
Backward compatibility module for existing imports.
"""

# Legacy imports removed - use resource_cache instead
# from netra_backend.app.services.api_gateway.cache_manager import LLMCacheManager
# from netra_backend.app.services.cache.cache_eviction import CacheEvictionManager

# Import from SSOT implementations
from netra_backend.app.llm.resource_cache import LRUCache as LLMCacheManager
from netra_backend.app.services.cache.cache_models import CacheEntry, CacheStrategy
from netra_backend.app.services.cache.cache_serialization import CacheSerializer
from netra_backend.app.services.cache.cache_statistics import CacheStatistics

# Create placeholder for missing CacheEvictionManager
class CacheEvictionManager:
    """Placeholder for legacy CacheEvictionManager - functionality merged into LRUCache"""
    pass

# Make all exports available at module level
__all__ = [
    'CacheStrategy',
    'CacheEntry',
    'CacheStatistics',
    'LLMCacheManager',
    'CacheEvictionManager',
    'CacheSerializer'
]