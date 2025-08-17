"""
Permission Checking Logic for Unified Tools API
"""
from typing import Dict, Any
from app.db.models_postgres import User
from app.schemas.ToolPermission import ToolExecutionContext
from app.logging_config import central_logger

logger = central_logger


def extract_user_context_data(current_user: User) -> Dict[str, Any]:
    """Extract user context data."""
    return {
        "user_id": str(current_user.id),
        "user_plan": current_user.plan_tier,
        "user_roles": getattr(current_user, 'roles', []),
        "feature_flags": current_user.feature_flags or {},
        "is_developer": current_user.is_developer
    }


def create_tool_execution_context(
    current_user: User, tool_name: str, action: str
) -> ToolExecutionContext:
    """Create tool execution context for permission checking."""
    user_data = extract_user_context_data(current_user)
    return ToolExecutionContext(
        tool_name=tool_name,
        requested_action=action,
        **user_data
    )


async def check_tool_permission_with_service(permission_service, context: ToolExecutionContext):
    """Check tool permission using permission service."""
    return await permission_service.check_tool_permission(context)


def extract_permission_details(permission_result) -> Dict[str, Any]:
    """Extract permission details from result."""
    return {
        "allowed": permission_result.allowed,
        "reason": permission_result.reason,
        "required_permissions": permission_result.required_permissions,
        "missing_permissions": permission_result.missing_permissions,
        "upgrade_path": permission_result.upgrade_path,
        "rate_limit_status": permission_result.rate_limit_status
    }


def build_permission_response(tool_name: str, permission_result) -> Dict[str, Any]:
    """Build permission check response."""
    details = extract_permission_details(permission_result)
    return {"tool_name": tool_name, **details}


async def execute_permission_check(
    permission_service, tool_name: str, action: str, current_user: User
) -> Dict[str, Any]:
    """Execute permission check workflow."""
    context = create_tool_execution_context(current_user, tool_name, action)
    permission_result = await check_tool_permission_with_service(permission_service, context)
    return build_permission_response(tool_name, permission_result)