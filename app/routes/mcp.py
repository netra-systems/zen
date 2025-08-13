"""
MCP API Routes

HTTP endpoints for MCP server access using FastMCP 2.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.postgres import get_async_db
from app.dependencies import get_current_user, get_agent_service, get_thread_service, get_corpus_service, get_security_service
from app.auth.auth_dependencies import get_current_user_optional
from app.schemas import UserInDB
from app.services.mcp_service import MCPService, MCPClient
from app.services.synthetic_data_service import SyntheticDataService
from app.services.supply_catalog_service import SupplyCatalogService
from app.services.agent_service import AgentService
from app.services.thread_service import ThreadService
from app.services.corpus_service import CorpusService
from app.services.security_service import SecurityService
from app.logging_config import CentralLogger
import os

logger = CentralLogger()

router = APIRouter(prefix="/api/mcp", tags=["MCP"])

# Global MCP service instance (initialized on first request)
_mcp_service: Optional[MCPService] = None


class MCPClientCreateRequest(BaseModel):
    """Request model for creating MCP client"""
    name: str
    client_type: str
    api_key: Optional[str] = None
    permissions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPSessionCreateRequest(BaseModel):
    """Request model for creating MCP session"""
    client_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPToolCallRequest(BaseModel):
    """Request model for tool execution"""
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


class MCPResourceReadRequest(BaseModel):
    """Request model for resource reading"""
    uri: str
    session_id: Optional[str] = None


class MCPPromptGetRequest(BaseModel):
    """Request model for prompt retrieval"""
    prompt_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


async def get_mcp_service(
    agent_service: AgentService = Depends(get_agent_service),
    thread_service: ThreadService = Depends(get_thread_service),
    corpus_service: CorpusService = Depends(get_corpus_service),
    security_service: SecurityService = Depends(get_security_service)
) -> MCPService:
    """Get or create MCP service instance"""
    global _mcp_service
    
    if _mcp_service is None:
        # Create synthetic data and supply catalog services
        synthetic_data_service = SyntheticDataService()
        supply_catalog_service = SupplyCatalogService()
        
        _mcp_service = MCPService(
            agent_service=agent_service,
            thread_service=thread_service,
            corpus_service=corpus_service,
            synthetic_data_service=synthetic_data_service,
            security_service=security_service,
            supply_catalog_service=supply_catalog_service
        )
        
        logger.info("MCP service initialized with FastMCP 2")
        
    return _mcp_service


@router.get("/info")
async def get_server_info(
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
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


@router.get("/status")
async def get_mcp_status(
    mcp_service: MCPService = Depends(get_mcp_service),
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP server status"""
    return await get_server_info(mcp_service, user)


@router.post("/clients")
async def register_client(
    request: MCPClientCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
) -> MCPClient:
    """Register a new MCP client"""
    try:
        # Check if user is admin
        if "admin" not in getattr(current_user, "roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
            
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


# Legacy endpoint removed - use proper MCPClientCreateRequest with /clients endpoint


@router.post("/sessions")
async def create_session(
    request: MCPSessionCreateRequest,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
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


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
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


@router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
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


@router.get("/tools")
async def list_tools(
    category: Optional[str] = None,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """List available MCP tools"""
    try:
        # Get the FastMCP app and list tools
        app = mcp_service.get_fastmcp_app()
        tools = []
        
        # FastMCP stores tools in _tool_manager
        if hasattr(app, '_tool_manager'):
            for tool_name, tool_func in app._tool_manager.tools.items():
                tool_info = {
                    "name": tool_name,
                    "description": tool_func.__doc__ or "No description available"
                }
                # Try to extract category from docstring or metadata
                if hasattr(tool_func, '__category__'):
                    tool_info["category"] = tool_func.__category__
                tools.append(tool_info)
        
        # Filter by category if provided
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


@router.post("/tools/call")
async def call_tool(
    request: MCPToolCallRequest,
    db: AsyncSession = Depends(get_async_db),
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute an MCP tool"""
    import time
    start_time = time.time()
    
    try:
        # Get the MCP server
        server = mcp_service.get_mcp_server()
        
        # Execute the tool directly
        app = server.get_app()
        tool_func = None
        if hasattr(app, '_tool_manager') and request.tool_name in app._tool_manager.tools:
            tool_func = app._tool_manager.tools[request.tool_name]
        
        if not tool_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{request.tool_name}' not found"
            )
        
        # Execute the tool
        result = await tool_func(**request.arguments)
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Record execution if session provided
        if request.session_id:
            from datetime import datetime
            from app.services.mcp_service import MCPToolExecution
            
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
        
        return {
            "tool": request.tool_name,
            "result": result,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling tool: {e}", exc_info=True)
        
        # Record failed execution if session provided
        if request.session_id:
            from datetime import datetime
            from app.services.mcp_service import MCPToolExecution
            
            execution = MCPToolExecution(
                session_id=request.session_id,
                client_id=str(current_user.id),
                tool_name=request.tool_name,
                input_params=request.arguments,
                execution_time_ms=int((time.time() - start_time) * 1000),
                status="error",
                error=str(e)
            )
            await mcp_service.record_tool_execution(db, execution)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/resources")
async def list_resources(
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """List available MCP resources"""
    try:
        # Get the FastMCP app and list resources
        app = mcp_service.get_fastmcp_app()
        resources = []
        
        # FastMCP stores resources in _resource_manager
        if hasattr(app, '_resource_manager'):
            for resource_uri, resource_func in app._resource_manager.resources.items():
                resources.append({
                    "uri": resource_uri,
                    "description": resource_func.__doc__ or "No description available"
                })
        
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


@router.post("/resources/read")
async def read_resource(
    request: MCPResourceReadRequest,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """Read an MCP resource"""
    try:
        # Get the MCP server
        server = mcp_service.get_mcp_server()
        app = server.get_app()
        
        # Get the resource function
        resource_func = None
        if hasattr(app, '_resource_manager') and request.uri in app._resource_manager.resources:
            resource_func = app._resource_manager.resources[request.uri]
        
        if not resource_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource '{request.uri}' not found"
            )
        
        # Read the resource
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


@router.get("/prompts")
async def list_prompts(
    category: Optional[str] = None,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """List available MCP prompts"""
    try:
        # Get the FastMCP app and list prompts
        app = mcp_service.get_fastmcp_app()
        prompts = []
        
        # FastMCP stores prompts in _prompt_manager
        if hasattr(app, '_prompt_manager'):
            for prompt_name, prompt_func in app._prompt_manager.prompts.items():
                prompt_info = {
                    "name": prompt_name,
                    "description": prompt_func.__doc__ or "No description available"
                }
                # Try to extract category from docstring or metadata
                if hasattr(prompt_func, '__category__'):
                    prompt_info["category"] = prompt_func.__category__
                prompts.append(prompt_info)
        
        # Filter by category if provided
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


@router.post("/prompts/get")
async def get_prompt(
    request: MCPPromptGetRequest,
    mcp_service: MCPService = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get an MCP prompt"""
    try:
        # Get the MCP server
        server = mcp_service.get_mcp_server()
        app = server.get_app()
        
        # Get the prompt function
        prompt_func = None
        if hasattr(app, '_prompt_manager') and request.prompt_name in app._prompt_manager.prompts:
            prompt_func = app._prompt_manager.prompts[request.prompt_name]
        
        if not prompt_func:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{request.prompt_name}' not found"
            )
        
        # Get the prompt
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


@router.get("/config")
async def get_mcp_config(
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP configuration for clients"""
    base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    
    # Configuration for different clients
    configs = {
        "claude": {
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
        },
        "cursor": {
            "mcp": {
                "servers": {
                    "netra": {
                        "transport": "stdio",
                        "command": "python -m app.mcp.run_server"
                    }
                }
            }
        },
        "http": {
            "endpoint": f"{base_url}/api/mcp",
            "transport": "http",
            "authentication": "Bearer token or API key"
        },
        "websocket": {
            "endpoint": f"ws://{base_url.replace('http://', '').replace('https://', '')}/api/mcp/ws",
            "transport": "websocket",
            "authentication": "Query parameter: api_key"
        }
    }
    
    return configs


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = None,
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """
    WebSocket endpoint for MCP
    
    Connect with: ws://localhost:8000/api/mcp/ws?api_key=YOUR_KEY
    """
    await websocket.accept()
    
    try:
        # Create session for this WebSocket connection
        session_id = await mcp_service.create_session(
            metadata={"transport": "websocket", "api_key": api_key is not None}
        )
        
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id
        })
        
        # Handle WebSocket messages
        while True:
            data = await websocket.receive_json()
            
            # Update session activity
            await mcp_service.update_session_activity(session_id)
            
            # Process the request
            # This would need proper MCP protocol handling
            response = {
                "type": "response",
                "session_id": session_id,
                "status": "not_implemented",
                "message": "WebSocket MCP transport pending full implementation"
            }
            
            await websocket.send_json(response)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close()
    finally:
        # Clean up session
        if session_id:
            await mcp_service.close_session(session_id)