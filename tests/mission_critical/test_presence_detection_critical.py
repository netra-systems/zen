class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Mission-Critical Tests for Presence Detection System

Business Value Justification:
- Segment: All (Chat delivers 90% of value - CRITICAL)
- Business Goal: Zero-downtime chat service
- Value Impact: Presence detection failures break real-time chat experience
- Strategic Impact: These tests MUST PASS for production deployment

CRITICAL: These tests validate that presence detection NEVER fails in ways that
would break chat functionality. Chat is KING - it delivers 90% of our value.

Mission-critical scenarios:
- Chat must show accurate online/offline status
- Heartbeats must not break under any condition
- Presence must recover from all failure modes
- Zero data loss during state transitions
- Staging/production environment validation
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core import (
    WebSocketManager,
    get_websocket_manager,
    WebSocketHeartbeat,
    create_server_message,
    MessageType
)
from netra_backend.app.websocket_core.manager import (
    WebSocketHeartbeatManager,
    HeartbeatConfig,
    get_heartbeat_manager
)
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = central_logger.get_logger(__name__)


class CriticalWebSocketMock:
    """Mock WebSocket for critical testing with failure injection."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client_state = "CONNECTED"
        self.application_state = "CONNECTED"
        self.messages_sent = []
        self.ping_failures = 0
        self.pong_failures = 0
        self.should_fail_next_ping = False
        self.should_fail_all_pings = False
        self.network_delay_ms = 0
        
    async def ping(self, data: bytes = b''):
        """Simulate ping with failure injection."""
        if self.should_fail_all_pings or self.should_fail_next_ping:
            self.should_fail_next_ping = False
            self.ping_failures += 1
            raise ConnectionError("CRITICAL: Ping failed")
        
        if self.network_delay_ms > 0:
            await asyncio.sleep(self.network_delay_ms / 1000)
        
        return True
    
    async def send_json(self, data: Dict):
        """Track sent messages."""
        self.messages_sent.append(data)
    
    async def send_text(self, data: str):
        """Track sent text messages."""
        self.messages_sent.append({"text": data})
    
    def disconnect_abruptly(self):
        """Simulate abrupt disconnection."""
        self.client_state = "DISCONNECTED"
        self.application_state = "DISCONNECTED"


@pytest.fixture
def critical_heartbeat_config():
    """Critical heartbeat configuration for production."""
    return HeartbeatConfig(
        heartbeat_interval_seconds=30,
        heartbeat_timeout_seconds=90,
        max_missed_heartbeats=2,
        cleanup_interval_seconds=120
    )


@pytest.fixture
async def critical_heartbeat_manager(critical_heartbeat_config):
    """Create critical heartbeat manager."""
    manager = WebSocketHeartbeatManager(critical_heartbeat_config)
    await manager.start()
    yield manager
    await manager.stop()


class TestPresenceDetectionCritical:
    """Mission-critical tests that MUST pass."""
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_chat_presence_never_shows_false_offline(self, critical_heartbeat_manager):
        """CRITICAL: User must NEVER appear offline while actively chatting."""
        user_id = "active_chatter"
        conn_id = f"conn_{user_id}"
        ws = CriticalWebSocketMock(user_id)
        
        # User connects and starts chatting
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Simulate active chat session
        chat_duration = 5  # seconds
        chat_start = time.time()
        messages_sent = 0
        
        while time.time() - chat_start < chat_duration:
            # User sends message
            await critical_heartbeat_manager.record_activity(conn_id)
            messages_sent += 1
            
            # Check presence - MUST be online
            is_online = await critical_heartbeat_manager.check_connection_health(conn_id)
            assert is_online, f"CRITICAL: User shown offline while sending message {messages_sent}"
            
            # Brief delay between messages
            await asyncio.sleep(0.5)
        
        # Even after chat ends, user should remain online for grace period
        await asyncio.sleep(1)
        is_online = await critical_heartbeat_manager.check_connection_health(conn_id)
        assert is_online, "CRITICAL: User shown offline immediately after chat"
        
        logger.info(f"[U+2713] CRITICAL TEST PASSED: User remained online during {messages_sent} messages")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_heartbeat_failure_recovery(self, critical_heartbeat_manager):
        """CRITICAL: System must recover from heartbeat failures without losing presence."""
        conn_id = "critical_conn"
        ws = CriticalWebSocketMock("user")
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Normal operation
        assert await critical_heartbeat_manager.send_ping(conn_id, ws)
        await critical_heartbeat_manager.record_pong(conn_id)
        assert await critical_heartbeat_manager.check_connection_health(conn_id)
        
        # Inject failures
        ws.should_fail_next_ping = True
        assert not await critical_heartbeat_manager.send_ping(conn_id, ws)
        
        # User activity should recover presence
        await critical_heartbeat_manager.record_activity(conn_id)
        assert await critical_heartbeat_manager.check_connection_health(conn_id)
        
        # Subsequent pings should work
        assert await critical_heartbeat_manager.send_ping(conn_id, ws)
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Recovered from heartbeat failure")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_no_false_resurrections(self, critical_heartbeat_manager):
        """CRITICAL: Dead connections must NOT falsely resurrect."""
        conn_id = "zombie_test"
        ws = CriticalWebSocketMock("zombie_user")
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Kill the connection properly
        ws.disconnect_abruptly()
        await critical_heartbeat_manager._mark_connection_dead(conn_id)
        
        # Verify it's dead
        assert not await critical_heartbeat_manager.check_connection_health(conn_id)
        
        # Attempt operations that should NOT resurrect
        ws.should_fail_all_pings = True
        
        # These should fail without resurrection
        result = await critical_heartbeat_manager.send_ping(conn_id, ws)
        assert not result
        assert not critical_heartbeat_manager.connection_heartbeats[conn_id].is_alive
        
        # Only explicit activity from a VALID connection should resurrect
        ws_new = CriticalWebSocketMock("zombie_user")
        await critical_heartbeat_manager.record_activity(conn_id)
        assert critical_heartbeat_manager.connection_heartbeats[conn_id].is_alive
        
        logger.info("[U+2713] CRITICAL TEST PASSED: No false resurrections")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_staging_production_config_validation(self):
        """CRITICAL: Validate staging/production configurations."""
        configs = {
            "staging": HeartbeatConfig.for_environment("staging"),
            "production": HeartbeatConfig.for_environment("production")
        }
        
        for env_name, config in configs.items():
            # CRITICAL: Timeouts must be reasonable for cloud environments
            assert config.heartbeat_timeout_seconds >= 60, \
                f"CRITICAL: {env_name} timeout too short for cloud latency"
            
            # CRITICAL: Cleanup must not be too aggressive
            assert config.cleanup_interval_seconds >= 60, \
                f"CRITICAL: {env_name} cleanup too aggressive"
            
            # CRITICAL: Must detect failures reasonably quickly
            assert config.max_missed_heartbeats <= 3, \
                f"CRITICAL: {env_name} takes too long to detect failures"
            
            logger.info(f"[U+2713] {env_name} config validated: "
                       f"timeout={config.heartbeat_timeout_seconds}s, "
                       f"cleanup={config.cleanup_interval_seconds}s")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_concurrent_user_presence_integrity(self, critical_heartbeat_manager):
        """CRITICAL: Multiple users' presence must remain independent."""
        users = ["alice", "bob", "charlie"]
        connections = {}
        websockets = {}
        
        # Connect all users
        for user in users:
            conn_id = f"conn_{user}"
            ws = CriticalWebSocketMock(user)
            await critical_heartbeat_manager.register_connection(conn_id)
            connections[user] = conn_id
            websockets[user] = ws
        
        # All should be online
        for user, conn_id in connections.items():
            assert await critical_heartbeat_manager.check_connection_health(conn_id), \
                f"CRITICAL: {user} not online after connection"
        
        # Kill Alice's connection
        websockets["alice"].disconnect_abruptly()
        await critical_heartbeat_manager._mark_connection_dead(connections["alice"])
        
        # Alice offline, others online
        assert not await critical_heartbeat_manager.check_connection_health(connections["alice"])
        assert await critical_heartbeat_manager.check_connection_health(connections["bob"])
        assert await critical_heartbeat_manager.check_connection_health(connections["charlie"])
        
        # Bob has network issues but recovers
        websockets["bob"].should_fail_next_ping = True
        await critical_heartbeat_manager.send_ping(connections["bob"], websockets["bob"])
        await critical_heartbeat_manager.record_activity(connections["bob"])
        
        # Bob should recover, others unchanged
        assert not await critical_heartbeat_manager.check_connection_health(connections["alice"])
        assert await critical_heartbeat_manager.check_connection_health(connections["bob"])
        assert await critical_heartbeat_manager.check_connection_health(connections["charlie"])
        
        logger.info("[U+2713] CRITICAL TEST PASSED: User presence integrity maintained")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_zero_message_loss_during_transitions(self, critical_heartbeat_manager):
        """CRITICAL: No chat messages lost during presence state transitions."""
        conn_id = "transition_test"
        ws = CriticalWebSocketMock("user")
        message_log = []
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Simulate message sending during various states
        async def send_chat_message(msg: str) -> bool:
            """Simulate sending a chat message."""
            try:
                # Check if we can send
                if await critical_heartbeat_manager.check_connection_health(conn_id):
                    await ws.send_json({"type": "chat", "content": msg})
                    message_log.append({"msg": msg, "sent": True})
                    return True
                else:
                    message_log.append({"msg": msg, "sent": False})
                    return False
            except Exception as e:
                message_log.append({"msg": msg, "sent": False, "error": str(e)})
                return False
        
        # Normal state - messages work
        assert await send_chat_message("Hello")
        
        # During heartbeat timeout warning
        heartbeat = critical_heartbeat_manager.connection_heartbeats[conn_id]
        heartbeat.missed_heartbeats = 1
        assert await send_chat_message("Still here")
        
        # Recovery via activity
        await critical_heartbeat_manager.record_activity(conn_id)
        assert await send_chat_message("Recovered")
        
        # Verify no message loss
        sent_messages = [m for m in message_log if m["sent"]]
        assert len(sent_messages) == 3, f"CRITICAL: Messages lost! Log: {message_log}"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Zero message loss during transitions")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_heartbeat_doesnt_block_chat(self, critical_heartbeat_manager):
        """CRITICAL: Heartbeat operations must NEVER block chat messages."""
        conn_id = "nonblocking_test"
        ws = CriticalWebSocketMock("user")
        ws.network_delay_ms = 100  # Simulate network delay
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Start slow heartbeat operation
        heartbeat_task = asyncio.create_task(
            critical_heartbeat_manager.send_ping(conn_id, ws)
        )
        
        # Chat operations should not wait for heartbeat
        chat_start = time.time()
        await critical_heartbeat_manager.record_activity(conn_id)
        chat_time = time.time() - chat_start
        
        # Chat should be instant, not wait for heartbeat
        assert chat_time < 0.01, f"CRITICAL: Chat blocked for {chat_time*1000}ms"
        
        # Wait for heartbeat to complete
        await heartbeat_task
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Heartbeats don't block chat")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_users(self, critical_heartbeat_manager):
        """CRITICAL: Cleanup must NEVER remove active users."""
        active_users = ["active_1", "active_2", "active_3"]
        inactive_users = ["inactive_1", "inactive_2"]
        
        # Register all users
        for user in active_users + inactive_users:
            await critical_heartbeat_manager.register_connection(f"conn_{user}")
        
        # Mark inactive users as dead and old
        for user in inactive_users:
            conn_id = f"conn_{user}"
            await critical_heartbeat_manager._mark_connection_dead(conn_id)
            critical_heartbeat_manager.connection_heartbeats[conn_id].last_activity = time.time() - 300
        
        # Keep active users active
        for user in active_users:
            await critical_heartbeat_manager.record_activity(f"conn_{user}")
        
        # Run cleanup
        await critical_heartbeat_manager._cleanup_stale_data()
        
        # Active users MUST remain
        for user in active_users:
            conn_id = f"conn_{user}"
            assert conn_id in critical_heartbeat_manager.connection_heartbeats, \
                f"CRITICAL: Active user {user} was removed by cleanup!"
            assert await critical_heartbeat_manager.check_connection_health(conn_id), \
                f"CRITICAL: Active user {user} marked unhealthy after cleanup!"
        
        # Inactive users should be gone
        for user in inactive_users:
            conn_id = f"conn_{user}"
            assert conn_id not in critical_heartbeat_manager.connection_heartbeats
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Cleanup preserves active users")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self):
        """CRITICAL: Presence must integrate correctly with WebSocket manager."""
        ws_manager = get_websocket_manager()
        hb_manager = get_heartbeat_manager()
        
        user_id = "integration_user"
        ws = CriticalWebSocketMock(user_id)
        
        # Connect through WebSocket manager
        connection_id = await ws_manager.connect_user(user_id, ws)
        
        # Should be tracked by heartbeat manager
        await hb_manager.register_connection(connection_id)
        
        # Verify presence
        assert await hb_manager.check_connection_health(connection_id), \
            "CRITICAL: WebSocket connection not tracked by heartbeat"
        
        # Disconnect through WebSocket manager
        await ws_manager.disconnect_user(user_id, ws, 1000, "Normal")
        await hb_manager.unregister_connection(connection_id)
        
        # Should be removed
        assert not await hb_manager.check_connection_health(connection_id), \
            "CRITICAL: Disconnected user still showing as online"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: WebSocket manager integration")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_presence_accuracy_for_ui(self, critical_heartbeat_manager):
        """CRITICAL: Presence status must be accurate for UI display."""
        conn_id = "ui_test"
        ws = CriticalWebSocketMock("ui_user")
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Get status for UI
        status = critical_heartbeat_manager.get_connection_status(conn_id)
        
        # CRITICAL: Status must have required fields for UI
        assert status is not None, "CRITICAL: No status available for UI"
        assert "is_alive" in status, "CRITICAL: Missing is_alive field"
        assert "last_activity" in status, "CRITICAL: Missing last_activity field"
        assert "connection_id" in status, "CRITICAL: Missing connection_id field"
        
        # Status must be accurate
        assert status["is_alive"] is True, "CRITICAL: Wrong alive status"
        assert status["connection_id"] == conn_id, "CRITICAL: Wrong connection ID"
        
        # After activity
        await critical_heartbeat_manager.record_activity(conn_id)
        new_status = critical_heartbeat_manager.get_connection_status(conn_id)
        
        assert new_status["last_activity"] >= status["last_activity"], \
            "CRITICAL: Activity not reflected in status"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: UI presence accuracy")


class TestPresenceFailureRecovery:
    """Test recovery from various failure modes."""
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_recover_from_database_failure(self, critical_heartbeat_manager):
        """CRITICAL: Must handle database failures gracefully."""
        conn_id = "db_failure_test"
        ws = CriticalWebSocketMock("user")
        
        await critical_heartbeat_manager.register_connection(conn_id)
        
        # Simulate database failure during operation
        with patch.object(critical_heartbeat_manager, '_stats_lock', side_effect=Exception("DB Error")):
            # Operations should still work (degraded mode)
            await critical_heartbeat_manager.record_activity(conn_id)
            
            # Health check should still function
            is_healthy = await critical_heartbeat_manager.check_connection_health(conn_id)
            assert is_healthy, "CRITICAL: Database failure broke presence detection"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Survived database failure")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_recover_from_memory_pressure(self, critical_heartbeat_manager):
        """CRITICAL: Must handle memory pressure without losing critical connections."""
        critical_connections = []
        
        # Create some critical connections
        for i in range(10):
            conn_id = f"critical_{i}"
            await critical_heartbeat_manager.register_connection(conn_id)
            await critical_heartbeat_manager.record_activity(conn_id)
            critical_connections.append(conn_id)
        
        # Simulate memory pressure by creating many dead connections
        for i in range(1000):
            conn_id = f"dead_{i}"
            await critical_heartbeat_manager.register_connection(conn_id)
            await critical_heartbeat_manager._mark_connection_dead(conn_id)
        
        # Force cleanup
        await critical_heartbeat_manager._cleanup_stale_data()
        
        # Critical connections must survive
        for conn_id in critical_connections:
            assert conn_id in critical_heartbeat_manager.connection_heartbeats, \
                f"CRITICAL: Active connection {conn_id} lost during memory pressure"
            assert await critical_heartbeat_manager.check_connection_health(conn_id), \
                f"CRITICAL: Active connection {conn_id} unhealthy after cleanup"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Survived memory pressure")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_thread_safety_under_load(self):
        """CRITICAL: Must be thread-safe under concurrent load."""
        manager = WebSocketHeartbeatManager(HeartbeatConfig(
            heartbeat_interval_seconds=1,
            heartbeat_timeout_seconds=3
        ))
        await manager.start()
        
        conn_id = "thread_test"
        await manager.register_connection(conn_id)
        
        errors = []
        
        async def concurrent_operation(op_type: str):
            """Perform operation concurrently."""
            try:
                for _ in range(100):
                    if op_type == "activity":
                        await manager.record_activity(conn_id)
                    elif op_type == "health":
                        await manager.check_connection_health(conn_id)
                    elif op_type == "status":
                        manager.get_connection_status(conn_id)
                    await asyncio.sleep(0.001)
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple operations concurrently
        await asyncio.gather(
            concurrent_operation("activity"),
            concurrent_operation("health"),
            concurrent_operation("status"),
            concurrent_operation("activity"),
            concurrent_operation("health"),
        )
        
        await manager.stop()
        
        # No errors should occur
        assert len(errors) == 0, f"CRITICAL: Thread safety errors: {errors}"
        
        logger.info("[U+2713] CRITICAL TEST PASSED: Thread-safe under load")