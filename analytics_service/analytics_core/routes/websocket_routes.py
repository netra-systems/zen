"""
Analytics Service WebSocket Routes
Real-time metrics streaming and live analytics updates
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.websockets import WebSocketState

from analytics_service.analytics_core.config import AnalyticsConfig
from shared.isolated_environment import get_env
from analytics_service.analytics_core.database.connection import get_redis_connection
from analytics_service.analytics_core.services.metrics_service import MetricsService
from analytics_service.analytics_core.services.websocket_auth_service import WebSocketAuthService
from analytics_service.analytics_core.utils.websocket_security import WebSocketSecurityManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])

# Initialize services
metrics_service = MetricsService()
auth_service = WebSocketAuthService()
security_manager = WebSocketSecurityManager()


class ConnectionManager:
    """
    WebSocket connection manager for analytics streaming.
    
    Handles connection lifecycle, authentication, and message broadcasting.
    Implements security measures and rate limiting for production use.
    """
    
    def __init__(self):
        # Active connections organized by type
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "realtime_metrics": set(),
            "live_events": set(),
            "system_alerts": set()
        }
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Rate limiting
        self.last_message_time: Dict[WebSocket, float] = {}
        self.message_counts: Dict[WebSocket, int] = {}
        
        # Background tasks
        self._streaming_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Start background processes
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for streaming and cleanup."""
        # Start metrics streaming
        self._streaming_tasks["metrics"] = asyncio.create_task(
            self._stream_realtime_metrics()
        )
        
        # Start event streaming
        self._streaming_tasks["events"] = asyncio.create_task(
            self._stream_live_events()
        )
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(
            self._cleanup_stale_connections()
        )
    
    async def connect(
        self, 
        websocket: WebSocket, 
        stream_type: str = "realtime_metrics",
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> bool:
        """
        Accept and authenticate a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            stream_type: Type of stream (realtime_metrics, live_events, system_alerts)
            user_id: Optional user ID for authorization
            auth_token: Optional authentication token
            
        Returns:
            bool: True if connection accepted, False if rejected
        """
        try:
            # Accept the connection first
            await websocket.accept()
            logger.info(f"WebSocket connection attempt for stream: {stream_type}")
            
            # Authenticate if token provided
            authenticated_user = None
            if auth_token:
                try:
                    authenticated_user = await auth_service.authenticate_websocket_token(auth_token)
                    if not authenticated_user:
                        await websocket.close(code=4001, reason="Authentication failed")
                        return False
                    logger.info(f"WebSocket authenticated for user: {authenticated_user.get('user_id')}")
                except Exception as auth_error:
                    logger.warning(f"WebSocket authentication error: {auth_error}")
                    await websocket.close(code=4001, reason="Authentication error")
                    return False
            
            # Security checks
            if not await security_manager.validate_connection_security(websocket):
                await websocket.close(code=4003, reason="Security validation failed")
                return False
            
            # Rate limiting check
            if not self._check_rate_limit(websocket):
                await websocket.close(code=4029, reason="Rate limit exceeded")
                return False
            
            # Add to connection pool
            if stream_type not in self.active_connections:
                self.active_connections[stream_type] = set()
            
            self.active_connections[stream_type].add(websocket)
            
            # Store connection metadata
            self.connection_metadata[websocket] = {
                "stream_type": stream_type,
                "user_id": user_id,
                "authenticated_user": authenticated_user,
                "connected_at": datetime.now(timezone.utc),
                "last_ping": time.time(),
                "message_count": 0,
                "client_info": {
                    "headers": dict(websocket.headers),
                    "query_params": dict(websocket.query_params)
                }
            }
            
            logger.info(
                f"WebSocket connected: {stream_type}, "
                f"Total connections: {len(self.active_connections[stream_type])}"
            )
            
            # Send welcome message
            await self._send_welcome_message(websocket, stream_type, authenticated_user)
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            try:
                await websocket.close(code=4000, reason="Connection error")
            except:
                pass
            return False
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and clean up resources."""
        try:
            # Remove from all connection pools
            for stream_type, connections in self.active_connections.items():
                if websocket in connections:
                    connections.discard(websocket)
                    logger.info(f"WebSocket disconnected from {stream_type}")
            
            # Clean up metadata
            metadata = self.connection_metadata.pop(websocket, {})
            self.last_message_time.pop(websocket, None)
            self.message_counts.pop(websocket, None)
            
            # Log disconnection
            if metadata:
                duration = (datetime.now(timezone.utc) - metadata["connected_at"]).total_seconds()
                logger.info(
                    f"WebSocket session ended: duration={duration:.1f}s, "
                    f"messages_sent={metadata.get('message_count', 0)}"
                )
        
        except Exception as e:
            logger.error(f"WebSocket disconnect cleanup failed: {e}")
    
    async def broadcast_to_stream(self, stream_type: str, message: Dict[str, Any]):
        """Broadcast a message to all connections of a specific stream type."""
        if stream_type not in self.active_connections:
            return
        
        connections = self.active_connections[stream_type].copy()
        if not connections:
            return
        
        # Prepare message
        message_json = json.dumps({
            **message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream_type": stream_type
        })
        
        # Send to all connections
        disconnected = []
        for websocket in connections:
            try:
                if websocket.application_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_json)
                    
                    # Update metadata
                    if websocket in self.connection_metadata:
                        self.connection_metadata[websocket]["message_count"] += 1
                        self.connection_metadata[websocket]["last_ping"] = time.time()
                else:
                    disconnected.append(websocket)
                    
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    def _check_rate_limit(self, websocket: WebSocket) -> bool:
        """Check if connection is within rate limits."""
        now = time.time()
        
        # Initialize counters
        if websocket not in self.last_message_time:
            self.last_message_time[websocket] = now
            self.message_counts[websocket] = 0
            return True
        
        # Reset counter every minute
        if now - self.last_message_time[websocket] >= 60:
            self.message_counts[websocket] = 0
            self.last_message_time[websocket] = now
        
        # Check message count (allow up to 120 messages per minute)
        return self.message_counts[websocket] < 120
    
    async def _send_welcome_message(
        self, 
        websocket: WebSocket, 
        stream_type: str,
        authenticated_user: Optional[Dict[str, Any]]
    ):
        """Send welcome message to new connection."""
        config = AnalyticsConfig.get_instance()
        
        welcome_message = {
            "type": "connection_established",
            "stream_type": stream_type,
            "service": "analytics-service",
            "version": "1.0.0",
            "environment": config.environment,
            "authenticated": authenticated_user is not None,
            "user_info": authenticated_user if authenticated_user else None,
            "available_streams": list(self.active_connections.keys()),
            "streaming_interval_seconds": 5,
            "message": f"Connected to {stream_type} stream"
        }
        
        try:
            await websocket.send_text(json.dumps(welcome_message))
        except Exception as e:
            logger.warning(f"Failed to send welcome message: {e}")
    
    async def _stream_realtime_metrics(self):
        """Background task to stream real-time metrics every 5 seconds."""
        while True:
            try:
                if self.active_connections["realtime_metrics"]:
                    # Get current metrics
                    try:
                        metrics_data = await metrics_service.get_realtime_metrics()
                        
                        # Broadcast to all realtime_metrics connections
                        await self.broadcast_to_stream("realtime_metrics", {
                            "type": "metrics_update",
                            "data": metrics_data
                        })
                        
                    except Exception as e:
                        logger.error(f"Failed to get realtime metrics: {e}")
                        
                        # Send error message to connections
                        await self.broadcast_to_stream("realtime_metrics", {
                            "type": "error",
                            "message": "Failed to retrieve metrics",
                            "error_code": "METRICS_ERROR"
                        })
                
                await asyncio.sleep(5)  # 5-second interval
                
            except asyncio.CancelledError:
                logger.info("Realtime metrics streaming task cancelled")
                break
            except Exception as e:
                logger.error(f"Realtime metrics streaming error: {e}")
                await asyncio.sleep(5)
    
    async def _stream_live_events(self):
        """Background task to stream live events."""
        while True:
            try:
                if self.active_connections["live_events"]:
                    # Get recent events (last 30 seconds)
                    try:
                        recent_events = await metrics_service.get_recent_events(
                            time_window_seconds=30
                        )
                        
                        if recent_events:
                            # Broadcast recent events
                            await self.broadcast_to_stream("live_events", {
                                "type": "events_update", 
                                "data": {
                                    "events": recent_events,
                                    "count": len(recent_events),
                                    "time_window_seconds": 30
                                }
                            })
                    
                    except Exception as e:
                        logger.error(f"Failed to get live events: {e}")
                
                await asyncio.sleep(10)  # 10-second interval for events
                
            except asyncio.CancelledError:
                logger.info("Live events streaming task cancelled")
                break
            except Exception as e:
                logger.error(f"Live events streaming error: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_stale_connections(self):
        """Background task to clean up stale connections."""
        while True:
            try:
                now = time.time()
                stale_connections = []
                
                # Find stale connections (no ping in last 2 minutes)
                for websocket, metadata in self.connection_metadata.items():
                    last_ping = metadata.get("last_ping", now)
                    if now - last_ping > 120:  # 2 minutes
                        stale_connections.append(websocket)
                
                # Clean up stale connections
                for websocket in stale_connections:
                    logger.info("Cleaning up stale WebSocket connection")
                    await self.disconnect(websocket)
                    try:
                        await websocket.close(code=4008, reason="Connection timeout")
                    except:
                        pass
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Connection cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Connection cleanup error: {e}")
                await asyncio.sleep(60)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        stats = {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "connections_by_stream": {
                stream_type: len(connections)
                for stream_type, connections in self.active_connections.items()
            },
            "active_streams": len(self._streaming_tasks),
            "uptime_seconds": time.time() - getattr(self, '_start_time', time.time())
        }
        
        # Add per-connection stats
        connection_details = []
        for websocket, metadata in self.connection_metadata.items():
            if websocket.application_state == WebSocketState.CONNECTED:
                connection_details.append({
                    "stream_type": metadata.get("stream_type"),
                    "user_id": metadata.get("user_id"),
                    "connected_duration_seconds": (
                        datetime.now(timezone.utc) - metadata["connected_at"]
                    ).total_seconds(),
                    "message_count": metadata.get("message_count", 0),
                    "authenticated": metadata.get("authenticated_user") is not None
                })
        
        stats["connection_details"] = connection_details
        return stats
    
    async def shutdown(self):
        """Gracefully shutdown the connection manager."""
        logger.info("Shutting down WebSocket connection manager")
        
        # Cancel background tasks
        for task_name, task in self._streaming_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Cancelled streaming task: {task_name}")
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.info("Cancelled cleanup task")
        
        # Close all active connections
        all_connections = []
        for connections in self.active_connections.values():
            all_connections.extend(connections)
        
        for websocket in all_connections:
            try:
                await websocket.close(code=4000, reason="Server shutdown")
            except:
                pass
        
        logger.info("WebSocket connection manager shutdown complete")


# Global connection manager instance
connection_manager = ConnectionManager()


@router.websocket("/analytics")
async def analytics_websocket(
    websocket: WebSocket,
    stream: str = Query(default="realtime_metrics", description="Stream type"),
    token: Optional[str] = Query(default=None, description="Authentication token"),
    user_id: Optional[str] = Query(default=None, description="User ID")
):
    """
    Main analytics WebSocket endpoint for real-time streaming.
    
    Supported streams:
    - realtime_metrics: Live system metrics (5-second intervals)
    - live_events: Recent event feed (10-second intervals)  
    - system_alerts: Critical system alerts (as they occur)
    
    Authentication is optional but recommended for production use.
    """
    logger.info(f"WebSocket connection request: stream={stream}, user={user_id}")
    
    # Validate stream type
    valid_streams = ["realtime_metrics", "live_events", "system_alerts"]
    if stream not in valid_streams:
        await websocket.close(code=4400, reason=f"Invalid stream type. Valid: {valid_streams}")
        return
    
    # Connect and authenticate
    connected = await connection_manager.connect(
        websocket=websocket,
        stream_type=stream,
        user_id=user_id,
        auth_token=token
    )
    
    if not connected:
        return  # Connection was rejected and closed
    
    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (with timeout for ping/pong)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # Handle client message
                await _handle_client_message(websocket, message)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                except:
                    break  # Connection lost
                    
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(websocket)


async def _handle_client_message(websocket: WebSocket, message: str):
    """Handle incoming client messages."""
    try:
        data = json.loads(message)
        message_type = data.get("type")
        
        if message_type == "pong":
            # Update last ping time
            metadata = connection_manager.connection_metadata.get(websocket, {})
            metadata["last_ping"] = time.time()
            
        elif message_type == "subscribe":
            # Handle stream subscription changes
            new_stream = data.get("stream_type")
            if new_stream in connection_manager.active_connections:
                # Move connection to different stream
                await _change_stream_subscription(websocket, new_stream)
                
        elif message_type == "get_stats":
            # Send connection statistics
            stats = connection_manager.get_connection_stats()
            await websocket.send_text(json.dumps({
                "type": "stats_response",
                "data": stats
            }))
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON message: {message}")
    except Exception as e:
        logger.error(f"Error handling client message: {e}")


async def _change_stream_subscription(websocket: WebSocket, new_stream_type: str):
    """Change a connection's stream subscription."""
    try:
        metadata = connection_manager.connection_metadata.get(websocket, {})
        old_stream = metadata.get("stream_type")
        
        if old_stream and old_stream != new_stream_type:
            # Remove from old stream
            connection_manager.active_connections[old_stream].discard(websocket)
            
            # Add to new stream
            connection_manager.active_connections[new_stream_type].add(websocket)
            
            # Update metadata
            metadata["stream_type"] = new_stream_type
            
            # Send confirmation
            await websocket.send_text(json.dumps({
                "type": "stream_changed",
                "old_stream": old_stream,
                "new_stream": new_stream_type,
                "message": f"Switched to {new_stream_type} stream"
            }))
            
            logger.info(f"WebSocket stream changed: {old_stream} -> {new_stream_type}")
            
    except Exception as e:
        logger.error(f"Stream subscription change failed: {e}")


@router.get("/analytics/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Provides insights into current connections, streaming performance,
    and resource usage for monitoring and debugging.
    """
    try:
        stats = connection_manager.get_connection_stats()
        
        # Add system resource info
        config = AnalyticsConfig.get_instance()
        stats.update({
            "service": "analytics-service",
            "environment": config.environment,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Stats retrieval failed: {str(e)}"
        )


@router.post("/analytics/broadcast")
async def broadcast_message(
    stream_type: str,
    message: Dict[str, Any],
    auth_token: Optional[str] = None
):
    """
    Broadcast a custom message to all connections of a stream type.
    
    Useful for sending alerts, notifications, or custom events.
    Requires authentication in production environments.
    """
    try:
        # Authenticate for broadcast (if required)
        config = AnalyticsConfig.get_instance()
        if config.environment == "production" and not auth_token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for broadcasting"
            )
        
        if auth_token:
            # Validate token
            user = await auth_service.authenticate_websocket_token(auth_token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        # Validate stream type
        if stream_type not in connection_manager.active_connections:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stream type: {stream_type}"
            )
        
        # Broadcast message
        await connection_manager.broadcast_to_stream(stream_type, {
            "type": "custom_broadcast",
            "data": message
        })
        
        connection_count = len(connection_manager.active_connections[stream_type])
        
        return {
            "success": True,
            "stream_type": stream_type,
            "connections_notified": connection_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Broadcast failed: {str(e)}"
        )


# Graceful shutdown handler
@asynccontextmanager
async def websocket_lifespan():
    """Lifespan context manager for WebSocket resources."""
    try:
        yield
    finally:
        await connection_manager.shutdown()