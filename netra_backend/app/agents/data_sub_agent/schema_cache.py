"""
Backward compatibility module for SchemaCache.

The SchemaCache functionality has been consolidated into UnifiedDataAgent.
This module provides backward compatibility for existing imports.
"""

from typing import Dict, Any, Optional, List

class SchemaCache:
    """Legacy SchemaCache class for backward compatibility."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with backward compatibility."""
        self._cache = {}
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table schema from cache or fetch."""
        # Legacy compatibility method
        if table_name in self._cache:
            return self._cache[table_name]
        
        # Mock schema for compatibility
        schema = {
            "table_name": table_name,
            "columns": [
                {"name": "id", "type": "String", "nullable": False},
                {"name": "timestamp", "type": "DateTime", "nullable": False},
                {"name": "value", "type": "Float64", "nullable": True}
            ],
            "engine": "MergeTree",
            "order_by": ["timestamp"]
        }
        self._cache[table_name] = schema
        return schema
    
    async def refresh_schema(self, table_name: str) -> Dict[str, Any]:
        """Refresh schema cache."""
        # Legacy compatibility method
        if table_name in self._cache:
            del self._cache[table_name]
        return await self.get_table_schema(table_name)
    
    def get_cached_tables(self) -> List[str]:
        """Get list of cached table names."""
        return list(self._cache.keys())
    
    def clear_cache(self):
        """Clear all cached schemas."""
        self._cache.clear()

# Export for backward compatibility
__all__ = ["SchemaCache"]