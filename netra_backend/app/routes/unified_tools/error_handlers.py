"""
Error Handling Utilities for Unified Tools API
"""
from fastapi import HTTPException

from netra_backend.app.logging_config import central_logger

logger = central_logger


def handle_list_tools_error(e: Exception) -> None:
    """Handle list tools error."""
    logger.error(f"Error listing tools: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to list tools")


def handle_tool_execution_error(e: Exception, tool_name: str) -> None:
    """Handle tool execution error."""
    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


def handle_categories_error(e: Exception) -> None:
    """Handle categories retrieval error."""
    logger.error(f"Error getting tool categories: {e}")
    raise HTTPException(status_code=500, detail="Failed to get categories")


def handle_permission_check_error(e: Exception, tool_name: str) -> None:
    """Handle permission check error."""
    logger.error(f"Error checking permissions for {tool_name}: {e}")
    raise HTTPException(status_code=500, detail="Permission check failed")


def handle_user_plan_error(e: Exception) -> None:
    """Handle user plan retrieval error."""
    logger.error(f"Error getting user plan: {e}")
    raise HTTPException(status_code=500, detail="Failed to get plan information")


def handle_migration_error(e: Exception) -> None:
    """Handle migration error."""
    logger.error(f"Error migrating user: {e}")
    raise HTTPException(status_code=500, detail="Migration failed")