"""
WebSocket Token Refresh Handler - Seamless token rotation during active sessions.

CRITICAL: This module ensures uninterrupted WebSocket communication during token refresh.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

# JWT import removed - SSOT compliance: all JWT operations delegated to auth service
from fastapi import WebSocket, WebSocketDisconnect

from netra_backend.app.auth_integration.auth import auth_client
from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class TokenRefreshHandler:
    """Handles seamless token refresh for active WebSocket connections."""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.config = get_configuration()
        self.active_refreshes: Dict[str, asyncio.Task] = {}
        self.refresh_locks: Dict[str, asyncio.Lock] = {}
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        
        # Performance metrics
        self.metrics = {
            "total_refreshes": 0,
            "successful_refreshes": 0,
            "failed_refreshes": 0,
            "avg_refresh_time": 0.0,
            "max_refresh_time": 0.0
        }
    
    async def initialize_connection(self, websocket: WebSocket, token: str) -> Dict[str, Any]:
        """Initialize WebSocket connection with token tracking."""
        try:
            # Validate initial token
            validation = await auth_client.validate_token_jwt(token)
            if not validation or not validation.get("valid"):
                return {"success": False, "error": "Invalid token"}
            
            user_id = validation.get("user_id")
            
            # Store connection info
            connection_id = f"{user_id}_{time.time()}"
            self.token_cache[connection_id] = {
                "token": token,
                "user_id": user_id,
                "websocket": websocket,
                "last_refresh": time.time(),
                "refresh_count": 0
            }
            
            # Schedule automatic refresh check
            refresh_task = asyncio.create_task(
                self._auto_refresh_monitor(connection_id, token)
            )
            self.active_refreshes[connection_id] = refresh_task
            
            return {
                "success": True,
                "connection_id": connection_id,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize connection: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_token_refresh(
        self, 
        connection_id: str, 
        old_token: str, 
        new_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle token refresh for active connection."""
        start_time = time.time()
        
        # Ensure only one refresh per connection at a time
        if connection_id not in self.refresh_locks:
            self.refresh_locks[connection_id] = asyncio.Lock()
        
        async with self.refresh_locks[connection_id]:
            try:
                # Get connection info
                conn_info = self.token_cache.get(connection_id)
                if not conn_info:
                    return {"success": False, "error": "Connection not found"}
                
                # If no new token provided, refresh the old one
                if not new_token:
                    refresh_result = await self._refresh_token(old_token)
                    if not refresh_result:
                        self.metrics["failed_refreshes"] += 1
                        return {"success": False, "error": "Token refresh failed"}
                    new_token = refresh_result.get("access_token")
                
                # Validate new token
                validation = await auth_client.validate_token_jwt(new_token)
                if not validation or not validation.get("valid"):
                    self.metrics["failed_refreshes"] += 1
                    return {"success": False, "error": "Invalid new token"}
                
                # Update connection with new token
                conn_info["token"] = new_token
                conn_info["last_refresh"] = time.time()
                conn_info["refresh_count"] += 1
                
                # Notify client of successful refresh
                websocket = conn_info.get("websocket")
                if websocket:
                    await self._send_refresh_notification(websocket, new_token)
                
                # Update metrics
                refresh_time = time.time() - start_time
                self._update_metrics(refresh_time, success=True)
                
                logger.info(f"Token refreshed for connection {connection_id} in {refresh_time:.3f}s")
                
                return {
                    "success": True,
                    "new_token": new_token,
                    "refresh_time": refresh_time,
                    "refresh_count": conn_info["refresh_count"]
                }
                
            except Exception as e:
                logger.error(f"Token refresh error for {connection_id}: {e}")
                self.metrics["failed_refreshes"] += 1
                return {"success": False, "error": str(e)}
    
    async def _auto_refresh_monitor(self, connection_id: str, initial_token: str):
        """Monitor token expiration and auto-refresh when needed."""
        while connection_id in self.token_cache:
            try:
                conn_info = self.token_cache.get(connection_id)
                if not conn_info:
                    break
                
                current_token = conn_info["token"]
                
                # Check if token needs refresh
                if await self._needs_refresh(current_token):
                    logger.info(f"Auto-refreshing token for connection {connection_id}")
                    
                    # Perform refresh
                    refresh_result = await self.handle_token_refresh(
                        connection_id, 
                        current_token
                    )
                    
                    if not refresh_result.get("success"):
                        logger.error(f"Auto-refresh failed for {connection_id}")
                        # Notify client of refresh failure
                        websocket = conn_info.get("websocket")
                        if websocket:
                            await self._send_refresh_error(websocket)
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-refresh monitor error for {connection_id}: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _needs_refresh(self, token: str) -> bool:
        """Check if token needs refresh (expires within 5 minutes) - USES AUTH SERVICE."""
        try:
            # CRITICAL SECURITY FIX: Use auth service to check token expiry
            # Local JWT decoding is a security vulnerability
            validation = await auth_client.validate_token_jwt(token)
            if not validation or not validation.get("valid"):
                return True  # Token is invalid, needs refresh
            
            # Check if token expires soon
            expires_at = validation.get("expires_at")
            if not expires_at:
                return True  # No expiry info, refresh to be safe
            
            # Parse expiry time
            if isinstance(expires_at, (int, float)):
                exp_time = datetime.fromtimestamp(expires_at)
            else:
                # Try to parse as ISO string
                from datetime import datetime
                exp_time = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
            
            time_until_expiry = exp_time - datetime.utcnow()
            
            # Refresh if less than 5 minutes until expiry
            return time_until_expiry < timedelta(minutes=5)
            
        except Exception as e:
            logger.error(f"Failed to check token expiry through auth service: {e}")
            return True  # Err on side of caution
    
    async def _refresh_token(self, old_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token through auth service - CRITICAL SECURITY FIX."""
        try:
            # CRITICAL SECURITY FIX: ALL token operations MUST go through auth service
            # Creating tokens locally is a major security vulnerability
            logger.info("Refreshing token through auth service")
            
            # Use auth service to refresh the token
            refresh_result = await auth_client.refresh_token(old_token)
            
            if not refresh_result or not refresh_result.get("success"):
                logger.error("Auth service token refresh failed")
                return None
            
            return {
                "access_token": refresh_result.get("access_token"),
                "token_type": "Bearer",
                "expires_in": refresh_result.get("expires_in", 3600)
            }
            
        except Exception as e:
            logger.error(f"Token refresh through auth service failed: {e}")
            return None
    
    async def _send_refresh_notification(self, websocket: WebSocket, new_token: str):
        """Send token refresh notification to client."""
        try:
            await websocket.send_json({
                "type": "token_refreshed",
                "data": {
                    "new_token": new_token,
                    "timestamp": time.time()
                }
            })
        except Exception as e:
            logger.error(f"Failed to send refresh notification: {e}")
    
    async def _send_refresh_error(self, websocket: WebSocket):
        """Send refresh error notification to client."""
        try:
            await websocket.send_json({
                "type": "token_refresh_failed",
                "data": {
                    "error": "Token refresh failed",
                    "action": "Please re-authenticate",
                    "timestamp": time.time()
                }
            })
        except Exception as e:
            logger.error(f"Failed to send refresh error: {e}")
    
    def _update_metrics(self, refresh_time: float, success: bool):
        """Update performance metrics."""
        self.metrics["total_refreshes"] += 1
        
        if success:
            self.metrics["successful_refreshes"] += 1
            
            # Update average refresh time
            total = self.metrics["total_refreshes"]
            avg = self.metrics["avg_refresh_time"]
            self.metrics["avg_refresh_time"] = (avg * (total - 1) + refresh_time) / total
            
            # Update max refresh time
            if refresh_time > self.metrics["max_refresh_time"]:
                self.metrics["max_refresh_time"] = refresh_time
    
    async def cleanup_connection(self, connection_id: str):
        """Clean up connection resources."""
        try:
            # Cancel auto-refresh task
            if connection_id in self.active_refreshes:
                self.active_refreshes[connection_id].cancel()
                del self.active_refreshes[connection_id]
            
            # Remove from cache
            if connection_id in self.token_cache:
                del self.token_cache[connection_id]
            
            # Remove lock
            if connection_id in self.refresh_locks:
                del self.refresh_locks[connection_id]
            
            logger.info(f"Cleaned up connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup connection {connection_id}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.metrics,
            "active_connections": len(self.token_cache),
            "active_refreshes": len(self.active_refreshes)
        }


class TokenRefreshMiddleware:
    """Middleware for handling token refresh in WebSocket connections."""
    
    def __init__(self):
        self.handler = None
    
    def initialize(self, ws_manager: WebSocketManager):
        """Initialize middleware with WebSocket manager."""
        self.handler = TokenRefreshHandler(ws_manager)
    
    async def process_message(
        self, 
        websocket: WebSocket,
        message: Dict[str, Any],
        connection_id: str
    ) -> Optional[Dict[str, Any]]:
        """Process WebSocket messages for token refresh."""
        message_type = message.get("type")
        
        if message_type == "token_refresh":
            # Handle explicit token refresh request
            old_token = message.get("old_token")
            new_token = message.get("new_token")
            
            if not old_token:
                return {
                    "type": "error",
                    "error": "Missing old_token"
                }
            
            result = await self.handler.handle_token_refresh(
                connection_id,
                old_token,
                new_token
            )
            
            return {
                "type": "token_refresh_response",
                "data": result
            }
        
        # Pass through other messages
        return None
    
    async def on_connect(self, websocket: WebSocket, token: str) -> Dict[str, Any]:
        """Handle WebSocket connection with token."""
        if not self.handler:
            return {"success": False, "error": "Handler not initialized"}
        
        return await self.handler.initialize_connection(websocket, token)
    
    async def on_disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        if self.handler:
            await self.handler.cleanup_connection(connection_id)


# Global middleware instance
token_refresh_middleware = TokenRefreshMiddleware()


def get_token_refresh_handler() -> TokenRefreshHandler:
    """Get the token refresh handler instance."""
    if not token_refresh_middleware.handler:
        raise RuntimeError("Token refresh handler not initialized")
    return token_refresh_middleware.handler