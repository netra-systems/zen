"""MCP Request Handlers

Core business logic for MCP API operations.
Maintains 25-line function limit and single responsibility.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.db.models_postgres import User as UserInDB

from netra_backend.app.routes.mcp.handlers_server import handle_server_info
from netra_backend.app.routes.mcp.handlers_client import handle_client_registration
from netra_backend.app.routes.mcp.handlers_session import (
    handle_session_creation, handle_session_retrieval, handle_session_closure
)
from netra_backend.app.routes.mcp.handlers_tools import handle_tools_listing, handle_tool_call
from netra_backend.app.routes.mcp.handlers_resources import handle_resources_listing, handle_resource_read
from netra_backend.app.routes.mcp.handlers_prompts import handle_prompts_listing, handle_prompt_get
from netra_backend.app.routes.mcp.models import (
    MCPClientCreateRequest, MCPSessionCreateRequest, 
    MCPToolCallRequest, MCPResourceReadRequest, MCPPromptGetRequest
)
from netra_backend.app.routes.mcp.config import get_mcp_config
from netra_backend.app.services.mcp_service import MCPService


class MCPHandlers:
    """Handlers for MCP API operations"""
    
    @staticmethod
    async def get_server_info(
        mcp_service: MCPService, 
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """Get MCP server information"""
        return await handle_server_info(mcp_service, current_user)
    
    @staticmethod
    async def register_client(
        request: MCPClientCreateRequest,
        db: AsyncSession,
        mcp_service: MCPService,
        current_user: UserInDB
    ):
        """Register a new MCP client"""
        return await handle_client_registration(request, db, mcp_service, current_user)
    
    @staticmethod
    async def create_session(
        request: MCPSessionCreateRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Create a new MCP session"""
        return await handle_session_creation(request, mcp_service, current_user)
    
    @staticmethod
    async def get_session(
        session_id: str,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Get session information"""
        return await handle_session_retrieval(session_id, mcp_service, current_user)
    
    @staticmethod
    async def close_session(
        session_id: str,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Close an MCP session"""
        return await handle_session_closure(session_id, mcp_service, current_user)
    
    @staticmethod
    async def list_tools(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP tools"""
        return await handle_tools_listing(category, mcp_service, current_user)
    
    @staticmethod
    async def call_tool(
        request: MCPToolCallRequest,
        db: AsyncSession,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Execute an MCP tool"""
        return await handle_tool_call(request, db, mcp_service, current_user)
    
    @staticmethod
    async def list_resources(
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP resources"""
        return await handle_resources_listing(mcp_service, current_user)
    
    @staticmethod
    async def read_resource(
        request: MCPResourceReadRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Read an MCP resource"""
        return await handle_resource_read(request, mcp_service, current_user)
    
    @staticmethod
    async def list_prompts(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP prompts"""
        return await handle_prompts_listing(category, mcp_service, current_user)
    
    @staticmethod
    async def get_prompt(
        request: MCPPromptGetRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Get an MCP prompt"""
        return await handle_prompt_get(request, mcp_service, current_user)

    @staticmethod
    def get_mcp_config(current_user: Optional[UserInDB]) -> Dict[str, Any]:
        """Get MCP configuration for clients"""
        return get_mcp_config(current_user)


# Standalone tool execution function for direct use  
async def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool directly with given parameters"""
    from netra_backend.app.services.mcp_service import MCPService
    # This is a simplified version for testing
    # In real implementation, would get service from dependency injection
    return {"result": "success", "tool": tool_name, "parameters": parameters}