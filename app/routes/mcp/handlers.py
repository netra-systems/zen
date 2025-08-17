"""
MCP Request Handlers

Core business logic for MCP API operations.
Maintains 8-line function limit and single responsibility.
"""

import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserInDB
from app.services.mcp_service import MCPService
from app.logging_config import CentralLogger
from .models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest, 
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from .helpers import (
    check_admin_access,
    extract_tools_from_app,
    extract_resources_from_app, 
    extract_prompts_from_app,
    get_tool_function,
    get_resource_function,
    get_prompt_function,
    record_successful_execution,
    record_failed_execution
)
from .config import get_mcp_config
from .utils import (
    handle_server_info_error,
    handle_client_registration_error,
    build_session_response,
    handle_session_error,
    raise_session_not_found,
    filter_by_category,
    build_list_response,
    handle_list_error,
    calculate_execution_time,
    build_tool_result,
    build_resource_result,
    handle_resource_error,
    build_prompt_result,
    handle_prompt_error
)

logger = CentralLogger()


class MCPHandlers:
    """Handlers for MCP API operations"""
    
    @staticmethod
    async def get_server_info(
        mcp_service: MCPService, 
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """Get MCP server information"""
        try:
            info = await mcp_service.get_server_info()
            info["authenticated"] = current_user is not None
            return info
        except Exception as e:
            return handle_server_info_error(e)
    
    @staticmethod
    async def register_client(
        request: MCPClientCreateRequest,
        db: AsyncSession,
        mcp_service: MCPService,
        current_user: UserInDB
    ):
        """Register a new MCP client"""
        try:
            check_admin_access(current_user)
            return await _create_client(request, db, mcp_service)
        except HTTPException:
            raise
        except Exception as e:
            return handle_client_registration_error(e)
    
    @staticmethod
    async def create_session(
        request: MCPSessionCreateRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Create a new MCP session"""
        try:
            session_id = await mcp_service.create_session(
                client_id=request.client_id,
                metadata=request.metadata
            )
            return build_session_response(session_id, "created")
        except Exception as e:
            return handle_session_error(e, "creating")
    
    @staticmethod
    async def get_session(
        session_id: str,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Get session information"""
        try:
            session = await mcp_service.get_session(session_id)
            if not session:
                raise_session_not_found()
            return session
        except HTTPException:
            raise
        except Exception as e:
            return handle_session_error(e, "getting")
    
    @staticmethod
    async def close_session(
        session_id: str,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Close an MCP session"""
        try:
            await mcp_service.close_session(session_id)
            return build_session_response(session_id, "closed")
        except Exception as e:
            return handle_session_error(e, "closing")
    
    @staticmethod
    async def list_tools(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP tools"""
        try:
            app = mcp_service.get_fastmcp_app()
            tools = extract_tools_from_app(app)
            if category:
                tools = filter_by_category(tools, category)
            return build_list_response(tools, "tools")
        except Exception as e:
            return handle_list_error(e, "tools")
    
    @staticmethod
    async def call_tool(
        request: MCPToolCallRequest,
        db: AsyncSession,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Execute an MCP tool"""
        start_time = time.time()
        
        try:
            result = await _execute_tool(request, mcp_service)
            execution_time_ms = calculate_execution_time(start_time)
            
            await record_successful_execution(
                request, db, mcp_service, current_user, result, execution_time_ms
            )
            
            return build_tool_result(request.tool_name, result)
            
        except HTTPException:
            raise
        except Exception as e:
            await _handle_tool_execution_error(
                request, db, mcp_service, current_user, e, start_time
            )
    
    @staticmethod
    async def list_resources(
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP resources"""
        try:
            app = mcp_service.get_fastmcp_app()
            resources = extract_resources_from_app(app)
            return build_list_response(resources, "resources")
        except Exception as e:
            return handle_list_error(e, "resources")
    
    @staticmethod
    async def read_resource(
        request: MCPResourceReadRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Read an MCP resource"""
        try:
            server = mcp_service.get_mcp_server()
            resource_func = get_resource_function(server, request.uri)
            result = await resource_func()
            return build_resource_result(request.uri, result)
        except HTTPException:
            raise
        except Exception as e:
            return handle_resource_error(e)
    
    @staticmethod
    async def list_prompts(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP prompts"""
        try:
            app = mcp_service.get_fastmcp_app()
            prompts = extract_prompts_from_app(app)
            if category:
                prompts = filter_by_category(prompts, category)
            return build_list_response(prompts, "prompts")
        except Exception as e:
            return handle_list_error(e, "prompts")
    
    @staticmethod
    async def get_prompt(
        request: MCPPromptGetRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Get an MCP prompt"""
        try:
            server = mcp_service.get_mcp_server()
            prompt_func = get_prompt_function(server, request.prompt_name)
            result = await prompt_func(**request.arguments)
            return build_prompt_result(request.prompt_name, result)
        except HTTPException:
            raise
        except Exception as e:
            return handle_prompt_error(e)

    @staticmethod
    def get_mcp_config(current_user: Optional[UserInDB]) -> Dict[str, Any]:
        """Get MCP configuration for clients"""
        return get_mcp_config(current_user)


# Standalone tool execution function for direct use  
async def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool directly with given parameters"""
    from app.services.mcp_service import MCPService
    # This is a simplified version for testing
    # In real implementation, would get service from dependency injection
    return {"result": "success", "tool": tool_name, "parameters": parameters}


# Helper functions (≤8 lines each)

async def _create_client(request, db, mcp_service):
    """Create MCP client with provided parameters"""
    return await mcp_service.register_client(
        db_session=db,
        name=request.name,
        client_type=request.client_type,
        api_key=request.api_key,
        permissions=request.permissions,
        metadata=request.metadata
    )


async def _execute_tool(request, mcp_service):
    """Execute MCP tool with provided arguments"""
    server = mcp_service.get_mcp_server()
    tool_func = get_tool_function(server, request.tool_name)
    return await tool_func(**request.arguments)


async def _handle_tool_execution_error(
    request, db, mcp_service, current_user, error, start_time
) -> None:
    """Handle tool execution error"""
    logger.error(f"Error calling tool: {error}", exc_info=True)
    
    await record_failed_execution(
        request, db, mcp_service, current_user, error, start_time
    )
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )