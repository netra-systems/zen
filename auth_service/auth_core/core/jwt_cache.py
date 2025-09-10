"""
JWT Validation Cache - High-performance caching for JWT token validation
Provides Redis-backed caching with memory fallback for sub-100ms validation
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from netra_backend.app.redis_manager import redis_manager as auth_redis_manager

logger = logging.getLogger(__name__)

class JWTValidationCache:
    """High-performance JWT validation cache with Redis persistence"""
    
    def __init__(self):
        # Performance optimization: In-memory validation cache
        self._validation_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._max_cache_size = 10000
        
        # Redis client for persistent caching
        self.redis_manager = auth_redis_manager
        self._cache_enabled = self.redis_manager.enabled
        
        # Performance metrics
        self._validation_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'redis_hits': 0,
            'redis_misses': 0,
            'validation_count': 0
        }
        
        logger.info(f"JWT validation cache initialized - Redis enabled: {self._cache_enabled}")
    
    def get_cache_key(self, token: str, token_type: str = "access") -> str:
        """Generate consistent cache key for token validation"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return f"jwt_validation:{token_hash}:{token_type}"
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get validation result from cache with Redis fallback"""
        try:
            self._validation_stats['validation_count'] += 1
            
            # Try in-memory cache first (fastest - sub-millisecond)
            if cache_key in self._validation_cache:
                cached_entry = self._validation_cache[cache_key]
                if cached_entry['expires'] > time.time():
                    # Also check if the cached JWT token itself has expired
                    cached_data = cached_entry['data']
                    if cached_data and isinstance(cached_data, dict):
                        jwt_exp = cached_data.get('exp')
                        if jwt_exp and jwt_exp <= time.time():
                            # JWT token has expired, remove from cache
                            del self._validation_cache[cache_key]
                            return None
                    self._validation_stats['cache_hits'] += 1
                    return cached_data
                else:
                    # Expired, remove from memory cache
                    del self._validation_cache[cache_key]
            
            # Try Redis cache if available (fast - 1-5ms typically)
            if self._cache_enabled and self.redis_manager.get_client():
                try:
                    redis_data = self.redis_manager.get_client().get(f"jwt_cache:{cache_key}")
                    if redis_data:
                        cached_data = json.loads(redis_data)
                        
                        # Check if the cached JWT token itself has expired
                        if cached_data and isinstance(cached_data, dict):
                            jwt_exp = cached_data.get('exp')
                            if jwt_exp and jwt_exp <= time.time():
                                # JWT token has expired, remove from Redis cache
                                self.redis_manager.get_client().delete(f"jwt_cache:{cache_key}")
                                return None
                        
                        self._validation_stats['redis_hits'] += 1
                        
                        # Also update in-memory cache for next time
                        self._validation_cache[cache_key] = {
                            'data': cached_data,
                            'expires': time.time() + min(300, 60)  # 1-5 min memory cache
                        }
                        return cached_data
                    else:
                        self._validation_stats['redis_misses'] += 1
                except Exception as e:
                    logger.debug(f"Redis cache read failed: {e}")
                    self._validation_stats['redis_misses'] += 1
            
            self._validation_stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
            return None
    
    def cache_validation_result(self, cache_key: str, result: Optional[Dict], ttl: int = None):
        """Cache validation result with Redis persistence and memory cache"""
        try:
            if ttl is None:
                ttl = self._cache_ttl
            
            cache_data = result if result is not None else "INVALID"
            
            # Update in-memory cache (with size limit)
            if len(self._validation_cache) >= self._max_cache_size:
                # Remove oldest entries
                current_time = time.time()
                expired_keys = [k for k, v in self._validation_cache.items() 
                               if v['expires'] <= current_time]
                for key in expired_keys[:len(expired_keys)//2]:  # Remove half of expired
                    del self._validation_cache[key]
            
            # Cache in memory for fastest access
            self._validation_cache[cache_key] = {
                'data': cache_data,
                'expires': time.time() + min(ttl, 300)  # Max 5 min memory cache
            }
            
            # Update Redis cache if available (async to not block)
            if self._cache_enabled and self.redis_manager.get_client():
                try:
                    asyncio.create_task(self._cache_to_redis_async(cache_key, cache_data, ttl))
                except Exception as e:
                    logger.debug(f"Redis cache write failed: {e}")
        
        except Exception as e:
            logger.debug(f"Cache write error: {e}")
    
    async def _cache_to_redis_async(self, cache_key: str, cache_data: Any, ttl: int):
        """Async Redis cache write to avoid blocking"""
        try:
            redis_client = self.redis_manager.get_client()
            if redis_client:
                redis_client.setex(
                    f"jwt_cache:{cache_key}", 
                    ttl, 
                    json.dumps(cache_data, default=str)
                )
        except Exception as e:
            logger.debug(f"Async Redis cache write failed: {e}")
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cached tokens for a user (when user is blacklisted)"""
        try:
            # Remove from memory cache
            keys_to_remove = []
            for cache_key, cached_entry in self._validation_cache.items():
                if (isinstance(cached_entry['data'], dict) and 
                    cached_entry['data'].get('sub') == user_id):
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                del self._validation_cache[key]
            
            # Remove from Redis cache if available
            if self._cache_enabled and self.redis_manager.get_client():
                try:
                    # This is a simplified approach - in production you might want
                    # to maintain an index of user_id -> cache_keys
                    pattern = f"jwt_cache:*"
                    keys = self.redis_manager.get_client().keys(pattern)
                    for key in keys:
                        try:
                            data = self.redis_manager.get_client().get(key)
                            if data:
                                token_data = json.loads(data)
                                if (isinstance(token_data, dict) and 
                                    token_data.get('sub') == user_id):
                                    self.redis_manager.get_client().delete(key)
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Redis user cache invalidation failed: {e}")
            
            logger.info(f"Invalidated cached tokens for user {user_id}")
            
        except Exception as e:
            logger.error(f"User cache invalidation error: {e}")
    
    def clear_cache(self):
        """Clear all validation cache for testing or maintenance"""
        self._validation_cache.clear()
        if self._cache_enabled and self.redis_manager.get_client():
            try:
                # Clear JWT cache keys from Redis
                pattern = "jwt_cache:*"
                keys = self.redis_manager.get_client().keys(pattern)
                if keys:
                    self.redis_manager.get_client().delete(*keys)
            except Exception as e:
                logger.debug(f"Redis cache clear failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_validations = self._validation_stats['validation_count']
        memory_hit_rate = (self._validation_stats['cache_hits'] / total_validations * 100) if total_validations > 0 else 0
        redis_hit_rate = (self._validation_stats['redis_hits'] / total_validations * 100) if total_validations > 0 else 0
        overall_hit_rate = ((self._validation_stats['cache_hits'] + self._validation_stats['redis_hits']) / total_validations * 100) if total_validations > 0 else 0
        
        return {
            'validation_count': total_validations,
            'memory_cache_hits': self._validation_stats['cache_hits'],
            'redis_cache_hits': self._validation_stats['redis_hits'],
            'cache_misses': self._validation_stats['cache_misses'],
            'memory_hit_rate_percent': round(memory_hit_rate, 2),
            'redis_hit_rate_percent': round(redis_hit_rate, 2),
            'overall_hit_rate_percent': round(overall_hit_rate, 2),
            'memory_cache_size': len(self._validation_cache),
            'cache_enabled': self._cache_enabled
        }

# Global instance for performance
jwt_validation_cache = JWTValidationCache()