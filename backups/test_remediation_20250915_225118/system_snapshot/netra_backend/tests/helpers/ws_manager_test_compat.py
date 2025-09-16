"""WebSocket Manager Test Compatibility Layer.

Provides connection-ID-based API for test compatibility while maintaining
the 25-line-per-function limit as per CLAUDE.md requirements.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import ConnectionInfo

logger = central_logger.get_logger(__name__)

class WebSocketTestCompatibilityMixin:
    """Mixin providing test-compatible API methods."""

    def _setup_connection_tracking(self) -> None:
        """Initialize connection tracking attributes."""
        self.connections_dict: Dict[str, WebSocket] = {}
        self.connection_info_dict: Dict[str, ConnectionInfo] = {}
        self.connection_roles: Dict[str, Optional[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None, 
                     role: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Connect with connection-ID-based API (bypasses modular components for tests)."""
        conn_info = self._create_connection_info(connection_id, user_id, role, metadata, websocket)
        self.connections_dict[connection_id] = websocket
        self.connection_info_dict[connection_id] = conn_info
        self.connection_roles[connection_id] = role
        self.connection_metadata[connection_id] = metadata or {}

    def _create_connection_info(self, connection_id: str, user_id: Optional[str], 
                               role: Optional[str], metadata: Optional[Dict[str, Any]], websocket) -> ConnectionInfo:
        """Create ConnectionInfo object with correct parameters."""
        # Create a simple info object for test compatibility - role and metadata are stored separately
        return ConnectionInfo(
            websocket=websocket,
            user_id=user_id or f"test_user_{connection_id}",
            connected_at=datetime.now(timezone.utc),
            connection_id=connection_id
        )

    async def disconnect(self, connection_id: str, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        """Disconnect with connection-ID-based API."""
        websocket = self.connections_dict.get(connection_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await self._safe_websocket_close(websocket, code or 1000, reason or "Normal closure")
        self._cleanup_connection(connection_id)

    async def _safe_websocket_close(self, websocket: WebSocket, code: int, reason: str) -> None:
        """Safely close websocket connection."""
        try:
            await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing websocket: {e}")

    def _cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection from tracking dictionaries."""
        self.connections_dict.pop(connection_id, None)
        self.connection_info_dict.pop(connection_id, None)
        self.connection_roles.pop(connection_id, None)
        self.connection_metadata.pop(connection_id, None)

    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Send message to specific connection ID."""
        websocket = self.connections_dict.get(connection_id)
        if websocket:
            if websocket.client_state == WebSocketState.CONNECTED:
                await self._safe_send_json(websocket, message)
            elif websocket.client_state == WebSocketState.DISCONNECTED:
                self._cleanup_connection(connection_id)

    async def _safe_send_json(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Safely send JSON message to websocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Error sending message: {e}")
            # If sending fails, clean up the connection
            connection_id = self._find_connection_id(websocket)
            if connection_id:
                self._cleanup_connection(connection_id)

    def _find_connection_id(self, websocket: WebSocket) -> Optional[str]:
        """Find connection ID for a given websocket."""
        for conn_id, ws in self.connections_dict.items():
            if ws is websocket:
                return conn_id
        return None

    async def send_to_connection(self, connection_id: str, message_type: str, data: Dict[str, Any]) -> None:
        """Send formatted message to specific connection."""
        formatted_message = {"type": message_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        await self.send_message(connection_id, formatted_message)

    async def send_to_user(self, user_id: str, message_type: str, data: Dict[str, Any]) -> None:
        """Send message to all connections for a user."""
        user_connections = [cid for cid, info in self.connection_info_dict.items() if info.user_id == user_id]
        for connection_id in user_connections:
            await self.send_to_connection(connection_id, message_type, data)

    async def send_to_role(self, role: str, message_type: str, data: Dict[str, Any]) -> None:
        """Send message to all connections with specific role."""
        role_connections = [cid for cid, conn_role in self.connection_roles.items() if conn_role == role]
        for connection_id in role_connections:
            await self.send_to_connection(connection_id, message_type, data)

    def get_connection(self, connection_id: str) -> Optional[WebSocket]:
        """Get WebSocket by connection ID."""
        return self.connections_dict.get(connection_id)

    def is_connected(self, connection_id: str) -> bool:
        """Check if connection ID is connected."""
        websocket = self.connections_dict.get(connection_id)
        return websocket is not None and websocket.client_state == WebSocketState.CONNECTED

    def get_all_connections(self) -> Dict[str, WebSocket]:
        """Get all connections dictionary."""
        return self.connections_dict.copy()

    @property
    def connections(self) -> Dict[str, WebSocket]:
        """Property access to connections."""
        return self.connections_dict

    @property
    def connection_info(self) -> Dict[str, ConnectionInfo]:
        """Property access to connection info."""
        return self.connection_info_dict

    async def send_error(self, connection_id: str, error_message: str, error_code: Optional[str] = None) -> None:
        """Send error message to specific connection."""
        error_data = {"error": error_message}
        if error_code:
            error_data["code"] = error_code
        await self.send_to_connection(connection_id, "error", error_data)

    async def send_success(self, connection_id: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Send success message to specific connection."""
        success_data = {"message": message}
        if data:
            success_data["data"] = data
        await self.send_to_connection(connection_id, "success", success_data)

    async def send_notification(self, connection_id: str, title: str, level: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Send notification message to specific connection."""
        notification_data = {"title": title, "level": level}
        if metadata:
            notification_data["metadata"] = metadata
        await self.send_to_connection(connection_id, "notification", notification_data)

    async def send_status_update(self, connection_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Send status update to specific connection."""
        status_data = {"status": status}
        if details:
            status_data["details"] = details
        await self.send_to_connection(connection_id, "status_update", status_data)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None) -> None:
        """Broadcast message to all connections with optional exclusion."""
        exclude = exclude or []
        for connection_id, websocket in self.connections_dict.items():
            if connection_id not in exclude:
                await self.send_message(connection_id, message)