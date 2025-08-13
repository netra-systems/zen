"""
MCP Request Handlers

Core business logic for MCP API operations.
Maintains 8-line function limit and single responsibility.
"""

import time
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserInDB
from app.services.mcp_service import MCPService, MCPToolExecution
from app.logging_config import CentralLogger
from .models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest, 
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
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
            logger.error(f"Error getting server info: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def register_client(
        request: MCPClientCreateRequest,
        db: AsyncSession,
        mcp_service: MCPService,
        current_user: UserInDB
    ):
        """Register a new MCP client"""
        try:
            MCPHandlers._check_admin_access(current_user)
            
            client = await mcp_service.register_client(
                db_session=db,
                name=request.name,
                client_type=request.client_type,
                api_key=request.api_key,
                permissions=request.permissions,
                metadata=request.metadata
            )
            return client
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering client: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
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
            return {
                "session_id": session_id,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            return session
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def close_session(
        session_id: str,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Close an MCP session"""
        try:
            await mcp_service.close_session(session_id)
            return {
                "session_id": session_id,
                "status": "closed"
            }
        except Exception as e:
            logger.error(f"Error closing session: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def list_tools(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP tools"""
        try:
            app = mcp_service.get_fastmcp_app()
            tools = MCPHandlers._extract_tools_from_app(app)
            
            if category:
                tools = [t for t in tools if t.get("category") == category]
            
            return {
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            logger.error(f"Error listing tools: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
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
            server = mcp_service.get_mcp_server()
            tool_func = MCPHandlers._get_tool_function(server, request.tool_name)
            
            result = await tool_func(**request.arguments)
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            await MCPHandlers._record_successful_execution(
                request, db, mcp_service, current_user, result, execution_time_ms
            )
            
            return {
                "tool": request.tool_name,
                "result": result,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calling tool: {e}", exc_info=True)
            
            await MCPHandlers._record_failed_execution(
                request, db, mcp_service, current_user, e, start_time
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def list_resources(
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP resources"""
        try:
            app = mcp_service.get_fastmcp_app()
            resources = MCPHandlers._extract_resources_from_app(app)
            
            return {
                "resources": resources,
                "count": len(resources)
            }
        except Exception as e:
            logger.error(f"Error listing resources: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def read_resource(
        request: MCPResourceReadRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Read an MCP resource"""
        try:
            server = mcp_service.get_mcp_server()
            resource_func = MCPHandlers._get_resource_function(server, request.uri)
            
            result = await resource_func()
            
            return {
                "uri": request.uri,
                "content": result,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading resource: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def list_prompts(
        category: Optional[str],
        mcp_service: MCPService,
        current_user: Optional[UserInDB]
    ) -> Dict[str, Any]:
        """List available MCP prompts"""
        try:
            app = mcp_service.get_fastmcp_app()
            prompts = MCPHandlers._extract_prompts_from_app(app)
            
            if category:
                prompts = [p for p in prompts if p.get("category") == category]
            
            return {
                "prompts": prompts,
                "count": len(prompts)
            }
        except Exception as e:
            logger.error(f"Error listing prompts: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    async def get_prompt(
        request: MCPPromptGetRequest,
        mcp_service: MCPService,
        current_user: UserInDB
    ) -> Dict[str, Any]:
        """Get an MCP prompt"""
        try:
            server = mcp_service.get_mcp_server()
            prompt_func = MCPHandlers._get_prompt_function(server, request.prompt_name)
            
            result = await prompt_func(**request.arguments)
            
            return {
                "prompt": request.prompt_name,
                "messages": result,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting prompt: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @staticmethod
    def get_mcp_config(user: Optional[UserInDB]) -> Dict[str, Any]:
        """Get MCP configuration for clients"""
        base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
        
        return {
            "claude": MCPHandlers._get_claude_config(base_url),
            "cursor": MCPHandlers._get_cursor_config(),
            "http": MCPHandlers._get_http_config(base_url),
            "websocket": MCPHandlers._get_websocket_config(base_url)
        }
    
    @staticmethod
    def _check_admin_access(current_user: UserInDB) -> None:
        """Check if user has admin access"""
        if "admin" not in getattr(current_user, "roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
    
    @staticmethod
    def _extract_tools_from_app(app) -> list:
        """Extract tools from FastMCP app"""
        tools = []
        if hasattr(app, '_tool_manager'):
            for tool_name, tool_func in app._tool_manager.tools.items():
                tool_info = {
                    "name": tool_name,
                    "description": tool_func.__doc__ or "No description available"
                }
                if hasattr(tool_func, '__category__'):
                    tool_info["category"] = tool_func.__category__
                tools.append(tool_info)
        return tools
    
    @staticmethod
    def _extract_resources_from_app(app) -> list:
        """Extract resources from FastMCP app"""
        resources = []
        if hasattr(app, '_resource_manager'):
            for resource_uri, resource_func in app._resource_manager.resources.items():
                resources.append({
                    "uri": resource_uri,
                    "description": resource_func.__doc__ or "No description available"
                })
        return resources
    
    @staticmethod
    def _extract_prompts_from_app(app) -> list:
        """Extract prompts from FastMCP app"""
        prompts = []
        if hasattr(app, '_prompt_manager'):
            for prompt_name, prompt_func in app._prompt_manager.prompts.items():
                prompt_info = {
                    "name": prompt_name,
                    "description": prompt_func.__doc__ or "No description available"
                }
                if hasattr(prompt_func, '__category__'):
                    prompt_info["category"] = prompt_func.__category__
                prompts.append(prompt_info)
        return prompts
    
    @staticmethod
    def _get_tool_function(server, tool_name: str):
        """Get tool function from server"""
        app = server.get_app()
        tool_func = None
        if hasattr(app, '_tool_manager') and tool_name in app._tool_manager.tools:
            tool_func = app._tool_manager.tools[tool_name]
        
        if not tool_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found"
            )
        return tool_func
    
    @staticmethod
    def _get_resource_function(server, uri: str):
        """Get resource function from server"""
        app = server.get_app()
        resource_func = None
        if hasattr(app, '_resource_manager') and uri in app._resource_manager.resources:
            resource_func = app._resource_manager.resources[uri]
        
        if not resource_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource '{uri}' not found"
            )
        return resource_func
    
    @staticmethod
    def _get_prompt_function(server, prompt_name: str):
        """Get prompt function from server"""
        app = server.get_app()
        prompt_func = None
        if hasattr(app, '_prompt_manager') and prompt_name in app._prompt_manager.prompts:
            prompt_func = app._prompt_manager.prompts[prompt_name]
        
        if not prompt_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{prompt_name}' not found"
            )
        return prompt_func
    
    @staticmethod
    async def _record_successful_execution(
        request, db, mcp_service, current_user, result, execution_time_ms
    ) -> None:
        """Record successful tool execution"""
        if request.session_id:
            from datetime import datetime
            execution = MCPToolExecution(
                session_id=request.session_id,
                client_id=str(current_user.id),
                tool_name=request.tool_name,
                input_params=request.arguments,
                output_result={"result": result},
                execution_time_ms=execution_time_ms,
                status="success"
            )
            await mcp_service.record_tool_execution(db, execution)
    
    @staticmethod
    async def _record_failed_execution(
        request, db, mcp_service, current_user, error, start_time
    ) -> None:
        """Record failed tool execution"""
        if request.session_id:
            from datetime import datetime
            execution = MCPToolExecution(
                session_id=request.session_id,
                client_id=str(current_user.id),
                tool_name=request.tool_name,
                input_params=request.arguments,
                execution_time_ms=int((time.time() - start_time) * 1000),
                status="error",
                error=str(error)
            )
            await mcp_service.record_tool_execution(db, execution)
    
    @staticmethod
    def _get_claude_config(base_url: str) -> Dict[str, Any]:
        """Get Claude MCP configuration"""
        return {
            "mcpServers": {
                "netra": {
                    "command": "python",
                    "args": ["-m", "app.mcp.run_server"],
                    "env": {
                        "NETRA_API_KEY": "${NETRA_API_KEY}",
                        "NETRA_BASE_URL": base_url
                    }
                }
            }
        }
    
    @staticmethod
    def _get_cursor_config() -> Dict[str, Any]:
        """Get Cursor MCP configuration"""
        return {
            "mcp": {
                "servers": {
                    "netra": {
                        "transport": "stdio",
                        "command": "python -m app.mcp.run_server"
                    }
                }
            }
        }
    
    @staticmethod
    def _get_http_config(base_url: str) -> Dict[str, Any]:
        """Get HTTP MCP configuration"""
        return {
            "endpoint": f"{base_url}/api/mcp",
            "transport": "http",
            "authentication": "Bearer token or API key"
        }
    
    @staticmethod
    def _get_websocket_config(base_url: str) -> Dict[str, Any]:
        """Get WebSocket MCP configuration"""
        ws_url = f"ws://{base_url.replace('http://', '').replace('https://', '')}/api/mcp/ws"
        return {
            "endpoint": ws_url,
            "transport": "websocket",
            "authentication": "Query parameter: api_key"
        }