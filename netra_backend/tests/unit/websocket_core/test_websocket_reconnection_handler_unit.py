"""
Unit tests for WebSocket Reconnection Handler - Testing connection recovery and state restoration.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Seamless user experience during network instability
- Value Impact: Users maintain chat sessions despite network interruptions
- Strategic Impact: Critical for mobile users and unreliable networks - prevents lost conversations

These tests focus on reconnection logic, state restoration, message buffer management,
and ensuring users never lose their agent interaction context.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.websocket_core.reconnection_handler import (
    WebSocketReconnectionHandler,
    ReconnectionState,
    ReconnectionConfig,
    MaxRetriesExceededException,
    ReconnectionSession
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketReconnectionHandler:
    """Unit tests for WebSocket reconnection handling."""
    
    @pytest.fixture
    def reconnection_config(self):
        """Create reconnection configuration."""
        return ReconnectionConfig(
            max_retry_attempts=5,
            initial_retry_delay_seconds=1.0,
            max_retry_delay_seconds=30.0,
            backoff_multiplier=2.0,
            session_timeout_minutes=30,
            message_buffer_max_size=1000
        )
    
    @pytest.fixture
    def reconnection_handler(self, reconnection_config):
        """Create WebSocketReconnectionHandler instance."""
        return WebSocketReconnectionHandler(
            config=reconnection_config,
            websocket_manager=Mock(),
            message_buffer=Mock()
        )
    
    @pytest.fixture
    def sample_session(self):
        """Create sample reconnection session."""
        return {
            "user_id": "user_123",
            "connection_id": "conn_456", 
            "thread_id": "thread_789",
            "last_message_id": "msg_999",
            "connected_at": datetime.now(timezone.utc),
            "user_agent": "Mozilla/5.0...",
            "client_ip": "192.168.1.100"
        }
    
    def test_initializes_with_correct_configuration(self, reconnection_handler, reconnection_config):
        """Test ReconnectionHandler initializes with proper configuration."""
        assert reconnection_handler.config == reconnection_config
        assert len(reconnection_handler._active_sessions) == 0
        assert len(reconnection_handler._reconnection_states) == 0
        assert reconnection_handler._cleanup_lock is not None
    
    @pytest.mark.asyncio
    async def test_registers_active_session(self, reconnection_handler, sample_session):
        """Test registration of active WebSocket session."""
        session_id = "session_123"
        
        # Register session
        await reconnection_handler.register_session(session_id, sample_session)
        
        # Verify session registered
        assert session_id in reconnection_handler._active_sessions
        session = reconnection_handler._active_sessions[session_id]
        assert isinstance(session, ReconnectionSession)
        assert session.user_id == sample_session["user_id"]
        assert session.connection_id == sample_session["connection_id"]
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_handles_connection_lost_event(self, reconnection_handler, sample_session):
        """Test handling of connection lost event."""
        session_id = "session_123"
        
        # Register active session
        await reconnection_handler.register_session(session_id, sample_session)
        
        # Simulate connection lost
        await reconnection_handler.handle_connection_lost(session_id, reason="network_error")
        
        # Verify reconnection state created
        assert session_id in reconnection_handler._reconnection_states
        state = reconnection_handler._reconnection_states[session_id]
        assert isinstance(state, ReconnectionState)
        assert state.retry_count == 0
        assert state.is_reconnecting is True
        assert state.lost_reason == "network_error"
        
        # Verify session marked as inactive
        session = reconnection_handler._active_sessions[session_id]
        assert session.is_active is False
    
    @pytest.mark.asyncio
    async def test_calculates_backoff_delay_correctly(self, reconnection_handler):
        """Test exponential backoff delay calculation."""
        config = reconnection_handler.config
        
        # Test backoff progression
        delays = []
        for retry_count in range(5):
            delay = reconnection_handler._calculate_backoff_delay(retry_count)
            delays.append(delay)
        
        # Should follow exponential backoff pattern
        assert delays[0] == config.initial_retry_delay_seconds  # 1.0
        assert delays[1] == config.initial_retry_delay_seconds * config.backoff_multiplier  # 2.0
        assert delays[2] == config.initial_retry_delay_seconds * (config.backoff_multiplier ** 2)  # 4.0
        
        # Should cap at max delay
        max_delay = reconnection_handler._calculate_backoff_delay(10)
        assert max_delay <= config.max_retry_delay_seconds
    
    @pytest.mark.asyncio
    async def test_attempts_reconnection_with_backoff(self, reconnection_handler, sample_session):
        """Test reconnection attempts with exponential backoff."""
        session_id = "session_123"
        await reconnection_handler.register_session(session_id, sample_session)
        await reconnection_handler.handle_connection_lost(session_id, reason="timeout")
        
        # Mock successful reconnection after 2 attempts
        reconnection_handler.websocket_manager.attempt_reconnection = AsyncMock()
        reconnection_handler.websocket_manager.attempt_reconnection.side_effect = [
            False,  # First attempt fails
            False,  # Second attempt fails  
            True    # Third attempt succeeds
        ]
        
        # Start reconnection process
        with patch('asyncio.sleep') as mock_sleep:
            result = await reconnection_handler.attempt_reconnection(session_id)
        
        # Verify reconnection succeeded
        assert result is True
        
        # Verify backoff delays were used
        assert mock_sleep.call_count == 2  # 2 failed attempts before success
        
        # Verify retry count tracked
        state = reconnection_handler._reconnection_states[session_id]
        assert state.retry_count == 3
        assert state.is_reconnecting is False
        assert state.reconnected_at is not None
    
    @pytest.mark.asyncio
    async def test_fails_after_max_retry_attempts(self, reconnection_handler, sample_session):
        """Test failure after exceeding maximum retry attempts."""
        session_id = "session_123"
        await reconnection_handler.register_session(session_id, sample_session)
        await reconnection_handler.handle_connection_lost(session_id, reason="persistent_error")
        
        # Mock all reconnection attempts failing
        reconnection_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=False)
        
        # Attempt reconnection - should eventually fail
        with patch('asyncio.sleep'):  # Speed up test
            with pytest.raises(MaxRetriesExceededException) as exc_info:
                await reconnection_handler.attempt_reconnection(session_id)
        
        # Verify proper failure
        assert "max retry attempts" in str(exc_info.value).lower()
        
        # Verify state reflects failure
        state = reconnection_handler._reconnection_states[session_id]
        assert state.retry_count == reconnection_handler.config.max_retry_attempts
        assert state.is_reconnecting is False
        assert state.failed_permanently is True
    
    @pytest.mark.asyncio
    async def test_restores_session_state_on_reconnection(self, reconnection_handler, sample_session):
        """Test session state restoration after successful reconnection."""
        session_id = "session_123"
        await reconnection_handler.register_session(session_id, sample_session)
        
        # Add buffered messages during disconnection
        buffered_messages = [
            WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={"status": "analyzing"},
                user_id=sample_session["user_id"]
            ),
            WebSocketMessage(
                message_type=MessageType.TOOL_COMPLETED,
                payload={"result": "analysis complete"},
                user_id=sample_session["user_id"]
            )
        ]
        
        reconnection_handler.message_buffer.get_buffered_messages = AsyncMock(
            return_value=buffered_messages
        )
        reconnection_handler.websocket_manager.send_messages = AsyncMock()
        
        # Simulate successful reconnection
        await reconnection_handler.handle_successful_reconnection(
            session_id, new_connection_id="new_conn_789"
        )
        
        # Verify buffered messages sent
        reconnection_handler.message_buffer.get_buffered_messages.assert_called_once_with(
            sample_session["user_id"]
        )
        reconnection_handler.websocket_manager.send_messages.assert_called_once_with(
            "new_conn_789", buffered_messages
        )
        
        # Verify session state updated
        session = reconnection_handler._active_sessions[session_id]
        assert session.connection_id == "new_conn_789"
        assert session.is_active is True
        assert session.reconnected_at is not None
    
    @pytest.mark.asyncio
    async def test_prevents_duplicate_reconnection_attempts(self, reconnection_handler, sample_session):
        """Test prevention of duplicate reconnection attempts for same session."""
        session_id = "session_123"
        await reconnection_handler.register_session(session_id, sample_session)
        await reconnection_handler.handle_connection_lost(session_id, reason="duplicate_test")
        
        # Mock slow reconnection
        slow_reconnect_future = asyncio.Future()
        reconnection_handler.websocket_manager.attempt_reconnection = AsyncMock(
            return_value=slow_reconnect_future
        )
        
        # Start first reconnection attempt
        task1 = asyncio.create_task(
            reconnection_handler.attempt_reconnection(session_id)
        )
        await asyncio.sleep(0.01)  # Let first attempt start
        
        # Try to start second attempt - should be rejected
        task2 = asyncio.create_task(
            reconnection_handler.attempt_reconnection(session_id)
        )
        
        # Complete first attempt
        slow_reconnect_future.set_result(True)
        result1 = await task1
        result2 = await task2
        
        # First should succeed, second should be rejected/ignored
        assert result1 is True
        assert result2 in [False, None]  # Implementation dependent
        
        # Should only have one set of reconnection calls
        assert reconnection_handler.websocket_manager.attempt_reconnection.call_count == 1
    
    @pytest.mark.asyncio
    async def test_cleans_up_expired_sessions(self, reconnection_handler, sample_session):
        """Test cleanup of expired sessions and reconnection states."""
        session_id = "expired_session"
        await reconnection_handler.register_session(session_id, sample_session)
        
        # Age the session
        session = reconnection_handler._active_sessions[session_id]
        session.connected_at = datetime.now(timezone.utc) - timedelta(hours=2)
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Run cleanup
        await reconnection_handler.cleanup_expired_sessions()
        
        # Verify expired session cleaned up
        assert session_id not in reconnection_handler._active_sessions
        
        # If there was a reconnection state, it should also be cleaned
        assert session_id not in reconnection_handler._reconnection_states
    
    @pytest.mark.asyncio
    async def test_tracks_reconnection_metrics(self, reconnection_handler, sample_session):
        """Test collection of reconnection metrics and statistics."""
        session_id = "metrics_session"
        await reconnection_handler.register_session(session_id, sample_session)
        await reconnection_handler.handle_connection_lost(session_id, reason="metrics_test")
        
        # Mock successful reconnection
        reconnection_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=True)
        
        start_time = datetime.now(timezone.utc)
        with patch('asyncio.sleep'):
            await reconnection_handler.attempt_reconnection(session_id)
        
        # Get metrics
        metrics = await reconnection_handler.get_session_metrics(session_id)
        
        # Verify metrics collected
        assert metrics is not None
        assert metrics.total_disconnections >= 1
        assert metrics.total_reconnection_attempts >= 1
        assert metrics.successful_reconnections >= 1
        assert metrics.average_reconnection_time_seconds >= 0
        
        # Verify session-level metrics
        session = reconnection_handler._active_sessions[session_id]
        assert session.reconnection_count >= 1
        assert session.total_downtime_seconds >= 0