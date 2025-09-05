"""
Unified Tools API Router - Route definitions only
"""
from typing import Any, Dict, List, Optional

import redis
from fastapi import APIRouter, Depends, Query

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.db.models_postgres import User
from netra_backend.app.dependencies import DbDep
from netra_backend.app.routes.unified_tools.error_handlers import (
    handle_categories_error,
    handle_list_tools_error,
    handle_migration_error,
    handle_permission_check_error,
    handle_tool_execution_error,
    handle_user_plan_error,
)
from netra_backend.app.routes.unified_tools.migration import process_migration_request
from netra_backend.app.routes.unified_tools.permissions import execute_permission_check
from netra_backend.app.routes.unified_tools.tool_execution import process_tool_execution
from netra_backend.app.routes.unified_tools.tool_listing import (
    build_tool_availability_response,
    gather_tool_data,
)
from netra_backend.app.routes.unified_tools.user_plan import (
    build_user_plan_response,
    gather_user_plan_data,
)
from netra_backend.app.schemas.unified_tools import (
    ToolAvailabilityResponse,
    ToolExecutionRequest,
    UserPlanResponse,
)
from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.app.services.unified_tool_registry import UnifiedToolRegistry

router = APIRouter(
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

# Initialize services (in production, these would be dependency injected)
redis_client = None
try:
    config = unified_config_manager.get_config()
    redis_url = getattr(config, 'redis_url', 'redis://localhost:6379')
    redis_client = redis.Redis.from_url(redis_url)
except Exception:
    pass

permission_service = ToolPermissionService(redis_client)
tool_registry = UnifiedToolRegistry()


async def extract_tool_data_components(current_user: User, category: Optional[str]) -> tuple:
    """Extract tool data components."""
    tool_data = await gather_tool_data(tool_registry, current_user, category)
    return tool_data


async def process_list_tools_request(
    current_user: User, category: Optional[str]
) -> ToolAvailabilityResponse:
    """Process list tools request and return response."""
    available_tools, categories, tools_available = await extract_tool_data_components(current_user, category)
    return build_tool_availability_response(
        available_tools, tools_available, categories, current_user
    )


async def execute_list_tools_logic(current_user: User, category: Optional[str]) -> ToolAvailabilityResponse:
    """Execute list tools business logic."""
    return await process_list_tools_request(current_user, category)


@router.get("", summary="List available tools")
@router.get("/", summary="List available tools", include_in_schema=False)
async def list_tools(
    db: DbDep, category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user)
) -> ToolAvailabilityResponse:
    """Get list of all tools available to the current user"""
    try:
        return await execute_list_tools_logic(current_user, category)
    except Exception as e:
        handle_list_tools_error(e)


async def execute_tool_logic(request: ToolExecutionRequest, current_user: User, db: DbDep) -> Dict[str, Any]:
    """Execute tool business logic."""
    return await process_tool_execution(tool_registry, request, current_user, db)


@router.post("/execute", summary="Execute a tool")
async def execute_tool(
    request: ToolExecutionRequest, db: DbDep,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute a tool with permission checking and usage tracking"""
    try:
        return await execute_tool_logic(request, current_user, db)
    except Exception as e:
        handle_tool_execution_error(e, request.tool_name)


@router.get("/categories", summary="Get tool categories")
async def get_tool_categories() -> List[Dict[str, Any]]:
    """Get list of all tool categories with counts"""
    try:
        return tool_registry.get_tool_categories()
    except Exception as e:
        handle_categories_error(e)


async def execute_permission_check_logic(
    tool_name: str, action: str, current_user: User
) -> Dict[str, Any]:
    """Execute permission check business logic."""
    return await execute_permission_check(
        permission_service, tool_name, action, current_user
    )


@router.get("/permissions/{tool_name}", summary="Check tool permissions")
async def check_tool_permissions(
    tool_name: str, action: str = Query("execute", description="Action to check"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if user has permission to use a specific tool"""
    try:
        return await execute_permission_check_logic(tool_name, action, current_user)
    except Exception as e:
        handle_permission_check_error(e, tool_name)


async def extract_user_plan_components(current_user: User, db: DbDep) -> tuple:
    """Extract user plan data components."""
    plan_data = await gather_user_plan_data(current_user, db)
    return plan_data


async def process_user_plan_request(
    current_user: User, db: DbDep
) -> UserPlanResponse:
    """Process user plan request and return response."""
    current_plan_def, available_upgrades, usage_summary = await extract_user_plan_components(current_user, db)
    return build_user_plan_response(
        current_user, current_plan_def, available_upgrades, usage_summary
    )


@router.get("/user/plan", summary="Get user plan information")
async def get_user_plan(
    db: DbDep, current_user: User = Depends(get_current_user)
) -> UserPlanResponse:
    """Get current user's plan information and upgrade options"""
    try:
        return await process_user_plan_request(current_user, db)
    except Exception as e:
        handle_user_plan_error(e)


@router.post("/migrate-legacy", summary="Migrate from legacy admin system")
async def migrate_legacy_admin(
    db: DbDep, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Migrate user from legacy admin system to new tool-based system"""
    try:
        return process_migration_request(current_user, db)
    except Exception as e:
        handle_migration_error(e)