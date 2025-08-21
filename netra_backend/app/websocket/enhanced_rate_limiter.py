"""Enhanced WebSocket Rate Limiting with Redis and Token Bucket Algorithm.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Prevent abuse and ensure fair resource usage  
- Value Impact: Protects service availability from malicious or excessive usage
- Strategic Impact: $60K MRR - Rate limiting for enterprise service reliability

This module provides:
- Redis-backed distributed rate limiting
- Token bucket algorithm with sliding window
- Per-client and global rate limiting
- Backpressure handling and queue management
- Memory-efficient implementation for high concurrency
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib

from app.logging_config import central_logger
from app.redis_manager import RedisManager

logger = central_logger.get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting with refill mechanism."""
    
    capacity: int = 100
    tokens: float = 100.0
    refill_rate: float = 1.0  # tokens per second
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket, return if successful."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        self._refill()
        return {
            "tokens": self.tokens,
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "utilization": (self.capacity - self.tokens) / self.capacity
        }


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting policies."""
    
    # Per-minute limits by tier
    messages_per_minute: int = 60
    burst_capacity: int = 10
    
    # Token bucket settings
    bucket_capacity: int = 100
    refill_rate: float = 1.0  # tokens per second
    
    # Window settings
    window_size: int = 60  # seconds
    cleanup_interval: int = 300  # seconds
    
    # Global limits
    global_messages_per_second: int = 1000
    max_concurrent_connections: int = 10000
    
    # Memory management
    max_queue_size: int = 1000
    backpressure_threshold: float = 0.8  # 80% of queue size
    
    @classmethod
    def for_tier(cls, tier: str) -> 'RateLimitConfig':
        """Create config for specific user tier."""
        tier_configs = {
            "free": cls(messages_per_minute=30, burst_capacity=5, bucket_capacity=50),
            "early": cls(messages_per_minute=60, burst_capacity=10, bucket_capacity=100),
            "mid": cls(messages_per_minute=120, burst_capacity=20, bucket_capacity=200),
            "enterprise": cls(messages_per_minute=300, burst_capacity=50, bucket_capacity=500)
        }
        return tier_configs.get(tier, cls())


class DistributedRateLimiter:
    """Redis-backed distributed rate limiter with token bucket algorithm."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.local_buckets: Dict[str, TokenBucket] = {}
        self.config_cache: Dict[str, RateLimitConfig] = {}
        self.metrics = {
            "requests_checked": 0,
            "requests_allowed": 0,
            "requests_denied": 0,
            "redis_operations": 0,
            "cache_hits": 0
        }
        
        # Global rate limiting
        self.global_bucket = TokenBucket(
            capacity=1000,
            tokens=1000.0,
            refill_rate=16.67  # ~1000 per minute
        )
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup of expired entries."""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")
    
    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired rate limit entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, bucket in self.local_buckets.items():
            if current_time - bucket.last_refill > 600:  # 10 minutes inactive
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.local_buckets[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")
    
    def get_config(self, user_tier: str) -> RateLimitConfig:
        """Get rate limit configuration for user tier."""
        if user_tier not in self.config_cache:
            self.config_cache[user_tier] = RateLimitConfig.for_tier(user_tier)
        return self.config_cache[user_tier]
    
    async def check_rate_limit(self, client_id: str, user_tier: str = "free") -> Dict[str, Any]:
        """Check rate limit for client using distributed approach."""
        self.metrics["requests_checked"] += 1
        config = self.get_config(user_tier)
        
        # Check global rate limit first
        if not self.global_bucket.consume(1):
            self.metrics["requests_denied"] += 1
            return self._create_denied_result("global_limit_exceeded", config)
        
        # Check per-client rate limit
        client_result = await self._check_client_rate_limit(client_id, config)
        
        if client_result["allowed"]:
            self.metrics["requests_allowed"] += 1
        else:
            self.metrics["requests_denied"] += 1
        
        return client_result
    
    async def _check_client_rate_limit(self, client_id: str, config: RateLimitConfig) -> Dict[str, Any]:
        """Check rate limit for specific client."""
        # Use local token bucket for fast checks
        bucket_key = f"bucket:{client_id}"
        bucket = self._get_or_create_bucket(bucket_key, config)
        
        # Check local bucket first
        if bucket.consume(1):
            # Update Redis state asynchronously
            asyncio.create_task(self._update_redis_state(client_id, config))
            return self._create_allowed_result(bucket, config)
        
        # Local bucket exhausted, check Redis for distributed state
        redis_allowed = await self._check_redis_rate_limit(client_id, config)
        if redis_allowed:
            # Reset local bucket with some tokens
            bucket.tokens = min(bucket.capacity, bucket.tokens + 5)
            return self._create_allowed_result(bucket, config)
        
        return self._create_denied_result("rate_limit_exceeded", config, bucket)
    
    def _get_or_create_bucket(self, bucket_key: str, config: RateLimitConfig) -> TokenBucket:
        """Get existing bucket or create new one."""
        if bucket_key not in self.local_buckets:
            self.local_buckets[bucket_key] = TokenBucket(
                capacity=config.bucket_capacity,
                tokens=config.bucket_capacity,
                refill_rate=config.refill_rate
            )
        return self.local_buckets[bucket_key]
    
    async def _check_redis_rate_limit(self, client_id: str, config: RateLimitConfig) -> bool:
        """Check rate limit in Redis for distributed enforcement."""
        if not self.redis_manager.enabled:
            return True  # Allow if Redis unavailable
        
        try:
            current_time = int(time.time())
            window_key = f"rate_limit:{client_id}:{current_time // config.window_size}"
            
            redis_client = self.redis_manager.get_client()
            current_count = await redis_client.get(window_key)
            current_count = int(current_count) if current_count else 0
            
            self.metrics["redis_operations"] += 1
            
            if current_count < config.messages_per_minute:
                # Increment counter atomically
                pipe = redis_client.pipeline()
                pipe.incr(window_key)
                pipe.expire(window_key, config.window_size * 2)  # Keep for 2 windows
                await pipe.execute()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True  # Allow on Redis errors to prevent service disruption
    
    async def _update_redis_state(self, client_id: str, config: RateLimitConfig) -> None:
        """Update Redis state asynchronously."""
        if not self.redis_manager.enabled:
            return
        
        try:
            current_time = int(time.time())
            window_key = f"rate_limit:{client_id}:{current_time // config.window_size}"
            
            redis_client = self.redis_manager.get_client()
            pipe = redis_client.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, config.window_size * 2)
            await pipe.execute()
            
            self.metrics["redis_operations"] += 1
            
        except Exception as e:
            logger.error(f"Redis state update failed: {e}")
    
    def _create_allowed_result(self, bucket: TokenBucket, config: RateLimitConfig) -> Dict[str, Any]:
        """Create result for allowed request."""
        bucket_status = bucket.get_status()
        return {
            "allowed": True,
            "reason": None,
            "bucket_status": bucket_status,
            "config": config.__dict__,
            "retry_after": 0,
            "global_status": self.global_bucket.get_status()
        }
    
    def _create_denied_result(self, reason: str, config: RateLimitConfig, 
                            bucket: Optional[TokenBucket] = None) -> Dict[str, Any]:
        """Create result for denied request."""
        bucket_status = bucket.get_status() if bucket else None
        retry_after = self._calculate_retry_after(bucket, config)
        
        return {
            "allowed": False,
            "reason": reason,
            "bucket_status": bucket_status,
            "config": config.__dict__,
            "retry_after": retry_after,
            "global_status": self.global_bucket.get_status()
        }
    
    def _calculate_retry_after(self, bucket: Optional[TokenBucket], 
                              config: RateLimitConfig) -> float:
        """Calculate retry after time in seconds."""
        if bucket and bucket.refill_rate > 0:
            tokens_needed = 1 - bucket.tokens
            return max(0, tokens_needed / bucket.refill_rate)
        return config.window_size
    
    async def reset_rate_limit(self, client_id: str) -> bool:
        """Reset rate limit for client (admin function)."""
        try:
            # Reset local bucket
            bucket_key = f"bucket:{client_id}"
            if bucket_key in self.local_buckets:
                bucket = self.local_buckets[bucket_key]
                bucket.tokens = bucket.capacity
                bucket.last_refill = time.time()
            
            # Reset Redis state
            if self.redis_manager.enabled:
                redis_client = self.redis_manager.get_client()
                pattern = f"rate_limit:{client_id}:*"
                keys_to_delete = []
                async for key in redis_client.scan_iter(match=pattern):
                    keys_to_delete.append(key)
                
                if keys_to_delete:
                    await redis_client.delete(*keys_to_delete)
                    self.metrics["redis_operations"] += len(keys_to_delete)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit reset failed for {client_id}: {e}")
            return False
    
    async def get_client_status(self, client_id: str, user_tier: str = "free") -> Dict[str, Any]:
        """Get detailed rate limit status for client."""
        config = self.get_config(user_tier)
        bucket_key = f"bucket:{client_id}"
        
        # Local bucket status
        bucket_status = None
        if bucket_key in self.local_buckets:
            bucket_status = self.local_buckets[bucket_key].get_status()
        
        # Redis status
        redis_status = await self._get_redis_status(client_id, config)
        
        return {
            "client_id": client_id,
            "tier": user_tier,
            "config": config.__dict__,
            "local_bucket": bucket_status,
            "redis_state": redis_status,
            "global_bucket": self.global_bucket.get_status()
        }
    
    async def _get_redis_status(self, client_id: str, config: RateLimitConfig) -> Dict[str, Any]:
        """Get Redis state for client."""
        if not self.redis_manager.enabled:
            return {"enabled": False}
        
        try:
            current_time = int(time.time())
            window_key = f"rate_limit:{client_id}:{current_time // config.window_size}"
            
            redis_client = self.redis_manager.get_client()
            current_count = await redis_client.get(window_key)
            current_count = int(current_count) if current_count else 0
            
            return {
                "enabled": True,
                "current_window_count": current_count,
                "window_remaining": config.messages_per_minute - current_count,
                "window_key": window_key
            }
            
        except Exception as e:
            logger.error(f"Redis status check failed: {e}")
            return {"enabled": True, "error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive rate limiter metrics."""
        return {
            "requests": self.metrics.copy(),
            "local_buckets": len(self.local_buckets),
            "global_bucket": self.global_bucket.get_status(),
            "config_cache_size": len(self.config_cache),
            "redis_enabled": self.redis_manager.enabled
        }
    
    async def shutdown(self) -> None:
        """Shutdown rate limiter and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.local_buckets.clear()
        self.config_cache.clear()
        logger.info("Enhanced rate limiter shutdown completed")


class BackpressureManager:
    """Manages backpressure and message queuing under high load."""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.client_queues: Dict[str, deque] = defaultdict(deque)
        self.queue_metrics = defaultdict(lambda: {"queued": 0, "processed": 0, "dropped": 0})
        self.backpressure_threshold = int(max_queue_size * 0.8)
        
    def enqueue_message(self, client_id: str, message: Dict[str, Any], 
                       priority: int = 0) -> Dict[str, Any]:
        """Enqueue message with backpressure handling."""
        queue = self.client_queues[client_id]
        
        if len(queue) >= self.max_queue_size:
            self.queue_metrics[client_id]["dropped"] += 1
            return {
                "queued": False,
                "reason": "queue_full",
                "queue_size": len(queue)
            }
        
        # Add message with metadata
        queue_item = {
            "message": message,
            "priority": priority,
            "timestamp": time.time(),
            "attempts": 0
        }
        
        # Insert based on priority
        if priority > 0:
            # High priority - insert at front
            queue.appendleft(queue_item)
        else:
            # Normal priority - append at end
            queue.append(queue_item)
        
        self.queue_metrics[client_id]["queued"] += 1
        
        # Check backpressure
        backpressure = len(queue) >= self.backpressure_threshold
        
        return {
            "queued": True,
            "backpressure": backpressure,
            "queue_size": len(queue),
            "position": len(queue) - 1 if priority == 0 else 0
        }
    
    def dequeue_batch(self, client_id: str, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Dequeue batch of messages for processing."""
        queue = self.client_queues[client_id]
        batch = []
        
        for _ in range(min(batch_size, len(queue))):
            if queue:
                item = queue.popleft()
                batch.append(item)
                self.queue_metrics[client_id]["processed"] += 1
        
        return batch
    
    def get_queue_status(self, client_id: str) -> Dict[str, Any]:
        """Get queue status for client."""
        queue = self.client_queues[client_id]
        metrics = self.queue_metrics[client_id]
        
        return {
            "queue_size": len(queue),
            "max_size": self.max_queue_size,
            "utilization": len(queue) / self.max_queue_size,
            "backpressure": len(queue) >= self.backpressure_threshold,
            "metrics": metrics.copy()
        }
    
    def cleanup_empty_queues(self) -> int:
        """Clean up empty queues to free memory."""
        empty_clients = [
            client_id for client_id, queue in self.client_queues.items()
            if len(queue) == 0
        ]
        
        for client_id in empty_clients:
            del self.client_queues[client_id]
            if client_id in self.queue_metrics:
                del self.queue_metrics[client_id]
        
        return len(empty_clients)
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global backpressure metrics."""
        total_queued = sum(len(queue) for queue in self.client_queues.values())
        total_clients = len(self.client_queues)
        
        return {
            "total_clients_with_queues": total_clients,
            "total_queued_messages": total_queued,
            "average_queue_size": total_queued / total_clients if total_clients > 0 else 0,
            "max_queue_size": self.max_queue_size,
            "global_utilization": total_queued / (self.max_queue_size * max(1, total_clients))
        }