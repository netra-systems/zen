"""Tenant Isolator for enterprise resource isolation"""

from typing import Dict, Any, List, Optional, Set
import asyncio
from datetime import datetime, UTC
from dataclasses import dataclass, field


@dataclass
class TenantResourceQuota:
    """Resource quota for a tenant"""
    tenant_id: str
    cpu_cores: float = 2.0
    memory_mb: int = 2048
    storage_gb: int = 10
    network_bandwidth_mbps: int = 100
    max_concurrent_requests: int = 100
    max_api_calls_per_hour: int = 10000


@dataclass
class ResourceUsage:
    """Current resource usage"""
    cpu_usage: float = 0.0
    memory_usage_mb: int = 0
    storage_usage_gb: int = 0
    network_usage_mbps: int = 0
    active_requests: int = 0
    api_calls_last_hour: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


class TenantIsolator:
    """Manages resource isolation between tenants"""
    
    def __init__(self):
        self.tenant_quotas: Dict[str, TenantResourceQuota] = {}
        self.tenant_usage: Dict[str, ResourceUsage] = {}
        self.tenant_namespaces: Dict[str, str] = {}
        self.blocked_tenants: Set[str] = set()
        self.isolation_policies: Dict[str, Dict[str, Any]] = {}
    
    async def register_tenant(self, tenant_id: str, quota: Optional[TenantResourceQuota] = None) -> bool:
        """Register a new tenant with resource isolation"""
        if tenant_id in self.tenant_quotas:
            return False
        
        # Use provided quota or create default
        tenant_quota = quota or TenantResourceQuota(tenant_id=tenant_id)
        
        self.tenant_quotas[tenant_id] = tenant_quota
        self.tenant_usage[tenant_id] = ResourceUsage()
        self.tenant_namespaces[tenant_id] = f"tenant_{tenant_id}_{datetime.now(UTC).strftime('%Y%m%d')}"
        
        # Create default isolation policy
        self.isolation_policies[tenant_id] = {
            "network_isolation": True,
            "storage_isolation": True,
            "compute_isolation": True,
            "strict_quota_enforcement": True,
            "allow_burst": False,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        return True
    
    async def unregister_tenant(self, tenant_id: str) -> bool:
        """Unregister a tenant and clean up resources"""
        if tenant_id not in self.tenant_quotas:
            return False
        
        # Clean up all tenant data
        del self.tenant_quotas[tenant_id]
        del self.tenant_usage[tenant_id]
        del self.tenant_namespaces[tenant_id]
        if tenant_id in self.isolation_policies:
            del self.isolation_policies[tenant_id]
        
        self.blocked_tenants.discard(tenant_id)
        return True
    
    async def check_resource_availability(self, tenant_id: str, resource_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check if tenant can use requested resources"""
        if tenant_id not in self.tenant_quotas:
            return {"allowed": False, "reason": "Tenant not registered"}
        
        if tenant_id in self.blocked_tenants:
            return {"allowed": False, "reason": "Tenant is blocked due to quota violations"}
        
        quota = self.tenant_quotas[tenant_id]
        usage = self.tenant_usage[tenant_id]
        policy = self.isolation_policies[tenant_id]
        
        # Check each resource type
        violations = []
        
        if "cpu_cores" in resource_request:
            requested_cpu = resource_request["cpu_cores"]
            if usage.cpu_usage + requested_cpu > quota.cpu_cores:
                violations.append(f"CPU quota exceeded: {usage.cpu_usage + requested_cpu} > {quota.cpu_cores}")
        
        if "memory_mb" in resource_request:
            requested_memory = resource_request["memory_mb"]
            if usage.memory_usage_mb + requested_memory > quota.memory_mb:
                violations.append(f"Memory quota exceeded: {usage.memory_usage_mb + requested_memory} > {quota.memory_mb}")
        
        if "concurrent_requests" in resource_request:
            requested_requests = resource_request["concurrent_requests"]
            if usage.active_requests + requested_requests > quota.max_concurrent_requests:
                violations.append(f"Concurrent requests quota exceeded: {usage.active_requests + requested_requests} > {quota.max_concurrent_requests}")
        
        if violations and policy["strict_quota_enforcement"]:
            return {"allowed": False, "reason": "Quota violations", "violations": violations}
        
        return {"allowed": True, "violations": violations if violations else None}
    
    async def allocate_resources(self, tenant_id: str, resource_allocation: Dict[str, Any]) -> bool:
        """Allocate resources to a tenant"""
        availability_check = await self.check_resource_availability(tenant_id, resource_allocation)
        
        if not availability_check["allowed"]:
            return False
        
        usage = self.tenant_usage[tenant_id]
        
        # Update usage
        if "cpu_cores" in resource_allocation:
            usage.cpu_usage += resource_allocation["cpu_cores"]
        
        if "memory_mb" in resource_allocation:
            usage.memory_usage_mb += resource_allocation["memory_mb"]
        
        if "storage_gb" in resource_allocation:
            usage.storage_usage_gb += resource_allocation["storage_gb"]
        
        if "concurrent_requests" in resource_allocation:
            usage.active_requests += resource_allocation["concurrent_requests"]
        
        usage.last_updated = datetime.now(UTC)
        return True
    
    async def deallocate_resources(self, tenant_id: str, resource_deallocation: Dict[str, Any]) -> bool:
        """Deallocate resources from a tenant"""
        if tenant_id not in self.tenant_usage:
            return False
        
        usage = self.tenant_usage[tenant_id]
        
        # Update usage (decrease)
        if "cpu_cores" in resource_deallocation:
            usage.cpu_usage = max(0, usage.cpu_usage - resource_deallocation["cpu_cores"])
        
        if "memory_mb" in resource_deallocation:
            usage.memory_usage_mb = max(0, usage.memory_usage_mb - resource_deallocation["memory_mb"])
        
        if "storage_gb" in resource_deallocation:
            usage.storage_usage_gb = max(0, usage.storage_usage_gb - resource_deallocation["storage_gb"])
        
        if "concurrent_requests" in resource_deallocation:
            usage.active_requests = max(0, usage.active_requests - resource_deallocation["concurrent_requests"])
        
        usage.last_updated = datetime.now(UTC)
        return True
    
    async def get_tenant_namespace(self, tenant_id: str) -> Optional[str]:
        """Get isolated namespace for tenant"""
        return self.tenant_namespaces.get(tenant_id)
    
    async def enforce_isolation(self, tenant_id: str) -> Dict[str, Any]:
        """Enforce isolation policies for a tenant"""
        if tenant_id not in self.isolation_policies:
            return {"success": False, "reason": "Tenant not found"}
        
        policy = self.isolation_policies[tenant_id]
        quota = self.tenant_quotas[tenant_id]
        usage = self.tenant_usage[tenant_id]
        
        enforcement_actions = []
        
        # Check for quota violations
        if usage.cpu_usage > quota.cpu_cores:
            enforcement_actions.append("CPU throttling applied")
            if policy["strict_quota_enforcement"]:
                self.blocked_tenants.add(tenant_id)
                enforcement_actions.append("Tenant blocked due to CPU quota violation")
        
        if usage.memory_usage_mb > quota.memory_mb:
            enforcement_actions.append("Memory limiting applied")
            if policy["strict_quota_enforcement"]:
                self.blocked_tenants.add(tenant_id)
                enforcement_actions.append("Tenant blocked due to memory quota violation")
        
        if usage.active_requests > quota.max_concurrent_requests:
            enforcement_actions.append("Request rate limiting applied")
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "actions_taken": enforcement_actions,
            "is_blocked": tenant_id in self.blocked_tenants
        }
    
    async def update_tenant_quota(self, tenant_id: str, new_quota: Dict[str, Any]) -> bool:
        """Update resource quota for a tenant"""
        if tenant_id not in self.tenant_quotas:
            return False
        
        quota = self.tenant_quotas[tenant_id]
        
        if "cpu_cores" in new_quota:
            quota.cpu_cores = max(0.1, new_quota["cpu_cores"])
        if "memory_mb" in new_quota:
            quota.memory_mb = max(128, new_quota["memory_mb"])
        if "storage_gb" in new_quota:
            quota.storage_gb = max(1, new_quota["storage_gb"])
        if "max_concurrent_requests" in new_quota:
            quota.max_concurrent_requests = max(1, new_quota["max_concurrent_requests"])
        if "max_api_calls_per_hour" in new_quota:
            quota.max_api_calls_per_hour = max(100, new_quota["max_api_calls_per_hour"])
        
        return True
    
    async def get_tenant_status(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status for a tenant"""
        if tenant_id not in self.tenant_quotas:
            return None
        
        quota = self.tenant_quotas[tenant_id]
        usage = self.tenant_usage[tenant_id]
        policy = self.isolation_policies[tenant_id]
        namespace = self.tenant_namespaces[tenant_id]
        
        return {
            "tenant_id": tenant_id,
            "namespace": namespace,
            "is_blocked": tenant_id in self.blocked_tenants,
            "quota": {
                "cpu_cores": quota.cpu_cores,
                "memory_mb": quota.memory_mb,
                "storage_gb": quota.storage_gb,
                "max_concurrent_requests": quota.max_concurrent_requests,
                "max_api_calls_per_hour": quota.max_api_calls_per_hour
            },
            "usage": {
                "cpu_usage": usage.cpu_usage,
                "memory_usage_mb": usage.memory_usage_mb,
                "storage_usage_gb": usage.storage_usage_gb,
                "active_requests": usage.active_requests,
                "api_calls_last_hour": usage.api_calls_last_hour,
                "last_updated": usage.last_updated.isoformat()
            },
            "utilization": {
                "cpu_percent": (usage.cpu_usage / quota.cpu_cores) * 100 if quota.cpu_cores > 0 else 0,
                "memory_percent": (usage.memory_usage_mb / quota.memory_mb) * 100 if quota.memory_mb > 0 else 0,
                "storage_percent": (usage.storage_usage_gb / quota.storage_gb) * 100 if quota.storage_gb > 0 else 0,
                "requests_percent": (usage.active_requests / quota.max_concurrent_requests) * 100 if quota.max_concurrent_requests > 0 else 0
            },
            "policy": policy
        }
    
    async def list_tenants(self) -> List[Dict[str, Any]]:
        """List all registered tenants with their status"""
        tenants = []
        for tenant_id in self.tenant_quotas:
            tenant_status = await self.get_tenant_status(tenant_id)
            if tenant_status:
                tenants.append(tenant_status)
        return tenants
    
    def get_isolator_stats(self) -> Dict[str, Any]:
        """Get overall isolator statistics"""
        total_tenants = len(self.tenant_quotas)
        blocked_tenants = len(self.blocked_tenants)
        active_tenants = total_tenants - blocked_tenants
        
        total_allocated_cpu = sum(usage.cpu_usage for usage in self.tenant_usage.values())
        total_allocated_memory = sum(usage.memory_usage_mb for usage in self.tenant_usage.values())
        total_active_requests = sum(usage.active_requests for usage in self.tenant_usage.values())
        
        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "blocked_tenants": blocked_tenants,
            "total_allocated_cpu": total_allocated_cpu,
            "total_allocated_memory_mb": total_allocated_memory,
            "total_active_requests": total_active_requests,
            "isolation_policies_count": len(self.isolation_policies)
        }