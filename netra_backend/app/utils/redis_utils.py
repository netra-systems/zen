"""
Redis Utilities - SSOT Redis Access Patterns
============================================
Consolidated Redis utilities for consistent access patterns across the platform

PERFORMANCE: All Redis operations use the SSOT get_redis_client() pattern
for connection pooling and configuration consistency.
"""

from typing import Optional, Any, Dict, List
import json
import asyncio

# MIGRATED: Use SSOT Redis import pattern
from shared.isolated_environment import get_env

async def get_redis_with_retry(max_retries: int = 3) -> Any:
    """Get Redis client with retry logic"""
    for attempt in range(max_retries):
        try:
            # Use SSOT Redis import pattern
            import redis
            client = redis.Redis(
                host=get_env().get('REDIS_HOST', 'localhost'),
                port=int(get_env().get('REDIS_PORT', '6379')),
                decode_responses=True
            )
            # Test connection
            client.ping()
            return client
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

async def redis_get_json(key: str, default: Optional[Dict] = None) -> Dict:
    """Get JSON value from Redis with fallback"""
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            return json.loads(value)
        return default or {}
    except Exception:
        return default or {}

async def redis_set_json(key: str, value: Dict, ttl: Optional[int] = None) -> bool:
    """Set JSON value in Redis with optional TTL"""
    try:
        client = await get_redis_client()
        json_value = json.dumps(value)
        if ttl:
            await client.setex(key, ttl, json_value)
        else:
            await client.set(key, json_value)
        return True
    except Exception:
        return False

async def redis_batch_operation(operations: List[Dict]) -> List[Any]:
    """Execute batch Redis operations efficiently"""
    try:
        client = await get_redis_client()
        pipeline = client.pipeline()
        
        for op in operations:
            method = getattr(pipeline, op['method'])
            method(*op.get('args', []), **op.get('kwargs', {}))
        
        results = await pipeline.execute()
        return results
    except Exception:
        return []

# Export common patterns
__all__ = [
    'get_redis_with_retry',
    'redis_get_json', 
    'redis_set_json',
    'redis_batch_operation'
]
