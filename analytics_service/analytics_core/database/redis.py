"""Redis Cache Manager

Handles Redis connections and caching for analytics service.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError
except ImportError:
    # Fallback for when Redis is not available
    redis = None
    RedisError = Exception

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis cache manager for analytics service"""
    
    def __init__(self, 
                 url: str = "redis://localhost:6379/2",
                 max_connections: int = 20):
        """Initialize Redis manager"""
        self.url = url
        self.max_connections = max_connections
        self._pool = None
        self._redis = None
        
        # Cache TTL settings (in seconds)
        self.ttl_settings = {
            'user_session': 3600,      # 1 hour
            'rate_limiter': 60,        # 1 minute
            'real_time_metrics': 86400, # 1 day
            'hot_prompts': 1800,       # 30 minutes
            'event_buffer': 300        # 5 minutes
        }
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        if redis is None:
            logger.error("Redis not available - please install redis package")
            return False
            
        try:
            self._pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            self._redis = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._redis.ping()
            logger.info(f"Connected to Redis at {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            return False
    
    @property
    def redis(self):
        """Get Redis client"""
        return self._redis
    
    # User Session Cache
    async def set_user_session(self, user_id: str, session_data: Dict[str, Any]):
        """Set user session data"""
        if not self.redis:
            return False
            
        try:
            key = f"user_session:{user_id}"
            await self.redis.hset(key, mapping=session_data)
            await self.redis.expire(key, self.ttl_settings['user_session'])
            return True
        except Exception as e:
            logger.error(f"Failed to set user session: {e}")
            return False
    
    async def get_user_session(self, user_id: str) -> Dict[str, Any]:
        """Get user session data"""
        if not self.redis:
            return {}
            
        try:
            key = f"user_session:{user_id}"
            data = await self.redis.hgetall(key)
            # Convert byte strings to strings
            return {k.decode(): v.decode() for k, v in data.items()} if data else {}
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return {}
    
    async def update_user_session_field(self, user_id: str, field: str, value: Any):
        """Update specific field in user session"""
        if not self.redis:
            return False
            
        try:
            key = f"user_session:{user_id}"
            await self.redis.hset(key, field, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
            await self.redis.expire(key, self.ttl_settings['user_session'])
            return True
        except Exception as e:
            logger.error(f"Failed to update user session field: {e}")
            return False
    
    # Rate Limiting
    async def check_rate_limit(self, user_id: str, max_events: int = 1000) -> bool:
        """Check if user is within rate limit"""
        if not self.redis:
            return True  # Allow if Redis unavailable
            
        try:
            key = f"rate_limit:{user_id}"
            current = await self.redis.get(key)
            
            if current is None:
                # First request in window
                await self.redis.setex(key, self.ttl_settings['rate_limiter'], 1)
                return True
            
            current_count = int(current)
            if current_count >= max_events:
                return False
            
            # Increment counter
            await self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow if error occurs
    
    async def get_rate_limit_remaining(self, user_id: str, max_events: int = 1000) -> int:
        """Get remaining rate limit for user"""
        if not self.redis:
            return max_events
            
        try:
            key = f"rate_limit:{user_id}"
            current = await self.redis.get(key)
            return max_events - int(current) if current else max_events
        except Exception as e:
            logger.error(f"Failed to get rate limit remaining: {e}")
            return max_events
    
    # Real-time Metrics Cache
    async def set_realtime_metrics(self, metrics: Dict[str, Any]):
        """Set real-time metrics"""
        if not self.redis:
            return False
            
        try:
            key = "realtime_metrics"
            await self.redis.set(key, json.dumps(metrics), ex=self.ttl_settings['real_time_metrics'])
            
            # Also store in time series for trends
            timestamp = datetime.utcnow().timestamp()
            ts_key = f"metrics_timeseries:{int(timestamp // 300) * 300}"  # 5-minute buckets
            await self.redis.zadd(ts_key, {json.dumps(metrics): timestamp})
            await self.redis.expire(ts_key, self.ttl_settings['real_time_metrics'])
            
            return True
        except Exception as e:
            logger.error(f"Failed to set realtime metrics: {e}")
            return False
    
    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics"""
        if not self.redis:
            return {}
            
        try:
            key = "realtime_metrics"
            data = await self.redis.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            logger.error(f"Failed to get realtime metrics: {e}")
            return {}
    
    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for trend analysis"""
        if not self.redis:
            return []
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Get all timeseries keys for the time range
            pattern = "metrics_timeseries:*"
            keys = await self.redis.keys(pattern)
            
            all_metrics = []
            for key in keys:
                # Extract timestamp from key
                key_str = key.decode() if isinstance(key, bytes) else key
                ts_str = key_str.split(':')[1]
                if int(ts_str) >= cutoff_timestamp:
                    # Get metrics from this time bucket
                    metrics_data = await self.redis.zrange(key, 0, -1)
                    for metric_json in metrics_data:
                        try:
                            metric = json.loads(metric_json)
                            all_metrics.append(metric)
                        except json.JSONDecodeError:
                            continue
            
            # Sort by timestamp
            all_metrics.sort(key=lambda x: x.get('timestamp', ''))
            return all_metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    # Hot Prompts Cache
    async def add_hot_prompt(self, prompt_hash: str, prompt_data: Dict[str, Any]):
        """Add prompt to hot prompts cache"""
        if not self.redis:
            return False
            
        try:
            key = "hot_prompts"
            # Use sorted set with score as timestamp for ordering
            score = datetime.utcnow().timestamp()
            await self.redis.zadd(key, {json.dumps({
                'hash': prompt_hash,
                **prompt_data
            }): score})
            
            # Keep only recent prompts (last 100)
            await self.redis.zremrangebyrank(key, 0, -101)
            await self.redis.expire(key, self.ttl_settings['hot_prompts'])
            return True
            
        except Exception as e:
            logger.error(f"Failed to add hot prompt: {e}")
            return False
    
    async def get_hot_prompts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent hot prompts"""
        if not self.redis:
            return []
            
        try:
            key = "hot_prompts"
            # Get most recent prompts
            prompts_data = await self.redis.zrevrange(key, 0, limit - 1)
            
            prompts = []
            for prompt_json in prompts_data:
                try:
                    prompt = json.loads(prompt_json)
                    prompts.append(prompt)
                except json.JSONDecodeError:
                    continue
                    
            return prompts
            
        except Exception as e:
            logger.error(f"Failed to get hot prompts: {e}")
            return []
    
    # Event Buffer for Batch Processing
    async def buffer_event(self, event_data: Dict[str, Any]):
        """Buffer event for batch processing"""
        if not self.redis:
            return False
            
        try:
            key = "event_buffer"
            await self.redis.lpush(key, json.dumps(event_data))
            await self.redis.expire(key, self.ttl_settings['event_buffer'])
            return True
        except Exception as e:
            logger.error(f"Failed to buffer event: {e}")
            return False
    
    async def get_buffered_events(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Get batch of buffered events"""
        if not self.redis:
            return []
            
        try:
            key = "event_buffer"
            # Get events and remove them atomically
            pipeline = self.redis.pipeline()
            pipeline.lrange(key, 0, batch_size - 1)
            pipeline.ltrim(key, batch_size, -1)
            results = await pipeline.execute()
            
            events = []
            for event_json in results[0]:
                try:
                    event = json.loads(event_json)
                    events.append(event)
                except json.JSONDecodeError:
                    continue
                    
            return events
            
        except Exception as e:
            logger.error(f"Failed to get buffered events: {e}")
            return []
    
    async def get_buffer_size(self) -> int:
        """Get current buffer size"""
        if not self.redis:
            return 0
            
        try:
            key = "event_buffer"
            return await self.redis.llen(key)
        except Exception as e:
            logger.error(f"Failed to get buffer size: {e}")
            return 0
    
    # Analytics Caching
    async def cache_report(self, report_key: str, report_data: Dict[str, Any], ttl: int = 300):
        """Cache analytics report"""
        if not self.redis:
            return False
            
        try:
            key = f"report_cache:{report_key}"
            await self.redis.set(key, json.dumps(report_data), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to cache report: {e}")
            return False
    
    async def get_cached_report(self, report_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analytics report"""
        if not self.redis:
            return None
            
        try:
            key = f"report_cache:{report_key}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get cached report: {e}")
            return None
    
    # Health and Maintenance
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        if not self.redis:
            return False
            
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def cleanup_expired_keys(self):
        """Clean up expired keys (maintenance task)"""
        if not self.redis:
            return
            
        try:
            # Clean up old rate limit keys
            rate_limit_pattern = "rate_limit:*"
            rate_limit_keys = await self.redis.keys(rate_limit_pattern)
            
            expired_keys = []
            for key in rate_limit_keys:
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # Key exists but has no TTL
                    expired_keys.append(key)
            
            if expired_keys:
                await self.redis.delete(*expired_keys)
                logger.info(f"Cleaned up {len(expired_keys)} expired rate limit keys")
            
            # Clean up old metrics timeseries
            cutoff_time = datetime.utcnow() - timedelta(hours=48)  # Keep 48h of data
            cutoff_timestamp = cutoff_time.timestamp()
            
            metrics_pattern = "metrics_timeseries:*"
            metrics_keys = await self.redis.keys(metrics_pattern)
            
            old_keys = []
            for key in metrics_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                ts_str = key_str.split(':')[1]
                if int(ts_str) < cutoff_timestamp:
                    old_keys.append(key)
            
            if old_keys:
                await self.redis.delete(*old_keys)
                logger.info(f"Cleaned up {len(old_keys)} old metrics timeseries keys")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception:
                pass
        self._redis = None
        self._pool = None