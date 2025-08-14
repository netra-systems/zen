"""
Unified Tools API - New unified API for all tool operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import DbDep
from app.db.models_postgres import User
from app.auth.auth_dependencies import get_current_user
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
        # Get available tools for user
        available_tools = await tool_registry.list_available_tools(
            user=current_user,
            category=category
        )
        
        # Get tool categories
        categories = [cat["name"] for cat in tool_registry.get_tool_categories()]
        
        # Filter by availability
        tools_available = [tool for tool in available_tools if tool.get("available", False)]
        
        return ToolAvailabilityResponse(
            tools=[
                ToolAvailability(
                    tool_name=tool["name"],
                    category=tool["category"],
                    description=tool["description"],
                    available=tool.get("available", False),
                    required_permissions=tool.get("required_permissions", []),
                    missing_requirements=tool.get("missing_requirements", []),
                    upgrade_required=tool.get("upgrade_path")
                )
                for tool in available_tools
            ],
            user_plan=current_user.plan_tier,
            total_tools=len(available_tools),
            available_tools=len(tools_available),
            categories=categories
        )
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tools")


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
        # Execute tool through registry
        result = await tool_registry.execute_tool(
            tool_name=request.tool_name,
            arguments=request.arguments,
            user=current_user
        )
        
        # Log to database for analytics
        await _log_tool_execution_to_db(result, db)
        
        # Format response
        response = {
            "tool_name": result.tool_name,
            "status": result.status,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": result.created_at.isoformat()
        }
        
        if result.status == "success":
            response["result"] = result.result
        else:
            response["error"] = result.error_message
            
        # Add permission info if denied
        if result.status == "permission_denied" and result.permission_check:
            response["permission_info"] = {
                "required_permissions": result.permission_check.required_permissions,
                "missing_permissions": result.permission_check.missing_permissions,
                "upgrade_path": result.permission_check.upgrade_path,
                "rate_limit_status": result.permission_check.rate_limit_status
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get("/categories", summary="Get tool categories")
async def get_tool_categories() -> List[Dict[str, Any]]:
    """
    Get list of all tool categories with counts
    """
    try:
        return tool_registry.get_tool_categories()
    except Exception as e:
        logger.error(f"Error getting tool categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")


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
        from app.schemas.ToolPermission import ToolExecutionContext
        
        # Create execution context
        context = ToolExecutionContext(
            user_id=str(current_user.id),
            tool_name=tool_name,
            requested_action=action,
            user_plan=current_user.plan_tier,
            user_roles=getattr(current_user, 'roles', []),
            feature_flags=current_user.feature_flags or {},
            is_developer=current_user.is_developer,
        )
        
        # Check permissions
        permission_result = await permission_service.check_tool_permission(context)
        
        return {
            "tool_name": tool_name,
            "allowed": permission_result.allowed,
            "reason": permission_result.reason,
            "required_permissions": permission_result.required_permissions,
            "missing_permissions": permission_result.missing_permissions,
            "upgrade_path": permission_result.upgrade_path,
            "rate_limit_status": permission_result.rate_limit_status
        }
        
    except Exception as e:
        logger.error(f"Error checking permissions for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail="Permission check failed")


@router.get("/user/plan", summary="Get user plan information")
async def get_user_plan(
    db: DbDep,
    current_user: User = Depends(get_current_user)
) -> UserPlanResponse:
    """
    Get current user's plan information and upgrade options
    """
    try:
        # Get current plan definition
        current_plan_def = PLAN_DEFINITIONS.get(PlanTier(current_user.plan_tier))
        
        # Get available upgrades
        available_upgrades = []
        current_tier_index = list(PlanTier).index(PlanTier(current_user.plan_tier))
        for tier in list(PlanTier)[current_tier_index + 1:]:
            if tier != PlanTier.DEVELOPER:  # Developer tier not shown as upgrade option
                available_upgrades.append(tier.value)
        
        # Get usage summary (simplified for now)
        usage_summary = {
            "tools_used_today": await _get_daily_usage_count(current_user.id, db),
            "plan_utilization": "moderate",  # Would calculate from actual usage
            "approaching_limits": []  # Would check against plan limits
        }
        
        return UserPlanResponse(
            current_plan=current_user.plan_tier,
            plan_expires_at=current_user.plan_expires_at.isoformat() if current_user.plan_expires_at else None,
            features=current_plan_def.features.permissions if current_plan_def else [],
            available_upgrades=available_upgrades,
            usage_summary=usage_summary
        )
        
    except Exception as e:
        logger.error(f"Error getting user plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plan information")


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
        # Check if user has admin/developer role in old system
        if current_user.role in ["admin", "developer", "super_admin"]:
            # Grant appropriate plan tier
            if current_user.role == "super_admin":
                new_plan = "enterprise"
                feature_flags = ["*"]
            elif current_user.role == "admin":
                new_plan = "enterprise"
                feature_flags = ["data_operations", "advanced_analytics", "advanced_optimization", "system_management"]
            elif current_user.role == "developer":
                new_plan = "developer"
                feature_flags = ["*"]
            else:
                new_plan = "pro"
                feature_flags = ["data_operations", "advanced_analytics"]
            
            # Update user plan
            current_user.plan_tier = new_plan
            current_user.feature_flags = {flag: True for flag in feature_flags}
            
            db.commit()
            
            return {
                "status": "migrated",
                "old_role": current_user.role,
                "new_plan": new_plan,
                "feature_flags": feature_flags,
                "message": "Successfully migrated to new tool permission system"
            }
        else:
            return {
                "status": "no_migration_needed",
                "current_plan": current_user.plan_tier,
                "message": "User already on new system or no migration needed"
            }
            
    except Exception as e:
        logger.error(f"Error migrating user: {e}")
        raise HTTPException(status_code=500, detail="Migration failed")


# Helper functions

async def _log_tool_execution_to_db(result: ToolExecutionResult, db: AsyncSession):
    """Log tool execution to database for analytics"""
    try:
        from app.db.models_postgres import ToolUsageLog
        
        # Get tool info
        tool = tool_registry.tools.get(result.tool_name)
        
        log_entry = ToolUsageLog(
            user_id=result.user_id,
            tool_name=result.tool_name,
            category=tool.category if tool else "unknown",
            execution_time_ms=result.execution_time_ms,
            status=result.status,
            plan_tier="free",  # Would get from user
            permission_check_result=result.permission_check.dict() if result.permission_check else None
        )
        
        db.add(log_entry)
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error logging tool execution to DB: {e}")


async def _get_daily_usage_count(user_id: str, db: AsyncSession) -> int:
    """Get daily tool usage count for user"""
    try:
        from app.db.models_postgres import ToolUsageLog
        from sqlalchemy import func
        from datetime import date
        
        today = date.today()
        from sqlalchemy import select
        stmt = select(func.count(ToolUsageLog.id)).filter(
            ToolUsageLog.user_id == user_id,
            func.date(ToolUsageLog.created_at) == today
        )
        result = await db.execute(stmt)
        count = result.scalar()
        
        return count or 0
        
    except Exception as e:
        logger.error(f"Error getting daily usage count: {e}")
        return 0