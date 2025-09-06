"""
Integration Tests for Presence Detection System

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User Experience & System Reliability
- Value Impact: Accurate presence detection critical for real-time features
- Strategic Impact: Ensures chat responsiveness and connection state accuracy

Tests the complete presence detection flow including:
- WebSocket connection lifecycle
- Heartbeat mechanism
- Presence state transitions
- Multi-user scenarios
- Network interruption handling
- Recovery mechanisms
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import pytest
import websockets
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core import (
    WebSocketManager,
    get_websocket_manager,
    WebSocketHeartbeat
)
from netra_backend.app.websocket_core import (
    UnifiedWebSocketManager,
    HeartbeatConfig,
    get_heartbeat_manager
)
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockWebSocket:
    """Mock WebSocket for integration testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client_state = "CONNECTED"
        self.messages_sent: List[Dict] = []
        self.ping_count = 0
        self.pong_received = True
        self.is_connected = True
        self.last_ping_time = None
        
    async def ping(self, data: bytes = b''):
        """Simulate ping."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
        self.ping_count += 1
        self.last_ping_time = time.time()
        # Simulate network delay
        await asyncio.sleep(0.01)
        
    async def pong(self, data: bytes = b''):
        """Simulate pong response."""
        self.pong_received = True
        
    async def send_text(self, data: str):
        """Simulate sending text."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
        self.messages_sent.append({"type": "text", "data": data})
        
    async def send_json(self, data: Dict):
        """Simulate sending JSON."""
        if not self.is_connected:
            raise ConnectionError("WebSocket disconnected")
        self.messages_sent.append({"type": "json", "data": data})
        
    async def receive_json(self) -> Dict:
        """Simulate receiving JSON."""
        if not self.is_connected:
            raise WebSocketDisconnect(code=1000)
        # Simulate heartbeat response
        return {"type": "pong", "timestamp": time.time()}
    
    def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False
        self.client_state = "DISCONNECTED"


@pytest.fixture
async def heartbeat_manager():
    """Create heartbeat manager for testing."""
    config = HeartbeatConfig(
        heartbeat_interval_seconds=1,
        heartbeat_timeout_seconds=3,
        max_missed_heartbeats=2,
        cleanup_interval_seconds=5
    )
    manager = UnifiedWebSocketManager(config)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def websocket_manager():
    """Create WebSocket manager for testing."""
    manager = get_websocket_manager()
    yield manager


class TestPresenceDetectionIntegration:
    """Integration tests for presence detection."""
    
    @pytest.mark.asyncio
    async def test_user_connection_lifecycle(self, heartbeat_manager, websocket_manager):
        """Test complete user connection lifecycle with presence."""
        user_id = "user_123"
        ws = MockWebSocket(user_id)
        
        # Connect user
        connection_id = await websocket_manager.connect_user(user_id, ws)
        await heartbeat_manager.register_connection(connection_id)
        
        # Verify initial presence
        assert await heartbeat_manager.check_connection_health(connection_id)
        status = heartbeat_manager.get_connection_status(connection_id)
        assert status['is_alive'] is True
        
        # Simulate activity
        await heartbeat_manager.record_activity(connection_id)
        await asyncio.sleep(0.1)
        
        # Send heartbeat ping
        result = await heartbeat_manager.send_ping(connection_id, ws)
        assert result is True
        assert ws.ping_count == 1
        
        # Simulate pong response
        await heartbeat_manager.record_pong(connection_id)
        
        # Verify healthy state
        assert await heartbeat_manager.check_connection_health(connection_id)
        
        # Disconnect user
        ws.disconnect()
        await websocket_manager.disconnect_user(user_id, ws, 1000, "Normal closure")
        await heartbeat_manager.unregister_connection(connection_id)
        
        # Verify disconnected
        assert not await heartbeat_manager.check_connection_health(connection_id)
    
    @pytest.mark.asyncio
    async def test_multiple_users_presence(self, heartbeat_manager, websocket_manager):
        """Test presence detection with multiple concurrent users."""
        users = []
        connections = {}
        
        # Connect multiple users
        for i in range(5):
            user_id = f"user_{i}"
            ws = MockWebSocket(user_id)
            users.append((user_id, ws))
            
            conn_id = await websocket_manager.connect_user(user_id, ws)
            await heartbeat_manager.register_connection(conn_id)
            connections[user_id] = conn_id
        
        # Verify all users present
        for user_id, conn_id in connections.items():
            assert await heartbeat_manager.check_connection_health(conn_id)
        
        # Simulate activity for some users
        for i in [0, 2, 4]:
            user_id = f"user_{i}"
            await heartbeat_manager.record_activity(connections[user_id])
        
        # Send pings to all
        for (user_id, ws), conn_id in zip(users, connections.values()):
            await heartbeat_manager.send_ping(conn_id, ws)
        
        # Simulate pongs from active users only
        for i in [0, 2, 4]:
            user_id = f"user_{i}"
            await heartbeat_manager.record_pong(connections[user_id])
        
        await asyncio.sleep(0.1)
        
        # Check stats
        stats = heartbeat_manager.get_stats()
        assert stats['pings_sent'] == 5
        assert stats['pongs_received'] == 3
        
        # Disconnect all users
        for user_id, ws in users:
            ws.disconnect()
            await websocket_manager.disconnect_user(user_id, ws, 1000, "Normal")
            await heartbeat_manager.unregister_connection(connections[user_id])
    
    @pytest.mark.asyncio
    async def test_presence_timeout_detection(self, heartbeat_manager):
        """Test detection of timed-out connections."""
        user_id = "timeout_user"
        ws = MockWebSocket(user_id)
        connection_id = f"conn_{user_id}"
        
        # Register connection
        await heartbeat_manager.register_connection(connection_id)
        
        # Set last activity to past timeout
        heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
        heartbeat.last_activity = time.time() - heartbeat_manager.config.heartbeat_timeout_seconds - 1
        
        # Check health should mark as dead
        is_healthy = await heartbeat_manager.check_connection_health(connection_id)
        assert not is_healthy
        assert not heartbeat.is_alive
        
        # Verify stats
        assert heartbeat_manager.stats['timeouts_detected'] > 0
    
    @pytest.mark.asyncio
    async def test_missed_heartbeats_detection(self, heartbeat_manager):
        """Test detection of missed heartbeats."""
        user_id = "missed_hb_user"
        ws = MockWebSocket(user_id)
        connection_id = f"conn_{user_id}"
        
        await heartbeat_manager.register_connection(connection_id)
        
        # Send multiple pings without pongs
        for _ in range(heartbeat_manager.config.max_missed_heartbeats + 1):
            await heartbeat_manager.send_ping(connection_id, ws)
            # Simulate timeout by marking ping as old
            if connection_id in heartbeat_manager.active_pings:
                heartbeat_manager.active_pings[connection_id] = time.time() - 100
            
            # Process heartbeat to detect missed pong
            await heartbeat_manager._process_single_heartbeat(
                connection_id,
                heartbeat_manager.connection_heartbeats[connection_id],
                time.time()
            )
        
        # Should be marked as dead after max missed heartbeats
        assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive
    
    @pytest.mark.asyncio
    async def test_connection_resurrection(self, heartbeat_manager):
        """Test resurrection of dead connections."""
        connection_id = "resurrect_conn"
        
        await heartbeat_manager.register_connection(connection_id)
        
        # Mark as dead
        await heartbeat_manager._mark_connection_dead(connection_id)
        assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive
        
        # Record activity to resurrect
        await heartbeat_manager.record_activity(connection_id)
        
        # Should be alive again
        assert heartbeat_manager.connection_heartbeats[connection_id].is_alive
        assert heartbeat_manager.stats['resurrection_count'] > 0
    
    @pytest.mark.asyncio
    async def test_network_interruption_recovery(self, heartbeat_manager):
        """Test recovery from network interruptions."""
        user_id = "network_user"
        ws = MockWebSocket(user_id)
        connection_id = f"conn_{user_id}"
        
        await heartbeat_manager.register_connection(connection_id)
        
        # Simulate normal operation
        await heartbeat_manager.send_ping(connection_id, ws)
        await heartbeat_manager.record_pong(connection_id)
        assert await heartbeat_manager.check_connection_health(connection_id)
        
        # Simulate network interruption
        ws.is_connected = False
        
        # Ping should fail
        result = await heartbeat_manager.send_ping(connection_id, ws)
        assert not result
        
        # Simulate network recovery
        ws.is_connected = True
        
        # Activity should resurrect if marked dead
        await heartbeat_manager.record_activity(connection_id)
        assert await heartbeat_manager.check_connection_health(connection_id)
    
    @pytest.mark.asyncio
    async def test_concurrent_heartbeat_operations(self, heartbeat_manager):
        """Test thread safety with concurrent heartbeat operations."""
        connections = [f"conn_{i}" for i in range(10)]
        
        async def register_and_ping(conn_id):
            ws = MockWebSocket(conn_id)
            await heartbeat_manager.register_connection(conn_id)
            for _ in range(3):
                await heartbeat_manager.send_ping(conn_id, ws)
                await asyncio.sleep(0.01)
                await heartbeat_manager.record_pong(conn_id)
        
        # Run concurrent operations
        await asyncio.gather(*[register_and_ping(conn_id) for conn_id in connections])
        
        # Verify all connections healthy
        for conn_id in connections:
            assert await heartbeat_manager.check_connection_health(conn_id)
        
        # Cleanup
        for conn_id in connections:
            await heartbeat_manager.unregister_connection(conn_id)
    
    @pytest.mark.asyncio
    async def test_cleanup_process(self, heartbeat_manager):
        """Test automatic cleanup of stale connections."""
        # Create mix of healthy and dead connections
        healthy_conns = []
        dead_conns = []
        
        for i in range(3):
            conn_id = f"healthy_{i}"
            await heartbeat_manager.register_connection(conn_id)
            await heartbeat_manager.record_activity(conn_id)
            healthy_conns.append(conn_id)
        
        for i in range(3):
            conn_id = f"dead_{i}"
            await heartbeat_manager.register_connection(conn_id)
            await heartbeat_manager._mark_connection_dead(conn_id)
            # Set death time to past cleanup threshold
            heartbeat_manager.connection_heartbeats[conn_id].last_activity = time.time() - 200
            dead_conns.append(conn_id)
        
        # Run cleanup
        await heartbeat_manager._cleanup_stale_data()
        
        # Healthy connections should remain
        for conn_id in healthy_conns:
            assert conn_id in heartbeat_manager.connection_heartbeats
        
        # Dead connections should be removed
        for conn_id in dead_conns:
            assert conn_id not in heartbeat_manager.connection_heartbeats
    
    @pytest.mark.asyncio
    async def test_heartbeat_with_websocket_manager_integration(self, heartbeat_manager, websocket_manager):
        """Test heartbeat integration with WebSocket manager."""
        user_id = "integration_user"
        ws = MockWebSocket(user_id)
        
        # Connect through WebSocket manager
        connection_id = await websocket_manager.connect_user(user_id, ws)
        
        # Register with heartbeat manager
        await heartbeat_manager.register_connection(connection_id)
        
        # Create WebSocketHeartbeat instance
        ws_heartbeat = WebSocketHeartbeat(
            interval=heartbeat_manager.config.heartbeat_interval_seconds,
            timeout=heartbeat_manager.config.heartbeat_timeout_seconds
        )
        
        # Start heartbeat monitoring
        heartbeat_task = asyncio.create_task(ws_heartbeat.start(ws))
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop heartbeat
        await ws_heartbeat.stop()
        heartbeat_task.cancel()
        
        # Cleanup
        await websocket_manager.disconnect_user(user_id, ws, 1000, "Test complete")
        await heartbeat_manager.unregister_connection(connection_id)
    
    @pytest.mark.asyncio
    async def test_presence_state_transitions(self, heartbeat_manager):
        """Test all possible presence state transitions."""
        connection_id = "state_test"
        ws = MockWebSocket("user")
        
        # State: New -> Registered
        await heartbeat_manager.register_connection(connection_id)
        assert heartbeat_manager.connection_heartbeats[connection_id].is_alive
        
        # State: Registered -> Active (via ping)
        await heartbeat_manager.send_ping(connection_id, ws)
        assert connection_id in heartbeat_manager.active_pings
        
        # State: Active -> Healthy (via pong)
        await heartbeat_manager.record_pong(connection_id)
        assert connection_id not in heartbeat_manager.active_pings
        
        # State: Healthy -> Warning (missed heartbeat)
        heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
        heartbeat.missed_heartbeats = 1
        assert await heartbeat_manager.check_connection_health(connection_id)  # Still healthy
        
        # State: Warning -> Dead (timeout)
        heartbeat.last_activity = time.time() - 100
        assert not await heartbeat_manager.check_connection_health(connection_id)
        assert not heartbeat.is_alive
        
        # State: Dead -> Resurrected (activity)
        await heartbeat_manager.record_activity(connection_id)
        assert heartbeat.is_alive
        
        # State: Resurrected -> Unregistered
        await heartbeat_manager.unregister_connection(connection_id)
        assert connection_id not in heartbeat_manager.connection_heartbeats


class TestPresenceDetectionErrorScenarios:
    """Test error scenarios in presence detection."""
    
    @pytest.mark.asyncio
    async def test_websocket_error_during_ping(self, heartbeat_manager):
        """Test handling of WebSocket errors during ping."""
        connection_id = "error_conn"
        
        # Create mock that raises errors
        ws = MagicNone  # TODO: Use real service instance
        ws.ping = AsyncMock(side_effect=ConnectionError("Connection lost"))
        
        await heartbeat_manager.register_connection(connection_id)
        
        # Ping should fail gracefully
        result = await heartbeat_manager.send_ping(connection_id, ws)
        assert not result
        assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive
    
    @pytest.mark.asyncio
    async def test_rapid_reconnection(self, heartbeat_manager):
        """Test handling of rapid reconnection attempts."""
        connection_id = "rapid_conn"
        
        for _ in range(10):
            # Register
            await heartbeat_manager.register_connection(connection_id)
            
            # Immediately unregister
            await heartbeat_manager.unregister_connection(connection_id)
        
        # Should handle gracefully
        assert connection_id not in heartbeat_manager.connection_heartbeats
    
    @pytest.mark.asyncio
    async def test_clock_skew_handling(self, heartbeat_manager):
        """Test handling of system clock skew."""
        connection_id = "skew_conn"
        
        await heartbeat_manager.register_connection(connection_id)
        
        # Simulate clock going backwards
        heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
        heartbeat.last_activity = time.time() + 3600  # 1 hour in future
        
        # Cleanup should detect and handle
        await heartbeat_manager._cleanup_stale_data()
        
        # Activity time should be corrected
        if connection_id in heartbeat_manager.connection_heartbeats:
            assert heartbeat.last_activity <= time.time()
    
    @pytest.mark.asyncio
    async def test_memory_pressure_scenario(self, heartbeat_manager):
        """Test behavior under memory pressure with many connections."""
        # Register many connections
        connections = []
        for i in range(1000):
            conn_id = f"mem_test_{i}"
            await heartbeat_manager.register_connection(conn_id)
            connections.append(conn_id)
        
        # Mark half as dead
        for i in range(0, 500):
            await heartbeat_manager._mark_connection_dead(connections[i])
            # Make them old enough for cleanup
            heartbeat_manager.connection_heartbeats[connections[i]].last_activity = time.time() - 300
        
        # Run cleanup
        await heartbeat_manager._cleanup_stale_data()
        
        # Dead connections should be removed
        assert len(heartbeat_manager.connection_heartbeats) == 500
        
        # Clean up remaining
        for conn_id in connections[500:]:
            if conn_id in heartbeat_manager.connection_heartbeats:
                await heartbeat_manager.unregister_connection(conn_id)