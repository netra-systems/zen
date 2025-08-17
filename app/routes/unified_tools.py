"""
Unified Tools API - New unified API for all tool operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import DbDep
from app.db.models_postgres import User
from app.auth_integration.auth import get_current_user
from app.services.unified_tool_registry import UnifiedToolRegistry, ToolExecutionResult
from app.services.tool_permission_service import ToolPermissionService
from app.schemas.ToolPermission import ToolAvailability, PermissionCheckResult
from app.schemas.UserPlan import PlanTier, PLAN_DEFINITIONS
from app.logging_config import central_logger
from pydantic import BaseModel
import redis
import os

logger = central_logger
router = APIRouter()

# Initialize services (in production, these would be dependency injected)
redis_client = None
try:
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")

permission_service = ToolPermissionService(redis_client)
tool_registry = UnifiedToolRegistry(permission_service=permission_service)


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""
    tool_name: str
    arguments: Dict[str, Any] = {}
    action: str = "execute"


class ToolAvailabilityResponse(BaseModel):
    """Response with available tools for user"""
    tools: List[ToolAvailability]
    user_plan: str
    total_tools: int
    available_tools: int
    categories: List[str]


class UserPlanResponse(BaseModel):
    """Response with user's plan information"""
    current_plan: str
    plan_expires_at: Optional[str]
    features: List[str]
    available_upgrades: List[str]
    usage_summary: Dict[str, Any]


async def _get_available_tools_for_user(current_user: User, category: Optional[str]):
    """Get available tools for user with optional category filter."""
    return await tool_registry.list_available_tools(
        user=current_user,
        category=category
    )

def _get_tool_category_names() -> List[str]:
    """Get list of tool category names."""
    return [cat["name"] for cat in tool_registry.get_tool_categories()]

def _filter_available_tools(available_tools: List[Dict]) -> List[Dict]:
    """Filter tools to only include available ones."""
    return [tool for tool in available_tools if tool.get("available", False)]

def _extract_tool_basic_info(tool: Dict) -> Dict:
    """Extract basic tool information."""
    return {
        "tool_name": tool["name"],
        "category": tool["category"],
        "description": tool["description"]
    }


def _extract_tool_requirements(tool: Dict) -> Dict:
    """Extract tool requirements information."""
    return {
        "available": tool.get("available", False),
        "required_permissions": tool.get("required_permissions", []),
        "missing_requirements": tool.get("missing_requirements", []),
        "upgrade_required": tool.get("upgrade_path")
    }


def _create_tool_availability(tool: Dict) -> ToolAvailability:
    """Create ToolAvailability object from tool dict."""
    basic_info = _extract_tool_basic_info(tool)
    requirements = _extract_tool_requirements(tool)
    return ToolAvailability(**{**basic_info, **requirements})

def _build_tool_availability_response(
    available_tools: List[Dict], tools_available: List[Dict], 
    categories: List[str], current_user: User
) -> ToolAvailabilityResponse:
    """Build the tool availability response."""
    tool_objects = [_create_tool_availability(tool) for tool in available_tools]
    return ToolAvailabilityResponse(
        tools=tool_objects,
        user_plan=current_user.plan_tier,
        total_tools=len(available_tools),
        available_tools=len(tools_available),
        categories=categories
    )

def _handle_list_tools_error(e: Exception):
    """Handle list tools error."""
    logger.error(f"Error listing tools: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to list tools")

async def _gather_tool_data(current_user: User, category: Optional[str]):
    """Gather tool data for user."""
    available_tools = await _get_available_tools_for_user(current_user, category)
    categories = _get_tool_category_names()
    tools_available = _filter_available_tools(available_tools)
    return available_tools, categories, tools_available

@router.get("/", summary="List available tools")
async def list_tools(
    db: DbDep,
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user)
) -> ToolAvailabilityResponse:
    """
    Get list of all tools available to the current user
    
    This endpoint replaces the old admin-specific tool listings and provides
    a unified view of all tools with their availability status.
    """
    try:
        available_tools, categories, tools_available = await _gather_tool_data(current_user, category)
        return _build_tool_availability_response(available_tools, tools_available, categories, current_user)
    except Exception as e:
        _handle_list_tools_error(e)


async def _execute_tool_through_registry(request: ToolExecutionRequest, current_user: User):
    """Execute tool through registry."""
    return await tool_registry.execute_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        user=current_user
    )

def _build_base_tool_response(result) -> Dict[str, Any]:
    """Build base tool execution response."""
    return {
        "tool_name": result.tool_name,
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": result.created_at.isoformat()
    }

def _add_result_or_error(response: Dict[str, Any], result) -> None:
    """Add result or error to response based on status."""
    if result.status == "success":
        response["result"] = result.result
    else:
        response["error"] = result.error_message

def _create_permission_info(permission_check) -> Dict[str, Any]:
    """Create permission info dictionary."""
    return {
        "required_permissions": permission_check.required_permissions,
        "missing_permissions": permission_check.missing_permissions,
        "upgrade_path": permission_check.upgrade_path,
        "rate_limit_status": permission_check.rate_limit_status
    }


def _add_permission_info_if_denied(response: Dict[str, Any], result) -> None:
    """Add permission info if access was denied."""
    if result.status == "permission_denied" and result.permission_check:
        response["permission_info"] = _create_permission_info(result.permission_check)

def _format_tool_execution_response(result) -> Dict[str, Any]:
    """Format complete tool execution response."""
    response = _build_base_tool_response(result)
    _add_result_or_error(response, result)
    _add_permission_info_if_denied(response, result)
    return response

def _handle_tool_execution_error(e: Exception, tool_name: str):
    """Handle tool execution error."""
    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

async def _process_tool_execution(request: ToolExecutionRequest, current_user: User, db: DbDep):
    """Process tool execution and logging."""
    result = await _execute_tool_through_registry(request, current_user)
    await _log_tool_execution_to_db(result, db)
    return _format_tool_execution_response(result)

@router.post("/execute", summary="Execute a tool")
async def execute_tool(
    request: ToolExecutionRequest,
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute a tool with permission checking and usage tracking
    
    This endpoint replaces all the separate tool execution endpoints and provides
    a unified interface for all tool operations.
    """
    try:
        return await _process_tool_execution(request, current_user, db)
    except Exception as e:
        _handle_tool_execution_error(e, request.tool_name)


def _get_tool_categories_from_registry() -> List[Dict[str, Any]]:
    """Get tool categories from registry."""
    return tool_registry.get_tool_categories()

def _handle_categories_error(e: Exception):
    """Handle categories retrieval error."""
    logger.error(f"Error getting tool categories: {e}")
    raise HTTPException(status_code=500, detail="Failed to get categories")

@router.get("/categories", summary="Get tool categories")
async def get_tool_categories() -> List[Dict[str, Any]]:
    """
    Get list of all tool categories with counts
    """
    try:
        return _get_tool_categories_from_registry()
    except Exception as e:
        _handle_categories_error(e)


def _extract_user_context_data(current_user: User) -> Dict[str, Any]:
    """Extract user context data."""
    return {
        "user_id": str(current_user.id),
        "user_plan": current_user.plan_tier,
        "user_roles": getattr(current_user, 'roles', []),
        "feature_flags": current_user.feature_flags or {},
        "is_developer": current_user.is_developer
    }


def _create_tool_execution_context(current_user: User, tool_name: str, action: str):
    """Create tool execution context for permission checking."""
    from app.schemas.ToolPermission import ToolExecutionContext
    user_data = _extract_user_context_data(current_user)
    return ToolExecutionContext(
        tool_name=tool_name,
        requested_action=action,
        **user_data
    )

async def _check_tool_permission_with_service(context):
    """Check tool permission using permission service."""
    return await permission_service.check_tool_permission(context)

def _extract_permission_details(permission_result) -> Dict[str, Any]:
    """Extract permission details from result."""
    return {
        "allowed": permission_result.allowed,
        "reason": permission_result.reason,
        "required_permissions": permission_result.required_permissions,
        "missing_permissions": permission_result.missing_permissions,
        "upgrade_path": permission_result.upgrade_path,
        "rate_limit_status": permission_result.rate_limit_status
    }


def _build_permission_response(tool_name: str, permission_result) -> Dict[str, Any]:
    """Build permission check response."""
    details = _extract_permission_details(permission_result)
    return {"tool_name": tool_name, **details}

def _handle_permission_check_error(e: Exception, tool_name: str):
    """Handle permission check error."""
    logger.error(f"Error checking permissions for {tool_name}: {e}")
    raise HTTPException(status_code=500, detail="Permission check failed")

async def _execute_permission_check(tool_name: str, action: str, current_user: User):
    """Execute permission check workflow."""
    context = _create_tool_execution_context(current_user, tool_name, action)
    permission_result = await _check_tool_permission_with_service(context)
    return _build_permission_response(tool_name, permission_result)

@router.get("/permissions/{tool_name}", summary="Check tool permissions")
async def check_tool_permissions(
    tool_name: str,
    action: str = Query("execute", description="Action to check"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if user has permission to use a specific tool
    
    This is useful for UI elements to show/hide tool options dynamically.
    """
    try:
        return await _execute_permission_check(tool_name, action, current_user)
    except Exception as e:
        _handle_permission_check_error(e, tool_name)


def _get_current_plan_definition(current_user: User):
    """Get current user's plan definition."""
    return PLAN_DEFINITIONS.get(PlanTier(current_user.plan_tier))

def _calculate_available_upgrades(current_user: User) -> List[str]:
    """Calculate available upgrade options for user."""
    available_upgrades = []
    current_tier_index = list(PlanTier).index(PlanTier(current_user.plan_tier))
    for tier in list(PlanTier)[current_tier_index + 1:]:
        if tier != PlanTier.DEVELOPER:  # Developer tier not shown as upgrade option
            available_upgrades.append(tier.value)
    return available_upgrades

async def _get_usage_summary(current_user: User, db: DbDep) -> Dict[str, Any]:
    """Get usage summary for user."""
    return {
        "tools_used_today": await _get_daily_usage_count(current_user.id, db),
        "plan_utilization": "moderate",  # Would calculate from actual usage
        "approaching_limits": []  # Would check against plan limits
    }

def _build_user_plan_response(
    current_user: User, current_plan_def, available_upgrades: List[str], 
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

def _handle_user_plan_error(e: Exception):
    """Handle user plan retrieval error."""
    logger.error(f"Error getting user plan: {e}")
    raise HTTPException(status_code=500, detail="Failed to get plan information")

async def _gather_user_plan_data(current_user: User, db: DbDep):
    """Gather user plan data components."""
    current_plan_def = _get_current_plan_definition(current_user)
    available_upgrades = _calculate_available_upgrades(current_user)
    usage_summary = await _get_usage_summary(current_user, db)
    return current_plan_def, available_upgrades, usage_summary

@router.get("/user/plan", summary="Get user plan information")
async def get_user_plan(
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> UserPlanResponse:
    """
    Get current user's plan information and upgrade options
    """
    try:
        current_plan_def, available_upgrades, usage_summary = await _gather_user_plan_data(current_user, db)
        return _build_user_plan_response(current_user, current_plan_def, available_upgrades, usage_summary)
    except Exception as e:
        _handle_user_plan_error(e)


def _check_user_needs_migration(current_user: User) -> bool:
    """Check if user needs migration from legacy system."""
    return current_user.role in ["admin", "developer", "super_admin"]

def _determine_migration_plan_and_flags(role: str) -> tuple[str, List[str]]:
    """Determine new plan and feature flags based on role."""
    if role == "super_admin":
        return "enterprise", ["*"]
    elif role == "admin":
        return "enterprise", ["data_operations", "advanced_analytics", "advanced_optimization", "system_management"]
    elif role == "developer":
        return "developer", ["*"]
    else:
        return "pro", ["data_operations", "advanced_analytics"]

def _update_user_plan_in_db(current_user: User, new_plan: str, feature_flags: List[str], db):
    """Update user plan and feature flags in database."""
    current_user.plan_tier = new_plan
    current_user.feature_flags = {flag: True for flag in feature_flags}
    db.commit()

def _build_migration_success_response(current_user: User, new_plan: str, feature_flags: List[str]) -> Dict[str, Any]:
    """Build successful migration response."""
    return {
        "status": "migrated",
        "old_role": current_user.role,
        "new_plan": new_plan,
        "feature_flags": feature_flags,
        "message": "Successfully migrated to new tool permission system"
    }

def _build_no_migration_response(current_user: User) -> Dict[str, Any]:
    """Build no migration needed response."""
    return {
        "status": "no_migration_needed",
        "current_plan": current_user.plan_tier,
        "message": "User already on new system or no migration needed"
    }

def _handle_migration_error(e: Exception):
    """Handle migration error."""
    logger.error(f"Error migrating user: {e}")
    raise HTTPException(status_code=500, detail="Migration failed")

def _execute_user_migration(current_user: User, db: DbDep):
    """Execute user migration workflow."""
    new_plan, feature_flags = _determine_migration_plan_and_flags(current_user.role)
    _update_user_plan_in_db(current_user, new_plan, feature_flags, db)
    return _build_migration_success_response(current_user, new_plan, feature_flags)

def _process_migration_request(current_user: User, db: DbDep):
    """Process migration request based on user status."""
    if _check_user_needs_migration(current_user):
        return _execute_user_migration(current_user, db)
    else:
        return _build_no_migration_response(current_user)

@router.post("/migrate-legacy", summary="Migrate from legacy admin system")
async def migrate_legacy_admin(
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Migrate user from legacy admin system to new tool-based system
    
    This endpoint handles the transition from role-based admin access
    to the new per-tool permission system.
    """
    try:
        return _process_migration_request(current_user, db)
    except Exception as e:
        _handle_migration_error(e)


# Helper functions

def _get_tool_info_for_logging(result: ToolExecutionResult):
    """Get tool info from registry for logging."""
    return tool_registry.tools.get(result.tool_name)

def _create_tool_usage_log_entry(result: ToolExecutionResult, tool):
    """Create tool usage log entry."""
    from app.db.models_postgres import ToolUsageLog
    return ToolUsageLog(
        user_id=result.user_id,
        tool_name=result.tool_name,
        category=tool.category if tool else "unknown",
        execution_time_ms=result.execution_time_ms,
        status=result.status,
        plan_tier="free",  # Would get from user
        permission_check_result=result.permission_check.dict() if result.permission_check else None
    )

async def _save_log_entry_to_db(log_entry, db: AsyncSession):
    """Save log entry to database."""
    db.add(log_entry)
    await db.commit()

def _handle_logging_error(e: Exception):
    """Handle logging error."""
    logger.error(f"Error logging tool execution to DB: {e}")

async def _log_tool_execution_to_db(result: ToolExecutionResult, db: AsyncSession):
    """Log tool execution to database for analytics"""
    try:
        tool = _get_tool_info_for_logging(result)
        log_entry = _create_tool_usage_log_entry(result, tool)
        await _save_log_entry_to_db(log_entry, db)
    except Exception as e:
        _handle_logging_error(e)


def _build_daily_usage_query(user_id: str):
    """Build daily usage count query."""
    from app.db.models_postgres import ToolUsageLog
    from sqlalchemy import func, select
    from datetime import date
    today = date.today()
    return select(func.count(ToolUsageLog.id)).filter(
        ToolUsageLog.user_id == user_id,
        func.date(ToolUsageLog.created_at) == today
    )

async def _execute_usage_count_query(stmt, db: AsyncSession) -> int:
    """Execute usage count query and return result."""
    result = await db.execute(stmt)
    count = result.scalar()
    return count or 0

def _handle_usage_count_error(e: Exception) -> int:
    """Handle usage count query error."""
    logger.error(f"Error getting daily usage count: {e}")
    return 0

async def _get_daily_usage_count(user_id: str, db: AsyncSession) -> int:
    """Get daily tool usage count for user"""
    try:
        stmt = _build_daily_usage_query(user_id)
        return await _execute_usage_count_query(stmt, db)
    except Exception as e:
        return _handle_usage_count_error(e)