"""
MCP Helper Functions

Utility functions for MCP operations.
Maintains 25-line function limit and single responsibility.
"""

import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.routes.unified_tools.schemas import UserInDB
from netra_backend.app.services.mcp_service import MCPService, MCPToolExecution
from netra_backend.app.logging_config import CentralLogger

logger = CentralLogger()


def check_admin_access(current_user: UserInDB) -> None:
    """Check if user has admin access"""
    if "admin" not in getattr(current_user, "roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def extract_tools_from_app(app) -> list:
    """Extract tools from FastMCP app"""
    if not hasattr(app, '_tool_manager'):
        return []
    return [_build_tool_info(name, func) 
            for name, func in app._tool_manager.tools.items()]


def _build_tool_info(tool_name: str, tool_func) -> Dict[str, Any]:
    """Build tool information dictionary"""
    tool_info = {
        "name": tool_name,
        "description": tool_func.__doc__ or "No description available"
    }
    _add_category_if_exists(tool_info, tool_func)
    return tool_info


def _add_category_if_exists(tool_info: Dict[str, Any], tool_func) -> None:
    """Add category to tool info if it exists"""
    if hasattr(tool_func, '__category__'):
        tool_info["category"] = tool_func.__category__


def extract_resources_from_app(app) -> list:
    """Extract resources from FastMCP app"""
    if not hasattr(app, '_resource_manager'):
        return []
    return [_build_resource_info(uri, func) 
            for uri, func in app._resource_manager.resources.items()]


def _build_resource_info(resource_uri: str, resource_func) -> Dict[str, Any]:
    """Build resource information dictionary"""
    return {
        "uri": resource_uri,
        "description": resource_func.__doc__ or "No description available"
    }


def extract_prompts_from_app(app) -> list:
    """Extract prompts from FastMCP app"""
    if not hasattr(app, '_prompt_manager'):
        return []
    return [_build_prompt_info(name, func) 
            for name, func in app._prompt_manager.prompts.items()]


def _build_prompt_info(prompt_name: str, prompt_func) -> Dict[str, Any]:
    """Build prompt information dictionary"""
    prompt_info = {
        "name": prompt_name,
        "description": prompt_func.__doc__ or "No description available"
    }
    _add_category_if_exists(prompt_info, prompt_func)
    return prompt_info


def get_tool_function(server, tool_name: str):
    """Get tool function from server"""
    app = server.get_app()
    if not _has_tool_manager_with_tool(app, tool_name):
        _raise_tool_not_found(tool_name)
    
    return app._tool_manager.tools[tool_name]


def _has_tool_manager_with_tool(app, tool_name: str) -> bool:
    """Check if app has tool manager with specified tool"""
    return (hasattr(app, '_tool_manager') and 
            tool_name in app._tool_manager.tools)


def _raise_tool_not_found(tool_name: str) -> None:
    """Raise HTTPException for tool not found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tool '{tool_name}' not found"
    )


def get_resource_function(server, uri: str):
    """Get resource function from server"""
    app = server.get_app()
    if not _has_resource_manager_with_uri(app, uri):
        _raise_resource_not_found(uri)
    
    return app._resource_manager.resources[uri]


def _has_resource_manager_with_uri(app, uri: str) -> bool:
    """Check if app has resource manager with specified URI"""
    return (hasattr(app, '_resource_manager') and 
            uri in app._resource_manager.resources)


def _raise_resource_not_found(uri: str) -> None:
    """Raise HTTPException for resource not found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Resource '{uri}' not found"
    )


def get_prompt_function(server, prompt_name: str):
    """Get prompt function from server"""
    app = server.get_app()
    if not _has_prompt_manager_with_prompt(app, prompt_name):
        _raise_prompt_not_found(prompt_name)
    
    return app._prompt_manager.prompts[prompt_name]


def _has_prompt_manager_with_prompt(app, prompt_name: str) -> bool:
    """Check if app has prompt manager with specified prompt"""
    return (hasattr(app, '_prompt_manager') and 
            prompt_name in app._prompt_manager.prompts)


def _raise_prompt_not_found(prompt_name: str) -> None:
    """Raise HTTPException for prompt not found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Prompt '{prompt_name}' not found"
    )


async def record_successful_execution(
    request, db, mcp_service, current_user, result, execution_time_ms
) -> None:
    """Record successful tool execution"""
    if not request.session_id:
        return
    await _record_execution(request, db, mcp_service, current_user, result, execution_time_ms)


async def _record_execution(
    request, db, mcp_service, current_user, result, execution_time_ms
) -> None:
    """Record execution in database"""
    execution = _create_success_execution(
        request, current_user, result, execution_time_ms
    )
    await mcp_service.record_tool_execution(db, execution)


def _create_success_execution(request, current_user, result, execution_time_ms):
    """Create successful execution record"""
    return MCPToolExecution(
        session_id=request.session_id,
        client_id=str(current_user.id),
        tool_name=request.tool_name,
        **_build_success_params(request, result, execution_time_ms)
    )


def _build_success_params(request, result, execution_time_ms) -> Dict[str, Any]:
    """Build parameters for successful execution"""
    return {
        "input_params": request.arguments,
        "output_result": {"result": result},
        "execution_time_ms": execution_time_ms,
        "status": "success"
    }


async def record_failed_execution(
    request, db, mcp_service, current_user, error, start_time
) -> None:
    """Record failed tool execution"""
    if not request.session_id:
        return
    execution = _create_failed_execution(request, current_user, error, start_time)
    await mcp_service.record_tool_execution(db, execution)


def _create_failed_execution(request, current_user, error, start_time):
    """Create failed execution record"""
    execution_time_ms = int((time.time() - start_time) * 1000)
    return MCPToolExecution(
        session_id=request.session_id,
        client_id=str(current_user.id),
        tool_name=request.tool_name,
        **_build_failed_params(request, error, execution_time_ms))


def _build_failed_params(request, error, execution_time_ms) -> Dict[str, Any]:
    """Build parameters for failed execution"""
    return {
        "input_params": request.arguments,
        "execution_time_ms": execution_time_ms,
        "status": "error",
        "error": str(error)
    }