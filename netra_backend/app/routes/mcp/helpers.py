"""
MCP Helper Functions

Utility functions for MCP operations.
Maintains 25-line function limit and single responsibility.
"""

import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User as UserInDB
from netra_backend.app.logging_config import CentralLogger
from netra_backend.app.services.mcp_service import MCPService, MCPToolExecution

logger = CentralLogger()


def check_admin_access(current_user: UserInDB) -> None:
    """Check if user has admin access"""
    if "admin" not in getattr(current_user, "roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


async def extract_tools_from_app(app) -> list:
    """Extract tools from FastMCP app"""
    if not hasattr(app, 'get_tools'):
        return []
    tools = await app.get_tools()
    return [_build_tool_info(name, tool) 
            for name, tool in tools.items()]


def _build_tool_info(tool_name: str, tool_data) -> Dict[str, Any]:
    """Build tool information dictionary"""
    # Handle both function and dict tool data
    if hasattr(tool_data, '__doc__'):
        description = tool_data.__doc__ or "No description available"
    elif isinstance(tool_data, dict):
        description = tool_data.get('description', "No description available")
    else:
        description = "No description available"
    
    tool_info = {
        "name": tool_name,
        "description": description
    }
    _add_category_if_exists(tool_info, tool_data)
    return tool_info


def _add_category_if_exists(tool_info: Dict[str, Any], tool_data) -> None:
    """Add category to tool info if it exists"""
    if hasattr(tool_data, '__category__'):
        tool_info["category"] = tool_data.__category__
    elif isinstance(tool_data, dict) and 'category' in tool_data:
        tool_info["category"] = tool_data['category']


async def extract_resources_from_app(app) -> list:
    """Extract resources from FastMCP app"""
    if not hasattr(app, 'get_resources'):
        return []
    resources = await app.get_resources()
    return [_build_resource_info(uri, resource) 
            for uri, resource in resources.items()]


def _build_resource_info(resource_uri: str, resource_data) -> Dict[str, Any]:
    """Build resource information dictionary"""
    # Handle both function and dict resource data
    if hasattr(resource_data, '__doc__'):
        description = resource_data.__doc__ or "No description available"
    elif isinstance(resource_data, dict):
        description = resource_data.get('description', "No description available")
    else:
        description = "No description available"
    
    return {
        "uri": resource_uri,
        "description": description
    }


async def extract_prompts_from_app(app) -> list:
    """Extract prompts from FastMCP app"""
    if not hasattr(app, 'get_prompts'):
        return []
    prompts = await app.get_prompts()
    return [_build_prompt_info(name, prompt) 
            for name, prompt in prompts.items()]


def _build_prompt_info(prompt_name: str, prompt_data) -> Dict[str, Any]:
    """Build prompt information dictionary"""
    # Handle both function and dict prompt data  
    if hasattr(prompt_data, '__doc__'):
        description = prompt_data.__doc__ or "No description available"
    elif isinstance(prompt_data, dict):
        description = prompt_data.get('description', "No description available")
    else:
        description = "No description available"
    
    prompt_info = {
        "name": prompt_name,
        "description": description
    }
    _add_category_if_exists(prompt_info, prompt_data)
    return prompt_info


async def get_tool_function(server, tool_name: str):
    """Get tool function from server"""
    app = server.get_app()
    if not hasattr(app, 'get_tool'):
        _raise_tool_not_found(tool_name)
    
    tool = await app.get_tool(tool_name)
    if tool is None:
        _raise_tool_not_found(tool_name)
    
    return tool


async def _has_tool_manager_with_tool(app, tool_name: str) -> bool:
    """Check if app has tool manager with specified tool"""
    if not hasattr(app, 'get_tool'):
        return False
    return await app.get_tool(tool_name) is not None


def _raise_tool_not_found(tool_name: str) -> None:
    """Raise HTTPException for tool not found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tool '{tool_name}' not found"
    )


async def get_resource_function(server, uri: str):
    """Get resource function from server"""
    app = server.get_app()
    if not hasattr(app, 'get_resource'):
        _raise_resource_not_found(uri)
    
    resource = await app.get_resource(uri)
    if resource is None:
        _raise_resource_not_found(uri)
    
    return resource


async def _has_resource_manager_with_uri(app, uri: str) -> bool:
    """Check if app has resource manager with specified URI"""
    if not hasattr(app, 'get_resource'):
        return False
    return await app.get_resource(uri) is not None


def _raise_resource_not_found(uri: str) -> None:
    """Raise HTTPException for resource not found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Resource '{uri}' not found"
    )


async def get_prompt_function(server, prompt_name: str):
    """Get prompt function from server"""
    app = server.get_app()
    if not hasattr(app, 'get_prompt'):
        _raise_prompt_not_found(prompt_name)
    
    prompt = await app.get_prompt(prompt_name)
    if prompt is None:
        _raise_prompt_not_found(prompt_name)
    
    return prompt


async def _has_prompt_manager_with_prompt(app, prompt_name: str) -> bool:
    """Check if app has prompt manager with specified prompt"""
    if not hasattr(app, 'get_prompt'):
        return False
    return await app.get_prompt(prompt_name) is not None


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