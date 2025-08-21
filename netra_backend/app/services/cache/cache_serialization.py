"""
Cache Serialization Utilities
Handles serialization and deserialization of cache entries
"""

import json
from datetime import datetime
from netra_backend.app.cache_models import CacheEntry


class CacheSerializer:
    """Handles serialization and deserialization of cache entries"""
    
    @staticmethod
    def serialize_entry(entry: CacheEntry) -> str:
        """Serialize cache entry to JSON string"""
        data = {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "accessed_at": entry.accessed_at.isoformat(),
            "access_count": entry.access_count,
            "ttl": entry.ttl,
            "tags": entry.tags,
            "metadata": entry.metadata
        }
        return json.dumps(data)
    
    @staticmethod
    def deserialize_entry(data: str) -> CacheEntry:
        """Deserialize JSON string to cache entry"""
        parsed = json.loads(data)
        return CacheEntry(
            key=parsed["key"],
            value=parsed["value"],
            created_at=datetime.fromisoformat(parsed["created_at"]),
            accessed_at=datetime.fromisoformat(parsed["accessed_at"]),
            access_count=parsed["access_count"],
            ttl=parsed["ttl"],
            tags=parsed["tags"],
            metadata=parsed["metadata"]
        )