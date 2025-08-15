"""
MCP Utility Functions

Utility functions for MCP handlers.
Maintains 8-line function limit and single responsibility.
"""

from typing import Dict, Any
from fastapi import HTTPException, status
from app.logging_config import CentralLogger

logger = CentralLogger()


def handle_server_info_error(error: Exception) -> None:
    """Handle server info retrieval error"""
    logger.error(f"Error getting server info: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )


def handle_client_registration_error(error: Exception) -> None:
    """Handle client registration error"""
    logger.error(f"Error registering client: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )


def build_session_response(session_id: str, status_text: str) -> Dict[str, Any]:
    """Build session operation response"""
    return {
        "session_id": session_id,
        "status": status_text
    }


def handle_session_error(error: Exception, operation: str) -> None:
    """Handle session operation error"""
    logger.error(f"Error {operation} session: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )


def raise_session_not_found() -> None:
    """Raise session not found error"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


def filter_by_category(items: list, category: str) -> list:
    """Filter items by category"""
    return [item for item in items if item.get("category") == category]


def build_list_response(items: list, item_type: str) -> Dict[str, Any]:
    """Build list response with items and count"""
    return {
        item_type: items,
        "count": len(items)
    }


def handle_list_error(error: Exception, item_type: str) -> None:
    """Handle list operation error"""
    logger.error(f"Error listing {item_type}: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )


def calculate_execution_time(start_time: float) -> int:
    """Calculate execution time in milliseconds"""
    import time
    return int((time.time() - start_time) * 1000)


def build_tool_result(tool_name: str, result: Any) -> Dict[str, Any]:
    """Build tool execution result"""
    return {
        "tool": tool_name,
        "result": result,
        "status": "success"
    }


def build_resource_result(uri: str, content: Any) -> Dict[str, Any]:
    """Build resource read result"""
    return {
        "uri": uri,
        "content": content,
        "status": "success"
    }


def handle_resource_error(error: Exception) -> None:
    """Handle resource operation error"""
    logger.error(f"Error reading resource: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )


def build_prompt_result(prompt_name: str, messages: Any) -> Dict[str, Any]:
    """Build prompt execution result"""
    return {
        "prompt": prompt_name,
        "messages": messages,
        "status": "success"
    }


def handle_prompt_error(error: Exception) -> None:
    """Handle prompt operation error"""
    logger.error(f"Error getting prompt: {error}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )