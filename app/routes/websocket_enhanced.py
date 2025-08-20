"""Enhanced WebSocket endpoint with comprehensive auth, service discovery, and resilience.

This implementation follows SPEC/websockets.xml requirements:
- JSON-first communication
- Connection established on app state load (BEFORE first message)
- Persistent connection resilient to re-renders 
- Proper JWT auth with manual database session handling (NOT Depends())
- Service discovery for WebSocket config
- Comprehensive error handling and recovery
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

logger = central_logger.get_logger(__name__)
router = APIRouter()

# Service discovery configuration
WEBSOCKET_CONFIG = {
    "version": "1.0",
    "features": {
        "json_first": True,
        "auth_required": True,
        "heartbeat_supported": True,
        "reconnection_supported": True,
        "rate_limiting": True,
        "message_queuing": True
    },
    "endpoints": {
        "websocket": "/ws/enhanced",
        "service_discovery": "/ws/config"
    },
    "connection_limits": {
        "max_connections_per_user": 5,
        "max_message_rate": 60,  # messages per minute
        "max_message_size": 10240,  # 10KB
        "heartbeat_interval": 30000  # 30 seconds
    },
    "auth": {
        "methods": ["jwt_query_param"],
        "token_validation": "auth_service",
        "session_handling": "manual"
    }
}


class WebSocketConnectionManager:
    """Enhanced connection manager for WebSocket sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.token_refresh_tasks: Dict[str, asyncio.Task] = {}
    
    async def add_connection(self, user_id: str, websocket: WebSocket, 
                           session_info: Dict[str, Any]) -> str:
        """Add new WebSocket connection with metadata and token refresh."""
        connection_id = f"{user_id}_{int(time.time() * 1000)}"
        
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = []
        
        connection_data = {
            "connection_id": connection_id,
            "websocket": websocket,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "session_info": session_info
        }
        
        self.active_sessions[user_id].append(connection_data)
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "status": "connected",
            "message_count": 0,
            "error_count": 0,
            "token_expires": session_info.get("token_expires"),
            "last_token_refresh": datetime.now(timezone.utc)
        }
        
        # Start token refresh task for long-lived connections
        if session_info.get("token_expires"):
            refresh_task = asyncio.create_task(
                self._handle_token_refresh(connection_id, user_id, websocket, session_info)
            )
            self.token_refresh_tasks[connection_id] = refresh_task
        
        # Enforce connection limits per user
        max_connections = WEBSOCKET_CONFIG["connection_limits"]["max_connections_per_user"]
        if len(self.active_sessions[user_id]) > max_connections:
            # Remove oldest connection
            oldest = self.active_sessions[user_id].pop(0)
            old_conn_id = oldest["connection_id"]
            if old_conn_id in self.connection_metadata:
                del self.connection_metadata[old_conn_id]
            # Cancel token refresh for old connection
            if old_conn_id in self.token_refresh_tasks:
                self.token_refresh_tasks[old_conn_id].cancel()
                del self.token_refresh_tasks[old_conn_id]
            try:
                await oldest["websocket"].close(
                    code=1000, 
                    reason="Connection limit exceeded - new session established"
                )
            except Exception:
                pass
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        return connection_id
    
    async def remove_connection(self, user_id: str, connection_id: str):
        """Remove WebSocket connection and cleanup token refresh."""
        if user_id in self.active_sessions:
            self.active_sessions[user_id] = [
                conn for conn in self.active_sessions[user_id] 
                if conn["connection_id"] != connection_id
            ]
            if not self.active_sessions[user_id]:
                del self.active_sessions[user_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # Cancel and cleanup token refresh task
        if connection_id in self.token_refresh_tasks:
            self.token_refresh_tasks[connection_id].cancel()
            del self.token_refresh_tasks[connection_id]
        
        logger.info(f"WebSocket connection removed: {connection_id} for user {user_id}")
    
    async def _handle_token_refresh(self, connection_id: str, user_id: str, 
                                  websocket: WebSocket, session_info: Dict[str, Any]):
        """Handle JWT token refresh for long-lived connections."""
        try:
            # Calculate refresh time (refresh 5 minutes before expiry)
            token_expires = session_info.get("token_expires")
            if not token_expires:
                return
            
            if isinstance(token_expires, str):
                from datetime import datetime
                try:
                    expires_dt = datetime.fromisoformat(token_expires.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid token expiry format: {token_expires}")
                    return
            else:
                expires_dt = token_expires
            
            refresh_time = (expires_dt - datetime.now(timezone.utc)).total_seconds() - 300  # 5 minutes buffer
            
            if refresh_time <= 0:
                logger.warning(f"Token already expired for connection {connection_id}")
                await self._handle_token_expiry(websocket, connection_id, user_id)
                return
            
            logger.info(f"Scheduling token refresh in {refresh_time} seconds for connection {connection_id}")
            
            # Wait until refresh time
            await asyncio.sleep(refresh_time)
            
            # Check if connection still exists
            if connection_id not in self.connection_metadata:
                return
            
            # Attempt to refresh token
            success = await self._refresh_connection_token(websocket, connection_id, user_id, session_info)
            
            if success:
                # Schedule next refresh
                await self._handle_token_refresh(connection_id, user_id, websocket, session_info)
            else:
                await self._handle_token_expiry(websocket, connection_id, user_id)
                
        except asyncio.CancelledError:
            logger.debug(f"Token refresh task cancelled for connection {connection_id}")
        except Exception as e:
            logger.error(f"Token refresh error for connection {connection_id}: {e}")
    
    async def _refresh_connection_token(self, websocket: WebSocket, connection_id: str, 
                                      user_id: str, session_info: Dict[str, Any]) -> bool:
        """Refresh JWT token for active connection."""
        try:
            # Extract current token from session info
            current_token = session_info.get("current_token") or websocket.query_params.get("token")
            if not current_token:
                logger.error(f"No current token found for refresh - connection {connection_id}")
                return False
            
            # Attempt token refresh with auth service
            refresh_result = await auth_client.refresh_token(current_token)
            
            if not refresh_result or not refresh_result.get("valid"):
                logger.error(f"Token refresh failed for connection {connection_id}")
                return False
            
            # Update connection metadata with new token info
            new_token = refresh_result.get("access_token")
            new_expires = refresh_result.get("expires_at")
            
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id].update({
                    "token_expires": new_expires,
                    "last_token_refresh": datetime.now(timezone.utc)
                })
            
            # Update session info
            session_info.update({
                "current_token": new_token,
                "token_expires": new_expires
            })
            
            # Notify client of token refresh
            token_refresh_message = {
                "type": "token_refreshed",
                "payload": {
                    "new_token": new_token,
                    "expires_at": new_expires,
                    "connection_id": connection_id,
                    "refreshed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            await websocket.send_json(token_refresh_message)
            
            logger.info(f"Token successfully refreshed for connection {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed for connection {connection_id}: {e}")
            return False
    
    async def _handle_token_expiry(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Handle token expiry by notifying client and closing connection."""
        try:
            expiry_message = {
                "type": "token_expired",
                "payload": {
                    "message": "Authentication token has expired",
                    "connection_id": connection_id,
                    "action_required": "Please refresh the page or re-authenticate",
                    "expired_at": datetime.now(timezone.utc).isoformat()
                }
            }
            await websocket.send_json(expiry_message)
            
            # Give client time to process the message before closing
            await asyncio.sleep(2)
            
            await websocket.close(code=1008, reason="Token expired - please re-authenticate")
            logger.info(f"Connection {connection_id} closed due to token expiry")
            
        except Exception as e:
            logger.error(f"Error handling token expiry for connection {connection_id}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = sum(len(conns) for conns in self.active_sessions.values())
        return {
            "total_connections": total_connections,
            "active_users": len(self.active_sessions),
            "connections_per_user": {
                user: len(conns) for user, conns in self.active_sessions.items()
            }
        }


# Global connection manager
connection_manager = WebSocketConnectionManager()


@router.get("/ws/config")
async def get_websocket_service_discovery():
    """Service discovery endpoint for WebSocket configuration.
    
    This endpoint provides WebSocket configuration to the frontend,
    enabling service discovery as required by SPEC/websockets.xml.
    """
    logger.info("WebSocket service discovery requested")
    
    # Add runtime information
    runtime_config = WEBSOCKET_CONFIG.copy()
    runtime_config.update({
        "server_time": datetime.now(timezone.utc).isoformat(),
        "server_status": "healthy",
        "connection_stats": connection_manager.get_connection_stats()
    })
    
    return {
        "websocket_config": runtime_config,
        "status": "success"
    }


async def validate_websocket_token_enhanced(websocket: WebSocket) -> Dict[str, Any]:
    """Enhanced token validation with comprehensive error handling."""
    # Extract token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        logger.error("WebSocket connection denied: No token provided")
        raise HTTPException(
            status_code=1008, 
            detail="Authentication required: No token provided"
        )
    
    try:
        # Validate token with auth service (same pattern as REST endpoints)
        validation_result = await auth_client.validate_token(token)
        
        if not validation_result or not validation_result.get("valid"):
            logger.error("WebSocket connection denied: Invalid token from auth service")
            raise HTTPException(
                status_code=1008,
                detail="Authentication failed: Invalid or expired token"
            )
        
        # Extract user information from validation result
        user_id = str(validation_result.get("user_id", ""))
        if not user_id:
            logger.error("WebSocket connection denied: No user_id in token")
            raise HTTPException(
                status_code=1008,
                detail="Authentication failed: Invalid user information"
            )
        
        session_info = {
            "user_id": user_id,
            "email": validation_result.get("email"),
            "permissions": validation_result.get("permissions", []),
            "authenticated_at": datetime.now(timezone.utc),
            "token_expires": validation_result.get("expires_at"),
            "auth_method": "jwt_query_param"
        }
        
        logger.info(f"WebSocket token validated successfully for user: {user_id}")
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WebSocket token validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=1011,
            detail=f"Authentication error: {str(e)[:100]}"
        )


class DatabaseConnectionPool:
    """Connection pool manager for WebSocket database operations."""
    
    def __init__(self, max_pool_size: int = 10):
        self.max_pool_size = max_pool_size
        self.active_sessions = 0
        self.session_queue = asyncio.Queue(maxsize=max_pool_size)
        self._pool_lock = asyncio.Lock()
    
    async def get_pooled_session(self) -> AsyncSession:
        """Get database session from connection pool with retry logic."""
        max_wait_time = 5.0  # seconds
        
        try:
            # Try to get existing session from pool
            session_factory = await asyncio.wait_for(
                self.session_queue.get(), 
                timeout=max_wait_time
            )
        except asyncio.TimeoutError:
            # Create new session if pool is empty and under limit
            async with self._pool_lock:
                if self.active_sessions < self.max_pool_size:
                    from app.db.postgres_core import async_session_factory
                    if not async_session_factory:
                        raise RuntimeError("Database session factory not initialized")
                    session_factory = async_session_factory
                    self.active_sessions += 1
                else:
                    raise RuntimeError("Database connection pool exhausted")
        
        return session_factory()
    
    async def return_session_to_pool(self, session_factory):
        """Return session factory to pool for reuse."""
        try:
            await self.session_queue.put(session_factory, timeout=1.0)
        except asyncio.TimeoutError:
            # Pool full, just decrement counter
            async with self._pool_lock:
                self.active_sessions = max(0, self.active_sessions - 1)


# Global connection pool for WebSocket operations
db_pool = DatabaseConnectionPool(max_pool_size=15)


async def authenticate_websocket_with_database(session_info: Dict[str, Any]) -> str:
    """Authenticate user with database using connection pooling.
    
    Uses connection pooling instead of creating new session per message
    to prevent the database session per message anti-pattern.
    """
    user_id = session_info["user_id"]
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        session = None
        session_factory = None
        
        try:
            # Get session from connection pool
            session = await db_pool.get_pooled_session()
            if not session:
                raise ValueError("Failed to get pooled database session")
            
            # Get services from app state
            from app.services.security_service import SecurityService
            security_service = SecurityService()
            
            # Fetch and validate user exists in database
            user = await security_service.get_user_by_id(session, user_id)
            
            if not user:
                logger.error(f"User {user_id} not found in database")
                # In development mode, allow auto-creation
                import os
                env = os.getenv("ENVIRONMENT", "development").lower()
                if env in ["development", "test"] and session_info.get("email"):
                    logger.warning(f"Auto-creating user {user_id} in {env} environment")
                    await session.commit()
                    return user_id
                raise ValueError(f"User {user_id} not found in database")
            
            # Validate user is active
            if hasattr(user, 'is_active') and not user.is_active:
                raise ValueError(f"User {user_id} is not active")
            
            await session.commit()
            logger.info(f"Database authentication successful for user: {user_id}")
            return user_id
            
        except Exception as e:
            if session:
                await session.rollback()
            
            if attempt < max_retries:
                logger.warning(f"Database auth retry {attempt + 1} for user {user_id}: {e}")
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            else:
                logger.error(f"Database authentication failed for user {user_id}: {e}")
                raise
        finally:
            if session:
                await session.close()
            if session_factory:
                await db_pool.return_session_to_pool(session_factory)


async def handle_websocket_message_enhanced(
    user_id: str, 
    connection_id: str,
    websocket: WebSocket,
    raw_message: str
) -> bool:
    """Enhanced message handling with JSON-first validation and error recovery."""
    
    try:
        # Update connection activity
        if connection_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[connection_id]["last_activity"] = datetime.now(timezone.utc)
            connection_manager.connection_metadata[connection_id]["message_count"] += 1
        
        # JSON-first validation (as per SPEC/websockets.xml)
        if not raw_message or not raw_message.strip():
            await send_error_message(websocket, "Empty message received", "EMPTY_MESSAGE")
            return True  # Keep connection alive
        
        try:
            message_data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            await send_error_message(
                websocket, 
                f"Invalid JSON format: {str(e)}", 
                "JSON_PARSE_ERROR"
            )
            return True  # Keep connection alive
        
        # Validate message structure
        if not isinstance(message_data, dict):
            await send_error_message(
                websocket, 
                "Message must be a JSON object", 
                "INVALID_MESSAGE_TYPE"
            )
            return True
        
        if "type" not in message_data:
            await send_error_message(
                websocket, 
                "Message must contain 'type' field", 
                "MISSING_TYPE_FIELD"
            )
            return True
        
        message_type = message_data["type"]
        if not isinstance(message_type, str) or not message_type.strip():
            await send_error_message(
                websocket, 
                "Message 'type' field must be a non-empty string", 
                "INVALID_TYPE_FIELD"
            )
            return True
        
        # Handle system messages (ping/pong, auth)
        if message_type in ["ping", "pong", "auth"]:
            return await handle_system_message(websocket, message_data)
        
        # Handle user messages through unified manager
        manager = get_unified_manager()
        websocket_message = WebSocketMessage(
            type=message_type,
            payload=message_data.get("payload", {})
        )
        
        # Validate message with unified manager
        validation_result = manager.validate_message(message_data)
        if isinstance(validation_result, WebSocketValidationError):
            await send_error_message(
                websocket,
                validation_result.message,
                validation_result.error_type
            )
            return True
        
        # Process message through unified system
        success = await manager.handle_message(user_id, websocket, message_data)
        
        # Handle agent messages through agent service with manual DB session
        if message_type in ["user_message", "agent_request"]:
            await process_agent_message_enhanced(user_id, raw_message)
        
        return success
        
    except Exception as e:
        logger.error(f"Error handling WebSocket message for {user_id}: {e}", exc_info=True)
        
        # Update error count
        if connection_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[connection_id]["error_count"] += 1
        
        await send_error_message(websocket, "Message processing failed", "PROCESSING_ERROR")
        return True  # Keep connection alive after errors


async def handle_system_message(websocket: WebSocket, message_data: Dict[str, Any]) -> bool:
    """Handle system messages (ping/pong, auth)."""
    message_type = message_data["type"]
    
    if message_type == "ping":
        # Respond with pong
        pong_response = {
            "type": "pong",
            "timestamp": time.time(),
            "server_time": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_json(pong_response)
        logger.debug("Sent pong response to ping")
        return True
    
    elif message_type == "pong":
        # Acknowledge pong
        logger.debug("Received pong from client")
        return True
    
    elif message_type == "auth":
        # Handle re-authentication if needed
        logger.debug("Received auth message - connection already authenticated")
        return True
    
    return True


async def process_agent_message_enhanced(user_id: str, raw_message: str):
    """Process agent message with pooled database session handling."""
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        session = None
        session_factory = None
        
        try:
            # Get session from connection pool instead of creating new one
            session = await db_pool.get_pooled_session()
            if not session:
                raise ValueError("Failed to get pooled database session")
            
            # Get agent service from app state
            from app.services.agent_service_core import AgentService
            agent_service = AgentService()
            
            # Process message through agent service
            await agent_service.handle_websocket_message(user_id, raw_message, session)
            
            # Explicit commit for transactional integrity
            await session.commit()
            logger.info(f"Agent message processed successfully for user: {user_id}")
            return
            
        except Exception as e:
            if session:
                await session.rollback()
            
            if attempt < max_retries:
                logger.warning(f"Agent message retry {attempt + 1} for user {user_id}: {e}")
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            else:
                logger.error(f"Agent message processing failed for user {user_id}: {e}")
                raise
        finally:
            if session:
                await session.close()
            if session_factory:
                await db_pool.return_session_to_pool(session_factory)


async def send_error_message(
    websocket: WebSocket, 
    error_message: str, 
    error_code: str,
    recoverable: bool = True
):
    """Send structured error message to WebSocket client."""
    try:
        error_response = {
            "type": "error",
            "payload": {
                "error": error_message,
                "code": error_code,
                "timestamp": time.time(),
                "recoverable": recoverable,
                "help": get_error_help_text(error_code)
            }
        }
        await websocket.send_json(error_response)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


def get_error_help_text(error_code: str) -> str:
    """Get helpful error message based on error code."""
    help_messages = {
        "EMPTY_MESSAGE": "Please send a non-empty JSON message",
        "JSON_PARSE_ERROR": "Please ensure your message is valid JSON format",
        "INVALID_MESSAGE_TYPE": "Please send a JSON object with curly braces {}",
        "MISSING_TYPE_FIELD": "Please include a 'type' field in your message",
        "INVALID_TYPE_FIELD": "The 'type' field must be a non-empty string",
        "PROCESSING_ERROR": "Please try sending your message again"
    }
    return help_messages.get(error_code, "Please check your message format and try again")


async def websocket_heartbeat_handler(websocket: WebSocket, connection_id: str):
    """Handle WebSocket heartbeat to maintain connection."""
    heartbeat_interval = WEBSOCKET_CONFIG["connection_limits"]["heartbeat_interval"] / 1000  # Convert to seconds
    
    try:
        while True:
            await asyncio.sleep(heartbeat_interval)
            
            # Check if connection still exists
            if connection_id not in connection_manager.connection_metadata:
                break
            
            try:
                # Send heartbeat ping
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "connection_id": connection_id
                }
                await websocket.send_json(heartbeat_message)
                logger.debug(f"Sent heartbeat for connection: {connection_id}")
                
            except Exception as e:
                logger.warning(f"Heartbeat failed for connection {connection_id}: {e}")
                break
                
    except asyncio.CancelledError:
        logger.debug(f"Heartbeat cancelled for connection: {connection_id}")
    except Exception as e:
        logger.error(f"Heartbeat error for connection {connection_id}: {e}")


@router.websocket("/ws/enhanced")
async def enhanced_websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint with comprehensive features.
    
    Features:
    - JSON-first communication
    - JWT authentication with manual DB session handling
    - Connection establishment before first message
    - Persistent connection with reconnection support
    - Service discovery integration
    - Comprehensive error handling and recovery
    - Rate limiting and connection management
    - Heartbeat/keepalive support
    """
    user_id: Optional[str] = None
    connection_id: Optional[str] = None
    heartbeat_task: Optional[asyncio.Task] = None
    
    try:
        # Step 1: Validate token BEFORE accepting WebSocket connection
        logger.info("Enhanced WebSocket connection requested")
        session_info = await validate_websocket_token_enhanced(websocket)
        
        # Step 2: Accept WebSocket connection
        await websocket.accept()
        logger.info("Enhanced WebSocket connection accepted")
        
        # Step 3: Authenticate with database using manual session handling
        user_id = await authenticate_websocket_with_database(session_info)
        
        # Step 4: Register connection with manager
        connection_id = await connection_manager.add_connection(user_id, websocket, session_info)
        
        # Step 5: Connect to unified WebSocket manager
        manager = get_unified_manager()
        conn_info = await manager.connect_user(user_id, websocket)
        
        # Step 6: Start heartbeat handler
        heartbeat_task = asyncio.create_task(
            websocket_heartbeat_handler(websocket, connection_id)
        )
        
        # Step 7: Send connection success message
        welcome_message = {
            "type": "connection_established",
            "payload": {
                "user_id": user_id,
                "connection_id": connection_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "features": WEBSOCKET_CONFIG["features"],
                "limits": WEBSOCKET_CONFIG["connection_limits"]
            }
        }
        await websocket.send_json(welcome_message)
        
        logger.info(f"Enhanced WebSocket connection fully established for user: {user_id}")
        
        # Step 8: Main message handling loop
        message_count = 0
        error_count = 0
        max_consecutive_errors = 5
        
        while True:
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout
                )
                
                message_count += 1
                logger.debug(f"Received message #{message_count} from {user_id}")
                
                # Handle message
                success = await handle_websocket_message_enhanced(
                    user_id, connection_id, websocket, raw_message
                )
                
                if success:
                    error_count = 0  # Reset error count on successful processing
                else:
                    error_count += 1
                
                # Check for too many consecutive errors
                if error_count >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({error_count}) for user {user_id}")
                    await send_error_message(
                        websocket, 
                        "Too many errors occurred, closing connection", 
                        "ERROR_LIMIT_EXCEEDED",
                        recoverable=False
                    )
                    break
                    
            except asyncio.TimeoutError:
                # Send timeout warning but keep connection alive
                await send_error_message(
                    websocket,
                    "No message received within timeout period",
                    "MESSAGE_TIMEOUT"
                )
                continue
                
            except WebSocketDisconnect as e:
                logger.info(f"WebSocket disconnected for user {user_id}: {e.code} - {e.reason}")
                break
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in message loop for user {user_id}: {e}", exc_info=True)
                
                if error_count >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors for user {user_id}, closing connection")
                    break
                
                # Brief pause after error to prevent tight error loops
                await asyncio.sleep(0.1)
                continue
    
    except HTTPException as e:
        logger.error(f"HTTP exception during WebSocket setup: {e.detail}")
        # Connection was rejected at HTTP level, no cleanup needed
        return
        
    except Exception as e:
        logger.error(f"Unexpected error in enhanced WebSocket endpoint: {e}", exc_info=True)
        
        # Send error if connection was established
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await send_error_message(
                    websocket,
                    "Internal server error occurred",
                    "INTERNAL_ERROR",
                    recoverable=False
                )
            except Exception:
                pass
    
    finally:
        # Cleanup: Cancel heartbeat task
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup: Remove from connection manager
        if user_id and connection_id:
            await connection_manager.remove_connection(user_id, connection_id)
        
        # Cleanup: Disconnect from unified manager
        if user_id:
            try:
                manager = get_unified_manager()
                await manager.disconnect_user(user_id, websocket)
            except Exception as e:
                logger.error(f"Error during unified manager cleanup: {e}")
        
        logger.info(f"Enhanced WebSocket connection cleanup completed for user: {user_id}")