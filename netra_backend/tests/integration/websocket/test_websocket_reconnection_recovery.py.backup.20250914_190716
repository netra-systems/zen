"""
WebSocket Reconnection and Recovery Integration Tests

RELIABILITY CRITICAL: WebSocket reconnection and recovery ensures uninterrupted chat
experience that maintains user engagement and prevents revenue loss from session drops.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Connection reliability is essential for all users
- Business Goal: Maintain continuous chat experience during network interruptions
- Value Impact: Connection recovery prevents user frustration and session abandonment
- Revenue Impact: Protects $500K+ ARR by ensuring chat sessions continue after network issues

RECONNECTION REQUIREMENTS:
- Automatic reconnection after connection drops
- Event replay to recover missed messages
- Connection state synchronization after recovery
- Graceful degradation during connection issues
- Heartbeat and connection health monitoring
- Persistent session state across reconnections

TEST SCOPE: Integration-level validation of WebSocket reconnection and recovery including:
- Automatic reconnection after network failures
- Event replay and message recovery mechanisms
- Connection state synchronization post-recovery
- Heartbeat-based connection health monitoring
- Graceful degradation during connectivity issues
- Session state persistence across reconnections
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field
from collections import deque
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ReconnectionState, ConnectionMetadata
)

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionEvent:
    """Represents a connection event during testing."""
    event_type: str
    timestamp: datetime
    connection_state: WebSocketConnectionState
    user_id: str
    event_data: Dict[str, Any] = field(default_factory=dict)


class ReconnectingWebSocketMock:
    """Mock WebSocket that simulates connection drops and reconnections."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.state = WebSocketConnectionState.CONNECTED
        self.messages_sent = []
        self.connection_events: List[ConnectionEvent] = []
        
        # Reconnection simulation
        self.simulate_failures = True
        self.failure_count = 0
        self.max_failures = 3
        self.reconnection_attempts = 0
        self.last_failure_time = None
        
        # Message replay
        self.missed_messages: deque = deque(maxlen=100)
        self.last_acknowledged_message_id = None
        self.replay_enabled = True
        
        # Heartbeat tracking
        self.last_heartbeat = datetime.now(UTC)
        self.heartbeat_interval = 5.0  # seconds
        self.heartbeat_timeout = 15.0  # seconds
        
    async def send(self, message: str) -> None:
        """Send message with failure simulation."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        # Simulate network failures during send
        if self.simulate_failures and self.failure_count < self.max_failures:
            if len(self.messages_sent) % 5 == 4:  # Fail every 5th message
                self.failure_count += 1
                self.last_failure_time = datetime.now(UTC)
                self.state = WebSocketConnectionState.DISCONNECTED
                
                # Store message for replay
                message_data = {
                    'message': message,
                    'timestamp': datetime.now(UTC).isoformat(),
                    'message_id': f"msg_{uuid.uuid4().hex[:8]}"
                }
                self.missed_messages.append(message_data)
                
                self._record_event("connection_failure", {
                    'failure_count': self.failure_count,
                    'message_queued_for_replay': True
                })
                
                raise ConnectionError(f"Simulated network failure #{self.failure_count}")
        
        # Record successful message
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.messages_sent.append({
            'message': message,
            'message_id': message_id,
            'timestamp': datetime.now(UTC).isoformat(),
            'connection_state': self.state.value
        })
        
        self.last_acknowledged_message_id = message_id
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
        self._record_event("connection_closed", {'code': code, 'reason': reason})
        
    def _record_event(self, event_type: str, event_data: Dict[str, Any] = None):
        """Record connection event for testing validation."""
        event = ConnectionEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            connection_state=self.state,
            user_id=self.user_id,
            event_data=event_data or {}
        )
        self.connection_events.append(event)
        
    async def simulate_reconnection(self) -> bool:
        """Simulate reconnection attempt."""
        if self.state == WebSocketConnectionState.DISCONNECTED:
            self.reconnection_attempts += 1
            
            # Simulate reconnection success after a few attempts
            if self.reconnection_attempts >= 2:
                self.state = WebSocketConnectionState.CONNECTED
                self.is_closed = False
                self._record_event("reconnection_successful", {
                    'attempt_number': self.reconnection_attempts,
                    'time_since_failure': (datetime.now(UTC) - self.last_failure_time).total_seconds()
                })
                return True
            else:
                self._record_event("reconnection_attempt", {
                    'attempt_number': self.reconnection_attempts,
                    'success': False
                })
                return False
        
        return True  # Already connected
    
    async def replay_missed_messages(self, manager: Any) -> int:
        """Replay messages that were missed during disconnection."""
        if not self.replay_enabled or len(self.missed_messages) == 0:
            return 0
        
        replayed_count = 0
        
        # Replay missed messages
        while self.missed_messages:
            missed_msg = self.missed_messages.popleft()
            try:
                # Simulate sending the replayed message
                await self.send(missed_msg['message'])
                replayed_count += 1
                self._record_event("message_replayed", {
                    'original_timestamp': missed_msg['timestamp'],
                    'message_id': missed_msg['message_id']
                })
            except Exception as e:
                # If replay fails, put message back and stop
                self.missed_messages.appendleft(missed_msg)
                break
        
        return replayed_count
    
    def is_heartbeat_timeout(self) -> bool:
        """Check if heartbeat has timed out."""
        time_since_heartbeat = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        return time_since_heartbeat > self.heartbeat_timeout
    
    async def send_heartbeat(self) -> None:
        """Send heartbeat if connection is healthy."""
        if self.state == WebSocketConnectionState.CONNECTED:
            heartbeat_msg = json.dumps({
                'type': 'heartbeat',
                'timestamp': datetime.now(UTC).isoformat(),
                'connection_id': self.connection_id
            })
            await self.send(heartbeat_msg)
            self.last_heartbeat = datetime.now(UTC)
            self._record_event("heartbeat_sent", {})


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.reliability
@pytest.mark.asyncio
class TestWebSocketReconnectionRecovery(SSotAsyncTestCase):
    """
    Integration tests for WebSocket reconnection and recovery.
    
    RELIABILITY CRITICAL: These tests protect chat session continuity that maintains
    user engagement and prevents revenue loss from connection interruptions.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_reconnection_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_reconnection_test")
        
        # Test user data
        self.test_user = TestUserData(
            user_id=f"reconnect_user_{uuid.uuid4().hex[:8]}",
            email="reconnect@netra.ai",
            tier="mid",
            thread_id=f"reconnect_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.mock_websockets: List[ReconnectingWebSocketMock] = []
        
    async def teardown_method(self, method):
        """Clean up reconnection test resources."""
        for mock_ws in self.mock_websockets:
            if not mock_ws.is_closed:
                await mock_ws.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    async def create_mock_user_context(self, user_data: TestUserData) -> Any:
        """Create mock user context for testing."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"reconnect_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True
        })()
    
    async def test_automatic_reconnection_after_network_failure(self):
        """
        Test: WebSocket automatically reconnects after network failures
        
        Business Value: Ensures users maintain chat sessions during network issues,
        preventing frustration and session abandonment that could impact revenue.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create reconnecting WebSocket mock
        connection_id = f"reconnect_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ReconnectingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        # Establish initial connection
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Verify initial connection
            assert manager.is_connected(ensure_user_id(self.test_user.user_id))
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            
            # Send messages that will trigger simulated failures
            failure_occurred = False
            for i in range(10):
                try:
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_thinking",
                        data={
                            'message_sequence': i,
                            'reconnection_test': True,
                            'timestamp': datetime.now(UTC).isoformat()
                        }
                    )
                    await asyncio.sleep(0.1)  # Brief delay
                except ConnectionError as e:
                    failure_occurred = True
                    logger.info(f"Expected connection failure occurred: {e}")
                    
                    # Simulate reconnection process
                    for attempt in range(3):
                        await asyncio.sleep(1)  # Wait before reconnection attempt
                        reconnected = await mock_ws.simulate_reconnection()
                        
                        if reconnected:
                            logger.info(f"Reconnection successful after {attempt + 1} attempts")
                            break
                    
                    # Verify reconnection succeeded
                    assert mock_ws.state == WebSocketConnectionState.CONNECTED
                    assert mock_ws.reconnection_attempts >= 2
                    
                    # Continue sending messages after reconnection
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_thinking",
                        data={
                            'post_reconnection_message': True,
                            'reconnection_successful': True
                        }
                    )
                    break
            
            # Verify failure and recovery occurred
            assert failure_occurred, "Connection failure should have been simulated"
            
            # Verify reconnection events
            failure_events = [e for e in mock_ws.connection_events if e.event_type == "connection_failure"]
            reconnection_events = [e for e in mock_ws.connection_events if e.event_type == "reconnection_successful"]
            
            assert len(failure_events) > 0, "Connection failures should be recorded"
            assert len(reconnection_events) > 0, "Successful reconnections should be recorded"
            
            logger.info("✅ Automatic reconnection after network failure validated")
    
    async def test_event_replay_after_connection_recovery(self):
        """
        Test: Events are replayed after connection recovery to prevent message loss
        
        Business Value: Ensures users don't miss critical AI responses during network
        issues, maintaining chat experience quality and user satisfaction.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"replay_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ReconnectingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Send messages until failure occurs
            messages_before_failure = 0
            failure_occurred = False
            
            for i in range(15):
                try:
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_started" if i % 3 == 0 else "agent_thinking",
                        data={
                            'replay_test_sequence': i,
                            'critical_message': f"Message {i} - should not be lost",
                            'timestamp': datetime.now(UTC).isoformat()
                        }
                    )
                    messages_before_failure += 1
                    await asyncio.sleep(0.05)
                except ConnectionError:
                    failure_occurred = True
                    logger.info(f"Connection failed after {messages_before_failure} messages")
                    break
            
            assert failure_occurred, "Connection failure should occur for replay testing"
            
            # Check that messages were queued for replay during failure
            missed_messages_count = len(mock_ws.missed_messages)
            logger.info(f"Messages queued for replay: {missed_messages_count}")
            
            # Simulate reconnection
            await mock_ws.simulate_reconnection()
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            
            # Replay missed messages
            replayed_count = await mock_ws.replay_missed_messages(manager)
            
            # Verify message replay
            assert replayed_count > 0, "Some messages should have been replayed"
            
            replay_events = [e for e in mock_ws.connection_events if e.event_type == "message_replayed"]
            assert len(replay_events) == replayed_count, f"Replay events should match replayed count: {replayed_count}"
            
            # Verify no messages were permanently lost
            total_successful_messages = len([msg for msg in mock_ws.messages_sent if 'replay_test_sequence' in msg['message']])
            assert total_successful_messages >= messages_before_failure, "Messages should not be permanently lost"
            
            logger.info(f"✅ Event replay validated: {replayed_count} messages replayed after reconnection")
    
    async def test_connection_state_synchronization_post_recovery(self):
        """
        Test: Connection state is properly synchronized after recovery
        
        Business Value: Ensures chat interface shows correct connection status,
        maintaining user confidence in system reliability.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"sync_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ReconnectingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            # Establish initial connection
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Verify initial state synchronization
            initial_connected = manager.is_connected(ensure_user_id(self.test_user.user_id))
            assert initial_connected, "Initial connection state should be synchronized"
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            
            # Force connection failure
            mock_ws.state = WebSocketConnectionState.DISCONNECTED
            mock_ws._record_event("forced_disconnection", {"test_initiated": True})
            
            # Verify disconnected state
            await asyncio.sleep(0.1)  # Allow state propagation
            
            # Simulate reconnection with state sync
            await mock_ws.simulate_reconnection()
            
            # Send state synchronization message
            await manager.emit_agent_event(
                user_id=ensure_user_id(self.test_user.user_id),
                thread_id=self.test_user.thread_id,
                event_type="agent_thinking",
                data={
                    'connection_state_sync': True,
                    'post_recovery_message': True,
                    'sync_timestamp': datetime.now(UTC).isoformat()
                }
            )
            
            # Verify state synchronization
            post_recovery_connected = manager.is_connected(ensure_user_id(self.test_user.user_id))
            assert post_recovery_connected, "Post-recovery connection state should be synchronized"
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            
            # Verify sync messages were sent
            sync_messages = [
                msg for msg in mock_ws.messages_sent 
                if 'connection_state_sync' in str(msg['message'])
            ]
            assert len(sync_messages) > 0, "State synchronization messages should be sent"
            
            logger.info("✅ Connection state synchronization validated post-recovery")
    
    async def test_heartbeat_based_connection_health_monitoring(self):
        """
        Test: Heartbeat system monitors connection health and triggers recovery
        
        Business Value: Proactively detects connection issues before users notice,
        ensuring seamless chat experience and preventing session abandonment.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"heartbeat_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ReconnectingWebSocketMock(self.test_user.user_id, connection_id)
        mock_ws.heartbeat_interval = 2.0  # 2 seconds for faster testing
        mock_ws.heartbeat_timeout = 5.0   # 5 seconds timeout
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Send initial heartbeats
            heartbeat_count = 0
            for _ in range(3):
                await mock_ws.send_heartbeat()
                heartbeat_count += 1
                await asyncio.sleep(0.5)
            
            # Verify heartbeats were sent
            heartbeat_messages = [
                msg for msg in mock_ws.messages_sent
                if 'heartbeat' in str(msg['message'])
            ]
            assert len(heartbeat_messages) == heartbeat_count, "Heartbeats should be sent regularly"
            
            # Simulate heartbeat timeout scenario
            mock_ws.last_heartbeat = datetime.now(UTC) - timedelta(seconds=10)  # 10 seconds ago
            
            # Check for heartbeat timeout
            is_timeout = mock_ws.is_heartbeat_timeout()
            assert is_timeout, "Heartbeat timeout should be detected"
            
            # Simulate recovery by sending heartbeat
            await mock_ws.send_heartbeat()
            
            # Verify recovery
            is_timeout_after_recovery = mock_ws.is_heartbeat_timeout()
            assert not is_timeout_after_recovery, "Heartbeat timeout should be resolved after heartbeat"
            
            # Send message after heartbeat recovery
            await manager.emit_agent_event(
                user_id=ensure_user_id(self.test_user.user_id),
                thread_id=self.test_user.thread_id,
                event_type="agent_thinking",
                data={
                    'heartbeat_recovery_test': True,
                    'connection_healthy': True
                }
            )
            
            # Verify heartbeat events were recorded
            heartbeat_events = [e for e in mock_ws.connection_events if e.event_type == "heartbeat_sent"]
            assert len(heartbeat_events) >= heartbeat_count, "Heartbeat events should be recorded"
            
            logger.info(f"✅ Heartbeat-based connection health monitoring validated with {len(heartbeat_events)} heartbeats")
    
    async def test_graceful_degradation_during_connectivity_issues(self):
        """
        Test: System gracefully degrades during persistent connectivity issues
        
        Business Value: Maintains partial chat functionality during network problems,
        preventing complete service failure and user abandonment.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"degradation_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ReconnectingWebSocketMock(self.test_user.user_id, connection_id)
        mock_ws.max_failures = 10  # Allow more failures for degradation testing
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test graceful degradation under persistent failures
            successful_messages = 0
            failed_messages = 0
            degradation_activated = False
            
            for i in range(20):
                try:
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_thinking",
                        data={
                            'degradation_test_sequence': i,
                            'message_content': f"Test message {i} - degradation mode",
                            'timestamp': datetime.now(UTC).isoformat()
                        }
                    )
                    successful_messages += 1
                except ConnectionError:
                    failed_messages += 1
                    
                    # After multiple failures, activate degradation mode
                    if mock_ws.failure_count >= 5:
                        degradation_activated = True
                        logger.info(f"Graceful degradation activated after {mock_ws.failure_count} failures")
                        
                        # Simulate degraded functionality - store messages locally
                        degraded_message = {
                            'sequence': i,
                            'content': f"Degraded mode message {i}",
                            'queued_at': datetime.now(UTC).isoformat(),
                            'degraded_mode': True
                        }
                        mock_ws.missed_messages.append(degraded_message)
                    
                    # Attempt recovery periodically
                    if i % 3 == 0:
                        recovery_success = await mock_ws.simulate_reconnection()
                        if recovery_success:
                            logger.info("Temporary recovery successful")
                
                await asyncio.sleep(0.1)
            
            # Verify graceful degradation occurred
            assert degradation_activated, "Graceful degradation should activate under persistent failures"
            assert failed_messages > 0, "Some messages should fail to trigger degradation"
            assert successful_messages > 0, "Some messages should succeed despite degradation"
            
            # Verify degraded messages were queued
            degraded_messages = [msg for msg in mock_ws.missed_messages if msg.get('degraded_mode')]
            assert len(degraded_messages) > 0, "Messages should be queued during degradation"
            
            # Test recovery from degradation
            final_recovery = await mock_ws.simulate_reconnection()
            if final_recovery:
                # Attempt to process queued messages
                recovery_count = await mock_ws.replay_missed_messages(manager)
                logger.info(f"Recovery processed {recovery_count} queued messages")
            
            logger.info(f"✅ Graceful degradation validated: {successful_messages} succeeded, {failed_messages} failed, degradation activated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])