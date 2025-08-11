"""
MCP Server Core Implementation

Handles protocol negotiation, session management, and request routing.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel, Field
from app.core.exceptions import NetraException
from app.logging_config import CentralLogger

logger = CentralLogger()


class MCPServerConfig(BaseModel):
    """MCP Server configuration"""
    protocol_version: str = "1.0.0"
    server_name: str = "Netra MCP Server"
    server_version: str = "1.0.0"
    max_sessions: int = Field(default=1000, ge=1)
    session_timeout: int = Field(default=3600, ge=60)  # seconds
    rate_limit: int = Field(default=100, ge=1)  # requests per minute
    enable_sampling: bool = True
    enable_tools: bool = True
    enable_resources: bool = True
    enable_prompts: bool = True


class MCPSession(BaseModel):
    """Represents an active MCP session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: Optional[str] = None
    transport: str  # stdio, http, websocket
    protocol_version: str
    capabilities: Dict[str, Any]
    state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))
    request_count: int = 0
    last_request_at: Optional[datetime] = None


class MCPServer:
    """
    Main MCP Server implementation
    
    Coordinates all MCP operations and manages sessions.
    """
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        self.config = config or MCPServerConfig()
        self.sessions: Dict[str, MCPSession] = {}
        self.request_handlers: Dict[str, Any] = {}
        self.tool_registry = None
        self.resource_manager = None
        self.prompt_manager = None
        self._initialize_handlers()
        
    def _initialize_handlers(self):
        """Initialize request handlers for different MCP methods"""
        from .handlers.request_handler import RequestHandler
        from .tools.tool_registry import ToolRegistry
        from .resources.resource_manager import ResourceManager
        from .prompts.prompt_manager import PromptManager
        
        self.request_handler = RequestHandler(self)
        self.tool_registry = ToolRegistry()
        self.resource_manager = ResourceManager()
        self.prompt_manager = PromptManager()
        
        # Register standard MCP methods
        self.register_method("initialize", self.handle_initialize)
        self.register_method("ping", self.handle_ping)
        self.register_method("tools/list", self.handle_tools_list)
        self.register_method("tools/call", self.handle_tools_call)
        self.register_method("resources/list", self.handle_resources_list)
        self.register_method("resources/read", self.handle_resources_read)
        self.register_method("prompts/list", self.handle_prompts_list)
        self.register_method("prompts/get", self.handle_prompts_get)
        self.register_method("sampling/createMessage", self.handle_sampling_create_message)
        
    def register_method(self, method: str, handler):
        """Register a method handler"""
        self.request_handlers[method] = handler
        
    async def handle_request(self, request: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC 2.0 request
        
        Args:
            request: JSON-RPC request object
            session_id: Optional session identifier
            
        Returns:
            JSON-RPC response object
        """
        try:
            # Validate JSON-RPC structure
            if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
                return self._error_response(
                    -32600, "Invalid Request", request.get("id")
                )
                
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if not method:
                return self._error_response(
                    -32600, "Invalid Request: missing method", request_id
                )
                
            # Update session activity
            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]
                session.request_count += 1
                session.last_request_at = datetime.utcnow()
                
                # Check rate limit
                if not self._check_rate_limit(session):
                    return self._error_response(
                        -32004, "Rate limit exceeded", request_id
                    )
            
            # Route to appropriate handler
            if method in self.request_handlers:
                handler = self.request_handlers[method]
                result = await handler(params, session_id)
                return self._success_response(result, request_id)
            else:
                return self._error_response(
                    -32601, f"Method not found: {method}", request_id
                )
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return self._error_response(
                -32603, f"Internal error: {str(e)}", request.get("id")
            )
            
    async def handle_initialize(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle initialization request"""
        protocol_version = params.get("protocolVersion", "1.0.0")
        capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        # Create or update session
        if not session_id:
            session_id = str(uuid.uuid4())
            
        session = MCPSession(
            id=session_id,
            transport=params.get("transport", "unknown"),
            protocol_version=protocol_version,
            capabilities=capabilities,
            state={"client_info": client_info}
        )
        
        self.sessions[session_id] = session
        
        # Return server capabilities
        return {
            "protocolVersion": self.config.protocol_version,
            "capabilities": {
                "tools": self.config.enable_tools and self.tool_registry is not None,
                "resources": self.config.enable_resources and self.resource_manager is not None,
                "prompts": self.config.enable_prompts and self.prompt_manager is not None,
                "sampling": self.config.enable_sampling
            },
            "serverInfo": {
                "name": self.config.server_name,
                "version": self.config.server_version
            }
        }
        
    async def handle_ping(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle ping request"""
        return {"pong": True, "timestamp": datetime.utcnow().isoformat()}
        
    async def handle_tools_list(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """List available tools"""
        if not self.tool_registry:
            return {"tools": []}
            
        tools = await self.tool_registry.list_tools(session_id)
        return {"tools": tools}
        
    async def handle_tools_call(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a tool"""
        if not self.tool_registry:
            raise NetraException("Tools not available")
            
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise NetraException("Tool name is required")
            
        result = await self.tool_registry.execute_tool(
            tool_name, arguments, session_id
        )
        
        return {
            "content": result.get("content", []),
            "isError": result.get("isError", False)
        }
        
    async def handle_resources_list(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """List available resources"""
        if not self.resource_manager:
            return {"resources": []}
            
        resources = await self.resource_manager.list_resources(session_id)
        return {"resources": resources}
        
    async def handle_resources_read(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Read resource content"""
        if not self.resource_manager:
            raise NetraException("Resources not available")
            
        uri = params.get("uri")
        if not uri:
            raise NetraException("Resource URI is required")
            
        content = await self.resource_manager.read_resource(uri, session_id)
        return {"contents": content}
        
    async def handle_prompts_list(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """List available prompts"""
        if not self.prompt_manager:
            return {"prompts": []}
            
        prompts = await self.prompt_manager.list_prompts(session_id)
        return {"prompts": prompts}
        
    async def handle_prompts_get(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get prompt template"""
        if not self.prompt_manager:
            raise NetraException("Prompts not available")
            
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise NetraException("Prompt name is required")
            
        messages = await self.prompt_manager.get_prompt(name, arguments, session_id)
        return {"messages": messages}
        
    async def handle_sampling_create_message(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Create LLM message through sampling"""
        if not self.config.enable_sampling:
            raise NetraException("Sampling not available")
            
        # This will integrate with the existing LLM manager
        from app.dependencies import get_llm_manager
        from app.db.postgres import get_async_db
        
        messages = params.get("messages", [])
        model_preferences = params.get("modelPreferences", {})
        system_prompt = params.get("systemPrompt")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("maxTokens", 1000)
        
        # TODO: Implement actual LLM sampling
        # For now, return a placeholder response
        return {
            "model": model_preferences.get("hints", ["claude-3-opus"])[0],
            "stopReason": "end_turn",
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "This is a placeholder response. Actual LLM integration pending."
            }
        }
        
    def _check_rate_limit(self, session: MCPSession) -> bool:
        """Check if session is within rate limits"""
        if not session.last_request_at:
            return True
            
        # Simple rate limit check (requests per minute)
        time_diff = (datetime.utcnow() - session.last_request_at).total_seconds()
        if time_diff < 60:  # Within the last minute
            requests_per_minute = session.request_count * (60 / time_diff)
            return requests_per_minute <= self.config.rate_limit
            
        return True
        
    def _success_response(self, result: Any, request_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
        """Create success response"""
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        if request_id is not None:
            response["id"] = request_id
        return response
        
    def _error_response(self, code: int, message: str, request_id: Optional[Union[str, int]] = None, data: Any = None) -> Dict[str, Any]:
        """Create error response"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
            
        response = {
            "jsonrpc": "2.0",
            "error": error
        }
        if request_id is not None:
            response["id"] = request_id
        return response
        
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.expires_at < now
        ]
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            del self.sessions[session_id]
            
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down MCP server")
        # Clean up resources
        self.sessions.clear()
        if self.tool_registry:
            await self.tool_registry.shutdown()
        if self.resource_manager:
            await self.resource_manager.shutdown()