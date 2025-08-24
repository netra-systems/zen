"""
Multi-Tenant Service

Business Value Justification:
- Segment: Enterprise/Mid/Early
- Business Goal: Multi-tenant data isolation and security
- Value Impact: Enables multi-tenant architecture with strict data isolation
- Strategic Impact: Essential for enterprise customers and compliance requirements

Provides tenant isolation, resource management, and configuration.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TenantStatus(str, Enum):
    """Status of a tenant."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    DELETED = "deleted"


class TenantTier(str, Enum):
    """Tenant tiers matching customer segments."""
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"


@dataclass
class TenantConfig:
    """Configuration for a tenant."""
    tenant_id: str
    name: str
    tier: TenantTier
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    max_users: int = 10
    max_api_calls_per_day: int = 1000
    max_storage_mb: int = 100
    features_enabled: Set[str] = field(default_factory=set)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    domain_restrictions: List[str] = field(default_factory=list)
    ip_whitelist: List[str] = field(default_factory=list)
    webhook_urls: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def create_default(cls, tenant_id: str, name: str, tier: TenantTier) -> 'TenantConfig':
        """Create default config based on tier."""
        configs = {
            TenantTier.FREE: {
                "max_users": 1,
                "max_api_calls_per_day": 100,
                "max_storage_mb": 50,
                "features_enabled": {"basic_optimization", "simple_reports"}
            },
            TenantTier.EARLY: {
                "max_users": 5,
                "max_api_calls_per_day": 1000,
                "max_storage_mb": 500,
                "features_enabled": {"basic_optimization", "advanced_reports", "webhooks"}
            },
            TenantTier.MID: {
                "max_users": 25,
                "max_api_calls_per_day": 10000,
                "max_storage_mb": 2000,
                "features_enabled": {"all_optimization", "custom_analytics", "webhooks", "api_access"}
            },
            TenantTier.ENTERPRISE: {
                "max_users": 1000,
                "max_api_calls_per_day": 100000,
                "max_storage_mb": 10000,
                "features_enabled": {"all_features", "custom_integrations", "sso", "audit_logs"}
            }
        }
        
        tier_config = configs[tier]
        return cls(
            tenant_id=tenant_id,
            name=name,
            tier=tier,
            max_users=tier_config["max_users"],
            max_api_calls_per_day=tier_config["max_api_calls_per_day"],
            max_storage_mb=tier_config["max_storage_mb"],
            features_enabled=tier_config["features_enabled"]
        )


@dataclass
class TenantUsage:
    """Current usage statistics for a tenant."""
    tenant_id: str
    current_users: int = 0
    api_calls_today: int = 0
    storage_used_mb: int = 0
    last_activity: float = field(default_factory=time.time)
    bandwidth_used_mb: int = 0
    webhook_calls_today: int = 0
    
    def is_over_limit(self, config: TenantConfig) -> Dict[str, bool]:
        """Check if tenant is over any limits."""
        return {
            "users": self.current_users > config.max_users,
            "api_calls": self.api_calls_today > config.max_api_calls_per_day,
            "storage": self.storage_used_mb > config.max_storage_mb
        }


class TenantIsolationService:
    """Ensures data isolation between tenants."""
    
    def __init__(self):
        self.tenant_data_prefixes: Dict[str, str] = {}
        self.active_tenant_contexts: Dict[str, str] = {}  # session_id -> tenant_id
        
    def get_tenant_data_prefix(self, tenant_id: str) -> str:
        """Get data prefix for tenant isolation."""
        if tenant_id not in self.tenant_data_prefixes:
            # Use tenant ID as prefix for data keys
            self.tenant_data_prefixes[tenant_id] = f"tenant:{tenant_id}:"
        return self.tenant_data_prefixes[tenant_id]
    
    def create_isolated_key(self, tenant_id: str, key: str) -> str:
        """Create an isolated key for tenant data."""
        prefix = self.get_tenant_data_prefix(tenant_id)
        return f"{prefix}{key}"
    
    def validate_tenant_access(self, session_tenant_id: str, resource_tenant_id: str) -> bool:
        """Validate that session can access resource."""
        return session_tenant_id == resource_tenant_id
    
    def set_tenant_context(self, session_id: str, tenant_id: str) -> None:
        """Set tenant context for a session."""
        self.active_tenant_contexts[session_id] = tenant_id
    
    def get_tenant_context(self, session_id: str) -> Optional[str]:
        """Get tenant context for a session."""
        return self.active_tenant_contexts.get(session_id)
    
    def clear_tenant_context(self, session_id: str) -> None:
        """Clear tenant context for a session."""
        self.active_tenant_contexts.pop(session_id, None)


class TenantResourceManager:
    """Manages resource allocation and limits per tenant."""
    
    def __init__(self):
        self.resource_pools: Dict[str, Dict[str, Any]] = {}
        self.resource_locks: Dict[str, asyncio.Lock] = {}
        
    async def allocate_resources(self, tenant_id: str, resource_type: str, 
                               amount: int) -> bool:
        """Allocate resources for a tenant."""
        pool_key = f"{tenant_id}:{resource_type}"
        
        if pool_key not in self.resource_locks:
            self.resource_locks[pool_key] = asyncio.Lock()
        
        async with self.resource_locks[pool_key]:
            current_pool = self.resource_pools.get(pool_key, {
                "allocated": 0,
                "max_limit": 1000,  # Default limit
                "last_updated": time.time()
            })
            
            if current_pool["allocated"] + amount > current_pool["max_limit"]:
                logger.warning(f"Resource allocation failed for {tenant_id}: "
                             f"{current_pool['allocated']} + {amount} > {current_pool['max_limit']}")
                return False
            
            current_pool["allocated"] += amount
            current_pool["last_updated"] = time.time()
            self.resource_pools[pool_key] = current_pool
            
            logger.debug(f"Allocated {amount} {resource_type} to {tenant_id}")
            return True
    
    async def deallocate_resources(self, tenant_id: str, resource_type: str,
                                 amount: int) -> None:
        """Deallocate resources for a tenant."""
        pool_key = f"{tenant_id}:{resource_type}"
        
        if pool_key not in self.resource_locks:
            return
        
        async with self.resource_locks[pool_key]:
            current_pool = self.resource_pools.get(pool_key)
            if current_pool:
                current_pool["allocated"] = max(0, current_pool["allocated"] - amount)
                current_pool["last_updated"] = time.time()
                logger.debug(f"Deallocated {amount} {resource_type} from {tenant_id}")
    
    def get_resource_usage(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """Get resource usage for a tenant."""
        tenant_resources = {}
        prefix = f"{tenant_id}:"
        
        for pool_key, pool_info in self.resource_pools.items():
            if pool_key.startswith(prefix):
                resource_type = pool_key[len(prefix):]
                tenant_resources[resource_type] = pool_info.copy()
        
        return tenant_resources


class MultiTenantService:
    """Main multi-tenant service."""
    
    def __init__(self):
        self.tenant_configs: Dict[str, TenantConfig] = {}
        self.tenant_usage: Dict[str, TenantUsage] = {}
        self.isolation_service = TenantIsolationService()
        self.resource_manager = TenantResourceManager()
        self.usage_cleanup_interval = 86400  # 24 hours
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the multi-tenant service."""
        self._cleanup_task = asyncio.create_task(self._usage_cleanup_loop())
        logger.info("Multi-tenant service started")
    
    async def stop(self) -> None:
        """Stop the multi-tenant service."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Multi-tenant service stopped")
    
    async def create_tenant(self, name: str, tier: TenantTier,
                          custom_config: Optional[Dict[str, Any]] = None) -> TenantConfig:
        """Create a new tenant."""
        tenant_id = str(uuid.uuid4())
        config = TenantConfig.create_default(tenant_id, name, tier)
        
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        self.tenant_configs[tenant_id] = config
        self.tenant_usage[tenant_id] = TenantUsage(tenant_id=tenant_id)
        
        logger.info(f"Created tenant {name} ({tenant_id}) with tier {tier}")
        return config
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration."""
        return self.tenant_configs.get(tenant_id)
    
    def get_tenant_usage(self, tenant_id: str) -> Optional[TenantUsage]:
        """Get tenant usage statistics."""
        return self.tenant_usage.get(tenant_id)
    
    async def update_tenant_config(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        """Update tenant configuration."""
        config = self.tenant_configs.get(tenant_id)
        if not config:
            return False
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        logger.info(f"Updated config for tenant {tenant_id}")
        return True
    
    async def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant."""
        config = self.tenant_configs.get(tenant_id)
        if not config:
            return False
        
        config.status = TenantStatus.SUSPENDED
        logger.warning(f"Suspended tenant {tenant_id}: {reason}")
        return True
    
    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        config = self.tenant_configs.get(tenant_id)
        if not config:
            return False
        
        config.status = TenantStatus.ACTIVE
        logger.info(f"Activated tenant {tenant_id}")
        return True
    
    def is_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """Check if a feature is enabled for a tenant."""
        config = self.tenant_configs.get(tenant_id)
        if not config or config.status != TenantStatus.ACTIVE:
            return False
        
        return feature in config.features_enabled or "all_features" in config.features_enabled
    
    async def record_api_usage(self, tenant_id: str, calls: int = 1) -> bool:
        """Record API usage for a tenant."""
        usage = self.tenant_usage.get(tenant_id)
        if not usage:
            return False
        
        usage.api_calls_today += calls
        usage.last_activity = time.time()
        
        # Check if over limit
        config = self.tenant_configs.get(tenant_id)
        if config and usage.api_calls_today > config.max_api_calls_per_day:
            logger.warning(f"Tenant {tenant_id} exceeded API call limit")
            return False
        
        return True
    
    async def record_storage_usage(self, tenant_id: str, storage_mb: int) -> bool:
        """Record storage usage for a tenant."""
        usage = self.tenant_usage.get(tenant_id)
        if not usage:
            return False
        
        usage.storage_used_mb = storage_mb
        usage.last_activity = time.time()
        return True
    
    def validate_tenant_access(self, session_tenant_id: str, 
                             resource_tenant_id: str) -> bool:
        """Validate cross-tenant access."""
        return self.isolation_service.validate_tenant_access(
            session_tenant_id, resource_tenant_id
        )
    
    def create_isolated_key(self, tenant_id: str, key: str) -> str:
        """Create tenant-isolated data key."""
        return self.isolation_service.create_isolated_key(tenant_id, key)
    
    async def get_tenant_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive tenant statistics."""
        config = self.tenant_configs.get(tenant_id)
        usage = self.tenant_usage.get(tenant_id)
        
        if not config or not usage:
            return None
        
        limits = usage.is_over_limit(config)
        resources = self.resource_manager.get_resource_usage(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "name": config.name,
            "tier": config.tier,
            "status": config.status,
            "usage": {
                "users": f"{usage.current_users}/{config.max_users}",
                "api_calls": f"{usage.api_calls_today}/{config.max_api_calls_per_day}",
                "storage_mb": f"{usage.storage_used_mb}/{config.max_storage_mb}"
            },
            "over_limits": limits,
            "resources": resources,
            "last_activity": usage.last_activity
        }
    
    async def list_tenants(self, status_filter: Optional[TenantStatus] = None) -> List[Dict[str, Any]]:
        """List all tenants with optional status filter."""
        tenants = []
        
        for tenant_id, config in self.tenant_configs.items():
            if status_filter and config.status != status_filter:
                continue
            
            stats = await self.get_tenant_stats(tenant_id)
            if stats:
                tenants.append(stats)
        
        return tenants
    
    async def _usage_cleanup_loop(self) -> None:
        """Clean up old usage data periodically."""
        try:
            while True:
                await asyncio.sleep(self.usage_cleanup_interval)
                await self._cleanup_old_usage()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in usage cleanup loop: {e}")
    
    async def _cleanup_old_usage(self) -> None:
        """Clean up old usage data."""
        # Reset daily counters (simplified - in production would check actual day)
        current_time = time.time()
        for usage in self.tenant_usage.values():
            if current_time - usage.last_activity > self.usage_cleanup_interval:
                usage.api_calls_today = 0
                usage.webhook_calls_today = 0
        
        logger.debug("Cleaned up old usage data")


# Global multi-tenant service instance
_multi_tenant_service: Optional[MultiTenantService] = None

def get_multi_tenant_service() -> MultiTenantService:
    """Get global multi-tenant service instance."""
    global _multi_tenant_service
    if _multi_tenant_service is None:
        _multi_tenant_service = MultiTenantService()
    return _multi_tenant_service


async def validate_tenant_request(tenant_id: str, feature: str) -> bool:
    """Validate that a tenant can access a feature."""
    service = get_multi_tenant_service()
    
    config = service.get_tenant_config(tenant_id)
    if not config or config.status != TenantStatus.ACTIVE:
        return False
    
    return service.is_feature_enabled(tenant_id, feature)


def get_tenant_isolated_key(tenant_id: str, key: str) -> str:
    """Get tenant-isolated key for data storage."""
    service = get_multi_tenant_service()
    return service.create_isolated_key(tenant_id, key)


async def record_tenant_api_call(tenant_id: str) -> bool:
    """Record an API call for tenant usage tracking."""
    service = get_multi_tenant_service()
    return await service.record_api_usage(tenant_id)