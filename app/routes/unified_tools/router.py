"""
Unified Tools API Router - Route definitions only
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any, Optional
from app.dependencies import DbDep
from app.db.models_postgres import User
from app.auth_integration.auth import get_current_user
from app.services.unified_tool_registry import UnifiedToolRegistry
from app.services.tool_permission_service import ToolPermissionService
import redis
import os

from .schemas import ToolExecutionRequest, ToolAvailabilityResponse, UserPlanResponse
from .tool_listing import gather_tool_data, build_tool_availability_response
from .tool_execution import process_tool_execution
from .permissions import execute_permission_check
from .user_plan import gather_user_plan_data, build_user_plan_response
from .migration import process_migration_request
from .error_handlers import (
    handle_list_tools_error, handle_tool_execution_error, handle_categories_error,
    handle_permission_check_error, handle_user_plan_error, handle_migration_error
)

router = APIRouter()

# Initialize services (in production, these would be dependency injected)
redis_client = None
try:
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
except Exception:
    pass

permission_service = ToolPermissionService(redis_client)
tool_registry = UnifiedToolRegistry(permission_service=permission_service)


@router.get("/", summary="List available tools")
async def list_tools(
    db: DbDep,
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user)
) -> ToolAvailabilityResponse:
    """Get list of all tools available to the current user"""
    try:
        available_tools, categories, tools_available = await gather_tool_data(
            tool_registry, current_user, category
        )
        return build_tool_availability_response(
            available_tools, tools_available, categories, current_user
        )
    except Exception as e:
        handle_list_tools_error(e)


@router.post("/execute", summary="Execute a tool")
async def execute_tool(
    request: ToolExecutionRequest,
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute a tool with permission checking and usage tracking"""
    try:
        return await process_tool_execution(tool_registry, request, current_user, db)
    except Exception as e:
        handle_tool_execution_error(e, request.tool_name)


@router.get("/categories", summary="Get tool categories")
async def get_tool_categories() -> List[Dict[str, Any]]:
    """Get list of all tool categories with counts"""
    try:
        return tool_registry.get_tool_categories()
    except Exception as e:
        handle_categories_error(e)


@router.get("/permissions/{tool_name}", summary="Check tool permissions")
async def check_tool_permissions(
    tool_name: str,
    action: str = Query("execute", description="Action to check"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if user has permission to use a specific tool"""
    try:
        return await execute_permission_check(
            permission_service, tool_name, action, current_user
        )
    except Exception as e:
        handle_permission_check_error(e, tool_name)


@router.get("/user/plan", summary="Get user plan information")
async def get_user_plan(
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> UserPlanResponse:
    """Get current user's plan information and upgrade options"""
    try:
        current_plan_def, available_upgrades, usage_summary = await gather_user_plan_data(
            current_user, db
        )
        return build_user_plan_response(
            current_user, current_plan_def, available_upgrades, usage_summary
        )
    except Exception as e:
        handle_user_plan_error(e)


@router.post("/migrate-legacy", summary="Migrate from legacy admin system")
async def migrate_legacy_admin(
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Migrate user from legacy admin system to new tool-based system"""
    try:
        return process_migration_request(current_user, db)
    except Exception as e:
        handle_migration_error(e)