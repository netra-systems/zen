"""Database query optimization and caching for performance enhancement.

This module provides intelligent query caching and performance metrics
tracking for database operations.
"""

import time
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Optional, Any, Callable

from app.logging_config import central_logger
from .performance_cache import MemoryCache

logger = central_logger.get_logger(__name__)


@dataclass
class QueryMetrics:
    """Database query performance metrics."""
    query_hash: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    max_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    cache_hits: int = 0
    cache_misses: int = 0


class QueryOptimizer:
    """Database query optimization and caching."""
    
    def __init__(self, cache_size: int = 500, cache_ttl: int = 300):
        self.cache = MemoryCache(max_size=cache_size, default_ttl=cache_ttl)
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self._slow_query_threshold = 1.0  # seconds
    
    def _get_query_hash(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate hash for query caching."""
        query_str = query.strip().lower()
        if params:
            param_str = json.dumps(params, sort_keys=True)
            combined = f"{query_str}|{param_str}"
        else:
            combined = query_str
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def execute_with_cache(self, query: str, params: Optional[Dict], 
                                executor: Callable) -> Any:
        """Execute query with caching and metrics tracking."""
        query_hash = self._get_query_hash(query, params)
        
        # Check cache first for read queries
        if self._is_read_query(query):
            cached_result = await self._try_cache_lookup(query_hash)
            if cached_result is not None:
                return cached_result
        
        # Execute query with timing
        return await self._execute_with_timing(query, query_hash, executor)
    
    async def _try_cache_lookup(self, query_hash: str) -> Optional[Any]:
        """Try to get result from cache."""
        cached_result = await self.cache.get(query_hash)
        if cached_result is not None:
            self._update_cache_hit_metrics(query_hash)
            return cached_result
        return None
    
    async def _execute_with_timing(self, query: str, query_hash: str, 
                                  executor: Callable) -> Any:
        """Execute query with performance timing."""
        start_time = time.time()
        try:
            result = await executor()
            execution_time = time.time() - start_time
            
            # Update metrics and cache
            self._update_query_metrics(query_hash, execution_time)
            await self._cache_result_if_applicable(query, query_hash, result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_metrics(query_hash, execution_time)
            logger.error(f"Query execution failed after {execution_time:.2f}s: {e}")
            raise
    
    async def _cache_result_if_applicable(self, query: str, query_hash: str, 
                                         result: Any) -> None:
        """Cache query result if applicable."""
        if self._is_read_query(query) and result is not None:
            cache_ttl = self._determine_cache_ttl(query)
            await self.cache.set(query_hash, result, ttl=cache_ttl)
    
    def _is_read_query(self, query: str) -> bool:
        """Check if query is a read operation."""
        query_lower = query.strip().lower()
        read_prefixes = ('select', 'show', 'describe', 'explain')
        return query_lower.startswith(read_prefixes)
    
    def _determine_cache_ttl(self, query: str) -> int:
        """Determine appropriate cache TTL based on query type."""
        query_lower = query.strip().lower()
        
        if 'user' in query_lower or 'session' in query_lower:
            return 60  # User data: 1 minute
        elif 'config' in query_lower or 'setting' in query_lower:
            return 600  # Config data: 10 minutes
        elif 'audit' in query_lower or 'log' in query_lower:
            return 30   # Audit data: 30 seconds
        else:
            return 300  # Default: 5 minutes
    
    def _update_query_metrics(self, query_hash: str, execution_time: float):
        """Update query execution metrics."""
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(query_hash=query_hash)
        
        metrics = self.query_metrics[query_hash]
        metrics.execution_count += 1
        metrics.total_execution_time += execution_time
        metrics.avg_execution_time = (
            metrics.total_execution_time / metrics.execution_count
        )
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
        metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
        
        if execution_time > self._slow_query_threshold:
            logger.warning(
                f"Slow query detected: {execution_time:.2f}s (hash: {query_hash})"
            )
    
    def _update_cache_hit_metrics(self, query_hash: str):
        """Update cache hit metrics."""
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(query_hash=query_hash)
        self.query_metrics[query_hash].cache_hits += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report."""
        slow_queries = self._get_slow_queries()
        cache_stats = self.cache.get_stats()
        
        return {
            "total_queries": len(self.query_metrics),
            "slow_queries": len(slow_queries),
            "cache_stats": cache_stats,
            "top_slow_queries": self._get_top_slow_queries(slow_queries)
        }
    
    def _get_slow_queries(self) -> list:
        """Get list of slow queries."""
        return [
            m for m in self.query_metrics.values() 
            if m.avg_execution_time > self._slow_query_threshold
        ]
    
    def _get_top_slow_queries(self, slow_queries: list) -> list:
        """Get top 10 slowest queries."""
        return sorted(
            slow_queries, 
            key=lambda x: x.avg_execution_time, 
            reverse=True
        )[:10]