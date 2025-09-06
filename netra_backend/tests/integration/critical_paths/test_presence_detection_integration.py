from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Integration Tests for Presence Detection System

# REMOVED_SYNTAX_ERROR: Business Value Justification:
    # REMOVED_SYNTAX_ERROR: - Segment: All (Free, Early, Mid, Enterprise)
    # REMOVED_SYNTAX_ERROR: - Business Goal: User Experience & System Reliability
    # REMOVED_SYNTAX_ERROR: - Value Impact: Accurate presence detection critical for real-time features
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Ensures chat responsiveness and connection state accuracy

    # REMOVED_SYNTAX_ERROR: Tests the complete presence detection flow including:
        # REMOVED_SYNTAX_ERROR: - WebSocket connection lifecycle
        # REMOVED_SYNTAX_ERROR: - Heartbeat mechanism
        # REMOVED_SYNTAX_ERROR: - Presence state transitions
        # REMOVED_SYNTAX_ERROR: - Multi-user scenarios
        # REMOVED_SYNTAX_ERROR: - Network interruption handling
        # REMOVED_SYNTAX_ERROR: - Recovery mechanisms
        # REMOVED_SYNTAX_ERROR: """"

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Optional, Any
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import websockets
        # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
        # REMOVED_SYNTAX_ERROR: from starlette.websockets import WebSocketDisconnect
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import ( )
        # REMOVED_SYNTAX_ERROR: WebSocketManager,
        # REMOVED_SYNTAX_ERROR: get_websocket_manager,
        # REMOVED_SYNTAX_ERROR: WebSocketHeartbeat
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import ( )
        # REMOVED_SYNTAX_ERROR: UnifiedWebSocketManager,
        # REMOVED_SYNTAX_ERROR: HeartbeatConfig,
        # REMOVED_SYNTAX_ERROR: get_heartbeat_manager
        
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger

        # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class MockWebSocket:
    # REMOVED_SYNTAX_ERROR: """Mock WebSocket for integration testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self, user_id: str):
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.client_state = "CONNECTED"
    # REMOVED_SYNTAX_ERROR: self.messages_sent: List[Dict] = []
    # REMOVED_SYNTAX_ERROR: self.ping_count = 0
    # REMOVED_SYNTAX_ERROR: self.pong_received = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self.last_ping_time = None

# REMOVED_SYNTAX_ERROR: async def ping(self, data: bytes = b''):
    # REMOVED_SYNTAX_ERROR: """Simulate ping."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")
        # REMOVED_SYNTAX_ERROR: self.ping_count += 1
        # REMOVED_SYNTAX_ERROR: self.last_ping_time = time.time()
        # Simulate network delay
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

# REMOVED_SYNTAX_ERROR: async def pong(self, data: bytes = b''):
    # REMOVED_SYNTAX_ERROR: """Simulate pong response."""
    # REMOVED_SYNTAX_ERROR: self.pong_received = True

# REMOVED_SYNTAX_ERROR: async def send_text(self, data: str):
    # REMOVED_SYNTAX_ERROR: """Simulate sending text."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append({"type": "text", "data": data})

# REMOVED_SYNTAX_ERROR: async def send_json(self, data: Dict):
    # REMOVED_SYNTAX_ERROR: """Simulate sending JSON."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append({"type": "json", "data": data})

# REMOVED_SYNTAX_ERROR: async def receive_json(self) -> Dict:
    # REMOVED_SYNTAX_ERROR: """Simulate receiving JSON."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise WebSocketDisconnect(code=1000)
        # Simulate heartbeat response
        # REMOVED_SYNTAX_ERROR: return {"type": "pong", "timestamp": time.time()}

# REMOVED_SYNTAX_ERROR: def disconnect(self):
    # REMOVED_SYNTAX_ERROR: """Simulate disconnection."""
    # REMOVED_SYNTAX_ERROR: self.is_connected = False
    # REMOVED_SYNTAX_ERROR: self.client_state = "DISCONNECTED"


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def heartbeat_manager():
    # REMOVED_SYNTAX_ERROR: """Create heartbeat manager for testing."""
    # REMOVED_SYNTAX_ERROR: config = HeartbeatConfig( )
    # REMOVED_SYNTAX_ERROR: heartbeat_interval_seconds=1,
    # REMOVED_SYNTAX_ERROR: heartbeat_timeout_seconds=3,
    # REMOVED_SYNTAX_ERROR: max_missed_heartbeats=2,
    # REMOVED_SYNTAX_ERROR: cleanup_interval_seconds=5
    
    # REMOVED_SYNTAX_ERROR: manager = UnifiedWebSocketManager(config)
    # REMOVED_SYNTAX_ERROR: await manager.start()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.stop()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for testing."""
    # REMOVED_SYNTAX_ERROR: manager = get_websocket_manager()
    # REMOVED_SYNTAX_ERROR: yield manager


# REMOVED_SYNTAX_ERROR: class TestPresenceDetectionIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for presence detection."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_connection_lifecycle(self, heartbeat_manager, websocket_manager):
        # REMOVED_SYNTAX_ERROR: """Test complete user connection lifecycle with presence."""
        # REMOVED_SYNTAX_ERROR: user_id = "user_123"
        # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)

        # Connect user
        # REMOVED_SYNTAX_ERROR: connection_id = await websocket_manager.connect_user(user_id, ws)
        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

        # Verify initial presence
        # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(connection_id)
        # REMOVED_SYNTAX_ERROR: status = heartbeat_manager.get_connection_status(connection_id)
        # REMOVED_SYNTAX_ERROR: assert status['is_alive'] is True

        # Simulate activity
        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(connection_id)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # Send heartbeat ping
        # REMOVED_SYNTAX_ERROR: result = await heartbeat_manager.send_ping(connection_id, ws)
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: assert ws.ping_count == 1

        # Simulate pong response
        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_pong(connection_id)

        # Verify healthy state
        # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(connection_id)

        # Disconnect user
        # REMOVED_SYNTAX_ERROR: ws.disconnect()
        # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user_id, ws, 1000, "Normal closure")
        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(connection_id)

        # Verify disconnected
        # REMOVED_SYNTAX_ERROR: assert not await heartbeat_manager.check_connection_health(connection_id)

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_multiple_users_presence(self, heartbeat_manager, websocket_manager):
            # REMOVED_SYNTAX_ERROR: """Test presence detection with multiple concurrent users."""
            # REMOVED_SYNTAX_ERROR: users = []
            # REMOVED_SYNTAX_ERROR: connections = {}

            # Connect multiple users
            # REMOVED_SYNTAX_ERROR: for i in range(5):
                # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)
                # REMOVED_SYNTAX_ERROR: users.append((user_id, ws))

                # REMOVED_SYNTAX_ERROR: conn_id = await websocket_manager.connect_user(user_id, ws)
                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(conn_id)
                # REMOVED_SYNTAX_ERROR: connections[user_id] = conn_id

                # Verify all users present
                # REMOVED_SYNTAX_ERROR: for user_id, conn_id in connections.items():
                    # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(conn_id)

                    # Simulate activity for some users
                    # REMOVED_SYNTAX_ERROR: for i in [0, 2, 4]:
                        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(connections[user_id])

                        # Send pings to all
                        # REMOVED_SYNTAX_ERROR: for (user_id, ws), conn_id in zip(users, connections.values()):
                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.send_ping(conn_id, ws)

                            # Simulate pongs from active users only
                            # REMOVED_SYNTAX_ERROR: for i in [0, 2, 4]:
                                # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_pong(connections[user_id])

                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                # Check stats
                                # REMOVED_SYNTAX_ERROR: stats = heartbeat_manager.get_stats()
                                # REMOVED_SYNTAX_ERROR: assert stats['pings_sent'] == 5
                                # REMOVED_SYNTAX_ERROR: assert stats['pongs_received'] == 3

                                # Disconnect all users
                                # REMOVED_SYNTAX_ERROR: for user_id, ws in users:
                                    # REMOVED_SYNTAX_ERROR: ws.disconnect()
                                    # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user_id, ws, 1000, "Normal")
                                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(connections[user_id])

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_presence_timeout_detection(self, heartbeat_manager):
                                        # REMOVED_SYNTAX_ERROR: """Test detection of timed-out connections."""
                                        # REMOVED_SYNTAX_ERROR: user_id = "timeout_user"
                                        # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)
                                        # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"

                                        # Register connection
                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                                        # Set last activity to past timeout
                                        # REMOVED_SYNTAX_ERROR: heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
                                        # REMOVED_SYNTAX_ERROR: heartbeat.last_activity = time.time() - heartbeat_manager.config.heartbeat_timeout_seconds - 1

                                        # Check health should mark as dead
                                        # REMOVED_SYNTAX_ERROR: is_healthy = await heartbeat_manager.check_connection_health(connection_id)
                                        # REMOVED_SYNTAX_ERROR: assert not is_healthy
                                        # REMOVED_SYNTAX_ERROR: assert not heartbeat.is_alive

                                        # Verify stats
                                        # REMOVED_SYNTAX_ERROR: assert heartbeat_manager.stats['timeouts_detected'] > 0

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_missed_heartbeats_detection(self, heartbeat_manager):
                                            # REMOVED_SYNTAX_ERROR: """Test detection of missed heartbeats."""
                                            # REMOVED_SYNTAX_ERROR: user_id = "missed_hb_user"
                                            # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)
                                            # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"

                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                                            # Send multiple pings without pongs
                                            # REMOVED_SYNTAX_ERROR: for _ in range(heartbeat_manager.config.max_missed_heartbeats + 1):
                                                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.send_ping(connection_id, ws)
                                                # Simulate timeout by marking ping as old
                                                # REMOVED_SYNTAX_ERROR: if connection_id in heartbeat_manager.active_pings:
                                                    # REMOVED_SYNTAX_ERROR: heartbeat_manager.active_pings[connection_id] = time.time() - 100

                                                    # Process heartbeat to detect missed pong
                                                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager._process_single_heartbeat( )
                                                    # REMOVED_SYNTAX_ERROR: connection_id,
                                                    # REMOVED_SYNTAX_ERROR: heartbeat_manager.connection_heartbeats[connection_id],
                                                    # REMOVED_SYNTAX_ERROR: time.time()
                                                    

                                                    # Should be marked as dead after max missed heartbeats
                                                    # REMOVED_SYNTAX_ERROR: assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_connection_resurrection(self, heartbeat_manager):
                                                        # REMOVED_SYNTAX_ERROR: """Test resurrection of dead connections."""
                                                        # REMOVED_SYNTAX_ERROR: connection_id = "resurrect_conn"

                                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                                                        # Mark as dead
                                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager._mark_connection_dead(connection_id)
                                                        # REMOVED_SYNTAX_ERROR: assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive

                                                        # Record activity to resurrect
                                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(connection_id)

                                                        # Should be alive again
                                                        # REMOVED_SYNTAX_ERROR: assert heartbeat_manager.connection_heartbeats[connection_id].is_alive
                                                        # REMOVED_SYNTAX_ERROR: assert heartbeat_manager.stats['resurrection_count'] > 0

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_network_interruption_recovery(self, heartbeat_manager):
                                                            # REMOVED_SYNTAX_ERROR: """Test recovery from network interruptions."""
                                                            # REMOVED_SYNTAX_ERROR: user_id = "network_user"
                                                            # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)
                                                            # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"

                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                                                            # Simulate normal operation
                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.send_ping(connection_id, ws)
                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_pong(connection_id)
                                                            # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(connection_id)

                                                            # Simulate network interruption
                                                            # REMOVED_SYNTAX_ERROR: ws.is_connected = False

                                                            # Ping should fail
                                                            # REMOVED_SYNTAX_ERROR: result = await heartbeat_manager.send_ping(connection_id, ws)
                                                            # REMOVED_SYNTAX_ERROR: assert not result

                                                            # Simulate network recovery
                                                            # REMOVED_SYNTAX_ERROR: ws.is_connected = True

                                                            # Activity should resurrect if marked dead
                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(connection_id)
                                                            # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(connection_id)

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_concurrent_heartbeat_operations(self, heartbeat_manager):
                                                                # REMOVED_SYNTAX_ERROR: """Test thread safety with concurrent heartbeat operations."""
                                                                # REMOVED_SYNTAX_ERROR: connections = ["formatted_string"
                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(conn_id)
                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(conn_id)
                        # REMOVED_SYNTAX_ERROR: healthy_conns.append(conn_id)

                        # REMOVED_SYNTAX_ERROR: for i in range(3):
                            # REMOVED_SYNTAX_ERROR: conn_id = "formatted_string"
                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(conn_id)
                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager._mark_connection_dead(conn_id)
                            # Set death time to past cleanup threshold
                            # REMOVED_SYNTAX_ERROR: heartbeat_manager.connection_heartbeats[conn_id].last_activity = time.time() - 200
                            # REMOVED_SYNTAX_ERROR: dead_conns.append(conn_id)

                            # Run cleanup
                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager._cleanup_stale_data()

                            # Healthy connections should remain
                            # REMOVED_SYNTAX_ERROR: for conn_id in healthy_conns:
                                # REMOVED_SYNTAX_ERROR: assert conn_id in heartbeat_manager.connection_heartbeats

                                # Dead connections should be removed
                                # REMOVED_SYNTAX_ERROR: for conn_id in dead_conns:
                                    # REMOVED_SYNTAX_ERROR: assert conn_id not in heartbeat_manager.connection_heartbeats

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_heartbeat_with_websocket_manager_integration(self, heartbeat_manager, websocket_manager):
                                        # REMOVED_SYNTAX_ERROR: """Test heartbeat integration with WebSocket manager."""
                                        # REMOVED_SYNTAX_ERROR: user_id = "integration_user"
                                        # REMOVED_SYNTAX_ERROR: ws = MockWebSocket(user_id)

                                        # Connect through WebSocket manager
                                        # REMOVED_SYNTAX_ERROR: connection_id = await websocket_manager.connect_user(user_id, ws)

                                        # Register with heartbeat manager
                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                                        # Create WebSocketHeartbeat instance
                                        # REMOVED_SYNTAX_ERROR: ws_heartbeat = WebSocketHeartbeat( )
                                        # REMOVED_SYNTAX_ERROR: interval=heartbeat_manager.config.heartbeat_interval_seconds,
                                        # REMOVED_SYNTAX_ERROR: timeout=heartbeat_manager.config.heartbeat_timeout_seconds
                                        

                                        # Start heartbeat monitoring
                                        # REMOVED_SYNTAX_ERROR: heartbeat_task = asyncio.create_task(ws_heartbeat.start(ws))

                                        # Let it run briefly
                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                        # Stop heartbeat
                                        # REMOVED_SYNTAX_ERROR: await ws_heartbeat.stop()
                                        # REMOVED_SYNTAX_ERROR: heartbeat_task.cancel()

                                        # Cleanup
                                        # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user_id, ws, 1000, "Test complete")
                                        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(connection_id)

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_presence_state_transitions(self, heartbeat_manager):
                                            # REMOVED_SYNTAX_ERROR: """Test all possible presence state transitions."""
                                            # REMOVED_SYNTAX_ERROR: connection_id = "state_test"
                                            # REMOVED_SYNTAX_ERROR: ws = MockWebSocket("user")

                                            # State: New -> Registered
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)
                                            # REMOVED_SYNTAX_ERROR: assert heartbeat_manager.connection_heartbeats[connection_id].is_alive

                                            # State: Registered -> Active (via ping)
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.send_ping(connection_id, ws)
                                            # REMOVED_SYNTAX_ERROR: assert connection_id in heartbeat_manager.active_pings

                                            # State: Active -> Healthy (via pong)
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_pong(connection_id)
                                            # REMOVED_SYNTAX_ERROR: assert connection_id not in heartbeat_manager.active_pings

                                            # State: Healthy -> Warning (missed heartbeat)
                                            # REMOVED_SYNTAX_ERROR: heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
                                            # REMOVED_SYNTAX_ERROR: heartbeat.missed_heartbeats = 1
                                            # REMOVED_SYNTAX_ERROR: assert await heartbeat_manager.check_connection_health(connection_id)  # Still healthy

                                            # State: Warning -> Dead (timeout)
                                            # REMOVED_SYNTAX_ERROR: heartbeat.last_activity = time.time() - 100
                                            # REMOVED_SYNTAX_ERROR: assert not await heartbeat_manager.check_connection_health(connection_id)
                                            # REMOVED_SYNTAX_ERROR: assert not heartbeat.is_alive

                                            # State: Dead -> Resurrected (activity)
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.record_activity(connection_id)
                                            # REMOVED_SYNTAX_ERROR: assert heartbeat.is_alive

                                            # State: Resurrected -> Unregistered
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(connection_id)
                                            # REMOVED_SYNTAX_ERROR: assert connection_id not in heartbeat_manager.connection_heartbeats


# REMOVED_SYNTAX_ERROR: class TestPresenceDetectionErrorScenarios:
    # REMOVED_SYNTAX_ERROR: """Test error scenarios in presence detection."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_error_during_ping(self, heartbeat_manager):
        # REMOVED_SYNTAX_ERROR: """Test handling of WebSocket errors during ping."""
        # REMOVED_SYNTAX_ERROR: connection_id = "error_conn"

        # Create mock that raises errors
        # REMOVED_SYNTAX_ERROR: ws = MagicMock()  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: ws.ping = AsyncMock(side_effect=ConnectionError("Connection lost"))

        # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

        # Ping should fail gracefully
        # REMOVED_SYNTAX_ERROR: result = await heartbeat_manager.send_ping(connection_id, ws)
        # REMOVED_SYNTAX_ERROR: assert not result
        # REMOVED_SYNTAX_ERROR: assert not heartbeat_manager.connection_heartbeats[connection_id].is_alive

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_rapid_reconnection(self, heartbeat_manager):
            # REMOVED_SYNTAX_ERROR: """Test handling of rapid reconnection attempts."""
            # REMOVED_SYNTAX_ERROR: connection_id = "rapid_conn"

            # REMOVED_SYNTAX_ERROR: for _ in range(10):
                # Register
                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                # Immediately unregister
                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(connection_id)

                # Should handle gracefully
                # REMOVED_SYNTAX_ERROR: assert connection_id not in heartbeat_manager.connection_heartbeats

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_clock_skew_handling(self, heartbeat_manager):
                    # REMOVED_SYNTAX_ERROR: """Test handling of system clock skew."""
                    # REMOVED_SYNTAX_ERROR: connection_id = "skew_conn"

                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(connection_id)

                    # Simulate clock going backwards
                    # REMOVED_SYNTAX_ERROR: heartbeat = heartbeat_manager.connection_heartbeats[connection_id]
                    # REMOVED_SYNTAX_ERROR: heartbeat.last_activity = time.time() + 3600  # 1 hour in future

                    # Cleanup should detect and handle
                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager._cleanup_stale_data()

                    # Activity time should be corrected
                    # REMOVED_SYNTAX_ERROR: if connection_id in heartbeat_manager.connection_heartbeats:
                        # REMOVED_SYNTAX_ERROR: assert heartbeat.last_activity <= time.time()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_memory_pressure_scenario(self, heartbeat_manager):
                            # REMOVED_SYNTAX_ERROR: """Test behavior under memory pressure with many connections."""
                            # Register many connections
                            # REMOVED_SYNTAX_ERROR: connections = []
                            # REMOVED_SYNTAX_ERROR: for i in range(1000):
                                # REMOVED_SYNTAX_ERROR: conn_id = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: await heartbeat_manager.register_connection(conn_id)
                                # REMOVED_SYNTAX_ERROR: connections.append(conn_id)

                                # Mark half as dead
                                # REMOVED_SYNTAX_ERROR: for i in range(0, 500):
                                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager._mark_connection_dead(connections[i])
                                    # Make them old enough for cleanup
                                    # REMOVED_SYNTAX_ERROR: heartbeat_manager.connection_heartbeats[connections[i]].last_activity = time.time() - 300

                                    # Run cleanup
                                    # REMOVED_SYNTAX_ERROR: await heartbeat_manager._cleanup_stale_data()

                                    # Dead connections should be removed
                                    # REMOVED_SYNTAX_ERROR: assert len(heartbeat_manager.connection_heartbeats) == 500

                                    # Clean up remaining
                                    # REMOVED_SYNTAX_ERROR: for conn_id in connections[500:]:
                                        # REMOVED_SYNTAX_ERROR: if conn_id in heartbeat_manager.connection_heartbeats:
                                            # REMOVED_SYNTAX_ERROR: await heartbeat_manager.unregister_connection(conn_id)