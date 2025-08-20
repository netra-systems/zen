"""DRAFT: Enhanced WebSocket endpoint fixes for DEV MODE connection issues.

This is a DRAFT implementation addressing the following issues:
1. CORS integration with WebSocket handler
2. Simplified JWT authentication flow
3. Improved connection establishment process
4. Consistent message format validation
5. Better heartbeat coordination

DO NOT DEPLOY TO PRODUCTION - THIS IS A DRAFT FOR REVIEW
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from starlette.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_async_db
from app.logging_config import central_logger
from app.clients.auth_client import auth_client
from app.websocket.unified.manager import get_unified_manager
from app.schemas.registry import WebSocketMessage, ServerMessage
from app.schemas.websocket_message_types import WebSocketValidationError
from app.core.websocket_cors import get_websocket_cors_handler, validate_websocket_origin

logger = central_logger.get_logger(__name__)
router = APIRouter()

# SIMPLIFIED WebSocket configuration for DEV MODE
DEV_WEBSOCKET_CONFIG = {
    "version": "1.0-dev",
    "features": {
        "json_first": True,
        "auth_required": True,
        "heartbeat_supported": True,
        "reconnection_supported": True,
        "cors_enabled": True,
        "dev_mode": True
    },
    "endpoints": {
        "websocket": "/ws/enhanced",
        "service_discovery": "/ws/config"
    },
    "connection_limits": {
        "max_connections_per_user": 3,  # Reduced for DEV
        "max_message_rate": 30,  # Reduced for DEV
        "max_message_size": 8192,  # 8KB
        "heartbeat_interval": 45000  # 45 seconds (longer for DEV)
    },
    "auth": {
        "methods": ["jwt_query_param"],
        "token_validation": "simplified_dev",
        "session_handling": "simplified"
    },
    "cors": {
        "enabled": True,
        "dev_mode": True,
        "check_origin": True
    }
}


class SimplifiedWebSocketAuth:
    """Simplified WebSocket authentication for DEV MODE."""
    
    def __init__(self):
        self.auth_cache = {}  # Simple in-memory cache for DEV
        self.cache_ttl = 300  # 5 minutes
    
    async def validate_token_simplified(self, token: str) -> Dict[str, Any]:
        """Simplified token validation for DEV MODE."""
        try:
            # Check cache first
            cache_key = f"token_{hash(token)}"
            if cache_key in self.auth_cache:
                cached_result, cached_time = self.auth_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    logger.debug("[WebSocket] Using cached auth result")
                    return cached_result
            
            # Validate with auth service
            validation_result = await auth_client.validate_token(token)
            
            if not validation_result or not validation_result.get("valid"):
                return {"valid": False, "error": "Invalid token"}
            
            user_id = str(validation_result.get("user_id", ""))
            if not user_id:
                return {"valid": False, "error": "No user_id in token"}
            
            # Simplified session info for DEV
            session_info = {
                "valid": True,
                "user_id": user_id,
                "email": validation_result.get("email", ""),
                "auth_method": "jwt_simplified",
                "validated_at": time.time(),
                "dev_mode": True
            }
            
            # Cache result
            self.auth_cache[cache_key] = (session_info, time.time())
            
            logger.info(f"[WebSocket] Token validated successfully for user: {user_id}")
            return session_info
            
        except Exception as e:
            logger.error(f"[WebSocket] Token validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    def cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, cached_time) in self.auth_cache.items()
            if current_time - cached_time > self.cache_ttl
        ]
        for key in expired_keys:
            del self.auth_cache[key]
        
        if expired_keys:
            logger.debug(f"[WebSocket] Cleaned up {len(expired_keys)} expired auth cache entries")


# Global simplified auth instance
simplified_auth = SimplifiedWebSocketAuth()


class DevWebSocketConnection:
    """Simplified connection management for DEV MODE."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.connection_stats = {"total": 0, "active": 0, "errors": 0}
    
    async def register_connection(self, user_id: str, websocket: WebSocket, 
                                session_info: Dict[str, Any]) -> str:
        """Register new WebSocket connection."""
        connection_id = f"dev_{user_id}_{int(time.time() * 1000)}"
        
        self.active_connections[connection_id] = {
            "user_id": user_id,
            "websocket": websocket,
            "session_info": session_info,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "status": "connected"
        }
        
        self.connection_stats["total"] += 1
        self.connection_stats["active"] += 1
        
        logger.info(f"[WebSocket] DEV connection registered: {connection_id}")
        return connection_id
    
    async def unregister_connection(self, connection_id: str):
        """Unregister WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            self.connection_stats["active"] -= 1
            logger.info(f"[WebSocket] DEV connection unregistered: {connection_id}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information."""
        return self.active_connections.get(connection_id)
    
    def update_activity(self, connection_id: str):
        """Update last activity time."""
        if connection_id in self.active_connections:
            self.active_connections[connection_id]["last_activity"] = datetime.now(timezone.utc)
            self.active_connections[connection_id]["message_count"] += 1


# Global connection manager for DEV
dev_connection_manager = DevWebSocketConnection()


@router.get("/ws/config")
async def get_websocket_config_dev():
    """Service discovery endpoint for WebSocket configuration - DEV MODE."""
    logger.info("[WebSocket] Service discovery requested (DEV MODE)")
    
    # Add CORS information to config
    cors_handler = get_websocket_cors_handler()
    
    runtime_config = DEV_WEBSOCKET_CONFIG.copy()
    runtime_config.update({
        "server_time": datetime.now(timezone.utc).isoformat(),
        "server_status": "healthy",
        "dev_mode": True,
        "cors_origins": cors_handler.allowed_origins[:5],  # Show first 5 for brevity
        "connection_stats": dev_connection_manager.connection_stats
    })
    
    return {
        "websocket_config": runtime_config,
        "status": "success",
        "mode": "development"
    }


async def validate_websocket_cors_and_auth(websocket: WebSocket) -> Dict[str, Any]:
    """Combined CORS and authentication validation for DEV MODE."""
    try:
        # Step 1: CORS validation
        cors_handler = get_websocket_cors_handler()
        if not validate_websocket_origin(websocket, cors_handler):
            raise HTTPException(
                status_code=1008,
                detail="CORS validation failed - origin not allowed"
            )
        
        # Step 2: Extract token
        token = websocket.query_params.get("token")
        if not token:
            raise HTTPException(
                status_code=1008,
                detail="No authentication token provided"
            )
        
        # Step 3: Validate token (simplified for DEV)
        auth_result = await simplified_auth.validate_token_simplified(token)
        if not auth_result.get("valid"):
            raise HTTPException(
                status_code=1008,
                detail=f"Authentication failed: {auth_result.get('error', 'Invalid token')}"
            )
        
        logger.info(f"[WebSocket] CORS and auth validation successful for user: {auth_result['user_id']}")
        return auth_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebSocket] Validation error: {e}")
        raise HTTPException(
            status_code=1011,
            detail=f"Validation error: {str(e)[:100]}"
        )


async def handle_websocket_message_dev(
    connection_id: str,
    websocket: WebSocket,
    raw_message: str
) -> bool:
    """Simplified message handling for DEV MODE."""
    try:
        # Update connection activity
        dev_connection_manager.update_activity(connection_id)
        
        # Get connection info
        conn_info = dev_connection_manager.get_connection_info(connection_id)
        if not conn_info:
            logger.error(f"[WebSocket] Connection not found: {connection_id}")
            return False
        
        user_id = conn_info["user_id"]
        
        # JSON validation (simplified)
        if not raw_message or not raw_message.strip():
            await send_error_response(websocket, "Empty message", "EMPTY_MESSAGE")
            return True
        
        try:
            message_data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            await send_error_response(websocket, f"Invalid JSON: {str(e)}", "JSON_ERROR")
            return True
        
        # Basic structure validation
        if not isinstance(message_data, dict) or "type" not in message_data:
            await send_error_response(websocket, "Message must be JSON object with 'type' field", "STRUCTURE_ERROR")
            return True
        
        message_type = message_data["type"]
        
        # Handle system messages
        if message_type in ["ping", "pong", "heartbeat"]:
            await handle_system_message_dev(websocket, message_data)
            return True
        
        # Handle user messages through unified manager
        manager = get_unified_manager()
        success = await manager.handle_message(user_id, websocket, message_data)
        
        logger.debug(f"[WebSocket] Message processed: {message_type} for user: {user_id}")
        return success
        
    except Exception as e:
        logger.error(f"[WebSocket] Message handling error: {e}", exc_info=True)
        dev_connection_manager.connection_stats["errors"] += 1
        await send_error_response(websocket, "Message processing failed", "PROCESSING_ERROR")
        return True  # Keep connection alive


async def handle_system_message_dev(websocket: WebSocket, message_data: Dict[str, Any]) -> bool:
    """Handle system messages for DEV MODE."""
    message_type = message_data["type"]
    
    if message_type in ["ping", "heartbeat"]:
        # Respond with pong
        pong_response = {
            "type": "pong",
            "timestamp": time.time(),
            "server_time": datetime.now(timezone.utc).isoformat(),
            "dev_mode": True
        }
        await websocket.send_json(pong_response)
        logger.debug("[WebSocket] Sent pong response")
        return True
    
    elif message_type == "pong":
        logger.debug("[WebSocket] Received pong from client")
        return True
    
    return True


async def send_error_response(websocket: WebSocket, error_message: str, error_code: str):
    """Send error response to WebSocket client."""
    try:
        error_response = {
            "type": "error",
            "payload": {
                "error": error_message,
                "code": error_code,
                "timestamp": time.time(),
                "recoverable": True,
                "dev_mode": True
            }
        }
        await websocket.send_json(error_response)
    except Exception as e:
        logger.error(f"[WebSocket] Failed to send error response: {e}")


async def websocket_heartbeat_dev(websocket: WebSocket, connection_id: str):
    """Simplified heartbeat for DEV MODE."""
    heartbeat_interval = DEV_WEBSOCKET_CONFIG["connection_limits"]["heartbeat_interval"] / 1000
    
    try:
        while True:
            await asyncio.sleep(heartbeat_interval)
            
            # Check if connection still exists
            if not dev_connection_manager.get_connection_info(connection_id):
                break
            
            try:
                heartbeat_message = {
                    "type": "server_heartbeat",
                    "timestamp": time.time(),
                    "connection_id": connection_id,
                    "dev_mode": True
                }
                await websocket.send_json(heartbeat_message)
                logger.debug(f"[WebSocket] Heartbeat sent: {connection_id}")
                
            except Exception as e:
                logger.warning(f"[WebSocket] Heartbeat failed: {connection_id} - {e}")
                break
                
    except asyncio.CancelledError:
        logger.debug(f"[WebSocket] Heartbeat cancelled: {connection_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Heartbeat error: {connection_id} - {e}")


@router.websocket("/ws/enhanced")
async def enhanced_websocket_endpoint_dev(websocket: WebSocket):
    """DRAFT: Enhanced WebSocket endpoint for DEV MODE with fixes.
    
    Key improvements:
    1. Integrated CORS validation
    2. Simplified authentication flow
    3. Better error handling
    4. Coordinated heartbeat system
    5. Cleaner connection lifecycle
    """
    connection_id: Optional[str] = None
    heartbeat_task: Optional[asyncio.Task] = None
    
    try:
        logger.info("[WebSocket] DEV MODE connection requested")
        
        # Step 1: Combined CORS and authentication validation
        session_info = await validate_websocket_cors_and_auth(websocket)
        user_id = session_info["user_id"]
        
        # Step 2: Accept WebSocket connection
        await websocket.accept()
        logger.info(f"[WebSocket] Connection accepted for user: {user_id}")
        
        # Step 3: Register connection
        connection_id = await dev_connection_manager.register_connection(
            user_id, websocket, session_info
        )
        
        # Step 4: Connect to unified manager
        manager = get_unified_manager()
        await manager.connect_user(user_id, websocket)
        
        # Step 5: Start heartbeat
        heartbeat_task = asyncio.create_task(
            websocket_heartbeat_dev(websocket, connection_id)
        )
        
        # Step 6: Send welcome message
        welcome_message = {
            "type": "connection_established",
            "payload": {
                "user_id": user_id,
                "connection_id": connection_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "config": DEV_WEBSOCKET_CONFIG["features"],
                "dev_mode": True
            }
        }
        await websocket.send_json(welcome_message)
        
        logger.info(f"[WebSocket] DEV connection fully established: {connection_id}")
        
        # Step 7: Main message loop with simplified error handling
        consecutive_errors = 0
        max_errors = 3  # Reduced for DEV
        
        while True:
            try:
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=90.0  # Longer timeout for DEV
                )
                
                success = await handle_websocket_message_dev(
                    connection_id, websocket, raw_message
                )
                
                if success:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                
                if consecutive_errors >= max_errors:
                    logger.error(f"[WebSocket] Too many errors ({consecutive_errors}) for {connection_id}")
                    await send_error_response(
                        websocket,
                        "Too many errors, closing connection",
                        "ERROR_LIMIT"
                    )
                    break
                    
            except asyncio.TimeoutError:
                logger.debug(f"[WebSocket] Message timeout for {connection_id}")
                continue
                
            except WebSocketDisconnect as e:
                logger.info(f"[WebSocket] Client disconnected: {connection_id} - {e.code}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"[WebSocket] Message loop error: {connection_id} - {e}")
                
                if consecutive_errors >= max_errors:
                    logger.error(f"[WebSocket] Fatal errors, closing: {connection_id}")
                    break
                
                await asyncio.sleep(0.5)  # Brief pause after error
    
    except HTTPException as e:
        logger.error(f"[WebSocket] Setup failed: {e.detail}")
        return
        
    except Exception as e:
        logger.error(f"[WebSocket] Unexpected error: {e}", exc_info=True)
        
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await send_error_response(websocket, "Server error", "INTERNAL_ERROR")
            except Exception:
                pass
    
    finally:
        # Cleanup
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if connection_id:
            await dev_connection_manager.unregister_connection(connection_id)
            
            # Disconnect from unified manager
            try:
                manager = get_unified_manager()
                user_id = dev_connection_manager.active_connections.get(connection_id, {}).get("user_id")
                if user_id:
                    await manager.disconnect_user(user_id, websocket)
            except Exception as e:
                logger.error(f"[WebSocket] Cleanup error: {e}")
        
        # Periodic auth cache cleanup
        if hasattr(simplified_auth, 'cleanup_cache'):
            simplified_auth.cleanup_cache()
        
        logger.info(f"[WebSocket] DEV connection cleanup completed: {connection_id}")


# Health check endpoint for DEV
@router.get("/ws/health")
async def websocket_health_dev():
    """WebSocket health check for DEV MODE."""
    return {
        "status": "healthy",
        "mode": "development",
        "stats": dev_connection_manager.connection_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }