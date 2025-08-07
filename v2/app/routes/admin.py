from fastapi import APIRouter, Depends, HTTPException
from app.config import settings, AppConfig
from app.auth.auth_dependencies import ActiveUserWsDep
from app.db.models_postgres import User
from typing import List, Dict

router = APIRouter()

@router.get("/settings", response_model=AppConfig)
async def get_app_settings(current_user: User = Depends(ActiveUserWsDep)):
    """
    Retrieve the current application settings.
    Only accessible to authenticated users.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to access settings")
    return settings

@router.post("/settings/log_table")
async def set_log_table(log_table: str, current_user: User = Depends(ActiveUserWsDep)):
    """
    Set the default ClickHouse log table.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' is not available.")

    settings.clickhouse_logging.default_table = log_table
    return {"message": f"Default log table updated to: {log_table}"}

@router.post("/settings/log_tables")
async def add_log_table(log_table: str, current_user: User = Depends(ActiveUserWsDep)):
    """
    Add a new ClickHouse log table to the list of available tables.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if log_table in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' already exists.")

    settings.clickhouse_logging.available_tables.append(log_table)
    return {"message": f"Log table '{log_table}' added to available tables."}

@router.delete("/settings/log_tables")
async def remove_log_table(log_table: str, current_user: User = Depends(ActiveUserWsDep)):
    """
    Remove a ClickHouse log table from the list of available tables.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' not found.")

    if settings.clickhouse_logging.default_table == log_table:
        raise HTTPException(status_code=400, detail=f"Cannot remove the default log table.")

    settings.clickhouse_logging.available_tables.remove(log_table)
    return {"message": f"Log table '{log_table}' removed from available tables."}

@router.post("/settings/time_period")
async def set_time_period(days: int, current_user: User = Depends(ActiveUserWsDep)):
    """
    Set the default time period for log analysis.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if days not in settings.clickhouse_logging.available_time_periods:
        raise HTTPException(status_code=400, detail=f"Time period '{days}' is not available.")
    
    settings.clickhouse_logging.default_time_period_days = days
    return {"message": f"Default time period updated to: {days} days"}

@router.post("/settings/default_log_table")
async def set_default_log_table_for_context(context: str, log_table: str, current_user: User = Depends(ActiveUserWsDep)):
    """
    Set the default ClickHouse log table for a specific context.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' is not available.")

    settings.clickhouse_logging.default_tables[context] = log_table
    return {"message": f"Default log table for context '{context}' updated to: {log_table}"}

@router.delete("/settings/default_log_table")
async def remove_default_log_table_for_context(context: str, current_user: User = Depends(ActiveUserWsDep)):
    """
    Remove the default ClickHouse log table for a specific context.
    Only accessible to superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update settings")
    
    if context not in settings.clickhouse_logging.default_tables:
        raise HTTPException(status_code=400, detail=f"Context '{context}' not found.")

    del settings.clickhouse_logging.default_tables[context]
    return {"message": f"Default log table for context '{context}' removed."}