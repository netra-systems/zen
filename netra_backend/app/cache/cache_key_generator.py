"""
Cache Key Generator - SSOT Import Compatibility Module

This module provides SSOT import compatibility by re-exporting the CacheKeyGenerator
from its actual location in the database cache configuration module.

Business Value Justification (BVJ):
- Segment: Platform/Internal - All user segments benefit from caching performance
- Business Goal: Performance optimization reduces infrastructure costs
- Value Impact: Efficient cache key generation improves cache hit rates
- Strategic Impact: Enables platform scalability for customer growth
"""

# SSOT Import: Re-export CacheKeyGenerator from its actual location
from netra_backend.app.db.cache_config import (
    CacheKeyGenerator,
    CacheEntry,
    CacheMetrics,
    CacheStrategy,
    QueryCacheConfig,
    AdaptiveTTLCalculator,
    CacheabilityChecker,
    QueryPatternAnalyzer
)

# Export for import compatibility
__all__ = [
    'CacheKeyGenerator',
    'CacheEntry',
    'CacheMetrics', 
    'CacheStrategy',
    'QueryCacheConfig',
    'AdaptiveTTLCalculator',
    'CacheabilityChecker',
    'QueryPatternAnalyzer'
]