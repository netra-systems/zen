"""Main Tool Permission Service - Orchestrates all permission functionality"""

from typing import Any, Dict, List, Optional

# MIGRATED: Use SSOT Redis import pattern
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool_permission import (
    PermissionCheckResult,
    ToolExecutionContext,
)
from netra_backend.app.schemas.user_plan import PLAN_DEFINITIONS, PlanTier, UserPlan
from netra_backend.app.services.tool_permissions.rate_limiter import RateLimiter
from netra_backend.app.services.tool_permissions.permission_checker import (
    PermissionChecker,
)
from netra_backend.app.services.tool_permissions.permission_definitions import (
    PermissionDefinitions,
)
from netra_backend.app.services.tool_permissions.tool_availability_processor import (
    ToolAvailabilityProcessor,
)

logger = central_logger


class ToolPermissionService:
    """Service for managing per-tool permissions and business logic"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.permissions_cache = {}
        self._permission_definitions = PermissionDefinitions.load_permission_definitions()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize service components"""
        self.permission_checker = PermissionChecker(self._permission_definitions)
        self.rate_limiter = RateLimiter(self.redis)
        self.availability_processor = ToolAvailabilityProcessor(
            self.permission_checker, self.rate_limiter
        )

    async def check_tool_permission(self, context: ToolExecutionContext) -> PermissionCheckResult:
        """Check if user has permission to execute a tool"""
        try:
            validation_result = await self._validate_tool_permissions(context)
            return validation_result or await self._process_permission_check(context)
        except Exception as e:
            return self._create_error_result(e)

    async def get_user_tool_availability(self, user_id: str, tool_registry: Dict[str, Any]) -> List:
        """Get list of tools available to a user"""
        return await self.availability_processor.get_user_tool_availability(user_id, tool_registry)

    async def record_tool_usage(
        self,
        user_id: str,
        tool_name: str,
        execution_time_ms: int,
        status: str
    ):
        """Record tool usage for rate limiting and analytics"""
        await self.rate_limiter.record_tool_usage(user_id, tool_name, execution_time_ms, status)

    async def _get_user_plan(self, user_id: str, context: Optional[ToolExecutionContext] = None) -> UserPlan:
        """Get user's current plan"""
        from netra_backend.app.schemas.user_plan import PlanFeatures
        
        # Use the plan from context if available, otherwise default to FREE
        if context and context.user_plan:
            try:
                tier = PlanTier(context.user_plan)
                return UserPlan(
                    user_id=user_id,
                    tier=tier,
                    features=PLAN_DEFINITIONS[tier].features
                )
            except (ValueError, KeyError):
                # Invalid tier, fallback to FREE
                pass
        
        # Default fallback
        return UserPlan(
            user_id=user_id,
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )

    async def _validate_tool_permissions(self, context: ToolExecutionContext) -> Optional[PermissionCheckResult]:
        """Validate tool permissions and return early if no permissions needed"""
        required_permissions = self.permission_checker.get_tool_required_permissions(context.tool_name)
        if not required_permissions:
            return PermissionCheckResult(allowed=True)
        user_plan = await self._get_user_plan(context.user_id, context)
        user_permissions = self.permission_checker.get_user_permissions(context, user_plan)
        missing_permissions = self.permission_checker.check_missing_permissions(required_permissions, user_permissions, context, user_plan)
        return self._create_permission_denied_result(missing_permissions, required_permissions, user_plan) if missing_permissions else None

    async def _process_permission_check(self, context: ToolExecutionContext) -> PermissionCheckResult:
        """Process permission check after validation"""
        required_permissions = self.permission_checker.get_tool_required_permissions(context.tool_name)
        user_plan = await self._get_user_plan(context.user_id, context)
        rate_limit_result = await self.rate_limiter.check_rate_limits(context, required_permissions, self._permission_definitions)
        if not rate_limit_result["allowed"]:
            return self._create_rate_limit_denied_result(rate_limit_result, user_plan)
        return self._create_success_result(required_permissions, rate_limit_result)

    def _create_permission_denied_result(
        self, missing_permissions: List[str], required_permissions: List[str], user_plan: UserPlan
    ) -> PermissionCheckResult:
        """Create permission denied result"""
        return PermissionCheckResult(
            allowed=False, reason=f"Missing permissions: {', '.join(missing_permissions)}",
            required_permissions=required_permissions, missing_permissions=missing_permissions,
            upgrade_path=self.permission_checker.get_upgrade_path(missing_permissions, user_plan))

    def _create_rate_limit_denied_result(
        self, rate_limit_result: Dict[str, Any], user_plan: UserPlan
    ) -> PermissionCheckResult:
        """Create rate limit denied result"""
        return PermissionCheckResult(
            allowed=False, reason=f"Rate limit exceeded: {rate_limit_result['message']}",
            rate_limit_status=rate_limit_result,
            upgrade_path=self.permission_checker.get_upgrade_path_for_rate_limits(user_plan))

    def _create_success_result(
        self, required_permissions: List[str], rate_limit_result: Dict[str, Any]
    ) -> PermissionCheckResult:
        """Create successful permission check result"""
        return PermissionCheckResult(
            allowed=True, required_permissions=required_permissions,
            business_requirements_met=True, rate_limit_status=rate_limit_result)

    def _create_error_result(self, error: Exception) -> PermissionCheckResult:
        """Create error result for permission check"""
        logger.error(f"Error checking tool permission: {error}", exc_info=True)
        return PermissionCheckResult(
            allowed=False,
            reason=f"Permission check failed: {str(error)}"
        )