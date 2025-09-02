"""
Modern WebSocket Abstraction Layer

This module provides a modern abstraction for WebSocket connections to replace
deprecated websockets.legacy usage. It provides compatibility with both modern
websockets library (v11+) and uvicorn's WebSocket implementation.

Key Features:
- Modern websockets.ClientConnection and ServerConnection support
- Backward compatibility with deprecated patterns
- Type-safe abstractions
- Connection lifecycle management
- Error handling and recovery
"""

import asyncio
import logging
import warnings
from typing import Any, Dict, Optional, Protocol, Union, runtime_checkable
from contextlib import asynccontextmanager
import json

# Modern websockets imports - avoid legacy
try:
    import websockets
    from websockets import ClientConnection, ServerConnection
    from websockets.exceptions import (
        ConnectionClosed,
        ConnectionClosedError, 
        ConnectionClosedOK,
        WebSocketException
    )
    # Note: InvalidStatusCode is deprecated, we handle status code errors differently
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    # Fallback types for environments without websockets
    ClientConnection = Any
    ServerConnection = Any

# FastAPI WebSocket import
try:
    from fastapi import WebSocket as FastAPIWebSocket
    from fastapi.websockets import WebSocketState
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPIWebSocket = Any

logger = logging.getLogger(__name__)


@runtime_checkable  
class ModernWebSocketProtocol(Protocol):
    """Protocol defining modern WebSocket interface."""
    
    async def send(self, message: Union[str, bytes]) -> None:
        """Send a message through the WebSocket."""
        ...
    
    async def recv(self) -> Union[str, bytes]:
        """Receive a message from the WebSocket."""
        ...
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection."""
        ...
        
    @property
    def closed(self) -> bool:
        """Check if connection is closed."""
        ...


class ModernWebSocketWrapper:
    """
    Modern WebSocket wrapper that abstracts different WebSocket implementations.
    
    This wrapper provides a unified interface for:
    - websockets.ClientConnection (modern client)
    - websockets.ServerConnection (modern server) 
    - FastAPI WebSocket (uvicorn)
    - Legacy websockets protocols (with warnings)
    """
    
    def __init__(self, websocket: Any):
        self._websocket = websocket
        self._connection_type = self._detect_connection_type(websocket)
        
        # Issue deprecation warning for legacy types
        if self._connection_type in ["legacy_client", "legacy_server"]:
            warnings.warn(
                f"Using deprecated WebSocket type {type(websocket)}. "
                "Upgrade to modern websockets.ClientConnection or websockets.ServerConnection.",
                DeprecationWarning,
                stacklevel=2
            )
    
    def _detect_connection_type(self, websocket: Any) -> str:
        """Detect the type of WebSocket connection."""
        if FASTAPI_AVAILABLE and isinstance(websocket, FastAPIWebSocket):
            return "fastapi"
        
        if WEBSOCKETS_AVAILABLE:
            if isinstance(websocket, ClientConnection):
                return "client"
            elif isinstance(websocket, ServerConnection):
                return "server"
        
        # Check for legacy types by name to avoid import errors
        websocket_type_name = type(websocket).__name__
        if "WebSocketClientProtocol" in websocket_type_name:
            return "legacy_client"
        elif "WebSocketServerProtocol" in websocket_type_name:
            return "legacy_server"
            
        return "unknown"
    
    async def send(self, message: Union[str, bytes, Dict[str, Any]]) -> None:
        """Send a message through the WebSocket."""
        try:
            # Convert dict to JSON string
            if isinstance(message, dict):
                message = json.dumps(message)
            
            if self._connection_type == "fastapi":
                if isinstance(message, bytes):
                    await self._websocket.send_bytes(message)
                else:
                    await self._websocket.send_text(str(message))
            else:
                # Modern websockets or legacy - both use send()
                await self._websocket.send(message)
                
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    async def receive(self) -> Union[str, bytes]:
        """Receive a message from the WebSocket."""
        try:
            if self._connection_type == "fastapi":
                # FastAPI WebSocket has different receive methods
                message = await self._websocket.receive()
                if "text" in message:
                    return message["text"]
                elif "bytes" in message:
                    return message["bytes"]
                else:
                    raise ValueError(f"Unknown FastAPI WebSocket message format: {message}")
            else:
                # Modern websockets or legacy - both use recv()
                return await self._websocket.recv()
                
        except Exception as e:
            logger.error(f"Failed to receive WebSocket message: {e}")
            raise
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection."""
        try:
            if self._connection_type == "fastapi":
                await self._websocket.close(code=code, reason=reason)
            else:
                # Modern websockets or legacy
                await self._websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing WebSocket: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        try:
            if self._connection_type == "fastapi":
                return (
                    hasattr(self._websocket, 'client_state') and 
                    self._websocket.client_state == WebSocketState.CONNECTED
                )
            else:
                # Modern websockets or legacy - check closed property
                return not getattr(self._websocket, 'closed', True)
        except Exception:
            return False
    
    @property 
    def connection_type(self) -> str:
        """Get the connection type."""
        return self._connection_type
    
    def __str__(self) -> str:
        return f"ModernWebSocketWrapper({self._connection_type})"


class ModernWebSocketManager:
    """
    Modern WebSocket connection manager with proper lifecycle management.
    """
    
    def __init__(self):
        self._active_connections: Dict[str, ModernWebSocketWrapper] = {}
        self._connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_connection(self, connection_id: str, websocket: Any, metadata: Optional[Dict[str, Any]] = None) -> ModernWebSocketWrapper:
        """Register a new WebSocket connection."""
        wrapper = ModernWebSocketWrapper(websocket)
        self._active_connections[connection_id] = wrapper
        self._connection_metadata[connection_id] = metadata or {}
        
        logger.info(f"Registered WebSocket connection {connection_id} ({wrapper.connection_type})")
        return wrapper
    
    def get_connection(self, connection_id: str) -> Optional[ModernWebSocketWrapper]:
        """Get an active WebSocket connection."""
        return self._active_connections.get(connection_id)
    
    async def send_to_connection(self, connection_id: str, message: Union[str, bytes, Dict[str, Any]]) -> bool:
        """Send a message to a specific connection."""
        wrapper = self.get_connection(connection_id)
        if not wrapper or not wrapper.is_connected:
            return False
        
        try:
            await wrapper.send(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to connection {connection_id}: {e}")
            await self.disconnect_connection(connection_id)
            return False
    
    async def broadcast_message(self, message: Union[str, bytes, Dict[str, Any]], exclude: Optional[set] = None) -> int:
        """Broadcast a message to all active connections."""
        exclude = exclude or set()
        sent_count = 0
        failed_connections = []
        
        for connection_id, wrapper in self._active_connections.items():
            if connection_id in exclude:
                continue
                
            if not wrapper.is_connected:
                failed_connections.append(connection_id)
                continue
                
            try:
                await wrapper.send(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Cleanup failed connections
        for connection_id in failed_connections:
            await self.disconnect_connection(connection_id)
        
        return sent_count
    
    async def disconnect_connection(self, connection_id: str) -> None:
        """Disconnect and cleanup a WebSocket connection."""
        wrapper = self._active_connections.pop(connection_id, None)
        self._connection_metadata.pop(connection_id, None)
        
        if wrapper:
            try:
                await wrapper.close()
            except Exception as e:
                logger.warning(f"Error closing connection {connection_id}: {e}")
            
            logger.info(f"Disconnected WebSocket connection {connection_id}")
    
    async def cleanup_all_connections(self) -> None:
        """Cleanup all active connections."""
        connection_ids = list(self._active_connections.keys())
        for connection_id in connection_ids:
            await self.disconnect_connection(connection_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._active_connections)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a connection."""
        if connection_id not in self._active_connections:
            return None
            
        wrapper = self._active_connections[connection_id]
        metadata = self._connection_metadata.get(connection_id, {})
        
        return {
            "connection_id": connection_id,
            "connection_type": wrapper.connection_type,
            "is_connected": wrapper.is_connected,
            "metadata": metadata
        }


# Global instance
_websocket_manager = ModernWebSocketManager()


def get_modern_websocket_manager() -> ModernWebSocketManager:
    """Get the global WebSocket manager instance."""
    return _websocket_manager


@asynccontextmanager
async def websocket_connection_context(connection_id: str, websocket: Any, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for WebSocket connection lifecycle."""
    manager = get_modern_websocket_manager()
    
    try:
        wrapper = manager.register_connection(connection_id, websocket, metadata)
        yield wrapper
    finally:
        await manager.disconnect_connection(connection_id)


# Compatibility aliases for legacy code
WebSocketClientProtocol = ClientConnection if WEBSOCKETS_AVAILABLE else Any
WebSocketServerProtocol = ServerConnection if WEBSOCKETS_AVAILABLE else Any

# Export deprecation warnings for legacy imports
def _warn_legacy_usage(old_name: str, new_name: str):
    """Issue deprecation warning for legacy usage."""
    warnings.warn(
        f"{old_name} is deprecated. Use {new_name} instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Legacy compatibility functions (with warnings)
def get_legacy_client_protocol():
    _warn_legacy_usage("get_legacy_client_protocol", "websockets.ClientConnection")
    return ClientConnection if WEBSOCKETS_AVAILABLE else None

def get_legacy_server_protocol():
    _warn_legacy_usage("get_legacy_server_protocol", "websockets.ServerConnection")  
    return ServerConnection if WEBSOCKETS_AVAILABLE else None


__all__ = [
    "ModernWebSocketWrapper",
    "ModernWebSocketManager", 
    "ModernWebSocketProtocol",
    "get_modern_websocket_manager",
    "websocket_connection_context",
    "WebSocketClientProtocol",
    "WebSocketServerProtocol"
]