"""
Legacy Migration Logic for Unified Tools API
"""
from typing import Dict, Any, List, Tuple, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app.logging_config import central_logger

logger = central_logger


def check_user_needs_migration(current_user: User) -> bool:
    """Check if user needs migration from legacy system."""
    return current_user.role in ["admin", "developer", "super_admin"]


def get_super_admin_config() -> Tuple[str, List[str]]:
    """Get super admin plan configuration."""
    return "enterprise", ["*"]


def get_admin_config() -> Tuple[str, List[str]]:
    """Get admin plan configuration."""
    return "enterprise", ["data_operations", "advanced_analytics", "advanced_optimization", "system_management"]


def get_developer_config() -> Tuple[str, List[str]]:
    """Get developer plan configuration."""
    return "developer", ["*"]


def get_default_config() -> Tuple[str, List[str]]:
    """Get default plan configuration."""
    return "pro", ["data_operations", "advanced_analytics"]


def get_role_config_map() -> Dict[str, callable]:
    """Get role to config function mapping."""
    return {
        "super_admin": get_super_admin_config,
        "admin": get_admin_config,
        "developer": get_developer_config
    }


def determine_migration_plan_and_flags(role: str) -> Tuple[str, List[str]]:
    """Determine new plan and feature flags based on role."""
    config_map = get_role_config_map()
    config_func = config_map.get(role, get_default_config)
    return config_func()


def update_user_plan_in_db(
    current_user: User, new_plan: str, feature_flags: List[str], db: AsyncSession
) -> None:
    """Update user plan and feature flags in database."""
    current_user.plan_tier = new_plan
    current_user.feature_flags = {flag: True for flag in feature_flags}
    db.commit()


def build_migration_data_fields(current_user: User, new_plan: str, feature_flags: List[str]) -> Dict[str, Any]:
    """Build migration data field dictionary."""
    return {
        "status": "migrated",
        "old_role": current_user.role,
        "new_plan": new_plan,
        "feature_flags": feature_flags
    }


def create_migration_response_data(
    current_user: User, new_plan: str, feature_flags: List[str]
) -> Dict[str, Any]:
    """Create migration response data dictionary."""
    return build_migration_data_fields(current_user, new_plan, feature_flags)


def add_migration_success_message(response: Dict[str, Any]) -> Dict[str, Any]:
    """Add success message to migration response."""
    response["message"] = "Successfully migrated to new tool permission system"
    return response


def build_migration_success_response(
    current_user: User, new_plan: str, feature_flags: List[str]
) -> Dict[str, Any]:
    """Build successful migration response."""
    response = create_migration_response_data(current_user, new_plan, feature_flags)
    return add_migration_success_message(response)


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