"""
MCP WebSocket Handler

Handles WebSocket connections for MCP protocol.
Maintains single responsibility under 450-line limit.
"""

import json
import time
from typing import Optional

from fastapi import WebSocket

from netra_backend.app.logging_config import CentralLogger
from netra_backend.app.services.mcp_service import MCPService

logger = CentralLogger()


class MCPWebSocketHandler:
    """Handles MCP WebSocket connections"""
    
    def __init__(self, mcp_service: MCPService):
        self.mcp_service = mcp_service
    
    async def handle_websocket(
        self, 
        websocket: WebSocket, 
        api_key: Optional[str] = None
    ) -> None:
        """WebSocket endpoint for MCP"""
        await _handle_websocket_connection(self, websocket, api_key)
    
    async def _handle_websocket_session(self, websocket: WebSocket, api_key: Optional[str]) -> Optional[str]:
        """Handle WebSocket session lifecycle"""
        session_id = None
        try:
            return await _process_websocket_session(self, websocket, api_key)
        except Exception as e:
            await self._handle_websocket_error(websocket, e)
            return session_id
    
    async def _handle_websocket_error(self, websocket: WebSocket, error: Exception) -> None:
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}", exc_info=True)
        await websocket.close()
    
    async def _create_session(self, api_key: Optional[str]) -> str:
        """Create WebSocket session"""
        return await self.mcp_service.create_session(
            metadata={"transport": "websocket", "api_key": api_key is not None}
        )
    
    async def _send_session_created(self, websocket: WebSocket, session_id: str) -> None:
        """Send session created message"""
        await websocket.send_json({
            "type": "session_created",
            "payload": {"session_id": session_id}
        })
    
    async def _handle_messages(self, websocket: WebSocket, session_id: str) -> None:
        """Handle incoming WebSocket messages"""
        while True:
            try:
                # Receive raw text to validate format
                raw_message = await websocket.receive_text()
                
                # Parse JSON
                try:
                    data = json.loads(raw_message)
                except json.JSONDecodeError as e:
                    await websocket.send_json({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": str(e)
                        },
                        "id": None
                    })
                    continue
                
                # Validate JSON-RPC format
                if not self._is_valid_jsonrpc(data):
                    error_msg = "Invalid JSON-RPC format. Expected: {\"jsonrpc\": \"2.0\", \"method\": \"...\", \"id\": ...}"
                    if isinstance(data, dict) and data.get("type") == "ping":
                        error_msg += ". This endpoint expects JSON-RPC format, not regular JSON. Use /ws for regular JSON messages."
                    
                    await websocket.send_json({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                            "data": error_msg
                        },
                        "id": data.get("id") if isinstance(data, dict) else None
                    })
                    continue
                
                await self.mcp_service.update_session_activity(session_id)
                response = await self._process_message(data, session_id)
                await websocket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error handling MCP WebSocket message: {e}", exc_info=True)
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    },
                    "id": None
                })
    
    def _is_valid_jsonrpc(self, data) -> bool:
        """Validate JSON-RPC 2.0 format"""
        if not isinstance(data, dict):
            return False
        
        # Must have jsonrpc field with value "2.0"
        if data.get("jsonrpc") != "2.0":
            return False
        
        # Must have method field for requests
        if "method" not in data:
            return False
        
        # Must have id field (can be None for notifications)
        if "id" not in data:
            return False
        
        return True
    
    async def _process_message(self, data: dict, session_id: str) -> dict:
        """Process WebSocket message"""
        method = data.get("method")
        message_id = data.get("id")
        
        # Handle ping method specially for validation
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "pong": True,
                    "timestamp": time.time(),
                    "session_id": session_id
                },
                "id": message_id
            }
        
        # For other methods, return not implemented
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": f"Method '{method}' is not implemented yet"
            },
            "id": message_id
        }
    
    async def _cleanup_session(self, session_id: Optional[str]) -> None:
        """Clean up WebSocket session"""
        if session_id:
            await self.mcp_service.close_session(session_id)


def _build_websocket_response(session_id: str) -> dict:
    """Build WebSocket response message"""
    return {
        "type": "response",
        "payload": {
            "session_id": session_id,
            "status": "not_implemented",
            "message": "WebSocket MCP transport pending full implementation"
        }
    }


async def _handle_websocket_connection(
    handler, websocket: WebSocket, api_key: Optional[str]
) -> None:
    """Handle complete WebSocket connection lifecycle"""
    await websocket.accept()
    session_id = await handler._handle_websocket_session(websocket, api_key)
    await handler._cleanup_session(session_id)


async def _process_websocket_session(
    handler, websocket: WebSocket, api_key: Optional[str]
) -> Optional[str]:
    """Process WebSocket session setup and message handling"""
    session_id = await handler._create_session(api_key)
    await handler._send_session_created(websocket, session_id)
    await handler._handle_messages(websocket, session_id)
    return session_id