"""
MCP WebSocket Transport

Implements JSON-RPC 2.0 over WebSocket for real-time bidirectional communication.
"""

from typing import Optional, Dict, Any, Set
import json
import asyncio
from datetime import datetime, UTC
import uuid

from fastapi import WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.logging_config import CentralLogger
from app.mcp.server import MCPServer
from app.core.exceptions import NetraException

logger = CentralLogger()


class WebSocketConnection:
    """Represents a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.connected_at = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)
        self.message_count = 0
        
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON data to client"""
        try:
            if self.websocket.application_state != WebSocketState.CONNECTED:
                raise ConnectionError("WebSocket is not connected")
            await self.websocket.send_json(data)
            self.last_activity = datetime.now(UTC)
            self.message_count += 1
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            raise
            
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON data from client"""
        data = await self.websocket.receive_json()
        self.last_activity = datetime.now(UTC)
        return data


class WebSocketTransport:
    """
    WebSocket transport for MCP
    
    Used for real-time agent-to-agent communication and live IDE integrations.
    """
    
    def __init__(self, server: Optional[MCPServer] = None):
        self.server = server or MCPServer()
        self.connections: Dict[str, WebSocketConnection] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}
        
    async def handle_websocket(self, websocket: WebSocket, api_key: Optional[str] = None):
        """
        Handle WebSocket connection
        
        Args:
            websocket: FastAPI WebSocket instance
            api_key: Optional API key for authentication
        """
        session_id = str(uuid.uuid4())
        connection = None
        
        try:
            # Accept connection
            await websocket.accept()
            logger.info(f"WebSocket connection accepted: {session_id}")
            
            # Create connection object
            connection = WebSocketConnection(websocket, session_id)
            self.connections[session_id] = connection
            self.connection_locks[session_id] = asyncio.Lock()
            
            # Send welcome message
            await connection.send_json({
                "jsonrpc": "2.0",
                "method": "connection.established",
                "params": {
                    "session_id": session_id,
                    "server": "Netra MCP Server",
                    "version": "1.0.0",
                    "transport": "websocket",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            })
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(connection)
            )
            
            # Main message loop
            await self._message_loop(connection)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
            if connection:
                try:
                    await connection.send_json({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    })
                except:
                    pass
        finally:
            # Cleanup
            if session_id in self.connections:
                del self.connections[session_id]
            if session_id in self.connection_locks:
                del self.connection_locks[session_id]
                
            # Cancel heartbeat
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()
                
            # Close WebSocket if still open
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close()
                
            logger.info(f"WebSocket cleanup complete: {session_id}")
            
    async def _message_loop(self, connection: WebSocketConnection):
        """Main message processing loop"""
        while True:
            try:
                # Receive message
                data = await connection.receive_json()
                
                # Process request asynchronously
                asyncio.create_task(
                    self._process_request(connection, data)
                )
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError as e:
                await connection.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                })
            except Exception as e:
                logger.error(f"Error in message loop: {e}", exc_info=True)
                await connection.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                })
                
    async def _process_request(self, connection: WebSocketConnection, request: Dict[str, Any]):
        """Process a single request"""
        async with self.connection_locks[connection.session_id]:
            try:
                # Add transport info for initialization
                if request.get("method") == "initialize":
                    request.setdefault("params", {})
                    request["params"]["transport"] = "websocket"
                    
                # Handle through server
                response = await self.server.handle_request(
                    request,
                    connection.session_id
                )
                
                # Send response (if not a notification)
                if response:
                    await connection.send_json(response)
                    
            except Exception as e:
                logger.error(f"Error processing WebSocket request: {e}", exc_info=True)
                await connection.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Processing error: {str(e)}"
                    },
                    "id": request.get("id")
                })
                
    async def _heartbeat_loop(self, connection: WebSocketConnection):
        """Send periodic heartbeat messages"""
        try:
            while connection.session_id in self.connections:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                if connection.websocket.application_state == WebSocketState.CONNECTED:
                    await connection.send_json({
                        "jsonrpc": "2.0",
                        "method": "heartbeat",
                        "params": {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "message_count": connection.message_count
                        }
                    })
                else:
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast message to a specific session"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                
    async def broadcast_to_all(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """Broadcast message to all connected sessions"""
        exclude = exclude or set()
        
        tasks = []
        for session_id, connection in self.connections.items():
            if session_id not in exclude:
                tasks.append(connection.send_json(message))
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Broadcast error: {result}")
                    
    def get_active_sessions(self) -> list[Dict[str, Any]]:
        """Get list of active sessions"""
        return [
            {
                "session_id": session_id,
                "connected_at": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat(),
                "message_count": conn.message_count
            }
            for session_id, conn in self.connections.items()
        ]
        
    async def close_session(self, session_id: str):
        """Close a specific session"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            try:
                await connection.websocket.close()
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")
            finally:
                if session_id in self.connections:
                    del self.connections[session_id]
                if session_id in self.connection_locks:
                    del self.connection_locks[session_id]


# Global WebSocket transport instance
ws_transport = WebSocketTransport()


async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None, description="API key for authentication")
):
    """
    FastAPI WebSocket endpoint for MCP
    
    Can be mounted in main application:
    app.websocket("/mcp/ws")(websocket_endpoint)
    """
    await ws_transport.handle_websocket(websocket, api_key)