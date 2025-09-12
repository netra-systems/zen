"""
Query Execution Strategy Pattern

This module implements the Strategy pattern for different query execution approaches.
Breaks down complex query logic into focused,  <= 8 line functions.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QueryExecutionStrategy(ABC):
    """Abstract strategy for query execution."""
    
    @abstractmethod
    async def execute(self, session: AsyncSession, query: str, params: Optional[Dict] = None) -> Any:
        """Execute the query strategy."""
        pass


class CachedQueryStrategy(QueryExecutionStrategy):
    """Strategy for cached query execution."""
    
    def __init__(self, query_cache, cache_tags: Optional[Set[str]] = None):
        """Initialize cached query strategy."""
        self.query_cache = query_cache
        self.cache_tags = cache_tags
    
    async def _check_cache_for_result(self, query: str, params: Optional[Dict]) -> Any:
        """Check cache for existing result."""
        return await self.query_cache.get_cached_result(query, params)

    async def execute(self, session: AsyncSession, query: str, params: Optional[Dict] = None) -> Any:
        """Execute query with caching using template method."""
        cached_result = await self._check_cache_for_result(query, params)
        if cached_result is not None:
            return cached_result
        
        result_data = await self._execute_fresh_query(session, query, params)
        await self._cache_query_result(query, params, result_data)
        return result_data
    
    async def _execute_fresh_query(self, session: AsyncSession, query: str, params: Optional[Dict]) -> Any:
        """Execute fresh query and return processed results."""
        executor = QueryExecutor()
        return await executor.execute_with_timing(session, query, params, self.query_cache)


class FreshQueryStrategy(QueryExecutionStrategy):
    """Strategy for fresh query execution without caching."""
    
    def __init__(self, query_cache):
        """Initialize fresh query strategy."""
        self.query_cache = query_cache
    
    async def execute(self, session: AsyncSession, query: str, params: Optional[Dict] = None) -> Any:
        """Execute query without caching."""
        executor = QueryExecutor()
        return await executor.execute_with_timing(session, query, params, self.query_cache)


class QueryExecutor:
    """Handles query execution with timing and result processing."""
    
    def _calculate_execution_duration(self, start_time: float) -> float:
        """Calculate query execution duration."""
        return time.time() - start_time

    async def execute_with_timing(self, session: AsyncSession, query: str, 
                                params: Optional[Dict], query_cache) -> Any:
        """Execute query with timing and metrics collection."""
        start_time = time.time()
        result_data = await self._execute_database_query(session, query, params)
        duration = self._calculate_execution_duration(start_time)
        self._update_query_metrics(query_cache, duration)
        return result_data
    
    async def _execute_database_query(self, session: AsyncSession, query: str, 
                                    params: Optional[Dict]) -> Any:
        """Execute database query and process results."""
        if params:
            result = await session.execute(text(query), params)
        else:
            result = await session.execute(text(query))
        
        return self._process_query_result(result)
    
    def _process_query_result(self, result) -> Any:
        """Process query result based on whether it returns rows."""
        if result.returns_rows:
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        return result.rowcount
    
    def _update_query_metrics(self, query_cache, duration: float) -> None:
        """Update query cache metrics."""
        query_cache.metrics.total_queries += 1
        query_cache.metrics.total_query_time += duration


class QueryCacheHelper:
    """Helper for query caching operations."""
    
    @staticmethod
    async def cache_query_result(query_cache, query: str, result_data: Any, 
                               params: Optional[Dict], duration: float, 
                               cache_tags: Optional[Set[str]]) -> None:
        """Cache query result with metadata."""
        await query_cache.cache_result(
            query=query, result=result_data, params=params,
            duration=duration, tags=cache_tags
        )


class QueryStrategyFactory:
    """Factory for creating query execution strategies."""
    
    @staticmethod
    def create_strategy(query_cache, force_refresh: bool = False, 
                       cache_tags: Optional[Set[str]] = None) -> QueryExecutionStrategy:
        """Create appropriate query execution strategy."""
        if force_refresh:
            return FreshQueryStrategy(query_cache)
        return CachedQueryStrategy(query_cache, cache_tags)