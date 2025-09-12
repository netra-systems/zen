"""
Embedded WebSocket Server for Integration Tests

This module provides an embedded WebSocket server for testing WebSocket functionality
without requiring Docker or external services. It's designed to support the CRITICAL
WebSocket events needed for chat business value delivery.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Eliminate WebSocket test failures blocking development velocity
- Value Impact: Enable reliable testing of chat features without Docker dependencies
- Strategic Impact: Faster CI/CD and reduced development friction

CRITICAL: This server emits all 5 required WebSocket events for chat business value:
1. agent_started
2. agent_thinking  
3. tool_executing
4. tool_completed
5. agent_completed
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any, Callable
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import uvicorn
from contextlib import asynccontextmanager
import threading
import socket

logger = logging.getLogger(__name__)


class EmbeddedWebSocketConnection:
    """Represents a WebSocket connection in the embedded server."""
    
    def __init__(self, websocket: WebSocket, user_id: str = None):
        self.websocket = websocket
        self.user_id = user_id or f"test_user_{int(time.time())}"
        self.connection_id = f"embedded_{self.user_id}_{int(time.time())}"
        self.connected_at = datetime.utcnow()
        self.message_count = 0
        
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket connection."""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_json(message)
                return True
            else:
                logger.warning(f"Cannot send to disconnected WebSocket: {self.connection_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return False


class EmbeddedWebSocketServer:
    """
    Embedded WebSocket server for testing.
    
    Provides a lightweight WebSocket server that can be started/stopped
    programmatically for integration tests.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = None):
        self.host = host
        self.port = port or self._find_free_port()
        self.app = FastAPI(title="Embedded WebSocket Test Server")
        self.connections: Dict[str, EmbeddedWebSocketConnection] = {}
        self.server = None
        self.server_task = None
        self.message_handlers: Dict[str, Callable] = {}
        
        # Configure WebSocket routes
        self._setup_routes()
        
        # Built-in handlers for critical events
        self._setup_builtin_handlers()
        
        logger.info(f"EmbeddedWebSocketServer initialized on {self.host}:{self.port}")
    
    def _find_free_port(self) -> int:
        """Find a free port for the server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _setup_routes(self):
        """Setup WebSocket routes."""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint for testing."""
            await self._handle_websocket_connection(websocket)
        
        @self.app.websocket("/websocket")
        async def websocket_legacy_endpoint(websocket: WebSocket):
            """Legacy WebSocket endpoint for backward compatibility."""
            await self._handle_websocket_connection(websocket)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "embedded_websocket_server",
                "connections": len(self.connections),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _setup_builtin_handlers(self):
        """Setup built-in message handlers for critical events."""
        
        async def handle_chat_message(connection: EmbeddedWebSocketConnection, message: Dict[str, Any]):
            """Handle chat messages and emit all 5 critical events."""
            content = message.get("payload", {}).get("content", "")
            user_id = connection.user_id
            
            if not content:
                await connection.send_message({
                    "type": "error",
                    "message": "Empty message content"
                })
                return
            
            # CRITICAL: Send all 5 required WebSocket events for chat business value
            logger.info(f"[U+1F916] Emitting CRITICAL WebSocket events for: '{content}'")
            
            # 1. agent_started
            await connection.send_message({
                "type": "agent_started",
                "event": "agent_started",
                "agent_name": "TestChatAgent",
                "user_id": user_id,
                "timestamp": time.time(),
                "message": f"Processing your message: {content}"
            })
            await asyncio.sleep(0.1)
            
            # 2. agent_thinking
            await connection.send_message({
                "type": "agent_thinking",
                "event": "agent_thinking", 
                "reasoning": f"Analyzing your request: {content}",
                "user_id": user_id,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.1)
            
            # 3. tool_executing
            await connection.send_message({
                "type": "tool_executing",
                "event": "tool_executing",
                "tool_name": "response_generator",
                "parameters": {"query": content},
                "user_id": user_id,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.1)
            
            # 4. tool_completed
            response_content = f"Echo response: {content}"
            await connection.send_message({
                "type": "tool_completed",
                "event": "tool_completed",
                "tool_name": "response_generator",
                "result": response_content,
                "user_id": user_id,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.1)
            
            # 5. agent_completed
            await connection.send_message({
                "type": "agent_completed",
                "event": "agent_completed",
                "agent_name": "TestChatAgent",
                "final_response": response_content,
                "user_id": user_id,
                "timestamp": time.time()
            })
            
            logger.info(f" PASS:  Successfully sent ALL 5 critical WebSocket events to {user_id}")
        
        async def handle_ping(connection: EmbeddedWebSocketConnection, message: Dict[str, Any]):
            """Handle ping messages."""
            await connection.send_message({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Register built-in handlers
        self.message_handlers["chat"] = handle_chat_message
        self.message_handlers["user_message"] = handle_chat_message
        self.message_handlers["ping"] = handle_ping
    
    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle incoming WebSocket connections."""
        connection_id = None
        
        try:
            # Accept connection (no auth required for testing)
            await websocket.accept()
            
            # Create connection
            connection = EmbeddedWebSocketConnection(websocket)
            connection_id = connection.connection_id
            self.connections[connection_id] = connection
            
            logger.info(f"WebSocket connected: {connection_id}")
            
            # Send welcome message
            await connection.send_message({
                "type": "connection_established",
                "connection_id": connection_id,
                "user_id": connection.user_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "message": "Embedded WebSocket server connected"
            })
            
            # Message handling loop
            while True:
                try:
                    # Receive message
                    raw_message = await websocket.receive_text()
                    connection.message_count += 1
                    
                    logger.debug(f"Received message from {connection_id}: {raw_message}")
                    
                    # Parse message
                    try:
                        message_data = json.loads(raw_message)
                    except json.JSONDecodeError as e:
                        await connection.send_message({
                            "type": "error",
                            "message": f"Invalid JSON: {str(e)}"
                        })
                        continue
                    
                    # Route message to handler
                    message_type = message_data.get("type", "unknown")
                    if message_type in self.message_handlers:
                        await self.message_handlers[message_type](connection, message_data)
                    else:
                        # Default echo response
                        await connection.send_message({
                            "type": "echo",
                            "original_message": message_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    try:
                        await connection.send_message({
                            "type": "error",
                            "message": f"Server error: {str(e)}"
                        })
                    except:
                        break  # Connection likely broken
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup connection
            if connection_id and connection_id in self.connections:
                del self.connections[connection_id]
                logger.info(f"Cleaned up connection: {connection_id}")
    
    async def start(self) -> str:
        """Start the embedded WebSocket server."""
        if self.server_task and not self.server_task.done():
            logger.warning("Server already running")
            return f"ws://{self.host}:{self.port}"
        
        try:
            # Create server config
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="error",  # Reduce noise in tests
                access_log=False,
                loop="asyncio"
            )
            
            # Create server
            self.server = uvicorn.Server(config)
            
            # Start server in background task
            self.server_task = asyncio.create_task(self.server.serve())
            
            # Wait for server to be ready with longer timeout
            await asyncio.sleep(0.5)
            
            # Verify server is accessible with retries
            for attempt in range(10):
                try:
                    import aiohttp
                    timeout = aiohttp.ClientTimeout(total=1.0)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(f"http://{self.host}:{self.port}/health") as resp:
                            if resp.status == 200:
                                websocket_url = f"ws://{self.host}:{self.port}/ws"
                                logger.info(f"Embedded WebSocket server started: {websocket_url}")
                                return websocket_url
                except Exception as e:
                    logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.2)
            
            # If health check fails, still return URL (server might be running)
            websocket_url = f"ws://{self.host}:{self.port}/ws"
            logger.warning(f"Embedded WebSocket server started but health check failed: {websocket_url}")
            return websocket_url
            
        except Exception as e:
            logger.error(f"Failed to start embedded WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Stop the embedded WebSocket server."""
        try:
            # Close all connections
            for connection in list(self.connections.values()):
                try:
                    await connection.websocket.close()
                except:
                    pass
            self.connections.clear()
            
            # Stop server
            if self.server:
                self.server.should_exit = True
                if self.server_task and not self.server_task.done():
                    self.server_task.cancel()
                    try:
                        await self.server_task
                    except asyncio.CancelledError:
                        pass
            
            logger.info("Embedded WebSocket server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping embedded WebSocket server: {e}")
    
    def add_message_handler(self, message_type: str, handler: Callable):
        """Add custom message handler."""
        self.message_handlers[message_type] = handler
        logger.info(f"Added message handler for: {message_type}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connections)
    
    def get_websocket_url(self) -> str:
        """Get the WebSocket URL."""
        return f"ws://{self.host}:{self.port}/ws"


@asynccontextmanager
async def embedded_websocket_server(host: str = "127.0.0.1", port: int = None):
    """
    Context manager for embedded WebSocket server.
    
    Usage:
        async with embedded_websocket_server() as websocket_url:
            # Use websocket_url for testing
            pass
    """
    server = EmbeddedWebSocketServer(host=host, port=port)
    try:
        websocket_url = await server.start()
        yield websocket_url
    finally:
        await server.stop()


class EmbeddedWebSocketTestHelper:
    """
    Helper class for WebSocket testing with embedded server.
    
    Provides utilities for testing WebSocket functionality without
    requiring external services or Docker.
    """
    
    def __init__(self):
        self.server: Optional[EmbeddedWebSocketServer] = None
        self.websocket_url: Optional[str] = None
    
    async def setup_test_server(self, host: str = "127.0.0.1", port: int = None) -> str:
        """Setup embedded WebSocket server for testing."""
        self.server = EmbeddedWebSocketServer(host=host, port=port)
        self.websocket_url = await self.server.start()
        return self.websocket_url
    
    async def teardown_test_server(self):
        """Teardown embedded WebSocket server."""
        if self.server:
            await self.server.stop()
            self.server = None
            self.websocket_url = None
    
    async def test_websocket_connection(self, websocket_url: str = None) -> bool:
        """Test WebSocket connection and basic functionality."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL available")
        
        try:
            import websockets
            
            async with websockets.connect(url) as websocket:
                # Test ping/pong
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": time.time()
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                
                return data.get("type") == "pong"
                
        except Exception as e:
            logger.error(f"WebSocket connection test failed: {e}")
            return False
    
    async def test_critical_events(self, websocket_url: str = None) -> Dict[str, bool]:
        """Test that all 5 critical WebSocket events are emitted."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL available")
        
        critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        received_events = {event: False for event in critical_events}
        
        try:
            import websockets
            
            async with websockets.connect(url) as websocket:
                # Send chat message to trigger critical events
                await websocket.send(json.dumps({
                    "type": "chat",
                    "payload": {
                        "content": "test message for critical events"
                    }
                }))
                
                # Collect events for up to 5 seconds
                timeout = 5.0
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        data = json.loads(response)
                        event_type = data.get("type") or data.get("event")
                        
                        if event_type in critical_events:
                            received_events[event_type] = True
                            logger.info(f" PASS:  Received critical event: {event_type}")
                        
                        # Check if all events received
                        if all(received_events.values()):
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving event: {e}")
                        break
                
        except Exception as e:
            logger.error(f"Critical events test failed: {e}")
        
        return received_events
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        if not self.server:
            return {"error": "No server running"}
        
        return {
            "connection_count": self.server.get_connection_count(),
            "websocket_url": self.websocket_url,
            "handlers": list(self.server.message_handlers.keys())
        }


# Export main components
__all__ = [
    "EmbeddedWebSocketServer",
    "EmbeddedWebSocketConnection", 
    "embedded_websocket_server",
    "EmbeddedWebSocketTestHelper"
]