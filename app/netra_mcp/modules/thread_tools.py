"""Thread Tools Module - MCP tools for thread management operations"""

import json
from typing import Dict, Any, Optional


class ThreadTools:
    """Thread management tools registration"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register thread management tools"""
        self._register_create_thread_tool(server)
        self._register_thread_history_tool(server)
    
    def _register_create_thread_tool(self, server):
        """Register create thread tool"""
        @self.mcp.tool()
        async def create_thread(
            title: str = "New Thread",
            metadata: Optional[Dict[str, Any]] = None
        ) -> str:
            """Create a new conversation thread"""
            return await self._execute_thread_creation(server, title, metadata)
    
    async def _execute_thread_creation(self, server, title: str, 
                                      metadata: Optional[Dict[str, Any]]) -> str:
        """Execute thread creation with error handling"""
        if not server.thread_service:
            return self._format_service_error("Thread service not available")
        try:
            return await self._perform_thread_creation(server, title, metadata)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_thread_creation(self, server, title: str, 
                                      metadata: Optional[Dict[str, Any]]) -> str:
        """Perform thread creation operation"""
        metadata = self._prepare_thread_metadata(metadata)
        thread_id = await server.thread_service.create_thread(
            title=title, metadata=metadata
        )
        return self._format_thread_result(thread_id, title)
    
    def _prepare_thread_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare metadata for thread creation"""
        result = metadata or {}
        result["source"] = "mcp"
        return result
    
    def _format_thread_result(self, thread_id: str, title: str) -> str:
        """Format thread creation result"""
        return json.dumps({
            "thread_id": thread_id, "title": title, "created": True
        }, indent=2)
    
    def _format_service_error(self, error_message: str) -> str:
        """Format service error response"""
        return json.dumps({"error": error_message})
    
    def _register_thread_history_tool(self, server):
        """Register thread history tool"""
        @self.mcp.tool()
        async def get_thread_history(thread_id: str, limit: int = 50) -> str:
            """Get thread message history"""
            if not server.thread_service:
                return json.dumps({"error": "Thread service not available"})
            try:
                messages = await server.thread_service.get_thread_messages(
                    thread_id=thread_id, limit=limit
                )
                return json.dumps(messages, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})