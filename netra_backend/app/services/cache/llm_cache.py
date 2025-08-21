"""Advanced LLM Cache Service

Implements intelligent caching with invalidation strategies.
Backward compatibility module for existing imports.
"""

# Re-export all public classes and enums for backward compatibility
from netra_backend.app.cache_models import CacheStrategy, CacheEntry
from netra_backend.app.cache_statistics import CacheStatistics
from netra_backend.app.cache_manager import LLMCacheManager
from netra_backend.app.cache_eviction import CacheEvictionManager
from netra_backend.app.cache_serialization import CacheSerializer

# Make all exports available at module level
__all__ = [
    'CacheStrategy',
    'CacheEntry',
    'CacheStatistics',
    'LLMCacheManager',
    'CacheEvictionManager',
    'CacheSerializer'
]