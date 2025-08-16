"""
Tool Permission Schemas
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from enum import Enum


class PermissionLevel(str, Enum):
    """Permission levels for tools"""
    NONE = "none"
    READ = "read" 
    WRITE = "write"
    ADMIN = "admin"


class BusinessRequirement(BaseModel):
    """Business requirements for tool access"""
    plan_tiers: Optional[List[str]] = Field(default=None, description="Required plan tiers")
    feature_flags: Optional[List[str]] = Field(default=None, description="Required feature flags")
    role_requirements: Optional[List[str]] = Field(default=None, description="Required user roles")
    developer_status: Optional[bool] = Field(default=None, description="Requires developer status")
    environment: Optional[List[str]] = Field(default=None, description="Allowed environments")


class RateLimit(BaseModel):
    """Rate limiting configuration for tools"""
    per_minute: Optional[int] = Field(default=None, description="Calls per minute")
    per_hour: Optional[int] = Field(default=None, description="Calls per hour") 
    per_day: Optional[int] = Field(default=None, description="Calls per day")
    burst_limit: Optional[int] = Field(default=None, description="Burst allowance")


class ToolPermission(BaseModel):
    """Tool permission definition"""
    name: str = Field(description="Permission name/identifier")
    description: str = Field(description="Human-readable description")
    level: PermissionLevel = Field(default=PermissionLevel.READ, description="Permission level")
    tools: List[str] = Field(description="Tools that require this permission")
    business_requirements: BusinessRequirement = Field(default_factory=BusinessRequirement)
    rate_limits: Optional[RateLimit] = Field(default=None, description="Rate limiting rules")
    expires_at: Optional[datetime] = Field(default=None, description="Permission expiration")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserToolPermission(BaseModel):
    """User's permission for a specific tool"""
    user_id: str = Field(description="User identifier")
    tool_name: str = Field(description="Tool name")
    permission_level: PermissionLevel = Field(description="Granted permission level")
    granted_by: Optional[str] = Field(default=None, description="Who granted this permission")
    expires_at: Optional[datetime] = Field(default=None, description="Permission expiration")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolExecutionContext(BaseModel):
    """Context for tool execution permission checking"""
    user_id: str = Field(description="User executing the tool")
    tool_name: str = Field(description="Tool being executed")
    requested_action: str = Field(description="Specific action being requested")
    user_plan: str = Field(description="User's current plan")
    user_roles: List[str] = Field(default_factory=list, description="User's roles")
    feature_flags: Dict[str, bool] = Field(default_factory=dict, description="User's feature flags")
    is_developer: bool = Field(default=False, description="Is user a developer")
    environment: str = Field(default="production", description="Current environment")


class PermissionCheckResult(BaseModel):
    """Result of permission check"""
    allowed: bool = Field(description="Whether action is allowed")
    reason: Optional[str] = Field(default=None, description="Reason for denial")
    required_permissions: List[str] = Field(default_factory=list, description="Required permissions")
    missing_permissions: List[str] = Field(default_factory=list, description="Missing permissions")
    business_requirements_met: bool = Field(default=True, description="Business requirements satisfied")
    rate_limit_status: Optional[Dict[str, Any]] = Field(default=None, description="Rate limit information")
    upgrade_path: Optional[str] = Field(default=None, description="Suggested upgrade path")


class ToolAvailability(BaseModel):
    """Tool availability information for a user"""
    tool_name: str = Field(description="Tool name")
    category: str = Field(description="Tool category")
    description: str = Field(description="Tool description") 
    available: bool = Field(description="Whether tool is available to user")
    permission_level: Optional[PermissionLevel] = Field(default=None, description="User's permission level")
    required_permissions: List[str] = Field(default_factory=list, description="Required permissions")
    missing_requirements: List[str] = Field(default_factory=list, description="Missing requirements")
    rate_limits: Optional[RateLimit] = Field(default=None, description="Applicable rate limits")
    usage_today: Optional[int] = Field(default=None, description="Usage count today")
    upgrade_required: Optional[str] = Field(default=None, description="Required plan upgrade")


class PermissionGrant(BaseModel):
    """Grant permission to a user"""
    user_id: str = Field(description="Target user ID")
    permission_name: str = Field(description="Permission to grant")
    granted_by: str = Field(description="User granting permission")
    expires_at: Optional[datetime] = Field(default=None, description="Permission expiration")
    reason: Optional[str] = Field(default=None, description="Reason for grant")


class PermissionRevoke(BaseModel):
    """Revoke permission from a user"""
    user_id: str = Field(description="Target user ID")
    permission_name: str = Field(description="Permission to revoke")
    revoked_by: str = Field(description="User revoking permission")
    reason: Optional[str] = Field(default=None, description="Reason for revocation")