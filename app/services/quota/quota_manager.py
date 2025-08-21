"""Quota Manager Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic quota management functionality for tests
- Value Impact: Ensures quota management tests can execute without import errors
- Strategic Impact: Enables quota management functionality validation
"""

import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class QuotaType(Enum):
    """Types of quotas."""
    API_REQUESTS = "api_requests"
    TOKEN_USAGE = "token_usage"
    STORAGE = "storage"
    COMPUTE_TIME = "compute_time"


@dataclass
class QuotaConfig:
    """Quota configuration."""
    quota_type: QuotaType
    limit: int
    period: timedelta = timedelta(hours=1)
    reset_strategy: str = "rolling"


@dataclass
class QuotaUsage:
    """Current quota usage."""
    used: int = 0
    limit: int = 0
    remaining: int = 0
    reset_time: Optional[datetime] = None
    percentage_used: float = 0.0


class QuotaManager:
    """Manager for user and service quotas."""
    
    def __init__(self):
        """Initialize quota manager."""
        self._quotas: Dict[str, QuotaConfig] = {}
        self._usage: Dict[str, Dict[str, int]] = {}  # identifier -> quota_type -> usage
        self._reset_times: Dict[str, Dict[str, datetime]] = {}
        self._lock = asyncio.Lock()
    
    def set_quota(self, identifier: str, quota_config: QuotaConfig) -> None:
        """Set quota for an identifier."""
        key = f"{identifier}:{quota_config.quota_type.value}"
        self._quotas[key] = quota_config
    
    async def check_quota(self, identifier: str, quota_type: QuotaType) -> QuotaUsage:
        """Check current quota usage."""
        async with self._lock:
            key = f"{identifier}:{quota_type.value}"
            config = self._quotas.get(key)
            
            if not config:
                # Return unlimited quota if not configured
                return QuotaUsage(used=0, limit=-1, remaining=-1)
            
            usage = self._get_usage(identifier, quota_type)
            remaining = max(0, config.limit - usage)
            percentage = (usage / config.limit * 100) if config.limit > 0 else 0
            
            return QuotaUsage(
                used=usage,
                limit=config.limit,
                remaining=remaining,
                reset_time=self._get_reset_time(identifier, quota_type),
                percentage_used=percentage
            )
    
    async def consume_quota(
        self, 
        identifier: str, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> bool:
        """Consume quota if available."""
        async with self._lock:
            usage = await self.check_quota(identifier, quota_type)
            
            if usage.limit == -1:  # Unlimited
                self._add_usage(identifier, quota_type, amount)
                return True
            
            if usage.remaining >= amount:
                self._add_usage(identifier, quota_type, amount)
                return True
            
            return False
    
    async def reset_quota(self, identifier: str, quota_type: Optional[QuotaType] = None) -> None:
        """Reset quota usage for identifier."""
        async with self._lock:
            if identifier not in self._usage:
                return
                
            if quota_type:
                self._usage[identifier].pop(quota_type.value, None)
                if identifier in self._reset_times:
                    self._reset_times[identifier].pop(quota_type.value, None)
            else:
                self._usage.pop(identifier, None)
                self._reset_times.pop(identifier, None)
    
    def _get_usage(self, identifier: str, quota_type: QuotaType) -> int:
        """Get current usage for identifier and quota type."""
        return self._usage.get(identifier, {}).get(quota_type.value, 0)
    
    def _add_usage(self, identifier: str, quota_type: QuotaType, amount: int) -> None:
        """Add usage for identifier and quota type."""
        if identifier not in self._usage:
            self._usage[identifier] = {}
        
        current = self._usage[identifier].get(quota_type.value, 0)
        self._usage[identifier][quota_type.value] = current + amount
    
    def _get_reset_time(self, identifier: str, quota_type: QuotaType) -> Optional[datetime]:
        """Get reset time for quota."""
        if identifier not in self._reset_times:
            self._reset_times[identifier] = {}
        
        key = quota_type.value
        if key not in self._reset_times[identifier]:
            config_key = f"{identifier}:{quota_type.value}"
            config = self._quotas.get(config_key)
            if config:
                self._reset_times[identifier][key] = datetime.now() + config.period
        
        return self._reset_times[identifier].get(key)


# Global quota manager instance
default_quota_manager = QuotaManager()