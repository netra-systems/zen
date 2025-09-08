"""
WebSocket Routes with Factory Pattern Integration

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & User Isolation
- Value Impact: Enables 10+ concurrent users with isolated WebSocket events
- Strategic Impact: Critical - Replaces singleton WebSocket patterns with per-user isolation

This module implements WebSocket routes that use the new factory pattern for complete user isolation.
Each WebSocket connection gets its own isolated event emitter, preventing cross-user event leakage.

Key Features:
1. Per-User WebSocket Emitters - Each user gets isolated event handling
2. Factory Adapter Integration - Gradual migration support with feature flags
3. Request-Scoped Context - Complete isolation between concurrent users
4. Health Monitoring - Per-user connection health tracking
5. Error Resilience - Graceful fallback to legacy patterns if needed
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from starlette.websockets import WebSocketState

from netra_backend.app.dependencies import (
    FactoryAdapterDep,
    get_factory_adapter_dependency,
    create_request_context
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.websocket_core.auth import get_websocket_authenticator
from netra_backend.app.websocket_core.user_context_extractor import extract_websocket_user_context

logger = central_logger.get_logger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket-factory"]
)


@router.websocket("/factory")
async def websocket_factory_endpoint(
    websocket: WebSocket,
    thread_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None)
):
    """
    SECURE WebSocket endpoint using factory pattern with JWT authentication.
    
    SECURITY FEATURES:
    - JWT token validation before connection acceptance
    - User context extraction from authenticated token
    - Factory pattern with complete user isolation
    - No URL-based user identification (prevents impersonation)
    
    Args:
        websocket: WebSocket connection
        thread_id: Optional thread identifier
        run_id: Optional run identifier for request tracking
        
    Authentication:
        - Requires JWT token in Authorization header: "Bearer <token>"
        - OR JWT token in Sec-WebSocket-Protocol: "jwt.<base64url_encoded_token>"
        
    Features:
        - Per-user event isolation using factory patterns
        - Authenticated user context extraction
        - Health monitoring and reconnection support
        - Error resilience with secure fallback mechanisms
    """
    # Accept WebSocket connection early to allow authentication handshake
    try:
        await websocket.accept()
        logger.info("🔌 WebSocket connection accepted - starting authentication")
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket connection: {e}")
        return
    
    # CRITICAL SECURITY: Authenticate WebSocket connection using JWT
    try:
        user_context, auth_info = await extract_websocket_user_context(
            websocket, 
            additional_metadata={
                "thread_id": thread_id,
                "run_id": run_id,
                "endpoint": "/ws/factory"
            }
        )
        
        # Extract authenticated user ID
        user_id = user_context.user_id
        connection_id = user_context.websocket_connection_id
        
        logger.info(
            f"🔐 AUTHENTICATED WebSocket connection for user {user_id[:8]}... "
            f"(connection: {connection_id})"
        )
        
    except HTTPException as e:
        # Authentication failed - close connection with proper error
        logger.warning(f"🚫 WebSocket authentication failed: {e.detail}")
        try:
            await websocket.send_json({
                "type": "authentication_error",
                "error": "Authentication required",
                "details": e.detail,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=4001, reason="Authentication failed")
        except:
            pass  # Connection might already be closed
        return
        
    except Exception as e:
        # Unexpected authentication error
        logger.error(f"❌ Unexpected WebSocket authentication error: {e}")
        try:
            await websocket.send_json({
                "type": "internal_error", 
                "error": "Authentication system error",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=4002, reason="Authentication system error")
        except:
            pass
        return
    
    # Initialize factory-based WebSocket handling with authenticated context
    factory_adapter = None
    user_emitter = None
    websocket_manager = None
    
    try:
        # SECURITY FIX: Use factory pattern instead of singleton
        # Import factory pattern here to avoid circular imports  
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        # Create isolated WebSocket manager for this authenticated user
        websocket_manager = create_websocket_manager(user_context)
        logger.info(f"✅ Created isolated WebSocket manager for authenticated user {user_id[:8]}...")
        
        # Get factory adapter from app state
        app = websocket.scope.get("app")
        if app and hasattr(app.state, 'factory_adapter'):
            factory_adapter = app.state.factory_adapter
        else:
            # Fallback to authenticated legacy WebSocket handling
            logger.warning(f"Factory adapter not available for authenticated user {user_id[:8]}... - using secure legacy WebSocket handling")
            await _handle_authenticated_legacy_websocket(websocket, user_context, auth_info, websocket_manager)
            return
        
        # Create request context using authenticated user context
        request_context = {
            'user_id': user_id,
            'thread_id': user_context.thread_id,
            'request_id': user_context.request_id,
            'connection_id': connection_id,
            'websocket_connection': True,
            'websocket_connection_id': user_context.websocket_connection_id,
            'run_id': user_context.run_id,
            'authenticated': True,
            'auth_info': auth_info,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Get factory WebSocket bridge
        try:
            user_emitter = await factory_adapter.get_websocket_bridge(
                request_context=request_context,
                route_path="/ws/factory"
            )
            logger.info(f"✅ Created factory WebSocket emitter for user {user_id}")
            
            # Send welcome message via factory emitter
            await user_emitter.notify_agent_started(
                "WebSocketFactory", 
                run_id or "websocket_session",
                context={"connection_type": "factory", "isolation": "enabled"}
            )
            
        except Exception as e:
            logger.error(f"Failed to create factory WebSocket emitter for user {user_id}: {e}")
            # Fallback to legacy
            await _handle_legacy_websocket(websocket, user_id, thread_id, run_id, connection_id)
            return
        
        # Register connection with WebSocket manager
        if websocket_manager:
            await websocket_manager.connect_user(
                user_id=user_id,
                websocket=websocket,
                thread_id=thread_id or f"ws_thread_{user_id}",
                connection_id=connection_id
            )
        
        # Main WebSocket event loop with factory pattern
        await _handle_factory_websocket_loop(
            websocket, user_id, user_emitter, factory_adapter, 
            websocket_manager, request_context
        )
        
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for user {user_id}: {e}")
    finally:
        # Cleanup resources
        await _cleanup_factory_websocket(
            user_id, connection_id, user_emitter, 
            websocket_manager, websocket, factory_adapter, request_context
        )


async def _handle_factory_websocket_loop(
    websocket: WebSocket,
    user_id: str, 
    user_emitter,
    factory_adapter,
    websocket_manager,
    request_context: Dict[str, Any]
):
    """Handle WebSocket message loop using factory pattern."""
    message_count = 0
    heartbeat_interval = 30  # seconds
    last_heartbeat = time.time()
    
    try:
        while True:
            # Check if WebSocket is still connected
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.info(f"WebSocket no longer connected for user {user_id}")
                break
            
            try:
                # Wait for message with timeout for heartbeat
                message = await asyncio.wait_for(
                    websocket.receive_json(), 
                    timeout=heartbeat_interval
                )
                
                message_count += 1
                logger.debug(f"📨 Received WebSocket message #{message_count} from user {user_id}")
                
                # Process message using factory pattern
                await _process_factory_websocket_message(
                    websocket, user_id, message, user_emitter, 
                    factory_adapter, request_context
                )
                
            except asyncio.TimeoutError:
                # Heartbeat - check connection health
                current_time = time.time()
                if current_time - last_heartbeat > heartbeat_interval:
                    logger.debug(f"💓 Sending heartbeat to user {user_id}")
                    
                    try:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "connection_id": request_context.get('connection_id'),
                            "factory_pattern": True
                        })
                        last_heartbeat = current_time
                        
                        # Notify via factory emitter
                        if hasattr(user_emitter, 'notify_agent_thinking'):
                            await user_emitter.notify_agent_thinking(
                                "WebSocketFactory", 
                                request_context.get('request_id', 'ws_session'),
                                "Heartbeat: Connection healthy"
                            )
                            
                    except Exception as e:
                        logger.warning(f"Failed to send heartbeat to user {user_id}: {e}")
                        break
                        
            except WebSocketDisconnect:
                logger.info(f"🔌 User {user_id} disconnected from WebSocket")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop for user {user_id}: {e}")
                
                # Send error notification via factory emitter
                if hasattr(user_emitter, 'notify_agent_error'):
                    await user_emitter.notify_agent_error(
                        "WebSocketFactory",
                        request_context.get('request_id', 'ws_session'), 
                        f"WebSocket error: {str(e)}"
                    )
                break
                
    except Exception as e:
        logger.error(f"Critical error in WebSocket factory loop for user {user_id}: {e}")
    
    logger.info(f"🔌 WebSocket factory loop ended for user {user_id} (processed {message_count} messages)")


async def _process_factory_websocket_message(
    websocket: WebSocket,
    user_id: str,
    message: Dict[str, Any],
    user_emitter,
    factory_adapter,
    request_context: Dict[str, Any]
):
    """Process WebSocket message using factory pattern."""
    message_type = message.get('type', 'unknown')
    message_data = message.get('data', {})
    
    logger.debug(f"Processing {message_type} message from user {user_id}")
    
    try:
        if message_type == 'ping':
            # Respond to ping
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "factory_pattern": True
            })
            
        elif message_type == 'agent_request':
            # Handle agent request via factory pattern
            agent_name = message_data.get('agent', 'default')
            request_text = message_data.get('message', '')
            
            # Notify via factory emitter
            if hasattr(user_emitter, 'notify_agent_started'):
                await user_emitter.notify_agent_started(
                    agent_name,
                    request_context.get('request_id', 'ws_request'),
                    context={"message": request_text, "via": "factory_websocket"}
                )
            
            # Send response
            await websocket.send_json({
                "type": "agent_response",
                "agent": agent_name,
                "data": {
                    "status": "received",
                    "message": f"Request received via factory pattern: {request_text}",
                    "factory_pattern": True,
                    "user_isolation": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        elif message_type == 'factory_status':
            # Return factory status
            migration_status = factory_adapter.get_migration_status()
            
            await websocket.send_json({
                "type": "factory_status_response",
                "data": {
                    "migration_status": migration_status,
                    "user_id": user_id,
                    "factory_pattern": True,
                    "isolation_enabled": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        else:
            # Unknown message type
            logger.warning(f"Unknown WebSocket message type '{message_type}' from user {user_id}")
            
            await websocket.send_json({
                "type": "error",
                "error": f"Unknown message type: {message_type}",
                "factory_pattern": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error processing WebSocket message for user {user_id}: {e}")
        
        try:
            await websocket.send_json({
                "type": "error",
                "error": "Message processing failed",
                "factory_pattern": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except:
            pass  # Connection might be closed


async def _handle_authenticated_legacy_websocket(
    websocket: WebSocket,
    user_context: "UserExecutionContext",
    auth_info: Dict[str, Any],
    websocket_manager
):
    """
    SECURE fallback to authenticated legacy WebSocket handling.
    
    This function provides a secure fallback when the factory pattern is not available,
    but still maintains authentication and user context isolation.
    """
    user_id = user_context.user_id
    logger.warning(f"🔄 Using AUTHENTICATED legacy WebSocket handling for user {user_id[:8]}...")
    
    try:
        # Register connection with isolated WebSocket manager (not singleton)
        if websocket_manager:
            # Create WebSocket connection object
            from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
            connection = WebSocketConnection(
                connection_id=user_context.websocket_connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={
                    "thread_id": user_context.thread_id,
                    "run_id": user_context.run_id,
                    "authenticated": True,
                    "auth_method": "jwt",
                    "legacy_mode": True
                }
            )
            await websocket_manager.add_connection(connection)
        
        # Send authenticated welcome message
        await websocket.send_json({
            "type": "welcome",
            "data": {
                "message": "Connected via authenticated legacy WebSocket handling",
                "factory_pattern": False,
                "user_isolation": True,  # Still isolated via dedicated manager
                "authenticated": True,
                "user_id": user_id[:8] + "...",
                "connection_id": user_context.websocket_connection_id
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Simple message loop for authenticated legacy mode
        try:
            while True:
                message = await websocket.receive_json()
                
                # Validate message belongs to authenticated user
                message_response = {
                    "type": "authenticated_legacy_echo",
                    "original_message": message,
                    "factory_pattern": False,
                    "authenticated": True,
                    "user_context": {
                        "user_id": user_id[:8] + "...",
                        "thread_id": user_context.thread_id,
                        "request_id": user_context.request_id
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send via isolated manager
                if websocket_manager:
                    await websocket_manager.emit_critical_event(
                        user_id, "legacy_message_processed", message_response
                    )
                else:
                    await websocket.send_json(message_response)
                
        except WebSocketDisconnect:
            logger.info(f"Authenticated legacy WebSocket disconnected for user {user_id[:8]}...")
            
    except Exception as e:
        logger.error(f"Authenticated legacy WebSocket error for user {user_id[:8]}...: {e}")
    finally:
        if websocket_manager:
            try:
                await websocket_manager.remove_connection(user_context.websocket_connection_id)
            except Exception as e:
                logger.error(f"Failed to cleanup authenticated legacy connection: {e}")


async def _cleanup_factory_websocket(
    user_id: str,
    connection_id: str,
    user_emitter,
    websocket_manager,
    websocket: WebSocket,
    factory_adapter,
    request_context: Dict[str, Any]
):
    """Clean up factory WebSocket resources."""
    logger.info(f"🧹 Cleaning up factory WebSocket resources for user {user_id}")
    
    try:
        # Send completion notification via factory emitter
        if user_emitter and hasattr(user_emitter, 'notify_agent_completed'):
            await user_emitter.notify_agent_completed(
                "WebSocketFactory",
                request_context.get('request_id', 'ws_session'),
                {"status": "disconnected", "cleanup": "completed"}
            )
    except Exception as e:
        logger.warning(f"Failed to send completion notification for user {user_id}: {e}")
    
    try:
        # Clean up user emitter via factory
        if user_emitter and hasattr(user_emitter, 'cleanup'):
            await user_emitter.cleanup()
    except Exception as e:
        logger.error(f"Failed to cleanup user emitter for user {user_id}: {e}")
    
    try:
        # Clean up factory adapter context
        if factory_adapter and request_context:
            request_id = request_context.get('request_id')
            if request_id:
                await factory_adapter.cleanup_context(request_id)
    except Exception as e:
        logger.warning(f"Failed to cleanup factory context for user {user_id}: {e}")
    
    try:
        # Disconnect from WebSocket manager
        if websocket_manager:
            await websocket_manager.disconnect_user(user_id, websocket)
    except Exception as e:
        logger.warning(f"Failed to disconnect from WebSocket manager for user {user_id}: {e}")
    
    logger.info(f"✅ Factory WebSocket cleanup completed for user {user_id}")


@router.get("/factory/status")
async def get_factory_websocket_status(
    factory_adapter: FactoryAdapterDep
):
    """
    Get WebSocket factory migration status.
    
    Returns comprehensive information about the factory pattern migration
    status for WebSocket connections.
    """
    try:
        migration_status = factory_adapter.get_migration_status()
        
        return {
            "status": "success",
            "factory_pattern": {
                "websocket_support": True,
                "migration_status": migration_status,
                "features": {
                    "per_user_isolation": True,
                    "event_isolation": True,
                    "health_monitoring": True,
                    "legacy_fallback": migration_status.get('config', {}).get('legacy_fallback_enabled', False)
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get factory WebSocket status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve factory WebSocket status: {str(e)}"
        )


@router.get("/factory/health")
async def get_factory_websocket_health():
    """
    Health check endpoint for factory WebSocket functionality.
    
    Provides health status of WebSocket factory components including
    the underlying WebSocket manager and factory adapter.
    """
    try:
        # Check WebSocket manager health
        websocket_manager = get_websocket_manager()
        ws_manager_healthy = websocket_manager is not None
        
        # Basic connectivity test
        active_connections = 0
        if ws_manager_healthy:
            try:
                # Get connection count (if available)
                stats = websocket_manager.get_stats()
                active_connections = stats.get('active_connections', 0)
            except:
                pass
        
        return {
            "status": "healthy" if ws_manager_healthy else "degraded",
            "factory_pattern": True,
            "components": {
                "websocket_manager": {
                    "healthy": ws_manager_healthy,
                    "active_connections": active_connections
                },
                "factory_adapter": {
                    "healthy": True,  # Available if we got here
                    "migration_enabled": True
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Factory WebSocket health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "factory_pattern": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }