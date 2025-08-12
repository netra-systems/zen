"""
MCP HTTP Transport with Server-Sent Events

Implements JSON-RPC 2.0 over HTTP with SSE for streaming responses.
"""

from typing import Optional, Dict, Any, AsyncGenerator
import json
import asyncio
from datetime import datetime, UTC

from fastapi import APIRouter, Request, Response, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from app.logging_config import CentralLogger
from app.mcp.server import MCPServer
from app.auth.auth_dependencies import get_current_user_optional
from app.schemas import UserInDB

logger = CentralLogger()


class MCPRequest(BaseModel):
    """MCP HTTP Request model"""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[Any] = None


class HttpTransport:
    """
    HTTP transport for MCP with SSE support
    
    Used by web-based clients and REST API integrations.
    """
    
    def __init__(self, server: Optional[MCPServer] = None):
        self.server = server or MCPServer()
        self.router = APIRouter(prefix="/mcp", tags=["MCP"])
        self.sessions: Dict[str, str] = {}  # Map HTTP session to MCP session
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.router.post("/")
        async def handle_request(
            request: MCPRequest,
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Handle MCP request over HTTP"""
            try:
                # Get or create session
                session_id = self._get_session_id(user)
                
                # Add transport info for initialization
                if request.method == "initialize":
                    request.params["transport"] = "http"
                    
                # Process request
                response = await self.server.handle_request(
                    request.dict(),
                    session_id
                )
                
                return response
                
            except Exception as e:
                logger.error(f"Error handling HTTP MCP request: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/batch")
        async def handle_batch_request(
            requests: list[MCPRequest],
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Handle batch MCP requests"""
            try:
                session_id = self._get_session_id(user)
                responses = []
                
                for request in requests:
                    if request.method == "initialize":
                        request.params["transport"] = "http"
                        
                    response = await self.server.handle_request(
                        request.dict(),
                        session_id
                    )
                    if response:  # Don't include notification responses
                        responses.append(response)
                        
                return responses
                
            except Exception as e:
                logger.error(f"Error handling batch MCP request: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/stream")
        async def stream_events(
            session_id: Optional[str] = Query(None),
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Stream MCP events via Server-Sent Events"""
            if not session_id:
                session_id = self._get_session_id(user)
                
            async def event_generator():
                """Generate SSE events"""
                try:
                    # Send initial connection event
                    yield {
                        "event": "connected",
                        "data": json.dumps({
                            "session_id": session_id,
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                    }
                    
                    # Keep connection alive and send events
                    event_queue = asyncio.Queue()
                    
                    # Register this session for events
                    if hasattr(self.server, 'register_event_listener'):
                        await self.server.register_event_listener(session_id, event_queue)
                    
                    try:
                        while True:
                            # Check for events with timeout for heartbeat
                            try:
                                event = await asyncio.wait_for(
                                    event_queue.get(), 
                                    timeout=30.0
                                )
                                
                                # Send the actual event
                                yield {
                                    "event": event.get("type", "message"),
                                    "data": json.dumps(event.get("data", {}))
                                }
                                
                            except asyncio.TimeoutError:
                                # Send heartbeat if no events
                                yield {
                                    "event": "heartbeat",
                                    "data": json.dumps({
                                        "timestamp": datetime.now(UTC).isoformat()
                                    })
                                }
                    finally:
                        # Unregister on disconnect
                        if hasattr(self.server, 'unregister_event_listener'):
                            await self.server.unregister_event_listener(session_id)
                        
                except asyncio.CancelledError:
                    logger.info(f"SSE connection closed for session {session_id}")
                    raise
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}", exc_info=True)
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": str(e),
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                    }
                    
            return EventSourceResponse(event_generator())
            
        @self.router.post("/tools/list")
        async def list_tools(
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """List available MCP tools"""
            session_id = self._get_session_id(user)
            return await self.server.handle_tools_list({}, session_id)
            
        @self.router.post("/tools/call")
        async def call_tool(
            tool_name: str,
            arguments: Dict[str, Any],
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Execute an MCP tool"""
            session_id = self._get_session_id(user)
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            return await self.server.handle_tools_call(params, session_id)
            
        @self.router.post("/resources/list")
        async def list_resources(
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """List available MCP resources"""
            session_id = self._get_session_id(user)
            return await self.server.handle_resources_list({}, session_id)
            
        @self.router.post("/resources/read")
        async def read_resource(
            uri: str,
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Read an MCP resource"""
            session_id = self._get_session_id(user)
            params = {"uri": uri}
            return await self.server.handle_resources_read(params, session_id)
            
        @self.router.post("/prompts/list")
        async def list_prompts(
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """List available MCP prompts"""
            session_id = self._get_session_id(user)
            return await self.server.handle_prompts_list({}, session_id)
            
        @self.router.post("/prompts/get")
        async def get_prompt(
            name: str,
            arguments: Dict[str, Any] = {},
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Get an MCP prompt template"""
            session_id = self._get_session_id(user)
            params = {
                "name": name,
                "arguments": arguments
            }
            return await self.server.handle_prompts_get(params, session_id)
            
        @self.router.post("/sampling/createMessage")
        async def create_message(
            messages: list[Dict[str, str]],
            model_preferences: Optional[Dict[str, Any]] = None,
            system_prompt: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 1000,
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            """Create message through LLM sampling"""
            session_id = self._get_session_id(user)
            params = {
                "messages": messages,
                "modelPreferences": model_preferences or {},
                "systemPrompt": system_prompt,
                "temperature": temperature,
                "maxTokens": max_tokens
            }
            return await self.server.handle_sampling_create_message(params, session_id)
            
        @self.router.get("/health")
        async def health_check():
            """MCP server health check"""
            return {
                "status": "healthy",
                "server": "Netra MCP Server",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat()
            }
            
    def _get_session_id(self, user: Optional[UserInDB]) -> str:
        """Get or create session ID for user"""
        if user:
            user_key = f"user_{user.id}"
            if user_key not in self.sessions:
                import uuid
                self.sessions[user_key] = str(uuid.uuid4())
            return self.sessions[user_key]
        else:
            # Anonymous session
            return "anonymous"
            
    def get_router(self) -> APIRouter:
        """Get FastAPI router"""
        return self.router