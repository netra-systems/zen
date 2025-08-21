from fastapi import APIRouter, Depends, HTTPException
from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.auth_integration.auth import ActiveUserDep, DeveloperDep, AdminDep, require_permission
from netra_backend.app import schemas
from netra_backend.app.config import settings
from netra_backend.app.services.permission_service import PermissionService
from typing import List, Dict, Any

router = APIRouter()

def verify_admin_role(user: Dict[str, Any]) -> bool:
    """Verify if a user has admin role."""
    return user.get("role") == "admin"

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from the system."""
    from netra_backend.app.core.configuration.services import user_service
    return await user_service.get_all_users()

async def update_user_role(user_id: str, role: str) -> Dict[str, Any]:
    """Update user role in the system."""
    from netra_backend.app.core.configuration.services import user_service
    return await user_service.update_user_role(user_id, role)

async def get_audit_logs(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get recent audit logs with pagination."""
    from netra_backend.app.core.configuration.services import audit_service
    return await audit_service.get_recent_logs(limit, offset)

@router.get("/settings", response_model=AppConfig)
async def get_app_settings(
    current_user: schemas.User = Depends(require_permission("system_config"))
) -> AppConfig:
    """
    Retrieve the current application settings.
    Only accessible to users with system_config permission (developers and admins).
    """
    return settings

def _validate_table_exists(log_table: str) -> None:
    """Validate table exists in available tables."""
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' is not available.")

def _update_default_table(log_table: str) -> None:
    """Update default table setting."""
    settings.clickhouse_logging.default_table = log_table

def _build_table_response(log_table: str, action: str) -> Dict[str, str]:
    """Build table operation response."""
    return {"message": f"Log table '{log_table}' {action}."}

@router.post("/settings/log_table")
async def set_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Set the default ClickHouse log table."""
    _validate_table_exists(data.log_table)
    _update_default_table(data.log_table)
    return {"message": f"Default log table updated to: {data.log_table}"}

def _validate_table_not_exists(log_table: str) -> None:
    """Validate table does not already exist."""
    if log_table in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' already exists.")

def _add_table_to_available(log_table: str) -> None:
    """Add table to available tables list."""
    settings.clickhouse_logging.available_tables.append(log_table)

@router.post("/settings/log_tables")
async def add_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Add a new ClickHouse log table to the list of available tables."""
    _validate_table_not_exists(data.log_table)
    _add_table_to_available(data.log_table)
    return _build_table_response(data.log_table, "added to available tables")

def _validate_table_removal(log_table: str) -> None:
    """Validate table can be removed."""
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' not found.")
    if settings.clickhouse_logging.default_table == log_table:
        raise HTTPException(status_code=400, detail="Cannot remove the default log table.")

def _remove_table_from_available(log_table: str) -> None:
    """Remove table from available tables list."""
    settings.clickhouse_logging.available_tables.remove(log_table)

@router.delete("/settings/log_tables")
async def remove_log_table(
    data: schemas.LogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Remove a ClickHouse log table from the list of available tables."""
    _validate_table_removal(data.log_table)
    _remove_table_from_available(data.log_table)
    return _build_table_response(data.log_table, "removed from available tables")

def _validate_time_period(days: int) -> None:
    """Validate time period is available."""
    if days not in settings.clickhouse_logging.available_time_periods:
        raise HTTPException(status_code=400, detail=f"Time period '{days}' is not available.")

def _update_default_time_period(days: int) -> None:
    """Update default time period setting."""
    settings.clickhouse_logging.default_time_period_days = days

@router.post("/settings/time_period")
async def set_time_period(
    data: schemas.TimePeriodSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Set the default time period for log analysis."""
    _validate_time_period(data.days)
    _update_default_time_period(data.days)
    return {"message": f"Default time period updated to: {data.days} days"}

def _set_context_default_table(context: str, log_table: str) -> None:
    """Set default table for specific context."""
    settings.clickhouse_logging.default_tables[context] = log_table

@router.post("/settings/default_log_table")
async def set_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Set the default ClickHouse log table for a specific context."""
    _validate_table_exists(data.log_table)
    _set_context_default_table(data.context, data.log_table)
    return {"message": f"Default log table for context '{data.context}' updated to: {data.log_table}"}

def _validate_context_exists(context: str) -> None:
    """Validate context exists in default tables."""
    if context not in settings.clickhouse_logging.default_tables:
        raise HTTPException(status_code=400, detail=f"Context '{context}' not found.")

def _remove_context_default_table(context: str) -> None:
    """Remove default table for context."""
    del settings.clickhouse_logging.default_tables[context]

@router.delete("/settings/default_log_table")
async def remove_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    current_user: schemas.User = AdminDep
) -> Dict[str, str]:
    """Remove the default ClickHouse log table for a specific context."""
    _validate_context_exists(data.context)
    _remove_context_default_table(data.context)
    return {"message": f"Default log table for context '{data.context}' removed."}

