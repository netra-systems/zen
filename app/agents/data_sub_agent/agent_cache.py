"""Cache management for DataSubAgent."""

from typing import Dict, Optional, List, Any
import time

from app.logging_config import central_logger as logger


class CacheManager:
    """Manages schema caching operations for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
        self._ensure_cache_initialized()
    
    def _ensure_cache_initialized(self) -> None:
        """Initialize cache dictionaries if they don't exist."""
        if not hasattr(self.agent, '_schema_cache'):
            self.agent._schema_cache: Dict[str, Dict[str, Any]] = {}
            self.agent._schema_cache_timestamps: Dict[str, float] = {}
    
    async def get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema information with TTL and cache invalidation."""
        self._ensure_cache_initialized()
        current_time = time.time()
        if not force_refresh and self._is_cache_valid(table_name, current_time):
            return self.agent._schema_cache[table_name]
        return await self._fetch_and_cache_schema(table_name, current_time)
    
    def _is_cache_valid(self, table_name: str, current_time: float) -> bool:
        """Check if cache entry exists and is still valid."""
        if table_name not in self.agent._schema_cache:
            return False
        
        cache_time = self.agent._schema_cache_timestamps.get(table_name, 0)
        cache_age = current_time - cache_time
        return cache_age < 300  # 5 minutes TTL
    
    async def _fetch_and_cache_schema(self, table_name: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Fetch fresh schema and update cache."""
        schema = await self.agent.clickhouse_ops.get_table_schema(table_name)
        if schema:
            self._update_schema_cache(table_name, schema, current_time)
            await self.cleanup_old_cache_entries(current_time)
        return schema
    
    def _update_schema_cache(self, table_name: str, schema: Dict[str, Any], current_time: float) -> None:
        """Update schema cache with new data."""
        self.agent._schema_cache[table_name] = schema
        self.agent._schema_cache_timestamps[table_name] = current_time
    
    async def cleanup_old_cache_entries(self, current_time: float) -> None:
        """Clean up old cache entries to prevent memory leaks."""
        max_cache_age = 3600  # 1 hour
        tables_to_remove = self._identify_expired_cache_entries(current_time, max_cache_age)
        self._remove_expired_cache_entries(tables_to_remove)
    
    def _identify_expired_cache_entries(self, current_time: float, max_cache_age: float) -> List[str]:
        """Identify cache entries that have expired."""
        return [
            table_name for table_name, timestamp in self.agent._schema_cache_timestamps.items()
            if current_time - timestamp > max_cache_age
        ]
    
    def _remove_expired_cache_entries(self, tables_to_remove: List[str]) -> None:
        """Remove expired entries from cache."""
        for table_name in tables_to_remove:
            self.agent._schema_cache.pop(table_name, None)
            self.agent._schema_cache_timestamps.pop(table_name, None)
    
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache for specific table or all tables."""
        if not hasattr(self.agent, '_schema_cache'):
            return
            
        if table_name:
            self._invalidate_single_table_cache(table_name)
        else:
            self._invalidate_all_cache_entries()
    
    def _invalidate_single_table_cache(self, table_name: str) -> None:
        """Invalidate cache for a specific table."""
        self.agent._schema_cache.pop(table_name, None)
        self.agent._schema_cache_timestamps.pop(table_name, None)
    
    def _invalidate_all_cache_entries(self) -> None:
        """Clear entire schema cache."""
        self.agent._schema_cache.clear()
        self.agent._schema_cache_timestamps.clear()
    
    def cache_clear(self) -> None:
        """Clear the schema cache (for test compatibility)."""
        if hasattr(self.agent, '_schema_cache'):
            self.agent._schema_cache.clear()
        if hasattr(self.agent, '_schema_cache_timestamps'):
            self.agent._schema_cache_timestamps.clear()