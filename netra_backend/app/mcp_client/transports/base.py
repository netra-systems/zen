"""
Base transport class for MCP (Model Context Protocol) clients.
Defines the abstract interface that all transport implementations must follow.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """
    Abstract base class for MCP transport implementations.
    Provides the interface contract for all transport protocols.
    """
    
    def __init__(self, timeout: int = 30000) -> None:
        """Initialize transport with timeout in milliseconds."""
        self.timeout = timeout
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the MCP server.
        Must set _connected to True on success.
        """
        pass
        
    @abstractmethod  
    async def disconnect(self) -> None:
        """
        Close connection to the MCP server.
        Must set _connected to False.
        """
        pass
        
    @abstractmethod
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send JSON-RPC 2.0 request and return response.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters dictionary
            
        Returns:
            JSON-RPC response as dictionary
            
        Raises:
            ConnectionError: If not connected
            TimeoutError: If request times out
            ValueError: If response is invalid
        """
        pass
        
    def is_connected(self) -> bool:
        """Return current connection status."""
        return self._connected
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class MCPTransportError(Exception):
    """Base exception for MCP transport errors."""
    pass


class MCPConnectionError(MCPTransportError):
    """Raised when connection operations fail."""
    pass


class MCPTimeoutError(MCPTransportError):
    """Raised when requests timeout."""
    pass


class MCPProtocolError(MCPTransportError):
    """Raised when JSON-RPC protocol violations occur."""
    pass