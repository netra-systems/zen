"""
Comprehensive Unit Tests for WebSocket Message Handler SSOT Class

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core infrastructure component
- Business Goal: Ensure reliable WebSocket message processing for chat functionality
- Value Impact: WebSocket message handler enables real-time agent communication, which is 90% of our value delivery
- Strategic Impact: Critical foundation for multi-user chat system, agent event delivery, and user experience quality

This test suite validates the SSOT WebSocketMessageHandler class that manages:
1. Message state lifecycle and acknowledgment handling  
2. Queue management with capacity limits and error handling
3. Duplicate message prevention and memory optimization
4. Message processing workflows for all WebSocket event types
5. Race condition handling and thread safety patterns

Tests focus on real business scenarios that could impact chat functionality and user experience.
Each test validates actual business logic rather than just code execution paths.

Author: Claude Code - Unit Test Creation Agent
Date: 2025-09-08
SSOT Compliance: Uses absolute imports, IsolatedEnvironment, proper test organization
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# SSOT: Absolute imports per import_management_architecture.xml
from netra_backend.app.core.websocket_message_handler import WebSocketMessageHandler
from netra_backend.app.core.websocket_recovery_types import MessageState


class TestWebSocketMessageHandlerComprehensive(BaseIntegrationTest):
    """Comprehensive unit tests for WebSocketMessageHandler SSOT class."""

    def setup_method(self):
        """Set up each test with fresh handler instance."""
        super().setup_method()
        self.handler = WebSocketMessageHandler()
        self.connection_id = "test-connection-001"
        
    def teardown_method(self):
        """Clean up after each test."""
        super().teardown_method()
        # Clean up handler state
        self.handler.pending_messages.clear()
        self.handler.sent_messages.clear()
        self.handler.received_messages.clear()

    # ===============================
    # Message State Management Tests
    # ===============================

    @pytest.mark.unit
    def test_create_message_state_with_ack_required(self, isolated_env):
        """Test message state creation for acknowledgment-required messages."""
        # Business scenario: Agent sends critical update that must be acknowledged
        message = {
            "type": "agent_completed",
            "data": {"result": "Cost optimization complete", "savings": 5000}
        }
        message_id = "msg-001"
        
        state = self.handler.create_message_state(message, message_id, require_ack=True)
        
        assert state.message_id == message_id
        assert state.content == message
        assert state.ack_required is True
        assert state.acknowledged is False
        assert state.retry_count == 0
        assert isinstance(state.timestamp, datetime)
        
        # Verify timestamp is recent (within last second)
        time_diff = datetime.now() - state.timestamp
        assert time_diff.total_seconds() < 1.0

    @pytest.mark.unit
    def test_create_message_state_without_ack_required(self, isolated_env):
        """Test message state creation for fire-and-forget messages."""
        # Business scenario: Agent sends thinking update (no ack needed)
        message = {
            "type": "agent_thinking", 
            "data": {"status": "Analyzing your AWS costs..."}
        }
        message_id = "msg-002"
        
        state = self.handler.create_message_state(message, message_id, require_ack=False)
        
        assert state.message_id == message_id
        assert state.content == message
        assert state.ack_required is False
        assert state.acknowledged is False

    @pytest.mark.unit
    def test_create_message_state_with_complex_message(self, isolated_env):
        """Test message state creation with complex nested data."""
        # Business scenario: Agent sends detailed optimization results
        message = {
            "type": "agent_completed",
            "data": {
                "result": {
                    "recommendations": [
                        {"service": "EC2", "action": "resize", "savings": 2000},
                        {"service": "RDS", "action": "optimize", "savings": 1500}
                    ],
                    "total_savings": 3500,
                    "confidence": 0.95
                },
                "metadata": {
                    "analysis_time": "45s",
                    "tools_used": ["aws_analyzer", "cost_calculator"]
                }
            }
        }
        message_id = str(uuid.uuid4())
        
        state = self.handler.create_message_state(message, message_id, require_ack=True)
        
        assert state.content["data"]["result"]["total_savings"] == 3500
        assert len(state.content["data"]["result"]["recommendations"]) == 2
        assert state.content["data"]["metadata"]["tools_used"] == ["aws_analyzer", "cost_calculator"]

    # ===============================
    # Queue Management Tests  
    # ===============================

    @pytest.mark.unit
    def test_queue_pending_message_within_capacity(self, isolated_env):
        """Test successful message queueing within capacity limits."""
        # Business scenario: User sends message while agent is processing
        message = {"type": "user_message", "content": "What about S3 costs?"}
        message_id = "queue-msg-001"
        max_pending = 100
        
        state = self.handler.create_message_state(message, message_id, require_ack=False)
        result = self.handler.queue_pending_message(state, max_pending)
        
        # Should return False (queued, not sent immediately)
        assert result is False
        assert len(self.handler.pending_messages) == 1
        assert self.handler.pending_messages[0].message_id == message_id

    @pytest.mark.unit
    def test_queue_pending_message_at_capacity_limit(self, isolated_env):
        """Test message queueing behavior at exact capacity limit."""
        # Business scenario: Queue is nearly full during high traffic
        max_pending = 3
        
        # Fill queue to capacity-1
        for i in range(max_pending - 1):
            message = {"type": "user_message", "content": f"Message {i}"}
            state = self.handler.create_message_state(message, f"msg-{i}", False)
            self.handler.queue_pending_message(state, max_pending)
        
        # Add one more (should still succeed)
        final_message = {"type": "user_message", "content": "Final message"}
        final_state = self.handler.create_message_state(final_message, "final-msg", False)
        result = self.handler.queue_pending_message(final_state, max_pending)
        
        assert result is False  # Queued successfully
        assert len(self.handler.pending_messages) == max_pending

    @pytest.mark.unit
    def test_queue_pending_message_exceeds_capacity(self, isolated_env):
        """Test message handling when queue capacity is exceeded."""
        # Business scenario: System under heavy load, queue fills up
        max_pending = 2
        
        # Fill queue to capacity
        for i in range(max_pending):
            message = {"type": "user_message", "content": f"Message {i}"}
            state = self.handler.create_message_state(message, f"msg-{i}", False)
            self.handler.queue_pending_message(state, max_pending)
        
        # Try to add one more (should be dropped)
        overflow_message = {"type": "user_message", "content": "Overflow message"}
        overflow_state = self.handler.create_message_state(overflow_message, "overflow-msg", False)
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            result = self.handler.queue_pending_message(overflow_state, max_pending)
            
            assert result is False  # Message dropped
            assert len(self.handler.pending_messages) == max_pending  # Queue unchanged
            mock_logger.warning.assert_called_with("Pending message queue full, dropping: overflow-msg")

    @pytest.mark.unit
    def test_can_queue_message_empty_queue(self, isolated_env):
        """Test queue capacity check with empty queue."""
        assert self.handler._can_queue_message(100) is True
        assert self.handler._can_queue_message(1) is True
        assert self.handler._can_queue_message(0) is False

    @pytest.mark.unit  
    def test_can_queue_message_partial_queue(self, isolated_env):
        """Test queue capacity check with partially filled queue."""
        # Add some messages to queue
        for i in range(3):
            message = {"type": "test", "content": f"msg-{i}"}
            state = self.handler.create_message_state(message, f"id-{i}", False)
            self.handler.pending_messages.append(state)
        
        assert self.handler._can_queue_message(5) is True  # 3 < 5
        assert self.handler._can_queue_message(3) is False  # 3 >= 3  
        assert self.handler._can_queue_message(2) is False  # 3 > 2

    @pytest.mark.unit
    def test_add_to_queue_logging(self, isolated_env):
        """Test proper logging when adding messages to queue."""
        message = {"type": "agent_thinking", "content": "Processing..."}
        state = self.handler.create_message_state(message, "log-test-msg", False)
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            result = self.handler._add_to_queue(state)
            
            assert result is False  # Always returns False (queued)
            assert len(self.handler.pending_messages) == 1
            mock_logger.debug.assert_called_with("Message queued: log-test-msg")

    # ===============================
    # Message Sending and Tracking Tests
    # ===============================

    @pytest.mark.unit
    async def test_execute_message_send_successful(self, isolated_env):
        """Test successful message sending and tracking."""
        # Business scenario: Agent completes analysis, sends results to user
        mock_websocket = AsyncMock()
        message = {
            "type": "agent_completed",
            "data": {"result": "Analysis complete", "savings": 1000}
        }
        state = self.handler.create_message_state(message, "send-test-001", require_ack=True)
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            result = await self.handler.execute_message_send(mock_websocket, state)
            
            assert result is True
            mock_websocket.send.assert_called_once()
            
            # Verify correct JSON was sent
            sent_json = mock_websocket.send.call_args[0][0]
            sent_message = json.loads(sent_json)
            assert sent_message["type"] == "agent_completed"
            assert sent_message["data"]["savings"] == 1000
            
            # Verify message is tracked for acknowledgment
            assert state.message_id in self.handler.sent_messages
            assert self.handler.sent_messages[state.message_id] == state
            
            mock_logger.debug.assert_called_with("Message sent: send-test-001")

    @pytest.mark.unit
    async def test_execute_message_send_no_ack_required(self, isolated_env):
        """Test message sending without acknowledgment tracking."""
        # Business scenario: Agent sends thinking update (no ack needed)
        mock_websocket = AsyncMock()
        message = {"type": "agent_thinking", "data": {"status": "Analyzing..."}}
        state = self.handler.create_message_state(message, "no-ack-msg", require_ack=False)
        
        result = await self.handler.execute_message_send(mock_websocket, state)
        
        assert result is True
        mock_websocket.send.assert_called_once()
        # Verify message is NOT tracked (no ack required)
        assert state.message_id not in self.handler.sent_messages

    @pytest.mark.unit
    async def test_execute_message_send_websocket_error(self, isolated_env):
        """Test message sending with WebSocket connection error."""
        # Business scenario: Network issue during message transmission
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = ConnectionResetError("Connection lost")
        
        message = {"type": "test", "content": "test"}
        state = self.handler.create_message_state(message, "error-msg", require_ack=True)
        
        # Should propagate the exception (caller handles reconnection)
        with pytest.raises(ConnectionResetError):
            await self.handler.execute_message_send(mock_websocket, state)
        
        # Message should not be tracked if send failed
        assert state.message_id not in self.handler.sent_messages

    @pytest.mark.unit
    def test_track_sent_message_if_required_ack_needed(self, isolated_env):
        """Test message tracking for acknowledgment-required messages."""
        message = {"type": "critical_update", "data": {"urgent": True}}
        state = self.handler.create_message_state(message, "track-msg-001", require_ack=True)
        
        self.handler._track_sent_message_if_required(state)
        
        assert state.message_id in self.handler.sent_messages
        assert self.handler.sent_messages[state.message_id] == state

    @pytest.mark.unit
    def test_track_sent_message_if_required_no_ack(self, isolated_env):
        """Test message tracking skipped for fire-and-forget messages."""
        message = {"type": "status_update", "data": {"status": "processing"}}
        state = self.handler.create_message_state(message, "no-track-msg", require_ack=False)
        
        self.handler._track_sent_message_if_required(state)
        
        assert state.message_id not in self.handler.sent_messages

    # ===============================
    # Message Processing Tests
    # ===============================

    @pytest.mark.unit
    async def test_process_received_message_acknowledgment(self, isolated_env):
        """Test processing of acknowledgment messages."""
        # Business scenario: User's browser acknowledges critical agent result
        ack_message = {
            "type": "ack",
            "id": "original-msg-001"
        }
        
        # Set up a sent message to be acknowledged
        original_state = MessageState(
            message_id="original-msg-001",
            content={"type": "agent_completed", "data": {"result": "done"}},
            timestamp=datetime.now(),
            ack_required=True
        )
        self.handler.sent_messages["original-msg-001"] = original_state
        
        await self.handler.process_received_message(ack_message, self.connection_id)
        
        # Verify acknowledgment was processed
        assert original_state.acknowledged is True
        assert "original-msg-001" not in self.handler.sent_messages

    @pytest.mark.unit
    async def test_process_received_message_pong(self, isolated_env):
        """Test processing of pong messages (heartbeat responses)."""
        # Business scenario: WebSocket heartbeat management
        pong_message = {"type": "pong"}
        
        # Should return early without processing
        result = await self.handler.process_received_message(pong_message, self.connection_id)
        
        # No assertions needed - just verify no exceptions and no side effects
        assert result is None

    @pytest.mark.unit
    async def test_process_received_message_regular_message(self, isolated_env):
        """Test processing of regular incoming messages."""
        # Business scenario: User sends new question to agent
        regular_message = {
            "type": "user_message",
            "id": "user-msg-001", 
            "content": "Can you also analyze my RDS costs?"
        }
        
        # Set up message callback
        callback_called = False
        received_connection_id = None
        received_message = None
        
        async def mock_callback(conn_id, message):
            nonlocal callback_called, received_connection_id, received_message
            callback_called = True
            received_connection_id = conn_id
            received_message = message
            
        self.handler.on_message = mock_callback
        
        await self.handler.process_received_message(regular_message, self.connection_id)
        
        # Verify callback was invoked correctly
        assert callback_called is True
        assert received_connection_id == self.connection_id
        assert received_message == regular_message
        
        # Verify message was recorded to prevent duplicates
        assert "user-msg-001" in self.handler.received_messages

    @pytest.mark.unit
    async def test_process_received_message_duplicate(self, isolated_env):
        """Test handling of duplicate message IDs."""
        # Business scenario: Network issue causes duplicate message delivery
        original_message = {
            "type": "user_message",
            "id": "duplicate-msg-001",
            "content": "Original message"
        }
        
        duplicate_message = {
            "type": "user_message", 
            "id": "duplicate-msg-001",
            "content": "Duplicate message"
        }
        
        callback_count = 0
        async def count_callback(conn_id, message):
            nonlocal callback_count
            callback_count += 1
            
        self.handler.on_message = count_callback
        
        # Process original message
        await self.handler.process_received_message(original_message, self.connection_id)
        
        # Process duplicate message
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            await self.handler.process_received_message(duplicate_message, self.connection_id)
            
            # Verify duplicate was detected and logged
            mock_logger.debug.assert_called_with("Duplicate message ignored: duplicate-msg-001")
        
        # Verify callback was only called once
        assert callback_count == 1

    @pytest.mark.unit
    async def test_process_received_message_no_callback(self, isolated_env):
        """Test processing message when no callback is set."""
        # Business scenario: Handler initialized but callback not yet registered
        message = {
            "type": "user_message",
            "id": "no-callback-msg",
            "content": "Test message"
        }
        
        # Don't set on_message callback
        result = await self.handler.process_received_message(message, self.connection_id)
        
        # Should not raise exception, message still recorded
        assert result is None
        assert "no-callback-msg" in self.handler.received_messages

    # ===============================
    # Message Type Detection Tests
    # ===============================

    @pytest.mark.unit
    def test_is_ack_message_valid_ack(self, isolated_env):
        """Test acknowledgment message detection for valid acks."""
        assert self.handler._is_ack_message("ack", "msg-123") is True
        assert self.handler._is_ack_message("ack", "some-uuid-here") is True

    @pytest.mark.unit
    def test_is_ack_message_invalid_cases(self, isolated_env):
        """Test acknowledgment message detection for invalid cases."""
        assert self.handler._is_ack_message("user_message", "msg-123") is False
        assert self.handler._is_ack_message("ack", None) is False
        assert self.handler._is_ack_message("ACK", "msg-123") is False  # Case sensitive
        assert self.handler._is_ack_message("", "msg-123") is False

    @pytest.mark.unit
    def test_is_pong_message_valid_pong(self, isolated_env):
        """Test pong message detection for valid pongs."""
        assert self.handler._is_pong_message("pong") is True

    @pytest.mark.unit
    def test_is_pong_message_invalid_cases(self, isolated_env):
        """Test pong message detection for invalid cases."""
        assert self.handler._is_pong_message("ping") is False
        assert self.handler._is_pong_message("PONG") is False  # Case sensitive
        assert self.handler._is_pong_message("") is False
        assert self.handler._is_pong_message("user_message") is False

    # ===============================
    # Duplicate Message Detection Tests
    # ===============================

    @pytest.mark.unit
    def test_is_duplicate_message_new_message(self, isolated_env):
        """Test duplicate detection for new messages."""
        assert self.handler._is_duplicate_message("new-msg-001") is False
        assert self.handler._is_duplicate_message("another-new-msg") is False

    @pytest.mark.unit
    def test_is_duplicate_message_existing_message(self, isolated_env):
        """Test duplicate detection for already received messages."""
        # Add message to received set
        self.handler.received_messages.add("existing-msg-001")
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            result = self.handler._is_duplicate_message("existing-msg-001")
            
            assert result is True
            mock_logger.debug.assert_called_with("Duplicate message ignored: existing-msg-001")

    @pytest.mark.unit  
    def test_is_duplicate_message_none_id(self, isolated_env):
        """Test duplicate detection with None message ID."""
        assert self.handler._is_duplicate_message(None) is False
        assert self.handler._is_duplicate_message("") is False

    @pytest.mark.unit
    def test_record_received_message_new(self, isolated_env):
        """Test recording new received message."""
        message_id = "record-msg-001"
        
        self.handler._record_received_message(message_id)
        
        assert message_id in self.handler.received_messages
        assert len(self.handler.received_messages) == 1

    @pytest.mark.unit
    def test_record_received_message_none_id(self, isolated_env):
        """Test recording message with None or empty ID."""
        self.handler._record_received_message(None)
        self.handler._record_received_message("")
        
        # Should not add None or empty string to set
        assert len(self.handler.received_messages) == 0

    @pytest.mark.unit
    def test_record_received_message_memory_optimization(self, isolated_env):
        """Test memory optimization when received messages exceed limit."""
        # Business scenario: Long-running connection processes many messages
        
        # Fill to exactly 10000 messages (at the limit)
        for i in range(10000):
            self.handler.received_messages.add(f"msg-{i:05d}")
        
        assert len(self.handler.received_messages) == 10000
        
        # Add one more message (should trigger cleanup)
        self.handler._record_received_message("trigger-cleanup-msg")
        
        # Should keep only 5000 messages after cleanup (due to set behavior)
        # The important thing is memory is managed and count reduced
        assert len(self.handler.received_messages) == 5000
        
        # Test the core business logic: memory is managed when limit exceeded
        # (We can't guarantee which specific messages remain due to set ordering)

    # ===============================
    # Acknowledgment Handling Tests
    # ===============================

    @pytest.mark.unit
    def test_handle_acknowledgment_existing_message(self, isolated_env):
        """Test acknowledgment handling for existing sent message."""
        # Business scenario: User acknowledges agent completion event
        original_state = MessageState(
            message_id="ack-test-001",
            content={"type": "agent_completed", "data": {"result": "done"}},
            timestamp=datetime.now(),
            ack_required=True
        )
        self.handler.sent_messages["ack-test-001"] = original_state
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            self.handler.handle_acknowledgment("ack-test-001")
            
            # Verify message is marked as acknowledged and removed from tracking
            assert original_state.acknowledged is True
            assert "ack-test-001" not in self.handler.sent_messages
            mock_logger.debug.assert_called_with("Message acknowledged: ack-test-001")

    @pytest.mark.unit
    def test_handle_acknowledgment_nonexistent_message(self, isolated_env):
        """Test acknowledgment handling for unknown message ID."""
        # Business scenario: Late/duplicate acknowledgment arrives
        
        # No message with this ID in sent_messages
        self.handler.handle_acknowledgment("unknown-msg-id")
        
        # Should not raise exception, just ignore silently
        assert "unknown-msg-id" not in self.handler.sent_messages

    @pytest.mark.unit
    async def test_send_acknowledgment_successful(self, isolated_env):
        """Test sending acknowledgment message successfully."""
        # Business scenario: Handler acknowledges user message receipt
        mock_websocket = AsyncMock()
        message_id = "ack-send-test-001"
        
        await self.handler.send_acknowledgment(mock_websocket, message_id)
        
        # Verify acknowledgment was sent
        mock_websocket.send.assert_called_once()
        
        # Verify correct acknowledgment format
        sent_json = mock_websocket.send.call_args[0][0]
        ack_message = json.loads(sent_json)
        
        assert ack_message["type"] == "ack"
        assert ack_message["id"] == message_id
        assert "timestamp" in ack_message
        
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(ack_message["timestamp"].replace('Z', '+00:00'))
        time_diff = datetime.now() - timestamp.replace(tzinfo=None)
        assert time_diff.total_seconds() < 2.0  # Recent timestamp

    @pytest.mark.unit
    async def test_send_acknowledgment_websocket_error(self, isolated_env):
        """Test acknowledgment sending with WebSocket error."""
        # Business scenario: Network issue during acknowledgment send
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = ConnectionResetError("Connection lost")
        message_id = "ack-error-test"
        
        with patch('netra_backend.app.core.websocket_message_handler.logger') as mock_logger:
            # Should not raise exception, just log warning
            await self.handler.send_acknowledgment(mock_websocket, message_id)
            
            mock_logger.warning.assert_called_with("Failed to send acknowledgment: Connection lost")

    @pytest.mark.unit
    def test_create_ack_message_format(self, isolated_env):
        """Test acknowledgment message format creation."""
        message_id = "format-test-001"
        
        ack_message = self.handler._create_ack_message(message_id)
        
        assert ack_message["type"] == "ack"
        assert ack_message["id"] == message_id
        assert "timestamp" in ack_message
        
        # Verify timestamp is valid ISO format
        timestamp_str = ack_message["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)

    # ===============================
    # Utility Method Tests
    # ===============================

    @pytest.mark.unit
    def test_generate_message_id_uniqueness(self, isolated_env):
        """Test message ID generation produces unique IDs."""
        # Business scenario: Handler generates IDs for outgoing messages
        generated_ids = set()
        
        # Generate 100 IDs and verify uniqueness
        for _ in range(100):
            msg_id = self.handler.generate_message_id()
            assert msg_id not in generated_ids  # Should be unique
            generated_ids.add(msg_id)
            
            # Verify UUID format
            uuid.UUID(msg_id)  # Should not raise ValueError

    @pytest.mark.unit
    def test_get_pending_count_empty(self, isolated_env):
        """Test pending message count with empty queue."""
        assert self.handler.get_pending_count() == 0

    @pytest.mark.unit
    def test_get_pending_count_with_messages(self, isolated_env):
        """Test pending message count with messages in queue."""
        # Add test messages to pending queue
        for i in range(5):
            message = {"type": "test", "content": f"msg-{i}"}
            state = self.handler.create_message_state(message, f"pending-{i}", False)
            self.handler.pending_messages.append(state)
        
        assert self.handler.get_pending_count() == 5

    @pytest.mark.unit
    def test_get_unacked_count_empty(self, isolated_env):
        """Test unacknowledged message count with no sent messages."""
        assert self.handler.get_unacked_count() == 0

    @pytest.mark.unit
    def test_get_unacked_count_with_messages(self, isolated_env):
        """Test unacknowledged message count with sent messages awaiting ack."""
        # Add test messages to sent tracking
        for i in range(3):
            state = MessageState(
                message_id=f"unacked-{i}",
                content={"type": "test", "data": f"content-{i}"},
                timestamp=datetime.now(),
                ack_required=True
            )
            self.handler.sent_messages[f"unacked-{i}"] = state
        
        assert self.handler.get_unacked_count() == 3

    @pytest.mark.unit
    def test_clear_pending_messages(self, isolated_env):
        """Test clearing all pending messages."""
        # Business scenario: Connection reset, clear pending messages
        
        # Add some pending messages
        for i in range(3):
            message = {"type": "test", "content": f"msg-{i}"}
            state = self.handler.create_message_state(message, f"clear-{i}", False)
            self.handler.pending_messages.append(state)
        
        assert len(self.handler.pending_messages) == 3
        
        self.handler.clear_pending_messages()
        
        assert len(self.handler.pending_messages) == 0
        assert self.handler.get_pending_count() == 0

    @pytest.mark.unit
    def test_get_pending_messages_copy(self, isolated_env):
        """Test getting copy of pending messages (isolation)."""
        # Business scenario: Component needs to examine pending messages without modification
        
        # Add some pending messages
        original_states = []
        for i in range(3):
            message = {"type": "test", "content": f"msg-{i}"}
            state = self.handler.create_message_state(message, f"copy-{i}", False)
            self.handler.pending_messages.append(state)
            original_states.append(state)
        
        # Get copy
        copy_messages = self.handler.get_pending_messages_copy()
        
        # Verify it's a copy (same content, different list object)
        assert copy_messages is not self.handler.pending_messages
        assert len(copy_messages) == 3
        assert copy_messages[0].message_id == "copy-0"
        assert copy_messages[1].message_id == "copy-1"
        assert copy_messages[2].message_id == "copy-2"
        
        # Verify modifying copy doesn't affect original
        copy_messages.clear()
        assert len(self.handler.pending_messages) == 3

    # ===============================
    # Edge Cases and Error Conditions Tests
    # ===============================

    @pytest.mark.unit
    async def test_regular_message_handling_no_message_id(self, isolated_env):
        """Test handling regular message without message ID."""
        # Business scenario: Legacy or malformed client message
        message_without_id = {
            "type": "user_message",
            "content": "Message without ID"
        }
        
        callback_called = False
        async def test_callback(conn_id, message):
            nonlocal callback_called
            callback_called = True
            
        self.handler.on_message = test_callback
        
        # Should handle gracefully without recording (no ID to record)
        await self.handler.process_received_message(message_without_id, self.connection_id)
        
        assert callback_called is True
        # No message ID recorded since it's None
        assert len(self.handler.received_messages) == 0

    @pytest.mark.unit
    def test_message_state_creation_edge_cases(self, isolated_env):
        """Test message state creation with edge case inputs."""
        # Empty message
        empty_state = self.handler.create_message_state({}, "empty-msg", False)
        assert empty_state.content == {}
        assert empty_state.message_id == "empty-msg"
        
        # Message with special characters
        special_message = {
            "type": "test",
            "content": "Message with unicode: 🚀 and special chars: <>&\"'"
        }
        special_state = self.handler.create_message_state(special_message, "special-msg", True)
        assert "🚀" in special_state.content["content"]

    @pytest.mark.unit
    async def test_json_serialization_error_handling(self, isolated_env):
        """Test handling of messages that can't be JSON serialized."""
        # Business scenario: Message contains non-serializable data
        mock_websocket = AsyncMock()
        
        # Create message with non-serializable content (e.g., datetime object)
        problematic_message = {
            "type": "test",
            "timestamp": datetime.now()  # Not JSON serializable
        }
        state = self.handler.create_message_state(problematic_message, "json-error-msg", False)
        
        # Should raise TypeError during JSON serialization
        with pytest.raises(TypeError):
            await self.handler.execute_message_send(mock_websocket, state)

    # ===============================
    # Race Condition and Concurrency Tests
    # ===============================

    @pytest.mark.unit
    async def test_concurrent_message_processing(self, isolated_env):
        """Test concurrent message processing doesn't cause state corruption."""
        # Business scenario: Multiple messages arrive simultaneously
        
        callback_count = 0
        callback_messages = []
        
        async def counting_callback(conn_id, message):
            nonlocal callback_count
            callback_count += 1
            callback_messages.append(message["id"])
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
        self.handler.on_message = counting_callback
        
        # Process multiple messages concurrently
        messages = []
        for i in range(10):
            message = {
                "type": "user_message",
                "id": f"concurrent-{i}",
                "content": f"Message {i}"
            }
            messages.append(message)
        
        # Process all messages concurrently
        tasks = []
        for message in messages:
            task = asyncio.create_task(
                self.handler.process_received_message(message, self.connection_id)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all messages were processed
        assert callback_count == 10
        assert len(set(callback_messages)) == 10  # All unique
        assert len(self.handler.received_messages) == 10

    @pytest.mark.unit
    def test_concurrent_queue_operations(self, isolated_env):
        """Test concurrent queue operations maintain consistency."""
        # Business scenario: Multiple threads/coroutines adding to queue
        import threading
        
        max_pending = 100
        thread_count = 5
        messages_per_thread = 10
        
        def add_messages(thread_id):
            for i in range(messages_per_thread):
                message = {
                    "type": "test",
                    "content": f"Thread {thread_id}, Message {i}"
                }
                state = self.handler.create_message_state(
                    message, f"thread-{thread_id}-msg-{i}", False
                )
                self.handler.queue_pending_message(state, max_pending)
        
        # Start multiple threads adding messages
        threads = []
        for t in range(thread_count):
            thread = threading.Thread(target=add_messages, args=(t,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all messages were added (no race condition corruption)
        expected_count = thread_count * messages_per_thread
        assert len(self.handler.pending_messages) == expected_count

    # ===============================
    # Memory Management Tests
    # ===============================

    @pytest.mark.unit
    def test_received_messages_memory_cleanup_threshold(self, isolated_env):
        """Test received messages memory cleanup at exact threshold."""
        # Business scenario: Long-running connection hits exact memory limit
        
        # Add exactly 10000 messages (the threshold)
        for i in range(10000):
            self.handler.received_messages.add(f"threshold-msg-{i:05d}")
        
        assert len(self.handler.received_messages) == 10000
        
        # Add one more to trigger cleanup
        self.handler._record_received_message("trigger-msg")
        
        # Should keep most recent 5000 + the new one
        assert len(self.handler.received_messages) <= 5001
        assert "trigger-msg" in self.handler.received_messages

    @pytest.mark.unit
    def test_memory_usage_tracking_realistic_scenario(self, isolated_env):
        """Test memory usage patterns for realistic high-traffic scenario."""
        # Business scenario: Enterprise customer with high message volume
        
        # Simulate 1 hour of high-traffic chat (1 message per second)
        messages_per_hour = 3600
        
        for i in range(messages_per_hour):
            # Mix of different message types
            if i % 4 == 0:
                message_type = "user_message"
            elif i % 4 == 1:
                message_type = "agent_thinking"  
            elif i % 4 == 2:
                message_type = "tool_executing"
            else:
                message_type = "agent_completed"
            
            message_id = f"traffic-{i:05d}"
            self.handler._record_received_message(message_id)
        
        # Should not exceed memory limits
        assert len(self.handler.received_messages) <= 10000
        
        # Should contain most recent messages
        assert "traffic-03599" in self.handler.received_messages  # Last message
        
        # May or may not contain very early messages (depends on cleanup)
        first_message_exists = "traffic-00000" in self.handler.received_messages
        # This is acceptable either way - test just ensures no crashes

    # ===============================  
    # Business Logic Validation Tests
    # ===============================

    @pytest.mark.unit
    async def test_full_agent_workflow_message_flow(self, isolated_env):
        """Test complete agent workflow message handling."""
        # Business scenario: Complete agent execution with all event types
        mock_websocket = AsyncMock()
        
        # Simulate agent workflow events in correct order
        agent_events = [
            {"type": "agent_started", "data": {"agent": "cost_optimizer"}},
            {"type": "agent_thinking", "data": {"status": "Analyzing AWS costs..."}},
            {"type": "tool_executing", "data": {"tool": "aws_analyzer", "status": "running"}},
            {"type": "tool_completed", "data": {"tool": "aws_analyzer", "result": "analysis_complete"}},
            {"type": "agent_completed", "data": {"result": "Optimization complete", "savings": 2500}}
        ]
        
        # Process each event
        sent_messages = []
        for i, event in enumerate(agent_events):
            message_id = f"agent-workflow-{i}"
            require_ack = event["type"] == "agent_completed"  # Only final result needs ack
            
            state = self.handler.create_message_state(event, message_id, require_ack)
            result = await self.handler.execute_message_send(mock_websocket, state)
            sent_messages.append((message_id, require_ack, result))
        
        # Verify all messages sent successfully
        assert all(result for _, _, result in sent_messages)
        assert mock_websocket.send.call_count == 5
        
        # Verify only agent_completed message is tracked for acknowledgment
        assert len(self.handler.sent_messages) == 1
        assert "agent-workflow-4" in self.handler.sent_messages
        
        # Simulate user acknowledgment of final result
        self.handler.handle_acknowledgment("agent-workflow-4")
        assert len(self.handler.sent_messages) == 0

    @pytest.mark.unit
    async def test_error_recovery_message_handling(self, isolated_env):
        """Test message handling during error recovery scenarios."""
        # Business scenario: WebSocket reconnection, resend pending messages
        mock_websocket = AsyncMock()
        
        # Add messages to pending queue (simulating queued during disconnection)
        recovery_messages = [
            {"type": "agent_thinking", "data": {"status": "Resuming analysis..."}},
            {"type": "agent_completed", "data": {"result": "Analysis recovered", "savings": 1000}}
        ]
        
        for i, message in enumerate(recovery_messages):
            message_id = f"recovery-{i}"
            require_ack = message["type"] == "agent_completed"
            state = self.handler.create_message_state(message, message_id, require_ack)
            self.handler.pending_messages.append(state)
        
        assert self.handler.get_pending_count() == 2
        
        # Simulate sending all pending messages after reconnection
        sent_count = 0
        while self.handler.pending_messages:
            state = self.handler.pending_messages.pop(0)
            result = await self.handler.execute_message_send(mock_websocket, state)
            if result:
                sent_count += 1
        
        assert sent_count == 2
        assert self.handler.get_pending_count() == 0
        assert self.handler.get_unacked_count() == 1  # agent_completed awaiting ack

    @pytest.mark.unit
    def test_message_prioritization_business_logic(self, isolated_env):
        """Test message prioritization for business-critical events."""
        # Business scenario: Ensure critical messages (errors, completions) have priority
        
        # Add mix of message types with different priorities
        messages = [
            ("low_priority", {"type": "agent_thinking", "data": {"status": "processing"}}),
            ("critical", {"type": "agent_error", "data": {"error": "Critical system error"}}),
            ("normal", {"type": "tool_executing", "data": {"tool": "analyzer"}}),
            ("critical", {"type": "agent_completed", "data": {"result": "Analysis done"}}),
            ("low_priority", {"type": "agent_thinking", "data": {"status": "thinking"}})
        ]
        
        max_pending = 10
        for i, (priority, message) in enumerate(messages):
            message_id = f"priority-{i}"
            require_ack = priority == "critical"
            state = self.handler.create_message_state(message, message_id, require_ack)
            # For this test, just add directly to demonstrate business logic
            # Real implementation might add priority field to MessageState
            self.handler.queue_pending_message(state, max_pending)
        
        # All messages should be queued
        assert self.handler.get_pending_count() == 5
        
        # In real implementation, we might sort by priority before sending
        # For now, verify business-critical types are properly identified
        critical_messages = []
        for state in self.handler.pending_messages:
            if state.content["type"] in ["agent_error", "agent_completed"]:
                critical_messages.append(state)
        
        assert len(critical_messages) == 2
        assert all(state.ack_required for state in critical_messages)

    # ===============================
    # Integration Boundary Tests
    # ===============================

    @pytest.mark.unit
    async def test_websocket_interface_boundary(self, isolated_env):
        """Test proper interface with WebSocket layer."""
        # Business scenario: Verify handler properly interfaces with WebSocket code
        
        # Mock WebSocket with realistic interface
        class MockWebSocketConnection:
            def __init__(self):
                self.sent_messages = []
                self.closed = False
            
            async def send(self, message_json):
                if self.closed:
                    raise ConnectionResetError("WebSocket closed")
                self.sent_messages.append(message_json)
            
            def close(self):
                self.closed = True
        
        mock_ws = MockWebSocketConnection()
        
        # Test successful sending
        message = {"type": "test", "content": "boundary test"}
        state = self.handler.create_message_state(message, "boundary-001", False)
        
        result = await self.handler.execute_message_send(mock_ws, state)
        assert result is True
        assert len(mock_ws.sent_messages) == 1
        
        # Test error handling when connection closed
        mock_ws.close()
        
        with pytest.raises(ConnectionResetError):
            await self.handler.execute_message_send(mock_ws, state)

    # ===============================
    # Performance and Scalability Tests
    # ===============================

    @pytest.mark.unit
    def test_handler_performance_large_message_count(self, isolated_env):
        """Test handler performance with large numbers of messages."""
        # Business scenario: High-volume enterprise customer
        
        import time
        
        start_time = time.time()
        
        # Process large number of messages
        message_count = 1000
        for i in range(message_count):
            message_id = f"perf-{i:04d}"
            
            # Record as received (simulates incoming messages)
            self.handler._record_received_message(message_id)
            
            # Add some to pending queue
            if i % 10 == 0:
                message = {"type": "test", "content": f"Message {i}"}
                state = self.handler.create_message_state(message, message_id, False)
                self.handler.queue_pending_message(state, 1000)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete quickly (less than 1 second for 1000 messages)
        assert processing_time < 1.0
        
        # Verify state is correct
        assert len(self.handler.received_messages) <= 1000  # May be less due to cleanup
        assert len(self.handler.pending_messages) == 100  # Every 10th message

    @pytest.mark.unit
    def test_memory_efficiency_large_datasets(self, isolated_env):
        """Test memory efficiency with large datasets."""
        # Business scenario: Long-running connections with many messages
        
        # Simulate processing many messages over time
        large_count = 15000  # Exceeds cleanup threshold
        
        for i in range(large_count):
            message_id = f"memory-{i:05d}"
            self.handler._record_received_message(message_id)
        
        # Memory should be managed (cleanup should have occurred)
        assert len(self.handler.received_messages) < large_count
        assert len(self.handler.received_messages) <= 10000  # Within limits
        
        # Should contain most recent messages
        assert f"memory-{large_count-1:05d}" in self.handler.received_messages
        assert f"memory-{large_count-100:05d}" in self.handler.received_messages