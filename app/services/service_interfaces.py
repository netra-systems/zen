"""Service interfaces for dependency injection.

Defines abstract base classes for all services.
Follows 300-line limit with 8-line function limit.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IAgentService(ABC):
    """Interface for agent service."""
    
    @abstractmethod
    async def start_agent(self, request_model, run_id: str, stream_updates: bool = False):
        """Start an agent with the given request model and run ID."""
        pass
    
    @abstractmethod
    async def stop_agent(self, user_id: str) -> bool:
        """Stop an agent for the given user."""
        pass
    
    @abstractmethod
    async def get_agent_status(self, user_id: str) -> Dict[str, Any]:
        """Get the status of an agent for the given user."""
        pass


class IThreadService(ABC):
    """Interface for thread service."""
    
    @abstractmethod
    async def create_thread(self, user_id: str, db=None):
        """Create a new thread for the user."""
        pass
    
    @abstractmethod
    async def get_thread(self, thread_id: str, user_id: str, db=None):
        """Get a specific thread by ID."""
        pass
    
    @abstractmethod
    async def get_threads(self, user_id: str, db=None):
        """Get all threads for a user."""
        pass
    
    @abstractmethod
    async def delete_thread(self, thread_id: str, user_id: str, db=None):
        """Delete a thread."""
        pass


class IMessageHandlerService(ABC):
    """Interface for message handler service."""
    
    @abstractmethod
    async def handle_message(self, user_id: str, message: Dict[str, Any]):
        """Handle a WebSocket message."""
        pass
    
    @abstractmethod
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        pass


class IMCPService(ABC):
    """Interface for MCP service."""
    
    @abstractmethod
    async def initialize(self):
        """Initialize the MCP service."""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Shutdown the MCP service."""
        pass
    
    @abstractmethod
    async def get_server_info(self):
        """Get server information."""
        pass


class IWebSocketService(ABC):
    """Interface for WebSocket service."""
    
    @abstractmethod
    async def connect(self, websocket, user_id: str):
        """Handle WebSocket connection."""
        pass
    
    @abstractmethod
    async def disconnect(self, user_id: str):
        """Handle WebSocket disconnection."""
        pass
    
    @abstractmethod
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user."""
        pass


class IMCPClientService(ABC):
    """Interface for MCP Client service."""
    
    @abstractmethod
    async def register_server(self, server_config: Dict[str, Any]) -> bool:
        """Register an external MCP server."""
        pass
    
    @abstractmethod
    async def connect_to_server(self, server_name: str) -> Dict[str, Any]:
        """Connect to a specific MCP server."""
        pass
    
    @abstractmethod
    async def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        pass
    
    @abstractmethod
    async def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools from an MCP server."""
        pass
    
    @abstractmethod
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server."""
        pass
    
    @abstractmethod
    async def get_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources from an MCP server."""
        pass
    
    @abstractmethod
    async def fetch_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Fetch a specific resource from an MCP server."""
        pass
    
    @abstractmethod
    async def clear_cache(self, server_name: Optional[str] = None):
        """Clear MCP client cache."""
        pass