"""Tool Availability Processor Module - Processes tool availability for users"""

from typing import Dict, List, Any
from app.schemas.ToolPermission import (
    ToolExecutionContext, ToolAvailability, PermissionCheckResult, RateLimit
)
from app.schemas.UserPlan import UserPlan, PlanTier, PLAN_DEFINITIONS
from app.logging_config import central_logger

logger = central_logger


class ToolAvailabilityProcessor:
    """Processes tool availability for users"""

    def __init__(self, permission_checker, rate_limiter):
        self.permission_checker = permission_checker
        self.rate_limiter = rate_limiter

    async def get_user_tool_availability(self, user_id: str, tool_registry: Dict[str, Any]) -> List[ToolAvailability]:
        """Get list of tools available to a user"""
        try:
            context_base = await self._create_base_context(user_id)
            return await self._process_tool_registry(context_base, tool_registry)
        except Exception as e:
            logger.error(f"Error getting tool availability: {e}", exc_info=True)
            return []

    async def _get_user_plan(self, user_id: str) -> UserPlan:
        """Get user's current plan"""
        from app.schemas.UserPlan import PlanFeatures
        return UserPlan(
            user_id=user_id,
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )

    async def _create_base_context(self, user_id: str) -> ToolExecutionContext:
        """Create base context for tool availability checking"""
        user_plan = await self._get_user_plan(user_id)
        return ToolExecutionContext(
            user_id=user_id,
            tool_name="",
            requested_action="list",
            user_plan=user_plan.tier.value if user_plan else "free",
            user_roles=[],
            is_developer=False
        )

    async def _process_tool_registry(
        self, context_base: ToolExecutionContext, tool_registry: Dict[str, Any]
    ) -> List[ToolAvailability]:
        """Process tool registry to create availability list"""
        availability_list = []
        for tool_name, tool_info in tool_registry.items():
            context = context_base.copy()
            context.tool_name = tool_name
            availability = await self._process_tool_availability(context, tool_info)
            availability_list.append(availability)
        return availability_list

    async def _process_tool_availability(
        self, context: ToolExecutionContext, tool_info: Dict[str, Any]
    ) -> ToolAvailability:
        """Process availability for a single tool"""
        permission_result = await self._check_tool_permission(context)
        usage_today = await self.rate_limiter._get_usage_count(context.user_id, context.tool_name, "day")
        availability = self._create_tool_availability(context, tool_info, permission_result, usage_today)
        self._add_rate_limit_info(availability, permission_result)
        return availability

    async def _check_tool_permission(self, context: ToolExecutionContext):
        """Check tool permission for availability processing"""
        # This would call the main permission service
        # For now, return a mock result
        return PermissionCheckResult(allowed=True, required_permissions=[])

    def _create_tool_availability(self, context: ToolExecutionContext, tool_info: Dict[str, Any], 
                                  permission_result: PermissionCheckResult, usage_today: int) -> ToolAvailability:
        """Create ToolAvailability object"""
        return ToolAvailability(tool_name=context.tool_name, category=tool_info.get("category", "uncategorized"),
                               description=tool_info.get("description", "No description"), available=permission_result.allowed,
                               required_permissions=permission_result.required_permissions, missing_requirements=permission_result.missing_permissions,
                               usage_today=usage_today, upgrade_required=permission_result.upgrade_path)

    def _add_rate_limit_info(self, availability: ToolAvailability, permission_result: PermissionCheckResult) -> None:
        """Add rate limit information to availability if present"""
        if permission_result.rate_limit_status:
            rate_limits = permission_result.rate_limit_status.get("limits")
            if rate_limits:
                availability.rate_limits = RateLimit(**rate_limits)