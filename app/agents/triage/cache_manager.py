# Triage Cache Manager Module - Request caching functionality
import json
import hashlib
import re
from typing import Optional, Dict, Any
from app.redis_manager import RedisManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class TriageCacheManager:
    """Manages caching for triage requests."""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None, cache_ttl: int = 3600):
        self.redis_manager = redis_manager
        self.cache_ttl = cache_ttl
    
    def generate_hash(self, request: str) -> str:
        """Generate a hash for caching similar requests."""
        normalized = self._normalize_request(request)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _normalize_request(self, request: str) -> str:
        """Normalize request for better cache hits."""
        normalized = request.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    async def get_cached(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached triage result if available."""
        if not self.redis_manager:
            return None
        
        try:
            key = self._get_cache_key(request_hash)
            cached = await self.redis_manager.get(key)
            if cached:
                logger.info(f"Cache hit for hash: {request_hash}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to retrieve from cache: {e}")
        
        return None
    
    async def cache_result(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Cache triage result for future use."""
        if not self.redis_manager:
            return
        
        try:
            key = self._get_cache_key(request_hash)
            await self.redis_manager.set(key, json.dumps(result), ex=self.cache_ttl)
            logger.debug(f"Cached result for hash: {request_hash}")
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    def _get_cache_key(self, request_hash: str) -> str:
        """Generate cache key from request hash."""
        return f"triage:cache:{request_hash}"