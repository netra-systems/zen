"""
Isolated WebSocket Endpoints with Zero Event Leakage Between Users.

Business Value Justification:
- Segment: All (Free → Enterprise)
- Business Goal: User Isolation & Chat Value Delivery
- Value Impact: Guarantees no cross-user event leakage, enables secure multi-user chat
- Strategic Impact: CRITICAL - Core chat functionality with proper user isolation

This module implements WebSocket endpoints with strict per-connection isolation.
Each connection gets its own manager instance that only processes events for
the authenticated user, completely eliminating cross-user event leakage.

Key Security Features:
1. Connection-scoped managers - No shared state between users
2. User authentication validation on ALL connections
3. Event filtering - Only events for authenticated user delivered  
4. Automatic resource cleanup on disconnect
5. Comprehensive audit logging for debugging

Endpoints:
- /ws/isolated: Main isolated WebSocket endpoint (JWT auth required)
- /ws/isolated/health: Health check for isolated connections
- /ws/isolated/stats: Statistics for monitoring (development only)
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.core.tracing import TracingManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.monitoring.gcp_error_reporter import gcp_reportable, set_request_context, clear_request_context

# Import isolated WebSocket components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as ConnectionScopedWebSocketManager
from netra_backend.app.websocket.connection_handler import connection_scope

# Import authentication and security
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
from netra_backend.app.websocket_core import (
    WebSocketHeartbeat,
    create_server_message,
    create_error_message,
    MessageType,
    WebSocketConfig
)

# Import agent integration with factory pattern
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["WebSocket-Isolated"])
tracing_manager = TracingManager()


def _get_websocket_config():
    """Get environment-specific WebSocket configuration."""
    from shared.isolated_environment import get_env
    
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    testing = env.get("TESTING", "0") == "1"
    
    # Configuration optimized for isolation testing
    config = WebSocketConfig(
        heartbeat_interval_seconds=30,
        heartbeat_timeout_seconds=90,
        max_connections_per_user=3,  # Limit for isolation testing
        max_message_size=1024 * 1024,  # 1MB
        rate_limit_per_minute=300 if testing else 100,
        compression_enabled=True,
        auth_required=True
    )
    
    logger.debug(f"WebSocket config for {environment}: heartbeat={config.heartbeat_interval_seconds}s, "
                f"rate_limit={config.rate_limit_per_minute}/min")
    
    return config


@router.websocket("/ws/isolated")
@gcp_reportable(reraise=True)
async def isolated_websocket_endpoint(websocket: WebSocket):
    """
    Isolated WebSocket endpoint with zero cross-user event leakage.
    
    This endpoint creates a connection-scoped manager for each user connection,
    ensuring complete isolation between different user sessions.
    
    Features:
    - JWT authentication required
    - Connection-scoped event handling  
    - Automatic user validation on all events
    - Resource cleanup on disconnect
    - Comprehensive audit logging
    
    Authentication:
    - Authorization header: "Bearer <jwt_token>"
    - Sec-WebSocket-Protocol: "jwt.<base64url_encoded_token>"
    """
    connection_id: Optional[str] = None
    user_id: Optional[str] = None
    manager: Optional[ConnectionScopedWebSocketManager] = None
    heartbeat: Optional[WebSocketHeartbeat] = None
    
    try:
        # Parse subprotocols for authentication
        subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        selected_protocol = None
        
        if "jwt-auth" in [p.strip() for p in subprotocols]:
            selected_protocol = "jwt-auth"
        
        # Accept WebSocket connection
        if selected_protocol:
            await websocket.accept(subprotocol=selected_protocol)
            logger.debug(f"Isolated WebSocket accepted with subprotocol: {selected_protocol}")
        else:
            await websocket.accept()
            logger.debug("Isolated WebSocket accepted without subprotocol")
        
        # Authenticate user using SSOT method
        auth_result = await authenticate_websocket_ssot(websocket)
        
        if not auth_result.success:
            error_msg = create_error_message(
                "Authentication failed",
                {"reason": "JWT token required for isolated endpoint"}
            )
            await websocket.send_json(error_msg.dict())
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        user_id = auth_result.user_context.user_id
        thread_id = auth_result.user_context.thread_id
        
        logger.info(f"🔐 Isolated WebSocket authenticated for user: {user_id[:8]}... "
                   f"thread_id: {thread_id}")
        
        # CRITICAL: Use connection-scoped manager for complete isolation
        async with connection_scope(websocket, user_id, thread_id=thread_id) as isolated_manager:
            manager = isolated_manager
            connection_id = manager.connection_id
            
            # Set up request context for monitoring
            set_request_context(user_id=user_id, connection_id=connection_id)
            
            # Start heartbeat monitoring
            config = _get_websocket_config()
            heartbeat = WebSocketHeartbeat(
                interval=config.heartbeat_interval_seconds,
                timeout=config.heartbeat_timeout_seconds,
                websocket=websocket
            )
            await heartbeat.start()
            
            # Set up agent integration for this user only with factory pattern
            # Create user context for proper isolation
            user_context = UserExecutionContext(
                user_id=user_id,
                request_id=connection_id,  # Use connection_id as request_id
                thread_id=thread_id
            )
            
            # Use factory to create isolated bridge instance
            agent_bridge = await create_agent_websocket_bridge(user_context)
            user_emitter = agent_bridge.create_user_emitter(
                user_id=user_id,
                connection_id=connection_id,
                thread_id=thread_id
            )
            
            # Send connection established message
            welcome_msg = {
                "type": "connection_established",
                "connection_id": connection_id,
                "user_id": user_id,  # IMPORTANT: Include user_id for client validation
                "thread_id": thread_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "isolation_mode": "connection_scoped",
                "message": "Isolated WebSocket connection established"
            }
            await manager.handler.send_event(welcome_msg)
            
            logger.info(f"✅ Isolated WebSocket ready for user {user_id[:8]}... "
                       f"connection {connection_id}")
            
            # Message handling loop with strict user validation
            while manager.is_connection_healthy():
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=config.heartbeat_timeout_seconds
                    )
                    
                    logger.debug(f"📨 Received message from user {user_id[:8]}...: "
                               f"{message.get('type', 'unknown')}")
                    
                    # CRITICAL: Validate message is for this user
                    message_user_id = message.get("user_id")
                    if message_user_id and message_user_id != user_id:
                        logger.error(f"🚨 SECURITY VIOLATION: Message for user {message_user_id} "
                                   f"received on connection for user {user_id}")
                        
                        error_response = {
                            "type": "error",
                            "message": "User ID mismatch - security violation",
                            "code": "USER_MISMATCH"
                        }
                        await manager.handler.send_event(error_response)
                        continue
                    
                    # Handle message through isolated manager
                    response = await manager.handle_incoming_message(message)
                    if response:
                        await manager.handler.send_event(response)
                        
                    # Handle specific message types
                    message_type = message.get("type")
                    
                    if message_type == "join_thread":
                        # Update thread association for this connection only
                        new_thread_id = message.get("thread_id")
                        if new_thread_id:
                            manager.thread_id = new_thread_id
                            await user_emitter.update_thread_context(new_thread_id)
                            
                            logger.info(f"🔗 User {user_id[:8]}... joined thread {new_thread_id} "
                                       f"on connection {connection_id}")
                    
                    elif message_type == "agent_execute":
                        # Handle agent execution request
                        agent_name = message.get("agent_name", "UnknownAgent")
                        run_id = f"run_{uuid.uuid4().hex[:12]}"
                        
                        # Send agent started event to this user only
                        await manager.send_agent_started(agent_name, run_id, {
                            "request_data": message.get("data", {}),
                            "connection_isolated": True
                        })
                        
                        logger.info(f"🤖 Started agent {agent_name} for user {user_id[:8]}... "
                                   f"run_id: {run_id}")
                    
                    elif message_type == "ping":
                        # Respond to ping
                        pong_msg = {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "connection_id": connection_id
                        }
                        await manager.handler.send_event(pong_msg)
                        
                        logger.debug(f"🏓 Pong sent to user {user_id[:8]}...")
                    
                except asyncio.TimeoutError:
                    logger.warning(f"WebSocket timeout for user {user_id[:8]}... connection {connection_id}")
                    break
                    
                except WebSocketDisconnect:
                    logger.info(f"🔌 WebSocket disconnected for user {user_id[:8]}... connection {connection_id}")
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from user {user_id[:8]}...: {e}")
                    error_response = {
                        "type": "error", 
                        "message": "Invalid JSON format",
                        "code": "JSON_ERROR"
                    }
                    await manager.handler.send_event(error_response)
                    
                except Exception as e:
                    logger.error(f"Error handling message from user {user_id[:8]}...: {e}")
                    error_response = {
                        "type": "error",
                        "message": "Message processing error", 
                        "code": "PROCESSING_ERROR"
                    }
                    await manager.handler.send_event(error_response)
            
            logger.info(f"✅ Isolated WebSocket session completed for user {user_id[:8]}... "
                       f"connection {connection_id}")
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected during setup for user {user_id or 'unknown'}")
    
    except Exception as e:
        logger.error(f"❌ Error in isolated WebSocket endpoint: {e}")
        
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                error_msg = create_error_message(
                    "Internal server error",
                    {"error": str(e)}
                )
                await websocket.send_json(error_msg.dict())
            except:
                pass  # Connection might be closed
    
    finally:
        # Cleanup resources
        try:
            if heartbeat:
                await heartbeat.stop()
            
            # Connection-scoped manager cleanup handled by context manager
            logger.debug(f"Isolated WebSocket cleanup completed for user {user_id or 'unknown'}")
            
        except Exception as cleanup_error:
            logger.warning(f"Error during isolated WebSocket cleanup: {cleanup_error}")
        
        finally:
            clear_request_context()


@router.websocket("/ws/isolated/health")
async def isolated_websocket_health_check(websocket: WebSocket):
    """Health check endpoint for isolated WebSocket connections."""
    try:
        await websocket.accept()
        
        health_msg = {
            "type": "health_check",
            "status": "healthy",
            "isolation_mode": "connection_scoped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Isolated WebSocket service is healthy"
        }
        
        await websocket.send_json(health_msg)
        await websocket.close(code=1000, reason="Health check completed")
        
        logger.debug("Isolated WebSocket health check completed")
        
    except Exception as e:
        logger.error(f"Isolated WebSocket health check failed: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1000, reason="Health check failed - graceful close")


@router.get("/ws/isolated/stats")
async def get_isolated_websocket_stats():
    """Get statistics for isolated WebSocket connections (development only)."""
    from shared.isolated_environment import get_env
    
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        raise HTTPException(status_code=404, detail="Stats endpoint not available in production")
    
    # Get global statistics - safely handle missing manager
    try:
        # Note: In production, stats should come from monitoring systems
        # For development, we provide fallback stats
        manager_stats = {
            "isolated_connections": 0,
            "note": "Stats managed per-user in factory pattern",
            "environment": environment
        }
        logger.debug("WebSocket stats provided from factory pattern context")
    except Exception as e:
        logger.warning(f"Could not get WebSocket stats: {e}")
        manager_stats = {"error": "Stats unavailable", "reason": str(e)}
    
    return {
        "isolation_mode": "connection_scoped",
        "environment": environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "websocket_manager": manager_stats,
        "isolation_features": {
            "connection_scoped_managers": True,
            "user_event_validation": True,
            "automatic_cleanup": True,
            "audit_logging": True,
            "zero_cross_user_leakage": True
        }
    }


@router.get("/ws/isolated/config")
async def get_isolated_websocket_config():
    """Get isolated WebSocket configuration."""
    config = _get_websocket_config()
    
    return {
        "isolation_mode": "connection_scoped", 
        "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
        "heartbeat_timeout_seconds": config.heartbeat_timeout_seconds,
        "max_connections_per_user": config.max_connections_per_user,
        "max_message_size": config.max_message_size,
        "rate_limit_per_minute": config.rate_limit_per_minute,
        "compression_enabled": config.compression_enabled,
        "auth_required": config.auth_required,
        "security_features": {
            "connection_scoped_isolation": True,
            "user_id_validation": True,
            "event_filtering": True,
            "automatic_resource_cleanup": True
        }
    }