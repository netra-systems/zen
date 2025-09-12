"""Rate Limiter Module - Rate limiting functionality for tool permissions"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

# MIGRATED: Use SSOT Redis import pattern
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool_permission import ToolExecutionContext

logger = central_logger


# Import general RateLimiter from canonical location - CIRCULAR IMPORT FIX
# Use service-level RateLimiter to avoid circular import with websocket_core
from netra_backend.app.services.rate_limiter import RateLimiter as CoreRateLimiter


class ToolPermissionRateLimiter:
    """Handles rate limiting functionality"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client

    async def check_rate_limits(
        self, 
        context: ToolExecutionContext,
        permissions: List[str],
        permission_definitions: Dict
    ) -> Dict[str, Any]:
        """Check rate limits for tool execution"""
        rate_limits = self._get_applicable_rate_limits(permissions, permission_definitions)
        if not rate_limits:
            return {"allowed": True, "limits": rate_limits}
        for period, limit in rate_limits.items():
            if limit is None:
                continue
            current_usage = await self._get_usage_count(
                context.user_id, context.tool_name, period.split("_")[1]
            )
            if current_usage >= limit:
                return self._build_limit_exceeded_response(period, limit, current_usage, rate_limits)
        return await self._build_allowed_response(rate_limits, context)

    def _get_applicable_rate_limits(self, permissions: List[str], permission_definitions: Dict) -> Dict:
        """Get applicable rate limits for permissions"""
        rate_limits = {}
        for perm_name in permissions:
            perm_def = permission_definitions.get(perm_name)
            if perm_def and perm_def.rate_limits:
                # Take the most restrictive (minimum) limit for each period
                for period in ["per_minute", "per_hour", "per_day"]:
                    limit = getattr(perm_def.rate_limits, period)
                    if limit is not None:
                        current_limit = rate_limits.get(period)
                        if current_limit is None or limit < current_limit:
                            rate_limits[period] = limit
        return rate_limits

    def _build_limit_exceeded_response(self, period: str, limit: int, current_usage: int, rate_limits: Dict) -> Dict:
        """Build response for rate limit exceeded"""
        return {
            "allowed": False,
            "message": f"Exceeded {period} limit of {limit}",
            "current_usage": current_usage,
            "limit": limit,
            "limits": rate_limits
        }

    async def _build_allowed_response(self, rate_limits: Dict, context: ToolExecutionContext) -> Dict:
        """Build response for allowed request"""
        return {
            "allowed": True,
            "limits": rate_limits,
            "current_usage": await self._get_usage_count(
                context.user_id, context.tool_name, "day"
            )
        }

    async def _get_usage_count(
        self, 
        user_id: str, 
        tool_name: str, 
        period: str
    ) -> int:
        """Get usage count for a period"""
        if not self.redis:
            return 0
        now = datetime.now(UTC)
        key = self._build_usage_key(user_id, tool_name, period, now)
        if not key:
            return 0
        try:
            count = await self.redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting usage count: {e}")
            return 0

    def _build_usage_key(self, user_id: str, tool_name: str, period: str, now: datetime) -> Optional[str]:
        """Build usage key for specific period"""
        if period == "minute":
            return f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H%M')}"
        elif period == "hour":
            return f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H')}"
        elif period == "day":
            return f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d')}"
        return None
    
    async def record_tool_usage(
        self,
        user_id: str,
        tool_name: str,
        execution_time_ms: int,
        status: str
    ):
        """Record tool usage for rate limiting and analytics"""
        if not self.redis:
            return
        try:
            now = datetime.now(UTC)
            for period in ["minute", "hour", "day"]:
                key, ttl = self._get_period_key_and_ttl(user_id, tool_name, period, now)
                if key:
                    await self.redis.incr(key)
                    await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Error recording tool usage: {e}")

    def _get_period_key_and_ttl(self, user_id: str, tool_name: str, period: str, now: datetime) -> tuple:
        """Get usage key and TTL for specific period"""
        if period == "minute":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H%M')}"
            ttl = 60
        elif period == "hour":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H')}"
            ttl = 3600
        elif period == "day":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d')}"
            ttl = 86400
        else:
            return None, None
        return key, ttl


# Alias for tool permission system compatibility
RateLimiter = ToolPermissionRateLimiter