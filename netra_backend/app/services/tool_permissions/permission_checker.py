"""Permission Checker Module - Core permission checking logic"""

from typing import Any, Dict, List, Optional, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.ToolPermission import (
    BusinessRequirement,
    PermissionCheckResult,
    ToolExecutionContext,
)
from netra_backend.app.schemas.UserPlan import PlanTier, UserPlan

logger = central_logger


class PermissionChecker:
    """Handles core permission checking logic"""

    def __init__(self, permission_definitions: Dict):
        self.permission_definitions = permission_definitions

    def get_user_permissions(
        self, 
        context: ToolExecutionContext, 
        user_plan: UserPlan
    ) -> Set[str]:
        """Get all permissions for a user"""
        permissions = set()
        permissions.update(user_plan.features.permissions)
        if "*" in permissions:
            permissions.update(self.permission_definitions.keys())
        if context.is_developer:
            permissions.add("developer_tools")
        return permissions
    
    def get_tool_required_permissions(self, tool_name: str) -> List[str]:
        """Get permissions required for a specific tool"""
        required = []
        for perm_name, perm_def in self.permission_definitions.items():
            if tool_name in perm_def.tools:
                required.append(perm_name)
        return required
    
    def has_permission(
        self, 
        permission_name: str, 
        user_permissions: Set[str], 
        context: ToolExecutionContext,
        user_plan: UserPlan
    ) -> bool:
        """Check if user has a specific permission"""
        if permission_name in user_permissions:
            perm_def = self.permission_definitions.get(permission_name)
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
        if requirements.plan_tiers:
            if context.user_plan not in requirements.plan_tiers:
                return False
        if requirements.feature_flags:
            user_flags = user_plan.features.feature_flags
            for flag in requirements.feature_flags:
                if flag not in user_flags:
                    return False
        if requirements.role_requirements:
            for role in requirements.role_requirements:
                if role not in context.user_roles:
                    return False
        if requirements.developer_status is not None:
            if requirements.developer_status != context.is_developer:
                return False
        if requirements.environment:
            if context.environment not in requirements.environment:
                return False
        return True

    def check_missing_permissions(
        self, required_permissions: List[str], user_permissions: Set[str], 
        context: ToolExecutionContext, user_plan: UserPlan
    ) -> List[str]:
        """Check for missing permissions"""
        return [perm for perm in required_permissions 
                if not self.has_permission(perm, user_permissions, context, user_plan)]

    def get_upgrade_path(
        self, 
        missing_permissions: List[str], 
        user_plan: UserPlan
    ) -> Optional[str]:
        """Get suggested upgrade path for missing permissions"""
        required_tiers = set()
        for perm_name in missing_permissions:
            perm_def = self.permission_definitions.get(perm_name)
            if perm_def and perm_def.business_requirements.plan_tiers:
                required_tiers.update(perm_def.business_requirements.plan_tiers)
        if not required_tiers:
            return None
        tier_hierarchy = ["free", "pro", "enterprise", "developer"]
        current_tier_index = tier_hierarchy.index(user_plan.tier.value)
        for tier in tier_hierarchy[current_tier_index + 1:]:
            if tier in required_tiers:
                return tier.capitalize()
        return None

    def get_upgrade_path_for_rate_limits(self, user_plan: UserPlan) -> Optional[str]:
        """Get upgrade path for rate limit issues"""
        if user_plan.tier == PlanTier.FREE:
            return "Pro"
        elif user_plan.tier == PlanTier.PRO:
            return "Enterprise"
        return None