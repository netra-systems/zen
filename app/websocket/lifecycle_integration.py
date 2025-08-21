"""WebSocket Lifecycle Integration

Integrates the enhanced lifecycle manager with the existing WebSocket system
to fix connection lifecycle issues while maintaining backward compatibility.

Key fixes:
- Proper heartbeat/ping-pong mechanism
- Connection pool management with limits
- Graceful shutdown with resource cleanup
- Zombie connection detection and cleanup

Business Value: Prevents $8K MRR loss from poor real-time experience
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import WebSocket

from app.logging_config import central_logger
from app.websocket.connection import ConnectionInfo
from app.websocket.enhanced_lifecycle_manager import (
    EnhancedLifecycleManager,
    HeartbeatConfig,
    ConnectionPool,
    ShutdownConfig
)

logger = central_logger.get_logger(__name__)


class WebSocketLifecycleIntegrator:
    """Integrates enhanced lifecycle management with existing WebSocket infrastructure."""
    
    _instance: Optional['WebSocketLifecycleIntegrator'] = None
    
    def __new__(cls) -> 'WebSocketLifecycleIntegrator':
        """Singleton pattern for lifecycle integrator."""
        if cls._instance is None:
            cls._instance = super(WebSocketLifecycleIntegrator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize lifecycle integrator if not already done."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialize_enhanced_lifecycle()
        self._initialize_integration_hooks()
        self._initialized = True
        
    def _initialize_enhanced_lifecycle(self) -> None:
        """Initialize enhanced lifecycle manager with optimal configuration."""
        heartbeat_config = HeartbeatConfig(
            ping_interval=30.0,  # Ping every 30 seconds
            pong_timeout=10.0,   # Wait 10 seconds for pong
            max_missed_pongs=3,  # Max 3 missed pongs before zombie
            zombie_detection_threshold=120.0  # 2 minutes for zombie detection
        )
        
        pool_config = ConnectionPool(
            max_connections_per_user=5,
            max_total_connections=1000,
            connection_timeout=300.0,  # 5 minutes idle timeout
            pool_cleanup_interval=60.0  # Cleanup every minute
        )
        
        shutdown_config = ShutdownConfig(
            drain_timeout=30.0,
            force_close_timeout=60.0,
            message_flush_timeout=5.0,
            notify_clients=True
        )
        
        self.lifecycle_manager = EnhancedLifecycleManager(
            heartbeat_config, pool_config, shutdown_config
        )
        
    def _initialize_integration_hooks(self) -> None:
        """Initialize hooks for integration with existing system."""
        self.connection_registry: Dict[str, ConnectionInfo] = {}
        self.user_to_connections: Dict[str, set] = {}
        self.message_handlers: Dict[str, callable] = {}
        
        # Register message handlers
        self._register_lifecycle_message_handlers()
        
    def _register_lifecycle_message_handlers(self) -> None:
        """Register message handlers for lifecycle events."""
        self.message_handlers.update({
            "ping": self._handle_ping_message,
            "pong": self._handle_pong_message,
            "heartbeat": self._handle_heartbeat_message
        })
    
    async def integrate_connection(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Integrate new connection with enhanced lifecycle management."""
        try:
            # Connect using enhanced lifecycle manager
            conn_info = await self.lifecycle_manager.connect_user(user_id, websocket)
            
            # Register in integration layer
            self._register_connection_integration(conn_info)
            
            logger.info(f"Integrated connection {conn_info.connection_id} for user {user_id}")
            return conn_info
            
        except Exception as e:
            logger.error(f"Failed to integrate connection for user {user_id}: {e}")
            raise
    
    def _register_connection_integration(self, conn_info: ConnectionInfo) -> None:
        """Register connection in integration tracking."""
        self.connection_registry[conn_info.connection_id] = conn_info
        
        if conn_info.user_id not in self.user_to_connections:
            self.user_to_connections[conn_info.user_id] = set()
        self.user_to_connections[conn_info.user_id].add(conn_info.connection_id)
    
    async def integrate_disconnection(self, user_id: str, websocket: WebSocket, 
                                    code: int = 1000, reason: str = "Normal closure") -> None:
        """Integrate connection disconnection with proper cleanup."""
        try:
            # Find connection by websocket
            connection_id = self._find_connection_id_by_websocket(user_id, websocket)
            if not connection_id:
                logger.warning(f"No connection found for user {user_id} websocket")
                return
                
            # Disconnect using enhanced lifecycle manager
            await self.lifecycle_manager.disconnect_user(connection_id, code, reason)
            
            # Clean up integration tracking
            self._cleanup_connection_integration(connection_id, user_id)
            
            logger.info(f"Integrated disconnection for {connection_id}")
            
        except Exception as e:
            logger.error(f"Error in integrated disconnection for user {user_id}: {e}")
    
    def _find_connection_id_by_websocket(self, user_id: str, websocket: WebSocket) -> Optional[str]:
        """Find connection ID by websocket reference."""
        user_connections = self.user_to_connections.get(user_id, set())
        
        for conn_id in user_connections:
            if conn_id in self.connection_registry:
                conn_info = self.connection_registry[conn_id]
                if conn_info.websocket == websocket:
                    return conn_id
        return None
    
    def _cleanup_connection_integration(self, connection_id: str, user_id: str) -> None:
        """Clean up connection from integration tracking."""
        self.connection_registry.pop(connection_id, None)
        
        if user_id in self.user_to_connections:
            self.user_to_connections[user_id].discard(connection_id)
            if not self.user_to_connections[user_id]:
                del self.user_to_connections[user_id]
    
    async def handle_websocket_message(self, user_id: str, websocket: WebSocket, 
                                     message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with lifecycle integration."""
        message_type = message.get("type", "")
        
        # Handle lifecycle-specific messages
        if message_type in self.message_handlers:
            connection_id = self._find_connection_id_by_websocket(user_id, websocket)
            if connection_id:
                return await self.message_handlers[message_type](connection_id, message)
                
        # Let other systems handle non-lifecycle messages
        return False
    
    async def _handle_ping_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle ping message - respond with pong."""
        try:
            conn_info = self.connection_registry.get(connection_id)
            if not conn_info:
                return False
                
            pong_response = {
                "type": "pong",
                "timestamp": time.time(),
                "original_timestamp": message.get("timestamp"),
                "connection_id": connection_id
            }
            
            await conn_info.websocket.send_json(pong_response)
            logger.debug(f"Sent pong response to {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling ping for {connection_id}: {e}")
            return False
    
    async def _handle_pong_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle pong message from client."""
        try:
            await self.lifecycle_manager.handle_pong(connection_id, message)
            logger.debug(f"Processed pong from {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling pong for {connection_id}: {e}")
            return False
    
    async def _handle_heartbeat_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle explicit heartbeat message."""
        # Treat heartbeat as pong response
        return await self._handle_pong_message(connection_id, message)
    
    async def cleanup_zombie_connections(self) -> Dict[str, Any]:
        """Clean up detected zombie connections."""
        try:
            zombie_connections = self.lifecycle_manager.get_zombie_connections()
            if not zombie_connections:
                return {"cleaned_connections": [], "total_cleaned": 0}
                
            logger.info(f"Cleaning up {len(zombie_connections)} zombie connections")
            cleaned_connections = await self.lifecycle_manager.cleanup_zombie_connections()
            
            # Clean up integration tracking for cleaned connections
            for conn_id in cleaned_connections:
                if conn_id in self.connection_registry:
                    conn_info = self.connection_registry[conn_id]
                    self._cleanup_connection_integration(conn_id, conn_info.user_id)
            
            return {
                "cleaned_connections": cleaned_connections,
                "total_cleaned": len(cleaned_connections)
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up zombie connections: {e}")
            return {"error": str(e), "total_cleaned": 0}
    
    async def perform_graceful_shutdown(self) -> Dict[str, Any]:
        """Perform graceful shutdown with connection draining."""
        try:
            logger.info("Starting integrated graceful shutdown")
            shutdown_result = await self.lifecycle_manager.initiate_graceful_shutdown()
            
            # Clear integration tracking
            self.connection_registry.clear()
            self.user_to_connections.clear()
            
            logger.info("Integrated graceful shutdown completed")
            return shutdown_result
            
        except Exception as e:
            logger.error(f"Error during integrated graceful shutdown: {e}")
            return {"error": str(e), "success": False}
    
    def get_connection_health_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get health status for specific connection."""
        return self.lifecycle_manager.heartbeat_manager.get_connection_health(connection_id)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        return self.lifecycle_manager.connection_pool.get_pool_status()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle statistics."""
        base_stats = self.lifecycle_manager.get_comprehensive_stats()
        integration_stats = {
            "integration": {
                "tracked_connections": len(self.connection_registry),
                "tracked_users": len(self.user_to_connections),
                "message_handlers": list(self.message_handlers.keys())
            }
        }
        
        return {**base_stats, **integration_stats}
    
    async def validate_connection_health(self) -> Dict[str, Any]:
        """Validate health of all tracked connections."""
        health_report = {
            "total_connections": len(self.connection_registry),
            "healthy_connections": 0,
            "zombie_connections": 0,
            "problematic_connections": []
        }
        
        zombie_connections = self.lifecycle_manager.get_zombie_connections()
        
        for conn_id, conn_info in self.connection_registry.items():
            if conn_id in zombie_connections:
                health_report["zombie_connections"] += 1
                health_report["problematic_connections"].append({
                    "connection_id": conn_id,
                    "user_id": conn_info.user_id,
                    "issue": "zombie_connection"
                })
            else:
                health_report["healthy_connections"] += 1
                
        return health_report
    
    async def schedule_periodic_cleanup(self, interval: float = 300.0) -> None:
        """Schedule periodic cleanup of zombie connections."""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(interval)
                    cleanup_result = await self.cleanup_zombie_connections()
                    if cleanup_result["total_cleaned"] > 0:
                        logger.info(f"Periodic cleanup removed {cleanup_result['total_cleaned']} zombie connections")
                except asyncio.CancelledError:
                    logger.info("Periodic cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
        
        asyncio.create_task(cleanup_task())
        logger.info(f"Scheduled periodic cleanup every {interval} seconds")


# Global integrator instance
_integrator: Optional[WebSocketLifecycleIntegrator] = None

def get_lifecycle_integrator() -> WebSocketLifecycleIntegrator:
    """Get or create lifecycle integrator instance."""
    global _integrator
    if _integrator is None:
        _integrator = WebSocketLifecycleIntegrator()
    return _integrator


async def integrate_with_existing_manager(ws_manager) -> None:
    """Integrate enhanced lifecycle with existing WebSocket manager."""
    integrator = get_lifecycle_integrator()
    
    # Replace connection methods with integrated versions
    original_connect = ws_manager.connect_user
    original_disconnect = ws_manager.disconnect_user
    original_handle_message = getattr(ws_manager, 'handle_message', None)
    
    async def integrated_connect(user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Integrated connect with enhanced lifecycle."""
        return await integrator.integrate_connection(user_id, websocket)
    
    async def integrated_disconnect(user_id: str, websocket: WebSocket, 
                                  code: int = 1000, reason: str = "Normal closure") -> None:
        """Integrated disconnect with proper cleanup."""
        await integrator.integrate_disconnection(user_id, websocket, code, reason)
    
    async def integrated_handle_message(user_id: str, websocket: WebSocket, 
                                      message: Dict[str, Any]) -> bool:
        """Integrated message handling with lifecycle support."""
        # First try lifecycle-specific handling
        if await integrator.handle_websocket_message(user_id, websocket, message):
            return True
            
        # Fall back to original handler if available
        if original_handle_message:
            return await original_handle_message(user_id, websocket, message)
        return False
    
    # Replace methods
    ws_manager.connect_user = integrated_connect
    ws_manager.disconnect_user = integrated_disconnect
    if original_handle_message:
        ws_manager.handle_message = integrated_handle_message
    
    # Add lifecycle management methods
    ws_manager.cleanup_zombie_connections = integrator.cleanup_zombie_connections
    ws_manager.perform_graceful_shutdown = integrator.perform_graceful_shutdown
    ws_manager.get_connection_health_status = integrator.get_connection_health_status
    ws_manager.get_pool_status = integrator.get_pool_status
    ws_manager.validate_connection_health = integrator.validate_connection_health
    
    # Start periodic cleanup
    await integrator.schedule_periodic_cleanup()
    
    logger.info("Successfully integrated enhanced lifecycle management with existing WebSocket manager")