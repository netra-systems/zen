"""
Tool Permission Service - Handles per-tool authentication and authorization
"""
import os
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.schemas.ToolPermission import (
    ToolPermission, ToolExecutionContext, PermissionCheckResult, 
    ToolAvailability, PermissionLevel, BusinessRequirement, RateLimit
)
from app.schemas.UserPlan import UserPlan, PlanTier, PLAN_DEFINITIONS
from app.logging_config import central_logger
from app.core.exceptions_base import NetraException
import redis
import json
from functools import lru_cache

logger = central_logger


class ToolPermissionService:
    """Service for managing per-tool permissions and business logic"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.permissions_cache = {}
        self._permission_definitions = self._load_permission_definitions()
    
    def _load_permission_definitions(self) -> Dict[str, ToolPermission]:
        """Load tool permission definitions"""
        return {
            "basic": ToolPermission(
                name="basic",
                description="Basic authenticated user tools",
                level=PermissionLevel.READ,
                tools=[
                    "create_thread", "get_thread_history", "list_agents",
                    "get_agent_status"
                ],
                business_requirements=BusinessRequirement(),
            ),
            
            "analytics": ToolPermission(
                name="analytics",
                description="Workload analytics and basic optimization",
                level=PermissionLevel.READ,
                tools=[
                    "analyze_workload", "query_corpus", "optimize_prompt"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["pro", "enterprise"],
                ),
                rate_limits=RateLimit(per_hour=100, per_day=1000),
            ),
            
            "data_management": ToolPermission(
                name="data_management",
                description="Data operations and corpus management",
                level=PermissionLevel.WRITE,
                tools=[
                    "generate_synthetic_data", "corpus_manager", 
                    "create_corpus", "modify_corpus"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["pro", "enterprise"],
                    feature_flags=["data_operations"],
                ),
                rate_limits=RateLimit(per_hour=50, per_day=500),
            ),
            
            "advanced_optimization": ToolPermission(
                name="advanced_optimization",
                description="Advanced AI optimization tools",
                level=PermissionLevel.WRITE,
                tools=[
                    "cost_analyzer", "latency_analyzer", "performance_predictor",
                    "multi_objective_optimization", "kv_cache_optimization_audit",
                    "advanced_optimization_for_core_function"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["enterprise"],
                    feature_flags=["advanced_optimization"],
                ),
                rate_limits=RateLimit(per_hour=20, per_day=100),
            ),
            
            "system_management": ToolPermission(
                name="system_management",
                description="System configuration and management",
                level=PermissionLevel.ADMIN,
                tools=[
                    "system_configurator", "log_analyzer", "user_admin",
                    "feature_flag_toggle"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["enterprise"],
                    role_requirements=["admin", "developer"],
                ),
            ),
            
            "developer_tools": ToolPermission(
                name="developer_tools",
                description="Development and debugging tools",
                level=PermissionLevel.ADMIN,
                tools=[
                    "debug_panel", "impersonation_tool", "system_logs",
                    "database_query_tool"
                ],
                business_requirements=BusinessRequirement(
                    developer_status=True,
                    environment=["development", "staging"],
                ),
            ),
        }
    
    async def check_tool_permission(
        self, 
        context: ToolExecutionContext
    ) -> PermissionCheckResult:
        """
        Check if user has permission to execute a tool
        
        Args:
            context: Tool execution context
            
        Returns:
            Permission check result
        """
        try:
            # Get user's plan and permissions
            user_plan = await self._get_user_plan(context.user_id)
            user_permissions = self._get_user_permissions(context, user_plan)
            
            # Find required permissions for tool
            required_permissions = self._get_tool_required_permissions(context.tool_name)
            if not required_permissions:
                # Tool doesn't require specific permissions
                return PermissionCheckResult(allowed=True)
            
            # Check if user has required permissions
            missing_permissions = []
            for perm_name in required_permissions:
                if not self._has_permission(perm_name, user_permissions, context, user_plan):
                    missing_permissions.append(perm_name)
            
            if missing_permissions:
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"Missing permissions: {', '.join(missing_permissions)}",
                    required_permissions=required_permissions,
                    missing_permissions=missing_permissions,
                    upgrade_path=self._get_upgrade_path(missing_permissions, user_plan)
                )
            
            # Check rate limits
            rate_limit_result = await self._check_rate_limits(context, required_permissions)
            if not rate_limit_result["allowed"]:
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"Rate limit exceeded: {rate_limit_result['message']}",
                    rate_limit_status=rate_limit_result,
                    upgrade_path=self._get_upgrade_path_for_rate_limits(user_plan)
                )
            
            return PermissionCheckResult(
                allowed=True,
                required_permissions=required_permissions,
                business_requirements_met=True,
                rate_limit_status=rate_limit_result
            )
            
        except Exception as e:
            logger.error(f"Error checking tool permission: {e}", exc_info=True)
            return PermissionCheckResult(
                allowed=False,
                reason=f"Permission check failed: {str(e)}"
            )
    
    async def get_user_tool_availability(
        self, 
        user_id: str, 
        tool_registry: Dict[str, Any]
    ) -> List[ToolAvailability]:
        """
        Get list of tools available to a user
        
        Args:
            user_id: User identifier
            tool_registry: Registry of all tools
            
        Returns:
            List of tool availability information
        """
        try:
            # Get user context
            user_plan = await self._get_user_plan(user_id)
            # Note: We would normally get this from the database
            # For now, create a basic context
            context_base = ToolExecutionContext(
                user_id=user_id,
                tool_name="",  # Will be set per tool
                requested_action="list",
                user_plan=user_plan.tier.value if user_plan else "free",
                user_roles=[],  # Would come from user object
                is_developer=False  # Would come from user object
            )
            
            availability_list = []
            
            for tool_name, tool_info in tool_registry.items():
                context = context_base.copy()
                context.tool_name = tool_name
                
                # Check permission
                permission_result = await self.check_tool_permission(context)
                
                # Get usage info
                usage_today = await self._get_usage_count(user_id, tool_name, "day")
                
                availability = ToolAvailability(
                    tool_name=tool_name,
                    category=tool_info.get("category", "uncategorized"),
                    description=tool_info.get("description", "No description"),
                    available=permission_result.allowed,
                    required_permissions=permission_result.required_permissions,
                    missing_requirements=permission_result.missing_permissions,
                    usage_today=usage_today,
                    upgrade_required=permission_result.upgrade_path
                )
                
                # Add rate limit info if available
                if permission_result.rate_limit_status:
                    rate_limits = permission_result.rate_limit_status.get("limits")
                    if rate_limits:
                        availability.rate_limits = RateLimit(**rate_limits)
                
                availability_list.append(availability)
            
            return availability_list
            
        except Exception as e:
            logger.error(f"Error getting tool availability: {e}", exc_info=True)
            return []
    
    async def _get_user_plan(self, user_id: str) -> UserPlan:
        """Get user's current plan"""
        # In a real implementation, this would query the database
        # For now, return a default free plan
        from app.schemas.UserPlan import PlanFeatures
        
        return UserPlan(
            user_id=user_id,
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
    
    def _get_user_permissions(
        self, 
        context: ToolExecutionContext, 
        user_plan: UserPlan
    ) -> Set[str]:
        """Get all permissions for a user"""
        permissions = set()
        
        # Add permissions from plan
        permissions.update(user_plan.features.permissions)
        
        # Handle wildcard permissions
        if "*" in permissions:
            # User has all permissions
            permissions.update(self._permission_definitions.keys())
        
        # Add developer permissions if applicable
        if context.is_developer:
            permissions.add("developer_tools")
        
        return permissions
    
    def _get_tool_required_permissions(self, tool_name: str) -> List[str]:
        """Get permissions required for a specific tool"""
        required = []
        for perm_name, perm_def in self._permission_definitions.items():
            if tool_name in perm_def.tools:
                required.append(perm_name)
        return required
    
    def _has_permission(
        self, 
        permission_name: str, 
        user_permissions: Set[str], 
        context: ToolExecutionContext,
        user_plan: UserPlan
    ) -> bool:
        """Check if user has a specific permission"""
        # Check direct permission
        if permission_name in user_permissions:
            # Check business requirements
            perm_def = self._permission_definitions.get(permission_name)
            if perm_def:
                return self._check_business_requirements(
                    perm_def.business_requirements, context, user_plan
                )
            return True
        
        return False
    
    def _check_business_requirements(
        self,
        requirements: BusinessRequirement,
        context: ToolExecutionContext,
        user_plan: UserPlan
    ) -> bool:
        """Check if business requirements are met"""
        # Check plan tier requirement
        if requirements.plan_tiers:
            if context.user_plan not in requirements.plan_tiers:
                return False
        
        # Check feature flags
        if requirements.feature_flags:
            user_flags = user_plan.features.feature_flags
            for flag in requirements.feature_flags:
                if flag not in user_flags:
                    return False
        
        # Check role requirements
        if requirements.role_requirements:
            for role in requirements.role_requirements:
                if role not in context.user_roles:
                    return False
        
        # Check developer status
        if requirements.developer_status is not None:
            if requirements.developer_status != context.is_developer:
                return False
        
        # Check environment
        if requirements.environment:
            if context.environment not in requirements.environment:
                return False
        
        return True
    
    async def _check_rate_limits(
        self, 
        context: ToolExecutionContext,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """Check rate limits for tool execution"""
        # Get applicable rate limits
        rate_limits = {}
        for perm_name in permissions:
            perm_def = self._permission_definitions.get(perm_name)
            if perm_def and perm_def.rate_limits:
                rate_limits.update({
                    "per_minute": perm_def.rate_limits.per_minute,
                    "per_hour": perm_def.rate_limits.per_hour,
                    "per_day": perm_def.rate_limits.per_day,
                })
        
        if not rate_limits:
            return {"allowed": True, "limits": rate_limits}
        
        # Check each rate limit
        for period, limit in rate_limits.items():
            if limit is None:
                continue
                
            current_usage = await self._get_usage_count(
                context.user_id, context.tool_name, period.split("_")[1]
            )
            
            if current_usage >= limit:
                return {
                    "allowed": False,
                    "message": f"Exceeded {period} limit of {limit}",
                    "current_usage": current_usage,
                    "limit": limit,
                    "limits": rate_limits
                }
        
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
        
        # Create cache key
        now = datetime.now(UTC)
        if period == "minute":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H%M')}"
        elif period == "hour":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H')}"
        elif period == "day":
            key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d')}"
        else:
            return 0
        
        try:
            count = await self.redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting usage count: {e}")
            return 0
    
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
            
            # Update usage counters
            for period in ["minute", "hour", "day"]:
                if period == "minute":
                    key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H%M')}"
                    ttl = 60
                elif period == "hour":
                    key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H')}"
                    ttl = 3600
                elif period == "day":
                    key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d')}"
                    ttl = 86400
                
                await self.redis.incr(key)
                await self.redis.expire(key, ttl)
                
        except Exception as e:
            logger.error(f"Error recording tool usage: {e}")
    
    def _get_upgrade_path(
        self, 
        missing_permissions: List[str], 
        user_plan: UserPlan
    ) -> Optional[str]:
        """Get suggested upgrade path for missing permissions"""
        # Check which plan tiers provide the missing permissions
        required_tiers = set()
        
        for perm_name in missing_permissions:
            perm_def = self._permission_definitions.get(perm_name)
            if perm_def and perm_def.business_requirements.plan_tiers:
                required_tiers.update(perm_def.business_requirements.plan_tiers)
        
        if not required_tiers:
            return None
        
        # Find the lowest tier that satisfies requirements
        tier_hierarchy = ["free", "pro", "enterprise", "developer"]
        current_tier_index = tier_hierarchy.index(user_plan.tier.value)
        
        for tier in tier_hierarchy[current_tier_index + 1:]:
            if tier in required_tiers:
                return tier.capitalize()
        
        return None
    
    def _get_upgrade_path_for_rate_limits(self, user_plan: UserPlan) -> Optional[str]:
        """Get upgrade path for rate limit issues"""
        if user_plan.tier == PlanTier.FREE:
            return "Pro"
        elif user_plan.tier == PlanTier.PRO:
            return "Enterprise"
        return None