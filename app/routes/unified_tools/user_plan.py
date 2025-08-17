"""
User Plan Management for Unified Tools API
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app.schemas.UserPlan import PlanTier, PLAN_DEFINITIONS
from app.logging_config import central_logger
from .schemas import UserPlanResponse
from .database_utils import get_daily_usage_count

logger = central_logger


def get_current_plan_definition(current_user: User):
    """Get current user's plan definition."""
    return PLAN_DEFINITIONS.get(PlanTier(current_user.plan_tier))


def calculate_available_upgrades(current_user: User) -> List[str]:
    """Calculate available upgrade options for user."""
    available_upgrades = []
    current_tier_index = list(PlanTier).index(PlanTier(current_user.plan_tier))
    for tier in list(PlanTier)[current_tier_index + 1:]:
        if tier != PlanTier.DEVELOPER:  # Developer tier not shown as upgrade option
            available_upgrades.append(tier.value)
    return available_upgrades


async def get_usage_summary(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    """Get usage summary for user."""
    return {
        "tools_used_today": await get_daily_usage_count(current_user.id, db),
        "plan_utilization": "moderate",  # Would calculate from actual usage
        "approaching_limits": []  # Would check against plan limits
    }


def build_user_plan_response(
    current_user: User, 
    current_plan_def, 
    available_upgrades: List[str], 
    usage_summary: Dict[str, Any]
) -> UserPlanResponse:
    """Build user plan response."""
    return UserPlanResponse(
        current_plan=current_user.plan_tier,
        plan_expires_at=current_user.plan_expires_at.isoformat() if current_user.plan_expires_at else None,
        features=current_plan_def.features.permissions if current_plan_def else [],
        available_upgrades=available_upgrades,
        usage_summary=usage_summary
    )


async def gather_user_plan_data(current_user: User, db: AsyncSession):
    """Gather user plan data components."""
    current_plan_def = get_current_plan_definition(current_user)
    available_upgrades = calculate_available_upgrades(current_user)
    usage_summary = await get_usage_summary(current_user, db)
    return current_plan_def, available_upgrades, usage_summary