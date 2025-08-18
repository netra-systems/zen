"""
Database Utilities for Unified Tools API
"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import date
from app.services.unified_tool_registry import ToolExecutionResult
from app.db.models_postgres import ToolUsageLog
from app.logging_config import central_logger

logger = central_logger


def get_tool_info_for_logging(tool_registry, result: ToolExecutionResult) -> Any:
    """Get tool info from registry for logging."""
    return tool_registry.tools.get(result.tool_name)


def extract_tool_category(tool: Any) -> str:
    """Extract category from tool or return default."""
    return tool.category if tool else "unknown"


def extract_permission_result(result: ToolExecutionResult) -> Any:
    """Extract permission check result or return None."""
    return result.permission_check.dict() if result.permission_check else None


def build_log_entry_params(result: ToolExecutionResult, tool: Any) -> dict:
    """Build parameters for tool usage log entry."""
    return {
        "user_id": result.user_id, "tool_name": result.tool_name,
        "category": extract_tool_category(tool), "execution_time_ms": result.execution_time_ms,
        "status": result.status, "plan_tier": "free",
        "permission_check_result": extract_permission_result(result)
    }


def create_tool_usage_log_entry(result: ToolExecutionResult, tool: Any) -> ToolUsageLog:
    """Create tool usage log entry."""
    params = build_log_entry_params(result, tool)
    return ToolUsageLog(**params)


async def save_log_entry_to_db(log_entry: ToolUsageLog, db: AsyncSession) -> None:
    """Save log entry to database."""
    db.add(log_entry)
    await db.commit()


def handle_logging_error(e: Exception) -> None:
    """Handle logging error."""
    logger.error(f"Error logging tool execution to DB: {e}")


async def process_tool_logging(tool_registry, result: ToolExecutionResult, db: AsyncSession) -> None:
    """Process tool execution logging workflow."""
    tool = get_tool_info_for_logging(tool_registry, result)
    log_entry = create_tool_usage_log_entry(result, tool)
    await save_log_entry_to_db(log_entry, db)


async def log_tool_execution_to_db(
    tool_registry, result: ToolExecutionResult, db: AsyncSession
) -> None:
    """Log tool execution to database for analytics"""
    try:
        await process_tool_logging(tool_registry, result, db)
    except Exception as e:
        handle_logging_error(e)


def build_daily_usage_query(user_id: str) -> Any:
    """Build daily usage count query."""
    today = date.today()
    return select(func.count(ToolUsageLog.id)).filter(
        ToolUsageLog.user_id == user_id,
        func.date(ToolUsageLog.created_at) == today
    )


async def execute_usage_count_query(stmt: Any, db: AsyncSession) -> int:
    """Execute usage count query and return result."""
    result = await db.execute(stmt)
    count = result.scalar()
    return count or 0


def handle_usage_count_error(e: Exception) -> int:
    """Handle usage count query error."""
    logger.error(f"Error getting daily usage count: {e}")
    return 0


async def get_daily_usage_count(user_id: str, db: AsyncSession) -> int:
    """Get daily tool usage count for user"""
    try:
        stmt = build_daily_usage_query(user_id)
        return await execute_usage_count_query(stmt, db)
    except Exception as e:
        return handle_usage_count_error(e)