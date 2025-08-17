"""
Legacy Migration Logic for Unified Tools API
"""
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app.logging_config import central_logger

logger = central_logger


def check_user_needs_migration(current_user: User) -> bool:
    """Check if user needs migration from legacy system."""
    return current_user.role in ["admin", "developer", "super_admin"]


def determine_migration_plan_and_flags(role: str) -> Tuple[str, List[str]]:
    """Determine new plan and feature flags based on role."""
    if role == "super_admin":
        return "enterprise", ["*"]
    elif role == "admin":
        return "enterprise", ["data_operations", "advanced_analytics", "advanced_optimization", "system_management"]
    elif role == "developer":
        return "developer", ["*"]
    else:
        return "pro", ["data_operations", "advanced_analytics"]


def update_user_plan_in_db(
    current_user: User, new_plan: str, feature_flags: List[str], db: AsyncSession
) -> None:
    """Update user plan and feature flags in database."""
    current_user.plan_tier = new_plan
    current_user.feature_flags = {flag: True for flag in feature_flags}
    db.commit()


def build_migration_success_response(
    current_user: User, new_plan: str, feature_flags: List[str]
) -> Dict[str, Any]:
    """Build successful migration response."""
    return {
        "status": "migrated",
        "old_role": current_user.role,
        "new_plan": new_plan,
        "feature_flags": feature_flags,
        "message": "Successfully migrated to new tool permission system"
    }


def build_no_migration_response(current_user: User) -> Dict[str, Any]:
    """Build no migration needed response."""
    return {
        "status": "no_migration_needed",
        "current_plan": current_user.plan_tier,
        "message": "User already on new system or no migration needed"
    }


def execute_user_migration(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    """Execute user migration workflow."""
    new_plan, feature_flags = determine_migration_plan_and_flags(current_user.role)
    update_user_plan_in_db(current_user, new_plan, feature_flags, db)
    return build_migration_success_response(current_user, new_plan, feature_flags)


def process_migration_request(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    """Process migration request based on user status."""
    if check_user_needs_migration(current_user):
        return execute_user_migration(current_user, db)
    else:
        return build_no_migration_response(current_user)