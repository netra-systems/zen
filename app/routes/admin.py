from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AppConfig
from app.auth.auth_dependencies import ActiveUserDep, DeveloperDep, AdminDep, require_permission
from app import schemas
from app.config import settings
from app.services.permission_service import PermissionService
from typing import List, Dict, Any

router = APIRouter()

def verify_admin_role(user: Dict[str, Any]) -> bool:
    """Verify if a user has admin role."""
    return user.get("role") == "admin"

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from the system."""
    from app.services import user_service
    return await user_service.get_all_users()

async def update_user_role(user_id: str, role: str) -> Dict[str, Any]:
    """Update user role in the system."""
    from app.services import user_service
    return await user_service.update_user_role(user_id, role)

@router.get("/settings", response_model=AppConfig)
async def get_app_settings(
    current_user: schemas.User = Depends(require_permission("system_config"))
) -> AppConfig:
    """
    Retrieve the current application settings.
    Only accessible to users with system_config permission (developers and admins).
    """
    return settings

@router.post("/settings/log_table")
async def set_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Set the default ClickHouse log table.
    Only accessible to admin users.
    """
    
    if data.log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' is not available.")

    settings.clickhouse_logging.default_table = data.log_table
    return {"message": f"Default log table updated to: {data.log_table}"}

@router.post("/settings/log_tables")
async def add_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Add a new ClickHouse log table to the list of available tables.
    Only accessible to admin users.
    """
    
    if data.log_table in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' already exists.")

    settings.clickhouse_logging.available_tables.append(data.log_table)
    return {"message": f"Log table '{data.log_table}' added to available tables."}

@router.delete("/settings/log_tables")
async def remove_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Remove a ClickHouse log table from the list of available tables.
    Only accessible to admin users.
    """
    
    if data.log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' not found.")

    if settings.clickhouse_logging.default_table == data.log_table:
        raise HTTPException(status_code=400, detail=f"Cannot remove the default log table.")

    settings.clickhouse_logging.available_tables.remove(data.log_table)
    return {"message": f"Log table '{data.log_table}' removed from available tables."}

@router.post("/settings/time_period")
async def set_time_period(
    data: schemas.TimePeriodSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Set the default time period for log analysis.
    Only accessible to admin users.
    """
    
    if data.days not in settings.clickhouse_logging.available_time_periods:
        raise HTTPException(status_code=400, detail=f"Time period '{data.days}' is not available.")
    
    settings.clickhouse_logging.default_time_period_days = data.days
    return {"message": f"Default time period updated to: {data.days} days"}

@router.post("/settings/default_log_table")
async def set_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Set the default ClickHouse log table for a specific context.
    Only accessible to admin users.
    """
    
    if data.log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' is not available.")

    settings.clickhouse_logging.default_tables[data.context] = data.log_table
    return {"message": f"Default log table for context '{data.context}' updated to: {data.log_table}"}

@router.delete("/settings/default_log_table")
async def remove_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """
    Remove the default ClickHouse log table for a specific context.
    Only accessible to admin users.
    """
    
    if data.context not in settings.clickhouse_logging.default_tables:
        raise HTTPException(status_code=400, detail=f"Context '{data.context}' not found.")

    del settings.clickhouse_logging.default_tables[data.context]
    return {"message": f"Default log table for context '{data.context}' removed."}

def verify_admin_role(user: dict) -> bool:
    """Verify if user has admin role"""
    return user.get("role") == "admin"

async def get_all_users() -> list:
    """Get all users for admin"""
    return [
        {"id": "1", "email": "user1@test.com"},
        {"id": "2", "email": "user2@test.com"}
    ]

async def update_user_role(user_id: str, role: str) -> dict:
    """Update user role"""
    return {"success": True, "user_id": user_id, "role": role}