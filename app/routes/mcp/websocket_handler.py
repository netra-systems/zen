"""
MCP WebSocket Handler

Handles WebSocket connections for MCP protocol.
Maintains single responsibility under 300-line limit.
"""

from typing import Optional
from fastapi import WebSocket
from app.services.mcp_service import MCPService
from app.logging_config import CentralLogger

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
        """
        WebSocket endpoint for MCP
        
        Connect with: ws://localhost:8000/api/mcp/ws?api_key=YOUR_KEY
        """
        await websocket.accept()
        session_id = None
        
        try:
            session_id = await self._create_session(api_key)
            await self._send_session_created(websocket, session_id)
            await self._handle_messages(websocket, session_id)
            
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            await websocket.close()
        finally:
            await self._cleanup_session(session_id)
    
    async def _create_session(self, api_key: Optional[str]) -> str:
        """Create WebSocket session"""
        return await self.mcp_service.create_session(
            metadata={"transport": "websocket", "api_key": api_key is not None}
        )
    
    async def _send_session_created(self, websocket: WebSocket, session_id: str) -> None:
        """Send session created message"""
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id
        })
    
    async def _handle_messages(self, websocket: WebSocket, session_id: str) -> None:
        """Handle incoming WebSocket messages"""
        while True:
            data = await websocket.receive_json()
            await self.mcp_service.update_session_activity(session_id)
            
            response = await self._process_message(data, session_id)
            await websocket.send_json(response)
    
    async def _process_message(self, data: dict, session_id: str) -> dict:
        """Process WebSocket message"""
        # This would need proper MCP protocol handling
        return {
            "type": "response",
            "session_id": session_id,
            "status": "not_implemented",
            "message": "WebSocket MCP transport pending full implementation"
        }
    
    async def _cleanup_session(self, session_id: Optional[str]) -> None:
        """Clean up WebSocket session"""
        if session_id:
            await self.mcp_service.close_session(session_id)