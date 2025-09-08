"""Cache Service

Provides caching services with consistency management.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheConsistencyManager:
    """Manages cache consistency across operations."""
    
    def __init__(self):
        self.consistency_log: List[Dict[str, Any]] = []
    
    def log_operation(self, operation: str, key: str, timestamp: datetime = None):
        """Log a cache operation for consistency tracking."""
        entry = {
            'operation': operation,
            'key': key,
            'timestamp': timestamp or datetime.now()
        }
        self.consistency_log.append(entry)
    
    def get_consistency_report(self) -> Dict[str, Any]:
        """Get cache consistency report."""
        return {
            'total_operations': len(self.consistency_log),
            'recent_operations': self.consistency_log[-10:],
            'operation_types': {}
        }


class CacheService:
    """Provides caching services."""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.ttl_cache: Dict[str, datetime] = {}
        self.consistency_manager = CacheConsistencyManager()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check TTL
        if key in self.ttl_cache:
            if datetime.now() > self.ttl_cache[key]:
                await self.delete(key)
                return None
        
        value = self.cache.get(key)
        self.consistency_manager.log_operation('get', key)
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            self.cache[key] = value
            if ttl:
                self.ttl_cache[key] = datetime.now() + timedelta(seconds=ttl)
            self.consistency_manager.log_operation('set', key)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if key in self.cache:
                del self.cache[key]
            if key in self.ttl_cache:
                del self.ttl_cache[key]
            self.consistency_manager.log_operation('delete', key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            self.cache.clear()
            self.ttl_cache.clear()
            self.consistency_manager.log_operation('clear', 'all')
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False