"""
WebSocket Authentication Service
Handles authentication for WebSocket connections in the analytics service
"""
import logging
from typing import Dict, Any, Optional, List
import jwt
import time

logger = logging.getLogger(__name__)

class WebSocketAuthService:
    """Service for authenticating WebSocket connections."""
    
    def __init__(self, secret_key: str = "analytics-ws-secret"):
        """Initialize WebSocket auth service."""
        self.secret_key = secret_key
        self.active_sessions = {}
    
    async def authenticate_connection(self, token: str) -> Dict[str, Any]:
        """Authenticate a WebSocket connection."""
        try:
            if not token:
                return {"authenticated": False, "error": "No token provided"}
            
            # For simplicity, just validate token format
            if token.startswith("ws_"):
                user_id = token.replace("ws_", "")
                
                session_info = {
                    "user_id": user_id,
                    "authenticated": True,
                    "permissions": ["read", "subscribe"],
                    "connected_at": time.time()
                }
                
                self.active_sessions[token] = session_info
                return session_info
            else:
                return {"authenticated": False, "error": "Invalid token format"}
                
        except Exception as e:
            logger.error(f"WebSocket auth error: {e}")
            return {"authenticated": False, "error": str(e)}
    
    async def authorize_action(self, token: str, action: str) -> bool:
        """Check if token is authorized for a specific action."""
        try:
            session = self.active_sessions.get(token)
            if not session or not session.get("authenticated"):
                return False
            
            permissions = session.get("permissions", [])
            
            # Basic permission mapping
            action_permissions = {
                "subscribe": ["read", "subscribe"],
                "publish": ["write", "publish"],
                "admin": ["admin"]
            }
            
            required_perms = action_permissions.get(action, ["read"])
            return any(perm in permissions for perm in required_perms)
            
        except Exception as e:
            logger.error(f"WebSocket authorization error: {e}")
            return False
    
    def get_session_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get session information for a token."""
        return self.active_sessions.get(token)
    
    def disconnect_session(self, token: str):
        """Remove session when disconnecting."""
        if token in self.active_sessions:
            del self.active_sessions[token]
            logger.debug(f"WebSocket session disconnected: {token[:10]}...")