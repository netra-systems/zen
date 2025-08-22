"""
Cache Manager: Centralized cache management module.

This module provides the cache manager functionality extracted from the main
cache module for better modularity and import compatibility.
"""

# Re-export from main cache module for backward compatibility
from . import (
    CacheManager,
    cache_manager,
    get_cache_manager,
    get_default_cache
)

__all__ = [
    "CacheManager",
    "cache_manager", 
    "get_cache_manager",
    "get_default_cache"
]