"""
Comprehensive Unit Tests for WebSocket Heartbeat Manager

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Reliability
- Value Impact: Ensures presence detection accuracy critical for user experience
- Strategic Impact: Prevents connection leaks, improves system resource management

Test coverage includes:
- Connection registration/unregistration
- Heartbeat sending/receiving
- Timeout detection
- Connection health checks
- Thread safety
- Error handling
- Statistics tracking
- Edge cases and resilience
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
from typing import Dict, Any

from netra_backend.app.websocket_core.manager import (
    WebSocketHeartbeatManager,
    HeartbeatConfig,
    ConnectionHeartbeat,
    get_heartbeat_manager,
    register_connection_heartbeat,
    unregister_connection_heartbeat,
    check_connection_heartbeat
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestHeartbeatConfig:
    """Test HeartbeatConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HeartbeatConfig()
        assert config.heartbeat_interval_seconds == 30
        assert config.heartbeat_timeout_seconds == 90
        assert config.max_missed_heartbeats == 2
        assert config.cleanup_interval_seconds == 120
        assert config.ping_payload_size_limit == 125
    
    def test_environment_specific_config(self):
        """Test environment-specific configuration."""
        # Test staging config
        staging_config = HeartbeatConfig.for_environment("staging")
        assert staging_config.heartbeat_timeout_seconds == 90
        assert staging_config.max_missed_heartbeats == 2
        
        # Test production config
        prod_config = HeartbeatConfig.for_environment("production")
        assert prod_config.heartbeat_interval_seconds == 25
        assert prod_config.heartbeat_timeout_seconds == 75
        
        # Test development config
        dev_config = HeartbeatConfig.for_environment("development")
        assert dev_config.heartbeat_interval_seconds == 45
        assert dev_config.max_missed_heartbeats == 3


class TestConnectionHeartbeat:
    """Test ConnectionHeartbeat dataclass."""
    
    def test_initialization(self):
        """Test ConnectionHeartbeat initialization."""
        heartbeat = ConnectionHeartbeat("conn_123")
        assert heartbeat.connection_id == "conn_123"
        assert heartbeat.last_ping_sent is None
        assert heartbeat.last_pong_received is None
        assert heartbeat.missed_heartbeats == 0
        assert heartbeat.is_alive is True
        assert heartbeat.last_activity is not None
        assert time.time() - heartbeat.last_activity < 1


class TestWebSocketHeartbeatManager:
    """Test WebSocketHeartbeatManager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a heartbeat manager for testing."""
        config = HeartbeatConfig(
            heartbeat_interval_seconds=1,
            heartbeat_timeout_seconds=3,
            max_missed_heartbeats=2,
            cleanup_interval_seconds=5
        )
        return WebSocketHeartbeatManager(config)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        ws = AsyncMock()
        ws.ping = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_register_connection(self, manager):
        """Test connection registration."""
        await manager.register_connection("conn_1")
        
        assert "conn_1" in manager.connection_heartbeats
        assert manager.connection_heartbeats["conn_1"].connection_id == "conn_1"
        assert manager.connection_heartbeats["conn_1"].is_alive is True
        assert manager.stats['total_connections_registered'] == 1
    
    @pytest.mark.asyncio
    async def test_register_duplicate_connection(self, manager):
        """Test duplicate connection registration handling."""
        await manager.register_connection("conn_1")
        
        # Register same connection again
        await manager.register_connection("conn_1")
        
        assert "conn_1" in manager.connection_heartbeats
        assert manager.stats['total_connections_registered'] == 2
    
    @pytest.mark.asyncio
    async def test_unregister_connection(self, manager):
        """Test connection unregistration."""
        await manager.register_connection("conn_1")
        await manager.unregister_connection("conn_1")
        
        assert "conn_1" not in manager.connection_heartbeats
        assert "conn_1" not in manager.active_pings
    
    @pytest.mark.asyncio
    async def test_unregister_unknown_connection(self, manager):
        """Test unregistering unknown connection doesn't raise error."""
        # Should not raise an error
        await manager.unregister_connection("unknown_conn")
    
    @pytest.mark.asyncio
    async def test_record_activity(self, manager):
        """Test activity recording."""
        await manager.register_connection("conn_1")
        
        # Simulate activity
        await asyncio.sleep(0.1)
        await manager.record_activity("conn_1")
        
        heartbeat = manager.connection_heartbeats["conn_1"]
        assert heartbeat.missed_heartbeats == 0
        assert heartbeat.is_alive is True
        assert time.time() - heartbeat.last_activity < 1
    
    @pytest.mark.asyncio
    async def test_resurrect_dead_connection(self, manager):
        """Test resurrecting a dead connection through activity."""
        await manager.register_connection("conn_1")
        
        # Mark connection as dead
        await manager._mark_connection_dead("conn_1")
        assert not manager.connection_heartbeats["conn_1"].is_alive
        
        # Record activity to resurrect
        await manager.record_activity("conn_1")
        
        assert manager.connection_heartbeats["conn_1"].is_alive
        assert manager.stats['resurrection_count'] == 1
    
    @pytest.mark.asyncio
    async def test_send_ping_success(self, manager, mock_websocket):
        """Test successful ping sending."""
        await manager.register_connection("conn_1")
        
        result = await manager.send_ping("conn_1", mock_websocket, b"test")
        
        assert result is True
        mock_websocket.ping.assert_called_once_with(b"test")
        assert "conn_1" in manager.active_pings
        assert manager.stats['pings_sent'] == 1
    
    @pytest.mark.asyncio
    async def test_send_ping_payload_too_large(self, manager, mock_websocket):
        """Test ping with oversized payload."""
        await manager.register_connection("conn_1")
        
        large_payload = b"x" * 200
        result = await manager.send_ping("conn_1", mock_websocket, large_payload)
        
        assert result is False
        mock_websocket.ping.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_ping_unregistered_connection(self, manager, mock_websocket):
        """Test sending ping to unregistered connection."""
        result = await manager.send_ping("unknown", mock_websocket)
        
        assert result is False
        mock_websocket.ping.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_ping_skip_pending(self, manager, mock_websocket):
        """Test skipping ping when previous ping is pending."""
        await manager.register_connection("conn_1")
        
        # Send first ping
        await manager.send_ping("conn_1", mock_websocket)
        
        # Try to send another ping immediately
        result = await manager.send_ping("conn_1", mock_websocket)
        
        assert result is True  # Not an error, just skipped
        assert mock_websocket.ping.call_count == 1  # Only one ping sent
    
    @pytest.mark.asyncio
    async def test_send_ping_timeout(self, manager, mock_websocket):
        """Test ping timeout handling."""
        await manager.register_connection("conn_1")
        
        # Make ping timeout
        mock_websocket.ping = AsyncMock(side_effect=asyncio.TimeoutError)
        
        result = await manager.send_ping("conn_1", mock_websocket)
        
        assert result is False
        assert manager.connection_heartbeats["conn_1"].missed_heartbeats == 1
    
    @pytest.mark.asyncio
    async def test_send_ping_error(self, manager, mock_websocket):
        """Test ping error handling."""
        await manager.register_connection("conn_1")
        
        # Make ping fail
        mock_websocket.ping = AsyncMock(side_effect=Exception("Network error"))
        
        result = await manager.send_ping("conn_1", mock_websocket)
        
        assert result is False
        assert not manager.connection_heartbeats["conn_1"].is_alive
    
    @pytest.mark.asyncio
    async def test_record_pong(self, manager):
        """Test pong recording."""
        await manager.register_connection("conn_1")
        
        # Simulate sending ping
        manager.active_pings["conn_1"] = time.time()
        
        await manager.record_pong("conn_1", manager.active_pings["conn_1"])
        
        heartbeat = manager.connection_heartbeats["conn_1"]
        assert heartbeat.last_pong_received is not None
        assert heartbeat.missed_heartbeats == 0
        assert heartbeat.is_alive is True
        assert "conn_1" not in manager.active_pings
        assert manager.stats['pongs_received'] == 1
    
    @pytest.mark.asyncio
    async def test_record_pong_unregistered(self, manager):
        """Test recording pong for unregistered connection."""
        # Should not raise error
        await manager.record_pong("unknown")
        assert manager.stats['pongs_received'] == 0
    
    @pytest.mark.asyncio
    async def test_record_pong_abnormal_ping_time(self, manager):
        """Test handling of abnormal ping times."""
        await manager.register_connection("conn_1")
        
        # Test high ping time
        manager.active_pings["conn_1"] = time.time() - 40
        await manager.record_pong("conn_1", manager.active_pings["conn_1"])
        
        # Test negative ping time
        await manager.register_connection("conn_2")
        manager.active_pings["conn_2"] = time.time() + 10
        await manager.record_pong("conn_2", manager.active_pings["conn_2"])
    
    @pytest.mark.asyncio
    async def test_check_connection_health_healthy(self, manager):
        """Test health check for healthy connection."""
        await manager.register_connection("conn_1")
        await manager.record_activity("conn_1")
        
        is_healthy = await manager.check_connection_health("conn_1")
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_check_connection_health_timeout(self, manager):
        """Test health check for timed out connection."""
        await manager.register_connection("conn_1")
        
        # Set last activity to past timeout
        heartbeat = manager.connection_heartbeats["conn_1"]
        heartbeat.last_activity = time.time() - manager.config.heartbeat_timeout_seconds - 1
        
        is_healthy = await manager.check_connection_health("conn_1")
        
        assert is_healthy is False
        assert not heartbeat.is_alive
    
    @pytest.mark.asyncio
    async def test_check_connection_health_missed_heartbeats(self, manager):
        """Test health check with too many missed heartbeats."""
        await manager.register_connection("conn_1")
        
        # Set missed heartbeats to max
        heartbeat = manager.connection_heartbeats["conn_1"]
        heartbeat.missed_heartbeats = manager.config.max_missed_heartbeats
        
        is_healthy = await manager.check_connection_health("conn_1")
        
        assert is_healthy is False
        assert not heartbeat.is_alive
    
    @pytest.mark.asyncio
    async def test_check_connection_health_stale_ping(self, manager):
        """Test health check with stale pending ping."""
        await manager.register_connection("conn_1")
        
        # Add stale ping
        manager.active_pings["conn_1"] = time.time() - manager.config.heartbeat_timeout_seconds - 1
        
        is_healthy = await manager.check_connection_health("conn_1")
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_check_connection_health_unknown(self, manager):
        """Test health check for unknown connection."""
        is_healthy = await manager.check_connection_health("unknown")
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_get_connection_status(self, manager):
        """Test getting connection status."""
        await manager.register_connection("conn_1")
        await manager.record_activity("conn_1")
        
        status = manager.get_connection_status("conn_1")
        
        assert status is not None
        assert status['connection_id'] == "conn_1"
        assert status['is_alive'] is True
        assert status['missed_heartbeats'] == 0
        assert 'last_activity' in status
        assert 'seconds_since_activity' in status
    
    @pytest.mark.asyncio
    async def test_get_connection_status_unknown(self, manager):
        """Test getting status for unknown connection."""
        status = manager.get_connection_status("unknown")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_mark_connection_dead(self, manager):
        """Test marking connection as dead."""
        await manager.register_connection("conn_1")
        manager.active_pings["conn_1"] = time.time()
        
        await manager._mark_connection_dead("conn_1")
        
        heartbeat = manager.connection_heartbeats["conn_1"]
        assert not heartbeat.is_alive
        assert "conn_1" not in manager.active_pings
        assert manager.stats['timeouts_detected'] == 1
        assert manager.stats['connections_dropped'] == 1
    
    @pytest.mark.asyncio
    async def test_mark_connection_dead_idempotent(self, manager):
        """Test marking already dead connection."""
        await manager.register_connection("conn_1")
        
        # Mark dead twice
        await manager._mark_connection_dead("conn_1")
        await manager._mark_connection_dead("conn_1")
        
        # Stats should only increment once
        assert manager.stats['timeouts_detected'] == 1
        assert manager.stats['connections_dropped'] == 1
    
    @pytest.mark.asyncio
    async def test_update_avg_ping_time(self, manager):
        """Test average ping time calculation."""
        # First ping time
        manager._update_avg_ping_time(1.0)
        assert manager.stats['avg_ping_time'] == 1.0
        
        # Second ping time
        manager._update_avg_ping_time(2.0)
        assert 1.0 < manager.stats['avg_ping_time'] < 2.0
        
        # Check min/max tracking
        assert manager.stats['min_ping_time'] == 1.0
        assert manager.stats['max_ping_time'] == 2.0
    
    @pytest.mark.asyncio
    async def test_update_avg_ping_time_invalid(self, manager):
        """Test handling of invalid ping times."""
        # Negative ping time
        manager._update_avg_ping_time(-1.0)
        assert manager.stats['avg_ping_time'] == 0.0
        
        # Excessive ping time
        manager._update_avg_ping_time(35.0)
        assert manager.stats['avg_ping_time'] == 0.0
        
        # Valid ping time
        manager._update_avg_ping_time(1.0)
        assert manager.stats['avg_ping_time'] == 1.0
    
    @pytest.mark.asyncio
    async def test_update_avg_ping_time_outlier_dampening(self, manager):
        """Test outlier dampening in average calculation."""
        # Establish baseline
        for _ in range(5):
            manager._update_avg_ping_time(1.0)
        
        baseline = manager.stats['avg_ping_time']
        
        # Add outlier
        manager._update_avg_ping_time(10.0)
        
        # Check that outlier effect is dampened
        assert manager.stats['avg_ping_time'] < baseline + 1.0
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Test statistics retrieval."""
        await manager.register_connection("conn_1")
        await manager.register_connection("conn_2")
        await manager._mark_connection_dead("conn_2")
        
        stats = manager.get_stats()
        
        assert stats['active_connections'] == 1
        assert stats['total_connections'] == 2
        assert stats['total_connections_registered'] == 2
        assert 'pings_sent' in stats
        assert 'pongs_received' in stats
    
    @pytest.mark.asyncio
    async def test_get_all_connection_statuses(self, manager):
        """Test getting all connection statuses."""
        await manager.register_connection("conn_1")
        await manager.register_connection("conn_2")
        
        all_statuses = manager.get_all_connection_statuses()
        
        assert len(all_statuses) == 2
        assert "conn_1" in all_statuses
        assert "conn_2" in all_statuses
        assert all_statuses["conn_1"]['connection_id'] == "conn_1"
    
    @pytest.mark.asyncio
    async def test_heartbeat_loop_processing(self, manager):
        """Test heartbeat loop processing."""
        await manager.register_connection("conn_1")
        
        # Simulate old activity
        heartbeat = manager.connection_heartbeats["conn_1"]
        heartbeat.last_activity = time.time() - manager.config.heartbeat_timeout_seconds - 1
        
        # Process heartbeats
        await manager._process_heartbeats()
        
        # Connection should be marked dead
        assert not heartbeat.is_alive
    
    @pytest.mark.asyncio
    async def test_cleanup_dead_connections(self, manager):
        """Test cleanup of dead connections."""
        await manager.register_connection("conn_1")
        await manager.register_connection("conn_2")
        
        # Mark connections as dead with different death times
        await manager._mark_connection_dead("conn_1")
        manager.connection_heartbeats["conn_1"].last_activity = time.time() - 200
        
        await manager._mark_connection_dead("conn_2")
        manager.connection_heartbeats["conn_2"].last_activity = time.time() - 10
        
        # Run cleanup
        await manager._cleanup_stale_data()
        
        # Only old dead connection should be removed
        assert "conn_1" not in manager.connection_heartbeats
        assert "conn_2" in manager.connection_heartbeats
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_pings(self, manager):
        """Test cleanup of orphaned pings."""
        # Add orphaned ping (no corresponding connection)
        manager.active_pings["orphan"] = time.time() - 200
        
        # Add normal ping
        await manager.register_connection("conn_1")
        manager.active_pings["conn_1"] = time.time()
        
        # Run cleanup
        await manager._cleanup_stale_data()
        
        # Orphaned ping should be removed
        assert "orphan" not in manager.active_pings
        assert "conn_1" in manager.active_pings
    
    @pytest.mark.asyncio
    async def test_cleanup_clock_skew_handling(self, manager):
        """Test handling of clock skew in cleanup."""
        await manager.register_connection("conn_1")
        
        # Simulate clock skew (future timestamp)
        heartbeat = manager.connection_heartbeats["conn_1"]
        heartbeat.is_alive = False
        heartbeat.last_activity = time.time() + 100
        
        # Run cleanup - should detect and correct
        await manager._cleanup_stale_data()
        
        # Activity time should be corrected
        assert heartbeat.last_activity <= time.time()
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, manager):
        """Test starting and stopping the manager."""
        await manager.start()
        
        # Check tasks are created
        assert manager._heartbeat_task is not None
        assert manager._cleanup_task is not None
        
        # Stop manager
        await manager.stop()
        
        # Check shutdown flag
        assert manager._shutdown is True
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, manager):
        """Test thread safety with concurrent operations."""
        async def register_many():
            for i in range(10):
                await manager.register_connection(f"conn_{i}")
                await asyncio.sleep(0.001)
        
        async def unregister_many():
            await asyncio.sleep(0.005)
            for i in range(5):
                await manager.unregister_connection(f"conn_{i}")
                await asyncio.sleep(0.001)
        
        async def record_activity_many():
            await asyncio.sleep(0.003)
            for i in range(10):
                await manager.record_activity(f"conn_{i}")
                await asyncio.sleep(0.001)
        
        # Run concurrent operations
        await asyncio.gather(
            register_many(),
            unregister_many(),
            record_activity_many()
        )
        
        # Verify state consistency
        assert len(manager.connection_heartbeats) == 5  # 10 registered - 5 unregistered
        for i in range(5, 10):
            assert f"conn_{i}" in manager.connection_heartbeats


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    @pytest.mark.asyncio
    async def test_get_heartbeat_manager(self):
        """Test global heartbeat manager singleton."""
        with patch('netra_backend.app.websocket_core.heartbeat_manager._heartbeat_manager', None):
            manager1 = get_heartbeat_manager()
            manager2 = get_heartbeat_manager()
            
            assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_register_connection_heartbeat(self):
        """Test global register function."""
        with patch('netra_backend.app.websocket_core.heartbeat_manager._heartbeat_manager', None):
            await register_connection_heartbeat("conn_1")
            
            manager = get_heartbeat_manager()
            assert "conn_1" in manager.connection_heartbeats
    
    @pytest.mark.asyncio
    async def test_unregister_connection_heartbeat(self):
        """Test global unregister function."""
        with patch('netra_backend.app.websocket_core.heartbeat_manager._heartbeat_manager', None):
            await register_connection_heartbeat("conn_1")
            await unregister_connection_heartbeat("conn_1")
            
            manager = get_heartbeat_manager()
            assert "conn_1" not in manager.connection_heartbeats
    
    @pytest.mark.asyncio
    async def test_check_connection_heartbeat(self):
        """Test global health check function."""
        with patch('netra_backend.app.websocket_core.heartbeat_manager._heartbeat_manager', None):
            await register_connection_heartbeat("conn_1")
            
            is_healthy = await check_connection_heartbeat("conn_1")
            assert is_healthy is True
            
            is_healthy = await check_connection_heartbeat("unknown")
            assert is_healthy is False


class TestEdgeCasesAndResilience:
    """Test edge cases and resilience scenarios."""
    
    @pytest.fixture
    def manager(self):
        config = HeartbeatConfig(
            heartbeat_interval_seconds=1,
            heartbeat_timeout_seconds=3,
            max_missed_heartbeats=2
        )
        return WebSocketHeartbeatManager(config)
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, manager):
        """Test rapid connection/disconnection cycles."""
        for _ in range(10):
            await manager.register_connection("conn_rapid")
            await manager.unregister_connection("conn_rapid")
        
        assert "conn_rapid" not in manager.connection_heartbeats
        assert manager.stats['total_connections_registered'] == 10
    
    @pytest.mark.asyncio
    async def test_process_heartbeat_error_handling(self, manager):
        """Test error handling in heartbeat processing."""
        await manager.register_connection("conn_1")
        
        # Mock an error in processing
        with patch.object(manager, '_mark_connection_dead', side_effect=Exception("Test error")):
            # Should not raise, just log error
            await manager._process_single_heartbeat(
                "conn_1",
                manager.connection_heartbeats["conn_1"],
                time.time()
            )
    
    @pytest.mark.asyncio
    async def test_cleanup_error_handling(self, manager):
        """Test error handling in cleanup."""
        # Mock an error in cleanup
        with patch.object(manager, 'unregister_connection', side_effect=Exception("Test error")):
            # Should not raise, just log error
            await manager._cleanup_stale_data()
    
    @pytest.mark.asyncio
    async def test_websocket_failure_during_ping(self, manager, mock_websocket):
        """Test WebSocket failure during ping operation."""
        await manager.register_connection("conn_1")
        
        # Simulate various WebSocket errors
        errors = [
            ConnectionError("Connection lost"),
            OSError("Socket closed"),
            RuntimeError("WebSocket not connected")
        ]
        
        for error in errors:
            mock_websocket.ping = AsyncMock(side_effect=error)
            result = await manager.send_ping("conn_1", mock_websocket)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, manager):
        """Test that manager doesn't leak memory with many connections."""
        # Register many connections
        for i in range(100):
            await manager.register_connection(f"conn_{i}")
        
        # Mark them all as dead
        for i in range(100):
            await manager._mark_connection_dead(f"conn_{i}")
        
        # Set death time to past cleanup threshold
        for conn_id in manager.connection_heartbeats:
            manager.connection_heartbeats[conn_id].last_activity = time.time() - 200
        
        # Run cleanup
        await manager._cleanup_stale_data()
        
        # All connections should be removed
        assert len(manager.connection_heartbeats) == 0
        assert len(manager.active_pings) == 0