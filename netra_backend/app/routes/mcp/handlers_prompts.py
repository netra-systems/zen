"""MCP prompts handlers."""
from typing import Dict, Any, Optional
from fastapi import HTTPException

from netra_backend.app.routes.unified_tools.schemas import UserInDB
from netra_backend.app.services.mcp_service import MCPService
from netra_backend.app.routes.mcp.models import MCPPromptGetRequest
from netra_backend.app.routes.mcp.helpers import extract_prompts_from_app, get_prompt_function
from netra_backend.app.routes.mcp.utils import (
    filter_by_category, build_list_response, handle_list_error,
    build_prompt_result, handle_prompt_error
)


async def handle_prompts_listing(
    category: Optional[str],
    mcp_service: MCPService,
    current_user: Optional[UserInDB]
) -> Dict[str, Any]:
    """List available MCP prompts"""
    try:
        return build_prompts_response(mcp_service, category)
    except Exception as e:
        return handle_list_error(e, "prompts")


async def handle_prompt_get(
    request: MCPPromptGetRequest,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Get an MCP prompt"""
    try:
        return await get_mcp_prompt(request, mcp_service)
    except HTTPException:
        raise
    except Exception as e:
        return handle_prompt_error(e)


def build_prompts_response(mcp_service: MCPService, category: Optional[str]) -> Dict[str, Any]:
    """Build prompts list response"""
    app = mcp_service.get_fastmcp_app()
    prompts = extract_prompts_from_app(app)
    if category:
        prompts = filter_by_category(prompts, category)
    return build_list_response(prompts, "prompts")


async def get_mcp_prompt(request: MCPPromptGetRequest, mcp_service: MCPService) -> Dict[str, Any]:
    """Get MCP prompt by name"""
    server = mcp_service.get_mcp_server()
    prompt_func = get_prompt_function(server, request.prompt_name)
    result = await prompt_func(**request.arguments)
    return build_prompt_result(request.prompt_name, result)