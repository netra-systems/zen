"""Tenant-related schema definitions for multi-tenant isolation and management.

This module defines the data structures for tenant management, permissions,
resources, and isolation boundaries in the Netra platform.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, validator


class SubscriptionTier(str, Enum):
    """Subscription tiers for tenants."""
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"


class ResourceType(str, Enum):
    """Types of resources that can be managed per tenant."""
    AGENTS = "agents"
    STORAGE = "storage"
    COMPUTE = "compute"
    API_CALLS = "api_calls"
    USERS = "users"
    PROJECTS = "projects"
    INTEGRATIONS = "integrations"


class PermissionAction(str, Enum):
    """Permission actions for resources."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    CREATE = "create"
    UPDATE = "update"
    EXECUTE = "execute"


class Permission(BaseModel):
    """Permission model for tenant access control."""
    
    id: Optional[str] = None
    name: str = Field(..., description="Human-readable permission name")
    resource_type: str = Field(..., description="Type of resource this permission applies to")
    action: PermissionAction = Field(..., description="Action allowed by this permission")
    description: Optional[str] = Field(None, description="Description of what this permission allows")
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conditions for permission")
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    
    class Config:
        use_enum_values = True


class TenantResource(BaseModel):
    """Resource allocation and limits for a tenant."""
    
    resource_type: ResourceType
    allocated: int = Field(..., description="Allocated amount of this resource")
    used: int = Field(0, description="Currently used amount")
    limit: int = Field(..., description="Maximum allowed amount")
    unit: str = Field(..., description="Unit of measurement (e.g., 'count', 'GB', 'requests/hour')")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @validator('used')
    def used_cannot_exceed_limit(cls, v, values):
        if 'limit' in values and v > values['limit']:
            raise ValueError(f'Used amount ({v}) cannot exceed limit ({values["limit"]})')
        return v
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage as percentage of limit."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100.0
    
    @property
    def is_near_limit(self) -> bool:
        """Check if usage is near the limit (>80%)."""
        return self.usage_percentage > 80.0
    
    @property
    def is_at_limit(self) -> bool:
        """Check if usage has reached the limit."""
        return self.used >= self.limit
    
    class Config:
        use_enum_values = True


class TenantSettings(BaseModel):
    """Configuration settings for a tenant."""
    
    enable_logging: bool = True
    log_retention_days: int = 30
    enable_metrics: bool = True
    metrics_retention_days: int = 90
    enable_audit_trail: bool = True
    audit_retention_days: int = 365
    max_concurrent_agents: int = 10
    max_agent_memory_mb: int = 1024
    allowed_integrations: List[str] = Field(default_factory=list)
    security_policies: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    custom_branding: Optional[Dict[str, str]] = None
    
    @validator('log_retention_days', 'metrics_retention_days', 'audit_retention_days')
    def retention_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Retention days must be positive')
        return v
    
    @validator('max_concurrent_agents', 'max_agent_memory_mb')
    def limits_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Resource limits must be positive')
        return v


class TenantIsolationConfig(BaseModel):
    """Isolation configuration for tenant data and resources."""
    
    database_schema: str = Field(..., description="Dedicated database schema for tenant")
    storage_prefix: str = Field(..., description="Storage path prefix for tenant files")
    encryption_key_id: Optional[str] = Field(None, description="Tenant-specific encryption key ID")
    network_isolation: bool = False
    compute_isolation: bool = False
    memory_isolation: bool = True
    process_isolation: bool = True
    allowed_regions: List[str] = Field(default_factory=list)
    data_residency_requirements: Optional[Dict[str, str]] = None
    compliance_tags: Set[str] = Field(default_factory=set)
    
    @validator('database_schema', 'storage_prefix')
    def isolation_identifiers_valid(cls, v):
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Isolation identifiers must be alphanumeric with underscores/hyphens')
        return v


class Tenant(BaseModel):
    """Main tenant model representing a complete tenant entity."""
    
    id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Human-readable tenant name")
    slug: str = Field(..., description="URL-friendly tenant identifier")
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    status: str = Field("active", description="Tenant status (active, suspended, deactivated)")
    
    # Contact and billing info
    contact_email: str = Field(..., description="Primary contact email")
    billing_email: Optional[str] = None
    company_name: Optional[str] = None
    
    # Configuration
    settings: TenantSettings = Field(default_factory=TenantSettings)
    isolation_config: TenantIsolationConfig = Field(..., description="Tenant isolation configuration")
    
    # Resources and permissions
    resources: List[TenantResource] = Field(default_factory=list)
    permissions: List[Permission] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    parent_tenant_id: Optional[str] = None  # For hierarchical tenants
    
    # Usage tracking
    last_activity: Optional[datetime] = None
    total_users: int = 0
    total_agents: int = 0
    
    @validator('slug')
    def slug_must_be_valid(cls, v):
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must be alphanumeric with hyphens and underscores only')
        return v.lower()
    
    @validator('contact_email', 'billing_email')
    def emails_must_be_valid(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('subscription_tier', pre=True)
    def normalize_subscription_tier(cls, v):
        if isinstance(v, str):
            return SubscriptionTier(v.lower())
        return v
    
    def get_resource(self, resource_type: ResourceType) -> Optional[TenantResource]:
        """Get resource allocation for a specific resource type."""
        for resource in self.resources:
            if resource.resource_type == resource_type:
                return resource
        return None
    
    def add_resource(self, resource: TenantResource) -> None:
        """Add or update a resource allocation."""
        existing = self.get_resource(resource.resource_type)
        if existing:
            # Update existing resource
            existing.allocated = resource.allocated
            existing.limit = resource.limit
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Add new resource
            self.resources.append(resource)
    
    def has_permission(self, resource_type: str, action: PermissionAction) -> bool:
        """Check if tenant has specific permission."""
        for permission in self.permissions:
            if (permission.resource_type == resource_type and 
                permission.action == action and 
                permission.is_active):
                return True
        return False
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the tenant."""
        # Check if permission already exists
        existing = next((p for p in self.permissions 
                        if p.resource_type == permission.resource_type and 
                           p.action == permission.action), None)
        
        if not existing:
            self.permissions.append(permission)
    
    def is_resource_available(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """Check if tenant has enough available resources."""
        resource = self.get_resource(resource_type)
        if not resource:
            return False
        
        return (resource.used + amount) <= resource.limit
    
    def consume_resource(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """Consume tenant resources if available."""
        resource = self.get_resource(resource_type)
        if not resource:
            return False
        
        if (resource.used + amount) <= resource.limit:
            resource.used += amount
            resource.updated_at = datetime.now(timezone.utc)
            return True
        
        return False
    
    def release_resource(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """Release consumed tenant resources."""
        resource = self.get_resource(resource_type)
        if not resource:
            return False
        
        resource.used = max(0, resource.used - amount)
        resource.updated_at = datetime.now(timezone.utc)
        return True
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == "active"
    
    @property
    def is_enterprise(self) -> bool:
        """Check if tenant is on enterprise tier."""
        return self.subscription_tier == SubscriptionTier.ENTERPRISE
    
    @property
    def resource_summary(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get summary of all resource usage."""
        summary = {}
        for resource in self.resources:
            summary[resource.resource_type.value] = {
                "used": resource.used,
                "limit": resource.limit,
                "usage_percentage": resource.usage_percentage,
                "available": resource.limit - resource.used
            }
        return summary
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    
    name: str
    slug: str
    contact_email: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    company_name: Optional[str] = None
    billing_email: Optional[str] = None
    settings: Optional[TenantSettings] = None
    
    class Config:
        use_enum_values = True


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant."""
    
    name: Optional[str] = None
    contact_email: Optional[str] = None
    billing_email: Optional[str] = None
    company_name: Optional[str] = None
    subscription_tier: Optional[SubscriptionTier] = None
    status: Optional[str] = None
    settings: Optional[TenantSettings] = None
    
    class Config:
        use_enum_values = True


class TenantResourceUsage(BaseModel):
    """Schema for reporting tenant resource usage."""
    
    tenant_id: str
    resource_type: ResourceType
    current_usage: int
    limit: int
    usage_percentage: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


class TenantMetrics(BaseModel):
    """Aggregated metrics for a tenant."""
    
    tenant_id: str
    period_start: datetime
    period_end: datetime
    
    # Usage metrics
    total_api_calls: int = 0
    total_agent_executions: int = 0
    total_storage_used_gb: float = 0.0
    total_compute_hours: float = 0.0
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    success_rate_percentage: float = 0.0
    
    # Resource metrics
    resource_usage: Dict[str, TenantResourceUsage] = Field(default_factory=dict)
    
    # Billing metrics
    estimated_cost: Optional[float] = None
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True