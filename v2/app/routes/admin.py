from fastapi import APIRouter, Depends, HTTPException
from app.config import settings, AppConfig
from app.auth.auth_dependencies import ActiveUserWsDep
from app import schemas
from typing import List, Dict

router = APIRouter()

class AdminRoutes:

    @router.get("/settings", response_model=AppConfig)
    async def get_app_settings(self, current_user: schemas.User = Depends(ActiveUserWsDep)) -> AppConfig:
        """
        Retrieve the current application settings.
        Only accessible to authenticated users.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to access settings")
        return settings

    @router.post("/settings/log_table")
    async def set_log_table(self, data: schemas.LogTableSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Set the default ClickHouse log table.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.log_table not in settings.clickhouse_logging.available_tables:
            raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' is not available.")

        settings.clickhouse_logging.default_table = data.log_table
        return {"message": f"Default log table updated to: {data.log_table}"}

    @router.post("/settings/log_tables")
    async def add_log_table(self, data: schemas.LogTableSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Add a new ClickHouse log table to the list of available tables.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.log_table in settings.clickhouse_logging.available_tables:
            raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' already exists.")

        settings.clickhouse_logging.available_tables.append(data.log_table)
        return {"message": f"Log table '{data.log_table}' added to available tables."}

    @router.delete("/settings/log_tables")
    async def remove_log_table(self, data: schemas.LogTableSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Remove a ClickHouse log table from the list of available tables.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.log_table not in settings.clickhouse_logging.available_tables:
            raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' not found.")

        if settings.clickhouse_logging.default_table == data.log_table:
            raise HTTPException(status_code=400, detail=f"Cannot remove the default log table.")

        settings.clickhouse_logging.available_tables.remove(data.log_table)
        return {"message": f"Log table '{data.log_table}' removed from available tables."}

    @router.post("/settings/time_period")
    async def set_time_period(self, data: schemas.TimePeriodSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Set the default time period for log analysis.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.days not in settings.clickhouse_logging.available_time_periods:
            raise HTTPException(status_code=400, detail=f"Time period '{data.days}' is not available.")
        
        settings.clickhouse_logging.default_time_period_days = data.days
        return {"message": f"Default time period updated to: {data.days} days"}

    @router.post("/settings/default_log_table")
    async def set_default_log_table_for_context(self, data: schemas.DefaultLogTableSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Set the default ClickHouse log table for a specific context.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.log_table not in settings.clickhouse_logging.available_tables:
            raise HTTPException(status_code=400, detail=f"Log table '{data.log_table}' is not available.")

        settings.clickhouse_logging.default_tables[data.context] = data.log_table
        return {"message": f"Default log table for context '{data.context}' updated to: {data.log_table}"}

    @router.delete("/settings/default_log_table")
    async def remove_default_log_table_for_context(self, data: schemas.DefaultLogTableSettings, current_user: schemas.User = Depends(ActiveUserWsDep)) -> Dict[str, str]:
        """
        Remove the default ClickHouse log table for a specific context.
        Only accessible to superusers.
        """
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update settings")
        
        if data.context not in settings.clickhouse_logging.default_tables:
            raise HTTPException(status_code=400, detail=f"Context '{data.context}' not found.")

        del settings.clickhouse_logging.default_tables[data.context]
        return {"message": f"Default log table for context '{data.context}' removed."}