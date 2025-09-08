"""
Unit tests for WebSocketMessageHandler

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable WebSocket message processing
- Value Impact: Critical for chat functionality and real-time agent communication
- Strategic Impact: Core platform functionality for all user interactions

The WebSocketMessageHandler is MISSION CRITICAL for delivering business value through:
- Reliable message delivery and acknowledgment
- Prevention of duplicate message processing  
- Message queuing and state management
- WebSocket connection reliability

Coverage Target: 100% - This is a critical component for user experience
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from netra_backend.app.core.websocket_message_handler import WebSocketMessageHandler
from netra_backend.app.core.websocket_recovery_types import MessageState
from test_framework.base_integration_test import BaseIntegrationTest


class TestWebSocketMessageHandler(BaseIntegrationTest):
    """Comprehensive test suite for WebSocketMessageHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create fresh WebSocketMessageHandler instance for each test."""
        return WebSocketMessageHandler()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        return websocket
    
    @pytest.fixture
    def sample_message(self):
        """Create sample message for testing."""
        return {
            "type": "agent_message", 
            "content": "Test message",
            "user_id": "test_user_123",
            "timestamp": datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_message_state(self, sample_message):
        """Create sample MessageState for testing."""
        return MessageState(
            message_id="test_msg_123",
            content=sample_message,
            timestamp=datetime.now(),
            ack_required=True
        )

    # ============ INITIALIZATION TESTS ============

    @pytest.mark.unit
    def test_handler_initialization(self, handler):
        """Test WebSocketMessageHandler initializes correctly."""
        assert handler.pending_messages == []
        assert handler.sent_messages == {}
        assert handler.received_messages == set()
        assert handler.on_message is None
    
    @pytest.mark.unit 
    def test_handler_attributes_types(self, handler):
        """Test handler attributes have correct types."""
        assert isinstance(handler.pending_messages, list)
        assert isinstance(handler.sent_messages, dict)
        assert isinstance(handler.received_messages, set)

    # ============ MESSAGE STATE CREATION TESTS ============

    @pytest.mark.unit
    def test_create_message_state_basic(self, handler, sample_message):
        """Test creating basic message state."""
        message_id = "test_id_123"
        require_ack = True
        
        state = handler.create_message_state(sample_message, message_id, require_ack)
        
        assert state.message_id == message_id
        assert state.content == sample_message
        assert state.ack_required == require_ack
        assert isinstance(state.timestamp, datetime)
        assert not state.acknowledged  # Default value
    
    @pytest.mark.unit
    def test_create_message_state_no_ack_required(self, handler, sample_message):
        """Test creating message state without acknowledgment requirement."""
        message_id = "no_ack_123"
        require_ack = False
        
        state = handler.create_message_state(sample_message, message_id, require_ack)
        
        assert state.message_id == message_id
        assert state.ack_required == False
        assert not state.acknowledged
    
    @pytest.mark.unit
    def test_create_message_state_empty_message(self, handler):
        """Test creating message state with empty message."""
        empty_message = {}
        message_id = "empty_123"
        
        state = handler.create_message_state(empty_message, message_id, True)
        
        assert state.content == empty_message
        assert state.message_id == message_id

    # ============ MESSAGE QUEUING TESTS ============

    @pytest.mark.unit
    def test_queue_pending_message_success(self, handler, sample_message_state):
        """Test successfully queuing a pending message."""
        max_pending = 100
        
        result = handler.queue_pending_message(sample_message_state, max_pending)
        
        assert result == False  # Returns False when queued (not sent immediately)
        assert len(handler.pending_messages) == 1
        assert handler.pending_messages[0] == sample_message_state
    
    @pytest.mark.unit
    def test_queue_pending_message_queue_full(self, handler):
        """Test queuing message when queue is at capacity."""
        max_pending = 2
        
        # Fill queue to capacity
        for i in range(max_pending):
            msg_state = MessageState(
                message_id=f"msg_{i}",
                content={"content": f"message {i}"},
                timestamp=datetime.now(),
                ack_required=False
            )
            handler.queue_pending_message(msg_state, max_pending)
        
        # Try to add one more (should be dropped)
        overflow_state = MessageState(
            message_id="overflow",
            content={"content": "overflow message"},
            timestamp=datetime.now(),
            ack_required=False
        )
        
        result = handler.queue_pending_message(overflow_state, max_pending)
        
        assert result == False
        assert len(handler.pending_messages) == max_pending
        assert overflow_state not in handler.pending_messages
    
    @pytest.mark.unit
    def test_can_queue_message_with_space(self, handler):
        """Test _can_queue_message when there's space."""
        max_pending = 10
        
        # Add some messages
        for i in range(5):
            handler.pending_messages.append(Mock())
        
        assert handler._can_queue_message(max_pending) == True
    
    @pytest.mark.unit
    def test_can_queue_message_at_limit(self, handler):
        """Test _can_queue_message when at capacity."""
        max_pending = 5
        
        # Fill to capacity
        for i in range(max_pending):
            handler.pending_messages.append(Mock())
        
        assert handler._can_queue_message(max_pending) == False
    
    @pytest.mark.unit
    def test_add_to_queue(self, handler, sample_message_state):
        """Test _add_to_queue method."""
        result = handler._add_to_queue(sample_message_state)
        
        assert result == False  # Always returns False
        assert sample_message_state in handler.pending_messages
        assert len(handler.pending_messages) == 1
    
    @pytest.mark.unit
    def test_handle_queue_full(self, handler, sample_message_state):
        """Test _handle_queue_full method."""
        result = handler._handle_queue_full(sample_message_state)
        
        assert result == False
        assert sample_message_state not in handler.pending_messages

    # ============ MESSAGE SENDING TESTS ============

    @pytest.mark.unit
    async def test_execute_message_send_success(self, handler, mock_websocket, sample_message_state):
        """Test successful message sending."""
        result = await handler.execute_message_send(mock_websocket, sample_message_state)
        
        assert result == True
        mock_websocket.send.assert_called_once()
        
        # Verify JSON was sent
        sent_data = mock_websocket.send.call_args[0][0]
        parsed_data = json.loads(sent_data)
        assert parsed_data == sample_message_state.content
    
    @pytest.mark.unit
    async def test_execute_message_send_with_ack_tracking(self, handler, mock_websocket):
        """Test message sending with acknowledgment tracking."""
        message_state = MessageState(
            message_id="ack_test_123",
            content={"type": "test", "data": "value"},
            timestamp=datetime.now(),
            ack_required=True
        )
        
        result = await handler.execute_message_send(mock_websocket, message_state)
        
        assert result == True
        assert message_state.message_id in handler.sent_messages
        assert handler.sent_messages[message_state.message_id] == message_state
    
    @pytest.mark.unit
    async def test_execute_message_send_no_ack_tracking(self, handler, mock_websocket):
        """Test message sending without acknowledgment tracking."""
        message_state = MessageState(
            message_id="no_ack_123",
            content={"type": "test"},
            timestamp=datetime.now(),
            ack_required=False
        )
        
        result = await handler.execute_message_send(mock_websocket, message_state)
        
        assert result == True
        assert message_state.message_id not in handler.sent_messages
    
    @pytest.mark.unit
    async def test_execute_message_send_websocket_error(self, handler, sample_message_state):
        """Test handling WebSocket send errors."""
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = Exception("WebSocket connection closed")
        
        with pytest.raises(Exception, match="WebSocket connection closed"):
            await handler.execute_message_send(mock_websocket, sample_message_state)
    
    @pytest.mark.unit
    def test_track_sent_message_if_required_with_ack(self, handler):
        """Test tracking sent message when ack is required."""
        message_state = MessageState(
            message_id="track_test_123",
            content={"test": "data"},
            timestamp=datetime.now(),
            ack_required=True
        )
        
        handler._track_sent_message_if_required(message_state)
        
        assert message_state.message_id in handler.sent_messages
        assert handler.sent_messages[message_state.message_id] == message_state
    
    @pytest.mark.unit
    def test_track_sent_message_if_required_no_ack(self, handler):
        """Test not tracking sent message when ack not required."""
        message_state = MessageState(
            message_id="no_track_123",
            content={"test": "data"},
            timestamp=datetime.now(),
            ack_required=False
        )
        
        handler._track_sent_message_if_required(message_state)
        
        assert message_state.message_id not in handler.sent_messages

    # ============ MESSAGE RECEIVING TESTS ============

    @pytest.mark.unit
    async def test_process_received_message_ack(self, handler):
        """Test processing acknowledgment message."""
        # Set up a sent message to acknowledge
        message_id = "ack_msg_123"
        sent_state = MessageState(
            message_id=message_id,
            content={"test": "data"},
            timestamp=datetime.now(),
            ack_required=True
        )
        handler.sent_messages[message_id] = sent_state
        
        # Process acknowledgment
        ack_message = {"type": "ack", "id": message_id}
        await handler.process_received_message(ack_message, "conn_123")
        
        # Verify acknowledgment was handled
        assert message_id not in handler.sent_messages
        assert sent_state.acknowledged == True
    
    @pytest.mark.unit
    async def test_process_received_message_pong(self, handler):
        """Test processing pong message."""
        pong_message = {"type": "pong", "timestamp": datetime.now().isoformat()}
        
        # Should not raise any exceptions or call on_message
        await handler.process_received_message(pong_message, "conn_123")
        
        # Pong messages are handled by heartbeat manager, so nothing to assert
    
    @pytest.mark.unit
    async def test_process_received_message_regular(self, handler):
        """Test processing regular message."""
        message_id = "regular_123"
        regular_message = {
            "type": "user_message",
            "id": message_id,
            "content": "Hello world",
            "user_id": "user_456"
        }
        
        # Set up on_message handler
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler.process_received_message(regular_message, "conn_123")
        
        # Verify message was processed
        on_message_mock.assert_called_once_with("conn_123", regular_message)
        assert message_id in handler.received_messages
    
    @pytest.mark.unit
    async def test_process_received_message_duplicate(self, handler):
        """Test processing duplicate message."""
        message_id = "duplicate_123"
        regular_message = {
            "type": "user_message",
            "id": message_id,
            "content": "Duplicate message"
        }
        
        # Add message ID to received messages
        handler.received_messages.add(message_id)
        
        # Set up on_message handler
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler.process_received_message(regular_message, "conn_123")
        
        # Verify duplicate was ignored
        on_message_mock.assert_not_called()
    
    @pytest.mark.unit
    async def test_process_received_message_no_id(self, handler):
        """Test processing message without ID."""
        regular_message = {
            "type": "user_message",
            "content": "No ID message"
        }
        
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler.process_received_message(regular_message, "conn_123")
        
        # Should still process message even without ID
        on_message_mock.assert_called_once_with("conn_123", regular_message)
    
    @pytest.mark.unit 
    def test_is_ack_message_valid(self, handler):
        """Test identifying valid acknowledgment messages."""
        assert handler._is_ack_message("ack", "msg_123") == True
        assert handler._is_ack_message("ack", None) == False
        assert handler._is_ack_message("message", "msg_123") == False
        assert handler._is_ack_message("", "msg_123") == False
    
    @pytest.mark.unit
    def test_is_pong_message(self, handler):
        """Test identifying pong messages."""
        assert handler._is_pong_message("pong") == True
        assert handler._is_pong_message("ping") == False
        assert handler._is_pong_message("message") == False
        assert handler._is_pong_message("") == False
    
    @pytest.mark.unit
    async def test_handle_regular_message_duplicate(self, handler):
        """Test handling duplicate regular message."""
        message_id = "dup_regular_123"
        message = {"type": "test", "id": message_id}
        
        # Add to received messages to simulate duplicate
        handler.received_messages.add(message_id)
        
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler._handle_regular_message(message, message_id, "conn_123")
        
        # Should be ignored
        on_message_mock.assert_not_called()
    
    @pytest.mark.unit
    async def test_handle_regular_message_new(self, handler):
        """Test handling new regular message."""
        message_id = "new_regular_123"
        message = {"type": "test", "id": message_id, "data": "value"}
        
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler._handle_regular_message(message, message_id, "conn_123")
        
        # Should process message
        on_message_mock.assert_called_once_with("conn_123", message)
        assert message_id in handler.received_messages
    
    @pytest.mark.unit
    async def test_handle_regular_message_no_handler(self, handler):
        """Test handling regular message with no on_message handler."""
        message_id = "no_handler_123"
        message = {"type": "test", "id": message_id}
        
        # No on_message handler set
        await handler._handle_regular_message(message, message_id, "conn_123")
        
        # Should record message but not call handler
        assert message_id in handler.received_messages

    # ============ DUPLICATE DETECTION TESTS ============

    @pytest.mark.unit
    def test_is_duplicate_message_new(self, handler):
        """Test detecting new message (not duplicate)."""
        message_id = "new_msg_123"
        
        assert handler._is_duplicate_message(message_id) == False
    
    @pytest.mark.unit
    def test_is_duplicate_message_duplicate(self, handler):
        """Test detecting duplicate message."""
        message_id = "duplicate_msg_123"
        handler.received_messages.add(message_id)
        
        assert handler._is_duplicate_message(message_id) == True
    
    @pytest.mark.unit
    def test_is_duplicate_message_none_id(self, handler):
        """Test duplicate detection with None message ID."""
        assert handler._is_duplicate_message(None) == False
        assert handler._is_duplicate_message("") == False
    
    @pytest.mark.unit
    def test_record_received_message_normal(self, handler):
        """Test recording received message ID."""
        message_id = "record_test_123"
        
        handler._record_received_message(message_id)
        
        assert message_id in handler.received_messages
    
    @pytest.mark.unit
    def test_record_received_message_none(self, handler):
        """Test recording None message ID."""
        handler._record_received_message(None)
        handler._record_received_message("")
        
        # Should not add None or empty string
        assert None not in handler.received_messages
        assert "" not in handler.received_messages
    
    @pytest.mark.unit
    def test_record_received_message_cleanup_large_set(self, handler):
        """Test cleanup when received messages set gets too large."""
        # Add messages to trigger cleanup threshold
        for i in range(10001):  # Over the 10000 limit
            handler.received_messages.add(f"msg_{i}")
        
        original_length = len(handler.received_messages)
        assert original_length > 10000
        
        # Add one more to trigger cleanup
        handler._record_received_message("trigger_cleanup")
        
        # Should have reduced to approximately 5000 messages
        # The cleanup logic converts set to list and takes last 5000
        assert len(handler.received_messages) <= 5001
        assert len(handler.received_messages) < original_length  # Cleanup occurred

    # ============ ACKNOWLEDGMENT HANDLING TESTS ============

    @pytest.mark.unit
    def test_handle_acknowledgment_existing(self, handler):
        """Test handling acknowledgment for existing message."""
        message_id = "ack_existing_123"
        message_state = MessageState(
            message_id=message_id,
            content={"test": "data"},
            timestamp=datetime.now(),
            ack_required=True
        )
        handler.sent_messages[message_id] = message_state
        
        handler.handle_acknowledgment(message_id)
        
        assert message_state.acknowledged == True
        assert message_id not in handler.sent_messages
    
    @pytest.mark.unit
    def test_handle_acknowledgment_nonexistent(self, handler):
        """Test handling acknowledgment for non-existent message."""
        message_id = "nonexistent_123"
        
        # Should not raise any exceptions
        handler.handle_acknowledgment(message_id)
        
        assert message_id not in handler.sent_messages
    
    @pytest.mark.unit
    async def test_send_acknowledgment(self, handler, mock_websocket):
        """Test sending acknowledgment message."""
        message_id = "send_ack_123"
        
        await handler.send_acknowledgment(mock_websocket, message_id)
        
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "ack"
        assert sent_data["id"] == message_id
        assert "timestamp" in sent_data
    
    @pytest.mark.unit
    async def test_send_acknowledgment_websocket_error(self, handler):
        """Test sending acknowledgment when WebSocket fails."""
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = Exception("Connection closed")
        
        # Should not raise exception (error is logged and ignored)
        await handler.send_acknowledgment(mock_websocket, "test_id")
    
    @pytest.mark.unit
    def test_create_ack_message(self, handler):
        """Test creating acknowledgment message."""
        message_id = "create_ack_123"
        
        ack_msg = handler._create_ack_message(message_id)
        
        assert ack_msg["type"] == "ack"
        assert ack_msg["id"] == message_id
        assert "timestamp" in ack_msg
        assert isinstance(ack_msg["timestamp"], str)
    
    @pytest.mark.unit
    async def test_send_ack_message_success(self, handler, mock_websocket):
        """Test _send_ack_message success."""
        ack_message = {"type": "ack", "id": "test", "timestamp": "2023-01-01T00:00:00"}
        
        await handler._send_ack_message(mock_websocket, ack_message)
        
        mock_websocket.send.assert_called_once_with(json.dumps(ack_message))
    
    @pytest.mark.unit
    async def test_send_ack_message_failure(self, handler):
        """Test _send_ack_message failure handling."""
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = Exception("Send failed")
        ack_message = {"type": "ack", "id": "test"}
        
        # Should not raise exception
        await handler._send_ack_message(mock_websocket, ack_message)

    # ============ UTILITY METHODS TESTS ============

    @pytest.mark.unit
    def test_generate_message_id(self, handler):
        """Test generating unique message IDs."""
        id1 = handler.generate_message_id()
        id2 = handler.generate_message_id()
        
        assert id1 != id2
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        # Should be valid UUIDs
        uuid.UUID(id1)
        uuid.UUID(id2)
    
    @pytest.mark.unit
    def test_get_pending_count(self, handler):
        """Test getting count of pending messages."""
        assert handler.get_pending_count() == 0
        
        # Add some pending messages
        for i in range(3):
            handler.pending_messages.append(Mock())
        
        assert handler.get_pending_count() == 3
    
    @pytest.mark.unit
    def test_get_unacked_count(self, handler):
        """Test getting count of unacknowledged messages."""
        assert handler.get_unacked_count() == 0
        
        # Add some sent messages
        for i in range(5):
            handler.sent_messages[f"msg_{i}"] = Mock()
        
        assert handler.get_unacked_count() == 5
    
    @pytest.mark.unit
    def test_clear_pending_messages(self, handler):
        """Test clearing pending messages."""
        # Add some pending messages
        for i in range(3):
            handler.pending_messages.append(Mock())
        
        assert len(handler.pending_messages) == 3
        
        handler.clear_pending_messages()
        
        assert len(handler.pending_messages) == 0
        assert handler.pending_messages == []
    
    @pytest.mark.unit
    def test_get_pending_messages_copy(self, handler, sample_message_state):
        """Test getting copy of pending messages."""
        handler.pending_messages.append(sample_message_state)
        
        copy = handler.get_pending_messages_copy()
        
        assert copy == handler.pending_messages
        assert copy is not handler.pending_messages  # Should be a copy
        
        # Modify copy shouldn't affect original
        copy.append(Mock())
        assert len(handler.pending_messages) == 1
        assert len(copy) == 2

    # ============ EDGE CASES AND ERROR SCENARIOS ============

    @pytest.mark.unit
    async def test_process_malformed_message(self, handler):
        """Test processing malformed message."""
        malformed_message = "not a dict"
        
        with pytest.raises(AttributeError):
            await handler.process_received_message(malformed_message, "conn_123")
    
    @pytest.mark.unit
    async def test_process_message_missing_type(self, handler):
        """Test processing message without type field."""
        message = {"id": "no_type_123", "content": "test"}
        
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        await handler.process_received_message(message, "conn_123")
        
        # Should still process as regular message
        on_message_mock.assert_called_once()
    
    @pytest.mark.unit
    def test_multiple_handlers_independence(self):
        """Test that multiple handler instances don't share state."""
        handler1 = WebSocketMessageHandler()
        handler2 = WebSocketMessageHandler()
        
        # Add data to first handler
        handler1.pending_messages.append(Mock())
        handler1.sent_messages["test"] = Mock()
        handler1.received_messages.add("test")
        
        # Second handler should be empty
        assert len(handler2.pending_messages) == 0
        assert len(handler2.sent_messages) == 0
        assert len(handler2.received_messages) == 0
    
    @pytest.mark.unit
    async def test_concurrent_message_processing(self, handler):
        """Test concurrent message processing doesn't cause issues."""
        messages = [
            {"type": "message", "id": f"concurrent_{i}", "data": f"message_{i}"}
            for i in range(10)
        ]
        
        on_message_mock = AsyncMock()
        handler.on_message = on_message_mock
        
        # Process messages concurrently
        tasks = [
            handler.process_received_message(msg, f"conn_{i}")
            for i, msg in enumerate(messages)
        ]
        
        await asyncio.gather(*tasks)
        
        # All messages should be processed
        assert on_message_mock.call_count == 10
        assert len(handler.received_messages) == 10
    
    @pytest.mark.unit
    def test_message_state_modification_after_queuing(self, handler):
        """Test that modifying MessageState after queuing doesn't affect handler."""
        message_state = MessageState(
            message_id="modify_test_123",
            content={"original": "data"},
            timestamp=datetime.now(),
            ack_required=True
        )
        
        handler.queue_pending_message(message_state, 100)
        
        # Modify the original state
        message_state.content["modified"] = "new_data"
        message_state.acknowledged = True
        
        # Handler should still have reference to same object (Python behavior)
        queued_state = handler.pending_messages[0]
        assert queued_state.content["modified"] == "new_data"
        assert queued_state.acknowledged == True
    
    @pytest.mark.unit
    async def test_send_message_with_complex_content(self, handler, mock_websocket):
        """Test sending message with complex nested content."""
        complex_content = {
            "type": "complex_message",
            "nested": {
                "arrays": [1, 2, 3, {"inner": "value"}],
                "boolean": True,
                "null_field": None
            },
            "unicode": "测试数据 🚀",
            "timestamp": datetime.now().isoformat()
        }
        
        message_state = MessageState(
            message_id="complex_123",
            content=complex_content,
            timestamp=datetime.now(),
            ack_required=False
        )
        
        result = await handler.execute_message_send(mock_websocket, message_state)
        
        assert result == True
        sent_json = mock_websocket.send.call_args[0][0]
        parsed_back = json.loads(sent_json)
        assert parsed_back == complex_content
    
    @pytest.mark.unit
    def test_received_messages_memory_management(self, handler):
        """Test that received messages memory is managed properly."""
        # Add exactly 10000 messages (at the threshold)
        for i in range(10000):
            handler.received_messages.add(f"msg_{i:06d}")
        
        assert len(handler.received_messages) == 10000
        
        # Add one more to trigger cleanup
        handler._record_received_message("trigger_cleanup")
        
        # Should be reduced to approximately 5000 messages + the new one
        assert len(handler.received_messages) <= 5001
        # The cleanup logic takes the last 5000 items from the list conversion
        # Since sets are unordered, we can't predict which specific items remain
        # Just verify the cleanup occurred
        assert len(handler.received_messages) <= 5001

    # ============ INTEGRATION-LIKE TESTS (Still Unit Tests) ============

    @pytest.mark.unit
    async def test_full_message_lifecycle(self, handler, mock_websocket):
        """Test complete message lifecycle: create, queue, send, acknowledge."""
        # 1. Create message state
        message = {"type": "test", "content": "lifecycle test"}
        message_id = "lifecycle_123" 
        message_state = handler.create_message_state(message, message_id, True)
        
        # 2. Queue message (simulating WebSocket not ready)
        result = handler.queue_pending_message(message_state, 100)
        assert result == False  # Queued, not sent
        assert len(handler.pending_messages) == 1
        
        # 3. Send queued message  
        queued_msg = handler.pending_messages[0]
        send_result = await handler.execute_message_send(mock_websocket, queued_msg)
        assert send_result == True
        assert message_id in handler.sent_messages  # Tracked for ack
        
        # 4. Receive acknowledgment
        ack_message = {"type": "ack", "id": message_id}
        await handler.process_received_message(ack_message, "conn_123")
        
        # 5. Verify lifecycle completion
        # Message should be removed from sent_messages after acknowledgment
        assert message_id not in handler.sent_messages  # Removed after ack
    
    @pytest.mark.unit 
    async def test_message_handler_with_callback(self, handler):
        """Test message handler with callback function."""
        processed_messages = []
        
        async def message_callback(connection_id: str, message: Dict[str, Any]):
            processed_messages.append((connection_id, message))
        
        handler.on_message = message_callback
        
        # Process several messages
        messages = [
            {"type": "msg1", "id": "id1", "data": "first"},
            {"type": "msg2", "id": "id2", "data": "second"},
            {"type": "msg3", "id": "id3", "data": "third"}
        ]
        
        for i, msg in enumerate(messages):
            await handler.process_received_message(msg, f"conn_{i}")
        
        # Verify all messages were processed through callback
        assert len(processed_messages) == 3
        for i in range(3):
            conn_id, msg = processed_messages[i]
            assert conn_id == f"conn_{i}"
            assert msg["data"] == messages[i]["data"]
    
    @pytest.mark.unit
    async def test_mixed_message_types_processing(self, handler, mock_websocket):
        """Test processing mixed message types in sequence."""
        # Set up tracking
        processed_regular = []
        
        async def message_callback(conn, msg):
            processed_regular.append(msg)
        
        handler.on_message = message_callback
        
        # Set up a message to acknowledge
        ack_msg_id = "to_acknowledge"
        sent_state = MessageState(
            message_id=ack_msg_id,
            content={"test": "data"}, 
            timestamp=datetime.now(),
            ack_required=True
        )
        handler.sent_messages[ack_msg_id] = sent_state
        
        # Process mixed message types
        messages = [
            {"type": "user_message", "id": "reg1", "content": "regular message"},
            {"type": "pong", "timestamp": "2023-01-01"},  # Should be ignored
            {"type": "ack", "id": ack_msg_id},  # Should trigger acknowledgment
            {"type": "user_message", "id": "reg2", "content": "another regular"},
            {"type": "ack", "id": "nonexistent"},  # Should be ignored safely
        ]
        
        for msg in messages:
            await handler.process_received_message(msg, "test_conn")
        
        # Verify outcomes
        assert len(processed_regular) == 2  # Only regular messages processed
        assert sent_state.acknowledged == True  # Ack was handled
        assert ack_msg_id not in handler.sent_messages  # Removed after ack
        
        # Verify message IDs were recorded
        assert "reg1" in handler.received_messages
        assert "reg2" in handler.received_messages

    # ============ PERFORMANCE AND STRESS TESTS ============

    @pytest.mark.unit
    def test_large_message_content(self, handler, mock_websocket):
        """Test handling large message content."""
        # Create large content (but not too large for unit test)
        large_content = {
            "type": "large_message",
            "data": "x" * 10000,  # 10KB string
            "metadata": {f"field_{i}": f"value_{i}" for i in range(100)}
        }
        
        message_state = handler.create_message_state(
            large_content, "large_123", False
        )
        
        # Should handle without issues
        assert message_state.content == large_content
        assert message_state.message_id == "large_123"
    
    @pytest.mark.unit
    def test_many_pending_messages(self, handler):
        """Test handling many pending messages efficiently."""
        max_pending = 1000
        
        # Add many messages
        for i in range(max_pending):
            msg_state = MessageState(
                message_id=f"batch_msg_{i}",
                content={"index": i, "data": f"message_{i}"},
                timestamp=datetime.now(),
                ack_required=(i % 2 == 0)  # Every other message needs ack
            )
            result = handler.queue_pending_message(msg_state, max_pending)
            assert result == False  # All should be queued
        
        # Verify all were queued
        assert len(handler.pending_messages) == max_pending
        assert handler.get_pending_count() == max_pending
        
        # Try adding one more (should be dropped)
        overflow_state = MessageState(
            message_id="overflow",
            content={"overflow": True},
            timestamp=datetime.now(),
            ack_required=False
        )
        result = handler.queue_pending_message(overflow_state, max_pending)
        assert result == False
        assert len(handler.pending_messages) == max_pending  # No change