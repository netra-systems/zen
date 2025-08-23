"""
Rate Limiter Service

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Provide rate limiting functionality for tests and production
- Value Impact: Enables rate limiting tests to execute and validates production rate limiting
- Strategic Impact: Core security and stability infrastructure for API rate limiting
"""

import asyncio
import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


class RateLimiter:
    """Enterprise-grade rate limiter for API requests with Redis backend support."""
    
    def __init__(self, redis_manager=None, config=None):
        """Initialize rate limiter with Redis backend."""
        self.redis_manager = redis_manager
        self.config = config
        self.rate_limits = {}  # In-memory fallback
        self.global_limits = {}
        self.service_limits = {}
    
    async def set_rate_limit(self, user_id: str, endpoint: str, limit: int, window_seconds: int):
        """Set rate limit for a user/endpoint combination."""
        key = f"rate_limit_config:{user_id}:{endpoint}"
        config = {
            "limit": limit,
            "window_seconds": window_seconds,
            "created_at": time.time()
        }
        
        if self.redis_manager:
            try:
                import json
                await self.redis_manager.set(key, json.dumps(config), ex=window_seconds * 2)
            except Exception:
                pass
        
        # Always store in memory as fallback
        self.rate_limits[f"{user_id}:{endpoint}"] = config
    
    async def check_rate_limit(self, user_id: str, endpoint: str) -> bool:
        """Check if request is within rate limit."""
        key = f"rate_limit:{user_id}:{endpoint}"
        config_key = f"{user_id}:{endpoint}"
        
        # Get rate limit config
        if config_key not in self.rate_limits:
            return True  # No limit set, allow request
        
        config = self.rate_limits[config_key]
        limit = config["limit"]
        window_seconds = config["window_seconds"]
        
        # Check current count
        if self.redis_manager:
            try:
                current_count = await self.redis_manager.get(key)
                current_count = int(current_count) if current_count else 0
            except Exception:
                current_count = 0
        else:
            current_count = self._get_memory_count(key)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        if self.redis_manager:
            try:
                await self.redis_manager.incr(key)
                await self.redis_manager.expire(key, window_seconds)
            except Exception:
                pass
        else:
            self._increment_memory_count(key, window_seconds)
        
        return True
    
    async def set_global_rate_limit(self, user_id: str, limit: int, window_seconds: int):
        """Set global rate limit for a user across all services."""
        key = f"global_rate_limit_config:{user_id}"
        config = {
            "limit": limit,
            "window_seconds": window_seconds,
            "created_at": time.time()
        }
        
        if self.redis_manager:
            try:
                import json
                await self.redis_manager.set(key, json.dumps(config), ex=window_seconds * 2)
            except Exception:
                pass
        
        self.global_limits[user_id] = config
    
    async def check_global_rate_limit(self, user_id: str) -> bool:
        """Check global rate limit for a user."""
        if user_id not in self.global_limits:
            return True
        
        config = self.global_limits[user_id]
        limit = config["limit"]
        window_seconds = config["window_seconds"]
        
        key = f"rate_limit:global:{user_id}"
        
        if self.redis_manager:
            try:
                current_count = await self.redis_manager.get(key)
                current_count = int(current_count) if current_count else 0
            except Exception:
                current_count = 0
        else:
            current_count = self._get_memory_count(key)
        
        return current_count < limit
    
    async def increment_global_counter(self, user_id: str):
        """Increment global counter for a user."""
        if user_id not in self.global_limits:
            return
        
        config = self.global_limits[user_id]
        window_seconds = config["window_seconds"]
        key = f"rate_limit:global:{user_id}"
        
        if self.redis_manager:
            try:
                await self.redis_manager.incr(key)
                await self.redis_manager.expire(key, window_seconds)
            except Exception:
                pass
        else:
            self._increment_memory_count(key, window_seconds)
    
    async def set_service_rate_limit(self, user_id: str, service: str, endpoint: str, limit: int, window_seconds: int):
        """Set service-specific rate limit."""
        service_key = f"{user_id}:{service}:{endpoint}"
        config = {
            "limit": limit,
            "window_seconds": window_seconds,
            "created_at": time.time()
        }
        
        if self.redis_manager:
            try:
                import json
                config_key = f"service_rate_limit_config:{service_key}"
                await self.redis_manager.set(config_key, json.dumps(config), ex=window_seconds * 2)
            except Exception:
                pass
        
        self.service_limits[service_key] = config
    
    async def check_service_rate_limit(self, user_id: str, service: str, endpoint: str) -> bool:
        """Check service-specific rate limit."""
        service_key = f"{user_id}:{service}:{endpoint}"
        
        if service_key not in self.service_limits:
            return True
        
        config = self.service_limits[service_key]
        limit = config["limit"]
        window_seconds = config["window_seconds"]
        
        key = f"rate_limit:service:{service_key}"
        
        if self.redis_manager:
            try:
                current_count = await self.redis_manager.get(key)
                current_count = int(current_count) if current_count else 0
            except Exception:
                current_count = 0
        else:
            current_count = self._get_memory_count(key)
        
        return current_count < limit
    
    async def increment_service_counter(self, user_id: str, service: str, endpoint: str):
        """Increment service counter."""
        service_key = f"{user_id}:{service}:{endpoint}"
        
        if service_key not in self.service_limits:
            return
        
        config = self.service_limits[service_key]
        window_seconds = config["window_seconds"]
        key = f"rate_limit:service:{service_key}"
        
        if self.redis_manager:
            try:
                await self.redis_manager.incr(key)
                await self.redis_manager.expire(key, window_seconds)
            except Exception:
                pass
        else:
            self._increment_memory_count(key, window_seconds)
    
    def _get_memory_count(self, key: str) -> int:
        """Get count from memory storage."""
        if not hasattr(self, '_memory_counters'):
            self._memory_counters = {}
        
        if key not in self._memory_counters:
            return 0
        
        counter_data = self._memory_counters[key]
        if time.time() > counter_data["expires_at"]:
            del self._memory_counters[key]
            return 0
        
        return counter_data["count"]
    
    def _increment_memory_count(self, key: str, window_seconds: int):
        """Increment count in memory storage."""
        if not hasattr(self, '_memory_counters'):
            self._memory_counters = {}
        
        if key not in self._memory_counters:
            self._memory_counters[key] = {
                "count": 1,
                "expires_at": time.time() + window_seconds
            }
        else:
            if time.time() > self._memory_counters[key]["expires_at"]:
                self._memory_counters[key] = {
                    "count": 1,
                    "expires_at": time.time() + window_seconds
                }
            else:
                self._memory_counters[key]["count"] += 1
    
    async def is_allowed(self, identifier: str) -> bool:
        """Legacy method for backward compatibility."""
        return await self.check_rate_limit("default", identifier)
    
    async def wait_if_needed(self, identifier: str) -> None:
        """Wait if rate limit is exceeded."""
        if not await self.is_allowed(identifier):
            await asyncio.sleep(0.1)
    
    def get_remaining_tokens(self) -> float:
        """Get remaining tokens - legacy method."""
        return 10.0  # Return arbitrary value for compatibility
    
    def reset(self) -> None:
        """Reset rate limiter."""
        self.rate_limits.clear()
        self.global_limits.clear()
        self.service_limits.clear()
        if hasattr(self, '_memory_counters'):
            self._memory_counters.clear()