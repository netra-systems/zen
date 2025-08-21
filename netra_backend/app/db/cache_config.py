"""Database Query Cache Configuration

Configuration classes and cache entry structures for the query caching system.
"""

import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set


class CacheStrategy(Enum):
    """Cache strategy types."""
    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on query patterns


@dataclass
class QueryCacheConfig:
    """Configuration for query caching."""
    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    cache_prefix: str = "db_query_cache:"
    metrics_enabled: bool = True
    
    # Adaptive caching thresholds
    frequent_query_threshold: int = 5  # Queries executed 5+ times
    frequent_query_ttl_multiplier: float = 2.0
    slow_query_threshold: float = 1.0  # Queries taking 1+ seconds
    slow_query_ttl_multiplier: float = 3.0


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    query_duration: float = 0.0
    tags: Set[str] = None
    
    def __post_init__(self) -> None:
        """Initialize post-creation fields."""
        if self.tags is None:
            self.tags = set()
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expires_at

    def access(self) -> None:
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def _build_entry_dict(self) -> Dict[str, Any]:
        """Build dictionary representation of cache entry."""
        return {
            'key': self.key, 'value': self.value, 'created_at': self.created_at,
            'expires_at': self.expires_at, 'access_count': self.access_count,
            'last_accessed': self.last_accessed, 'query_duration': self.query_duration,
            'tags': list(self.tags)
        }
    
    @classmethod
    def _extract_core_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract core fields from dictionary data."""
        return {
            'key': data['key'], 'value': data['value'],
            'created_at': data['created_at'], 'expires_at': data['expires_at']
        }
    
    @classmethod
    def _extract_metadata_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata fields from dictionary data."""
        return {
            'access_count': data['access_count'], 'last_accessed': data['last_accessed'],
            'query_duration': data['query_duration'], 'tags': set(data.get('tags', []))
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self._build_entry_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        core_fields = cls._extract_core_fields(data)
        metadata_fields = cls._extract_metadata_fields(data)
        return cls(**core_fields, **metadata_fields)


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    total_cache_time: float = 0.0
    total_query_time: float = 0.0
    cache_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries

    @property
    def avg_cache_time(self) -> float:
        """Average time to retrieve from cache."""
        if self.hits == 0:
            return 0.0
        return self.total_cache_time / self.hits

    @property
    def avg_query_time(self) -> float:
        """Average time for uncached queries."""
        if self.misses == 0:
            return 0.0
        return self.total_query_time / self.misses

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CacheKeyGenerator:
    """Generate cache keys for queries."""
    
    @staticmethod
    def _build_key_data(query: str, params: Optional[Dict]) -> Dict[str, Any]:
        """Build key data structure for hashing."""
        return {'query': query.strip(), 'params': params or {}}
    
    @staticmethod
    def _hash_key_string(key_string: str) -> str:
        """Generate hash from key string."""
        import hashlib
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    @staticmethod
    def generate_cache_key(query: str, params: Optional[Dict], prefix: str) -> str:
        """Generate cache key for query."""
        key_data = CacheKeyGenerator._build_key_data(query, params)
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = CacheKeyGenerator._hash_key_string(key_string)
        return f"{prefix}{key_hash[:32]}"


class QueryPatternAnalyzer:
    """Analyze query patterns for frequency tracking."""
    
    @staticmethod
    def _apply_pattern_normalization(pattern: str) -> str:
        """Apply regex substitutions for pattern normalization."""
        import re
        substitutions = [(r'\$\d+', '?'), (r':\w+', '?'), (r"'[^']*'", "'?'"),
                        (r'"[^"]*"', '"?"'), (r'\d+', '?')]
        for regex, replacement in substitutions:
            pattern = re.sub(regex, replacement, pattern)
        return pattern
    
    @staticmethod
    def normalize_query_pattern(query: str) -> str:
        """Extract query pattern for frequency tracking."""
        pattern = query.strip().upper()
        return QueryPatternAnalyzer._apply_pattern_normalization(pattern)

    @staticmethod
    def is_time_sensitive_query(query: str) -> bool:
        """Check if query is time-sensitive."""
        time_sensitive_keywords = ['now()', 'current_timestamp', 'today']
        return any(keyword in query.lower() for keyword in time_sensitive_keywords)


class CacheabilityChecker:
    """Check if queries should be cached."""
    
    NON_CACHEABLE_OPERATIONS = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'grant', 'revoke', 'begin', 'commit', 'rollback'
    ]
    
    @staticmethod
    def _is_empty_result(result: Any) -> bool:
        """Check if result is empty."""
        return isinstance(result, (list, tuple)) and len(result) == 0
    
    @staticmethod
    def _validate_all_cache_conditions(query: str, result: Any) -> bool:
        """Validate all caching conditions."""
        return (CacheabilityChecker.is_query_cacheable(query) and 
                CacheabilityChecker.is_result_cacheable(result) and 
                CacheabilityChecker.is_result_size_acceptable(result))
    
    @staticmethod
    def is_query_cacheable(query: str) -> bool:
        """Check if query type is cacheable."""
        query_lower = query.lower().strip()
        return not any(
            keyword in query_lower 
            for keyword in CacheabilityChecker.NON_CACHEABLE_OPERATIONS
        )

    @staticmethod
    def is_result_cacheable(result: Any) -> bool:
        """Check if result should be cached."""
        if result is None:
            return False
        return not CacheabilityChecker._is_empty_result(result)

    @staticmethod
    def is_result_size_acceptable(result: Any, max_size: int = 1_000_000) -> bool:
        """Check if result size is acceptable for caching."""
        try:
            result_size = len(str(result))
            return result_size <= max_size
        except:
            return True  # Allow caching if size check fails

    @staticmethod
    def should_cache_query(query: str, result: Any, config: QueryCacheConfig) -> bool:
        """Determine if query result should be cached."""
        if not config.enabled:
            return False
        return CacheabilityChecker._validate_all_cache_conditions(query, result)


class AdaptiveTTLCalculator:
    """Calculate adaptive TTL based on query characteristics."""
    
    @staticmethod
    def _get_base_calculation_values(
        query: str, duration: float, query_patterns: Dict[str, int], config: QueryCacheConfig
    ) -> tuple[int, float]:
        """Get base values for TTL calculation."""
        base_ttl = config.default_ttl
        pattern = QueryPatternAnalyzer.normalize_query_pattern(query)
        multipliers = AdaptiveTTLCalculator._calculate_multipliers(pattern, duration, query_patterns, config)
        return base_ttl, multipliers
    
    @staticmethod
    def _apply_final_adjustments(query: str, base_ttl: int, multipliers: float) -> int:
        """Apply final adjustments to TTL calculation."""
        adjusted_ttl = int(base_ttl * multipliers)
        final_ttl = AdaptiveTTLCalculator.apply_time_sensitivity_limit(query, adjusted_ttl)
        return max(final_ttl, 30)
    
    @staticmethod
    def _compute_adaptive_ttl(
        query: str, duration: float, query_patterns: Dict[str, int], config: QueryCacheConfig
    ) -> int:
        """Compute final adaptive TTL value."""
        base_ttl, multipliers = AdaptiveTTLCalculator._get_base_calculation_values(query, duration, query_patterns, config)
        return AdaptiveTTLCalculator._apply_final_adjustments(query, base_ttl, multipliers)
    
    @staticmethod
    def _calculate_multipliers(pattern: str, duration: float, query_patterns: Dict[str, int], config: QueryCacheConfig) -> float:
        """Calculate combined frequency and performance multipliers."""
        freq_mult = AdaptiveTTLCalculator.calculate_frequency_multiplier(pattern, query_patterns, config)
        perf_mult = AdaptiveTTLCalculator.calculate_performance_multiplier(duration, config)
        return freq_mult * perf_mult
    
    @staticmethod
    def calculate_frequency_multiplier(pattern: str, query_patterns: Dict[str, int], config: QueryCacheConfig) -> float:
        """Calculate TTL multiplier based on frequency."""
        frequency = query_patterns.get(pattern, 0)
        if frequency >= config.frequent_query_threshold:
            return config.frequent_query_ttl_multiplier
        return 1.0

    @staticmethod
    def calculate_performance_multiplier(duration: float, config: QueryCacheConfig) -> float:
        """Calculate TTL multiplier based on performance."""
        if duration >= config.slow_query_threshold:
            return config.slow_query_ttl_multiplier
        return 1.0

    @staticmethod
    def apply_time_sensitivity_limit(query: str, ttl: int) -> int:
        """Apply time sensitivity limits to TTL."""
        if QueryPatternAnalyzer.is_time_sensitive_query(query):
            return min(ttl, 60)  # Max 1 minute for time-sensitive
        return ttl

    @staticmethod
    def calculate_adaptive_ttl(
        query: str, duration: float, query_patterns: Dict[str, int], config: QueryCacheConfig
    ) -> int:
        """Calculate adaptive TTL based on query characteristics."""
        if config.strategy != CacheStrategy.ADAPTIVE:
            return config.default_ttl
        return AdaptiveTTLCalculator._compute_adaptive_ttl(query, duration, query_patterns, config)