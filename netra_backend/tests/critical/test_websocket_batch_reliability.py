"""Critical Tests for WebSocket Batch Message Reliability.

Tests the mandatory patterns from SPEC/websocket_reliability.xml to ensure
zero message loss under all failure scenarios.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import time
from typing import List

import pytest

from netra_backend.app.websocket_core.batch_message_core import MessageBatcher
from netra_backend.app.websocket_core.types import (
    BatchConfig,
    BatchingStrategy,
    MessageState,
    PendingMessage,
)
from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.websocket_core.manager import WebSocketManager as ConnectionManager

class TestNetworkFailureZeroMessageLoss:
    """Test zero message loss during network failures."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock: Component isolation for controlled unit testing
        self.connection_manager = Mock(spec=ConnectionManager)
        self.config = BatchConfig(max_batch_size=10, max_wait_time=0.1)
        self.batcher = MessageBatcher(self.config, self.connection_manager)
        
        # Mock connection
        # Mock: Component isolation for controlled unit testing
        self.mock_connection = Mock(spec=ConnectionInfo)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        self.mock_connection.websocket = AsyncNone  # TODO: Use real service instance
        self.mock_connection.message_count = 0
        self.connection_manager.get_connection_by_id.return_value = self.mock_connection
        self.connection_manager.get_user_connections.return_value = [
            # Mock: Component isolation for controlled unit testing
            Mock(connection_id="conn1")
        ]
    
    @pytest.mark.asyncio
    async def test_network_failure_during_batch_send_zero_loss(self):
        """Test scenario from websocket_reliability.xml: 100 messages, network failure, zero loss."""
        message_count = 100
        test_messages = [{"id": i, "data": f"critical_message_{i}"} for i in range(message_count)]
        
        # Queue all messages
        for msg in test_messages:
            success = await self.batcher.queue_message("user1", msg)
            assert success is True
        
        # Verify all messages are queued
        assert "conn1" in self.batcher._pending_messages
        queued_messages = self.batcher._pending_messages["conn1"]
        assert len(queued_messages) == message_count
        
        # All should be in PENDING state initially
        assert all(msg.state == MessageState.PENDING for msg in queued_messages)
        
        # Simulate network failure during send
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock, side_effect=ConnectionError("Network timeout")):
            await self.batcher._flush_batch("conn1")
        
        # CRITICAL: Verify zero message loss
        remaining_messages = self.batcher._pending_messages["conn1"]
        assert len(remaining_messages) == message_count, "CRITICAL: Messages lost during network failure!"
        
        # All messages should be reverted to PENDING state for retry
        pending_count = sum(1 for msg in remaining_messages if msg.state == MessageState.PENDING)
        assert pending_count == message_count, "Messages not properly reverted to PENDING state"
        
        # Verify message content integrity
        remaining_ids = {msg.content["id"] for msg in remaining_messages}
        expected_ids = set(range(message_count))
        assert remaining_ids == expected_ids, "Message content corrupted during failure"
    
    @pytest.mark.asyncio
    async def test_connection_close_failure_zero_loss(self):
        """Test WebSocket close failure doesn't lose messages."""
        await self.batcher.queue_message("user1", {"critical": "data"})
        
        # Simulate WebSocket close() throwing exception
        self.mock_connection.websocket.send_json.side_effect = ConnectionResetError("Connection closed")
        
        with pytest.raises(ConnectionResetError):
            # This should fail but not lose messages
            # Mock: Component isolation for testing without external dependencies
            with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                       new_callable=AsyncMock, side_effect=ConnectionResetError("Connection closed")):
                await self.batcher._flush_batch("conn1")
        
        # Message should still be in queue
        messages = self.batcher._pending_messages["conn1"]
        assert len(messages) == 1
        assert messages[0].state == MessageState.PENDING
        assert messages[0].content["critical"] == "data"
    
    @pytest.mark.asyncio
    async def test_multiple_failure_cycles_preserve_messages(self):
        """Test multiple failure cycles don't accumulate message loss."""
        await self.batcher.queue_message("user1", {"persistent": "message"})
        
        # Simulate 5 consecutive failures
        for failure_cycle in range(5):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                       new_callable=AsyncMock, side_effect=Exception(f"Failure {failure_cycle}")):
                await self.batcher._flush_batch("conn1")
            
            # Message should persist through each failure
            messages = self.batcher._pending_messages["conn1"]
            assert len(messages) == 1, f"Message lost during failure cycle {failure_cycle}"
            assert messages[0].content["persistent"] == "message"
            assert messages[0].state == MessageState.PENDING
    
    @pytest.mark.asyncio
    async def test_successful_send_after_failures_removes_messages(self):
        """Test successful send after failures properly removes messages."""
        await self.batcher.queue_message("user1", {"test": "recovery"})
        
        # First attempt fails
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock, side_effect=Exception("First failure")):
            await self.batcher._flush_batch("conn1")
        
        # Verify message persists
        messages = self.batcher._pending_messages["conn1"]
        assert len(messages) == 1
        assert messages[0].state == MessageState.PENDING
        
        # Second attempt succeeds
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock) as mock_send:
            await self.batcher._flush_batch("conn1")
        
        # Message should be removed after successful send
        messages = self.batcher._pending_messages.get("conn1", [])
        sent_messages = [msg for msg in messages if msg.state == MessageState.SENT]
        assert len(sent_messages) == 0, "SENT messages not properly cleaned up"

class TestTransactionalStateManagement:
    """Test atomic state management during failures."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock: Component isolation for controlled unit testing
        self.connection_manager = Mock(spec=ConnectionManager)
        self.config = BatchConfig(max_batch_size=5, max_wait_time=0.1)
        self.batcher = MessageBatcher(self.config, self.connection_manager)
        
        # Mock connection
        # Mock: Component isolation for controlled unit testing
        self.mock_connection = Mock(spec=ConnectionInfo)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        self.mock_connection.websocket = AsyncNone  # TODO: Use real service instance
        self.mock_connection.message_count = 0
        self.connection_manager.get_connection_by_id.return_value = self.mock_connection
        self.connection_manager.get_user_connections.return_value = [
            # Mock: Component isolation for controlled unit testing
            Mock(connection_id="conn1")
        ]
    
    @pytest.mark.asyncio
    async def test_atomic_state_transitions(self):
        """Test state transitions are atomic - all or nothing."""
        # Queue 3 messages
        for i in range(3):
            await self.batcher.queue_message("user1", {"batch": i})
        
        initial_messages = self.batcher._pending_messages["conn1"].copy()
        
        # Start flush (should mark as SENDING)
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock, side_effect=Exception("Atomic failure")):
            await self.batcher._flush_batch("conn1")
        
        # All messages should revert to PENDING atomically
        final_messages = self.batcher._pending_messages["conn1"]
        assert len(final_messages) == 3
        assert all(msg.state == MessageState.PENDING for msg in final_messages)
        
        # No messages should be stuck in SENDING state
        sending_messages = [msg for msg in final_messages if msg.state == MessageState.SENDING]
        assert len(sending_messages) == 0, "Messages stuck in SENDING state - not atomic"
    
    @pytest.mark.asyncio
    async def test_consistency_invariants_maintained(self):
        """Test consistency invariants are maintained under failures."""
        await self.batcher.queue_message("user1", {"invariant": "test"})
        
        # Before send attempt
        messages_before = self.batcher._pending_messages["conn1"]
        total_before = len(messages_before)
        
        # Failed send attempt
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock, side_effect=Exception("Consistency test")):
            await self.batcher._flush_batch("conn1")
        
        # After failed send attempt
        messages_after = self.batcher._pending_messages["conn1"]
        total_after = len(messages_after)
        
        # Consistency invariant: message count should be preserved
        assert total_before == total_after, "Consistency invariant violated: message count changed"
        
        # All messages should be in valid states
        valid_states = {MessageState.PENDING, MessageState.SENDING, MessageState.SENT, MessageState.FAILED}
        for msg in messages_after:
            assert msg.state in valid_states, f"Invalid message state: {msg.state}"
    
    def test_metrics_consistency_during_failures(self):
        """Test metrics remain consistent during failures."""
        # Add messages with different states to test counting
        msg1 = PendingMessage(content={"test": "1"}, connection_id="conn1", user_id="user1")
        msg2 = PendingMessage(content={"test": "2"}, connection_id="conn1", user_id="user1")
        msg3 = PendingMessage(content={"test": "3"}, connection_id="conn1", user_id="user1")
        
        msg1.state = MessageState.PENDING
        msg2.state = MessageState.SENDING
        msg3.state = MessageState.FAILED
        
        self.batcher._pending_messages["conn1"] = [msg1, msg2, msg3]
        
        metrics = self.batcher.get_metrics()
        
        # Metrics should accurately reflect state distribution
        assert metrics["pending_messages"] == 1
        assert metrics["sending_messages"] == 1
        assert metrics["failed_messages"] == 1
        assert metrics["total_messages"] == 3

class TestRetryMechanism:
    """Test exponential backoff retry mechanism."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock: Component isolation for controlled unit testing
        self.connection_manager = Mock(spec=ConnectionManager)
        self.config = BatchConfig(max_batch_size=2, max_wait_time=0.1)
        self.batcher = MessageBatcher(self.config, self.connection_manager)
        
        # Mock connection
        # Mock: Component isolation for controlled unit testing
        self.mock_connection = Mock(spec=ConnectionInfo)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        self.mock_connection.websocket = AsyncNone  # TODO: Use real service instance
        self.mock_connection.message_count = 0
        self.connection_manager.get_connection_by_id.return_value = self.mock_connection
        self.connection_manager.get_user_connections.return_value = [
            # Mock: Component isolation for controlled unit testing
            Mock(connection_id="conn1")
        ]
    
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test retry mechanism implements exponential backoff."""
        await self.batcher.queue_message("user1", {"retry": "test"})
        
        # First failure
        # Mock: Component isolation for testing without external dependencies
        with patch('app.websocket.batch_message_operations.send_batch_to_connection',
                   new_callable=AsyncMock, side_effect=Exception("Retry test 1")):
            await self.batcher._flush_batch("conn1")
        
        # Check retry count
        msg = self.batcher._pending_messages["conn1"][0]
        assert msg.retry_count == 0  # Revert doesn't increment retry count
        assert msg.state == MessageState.PENDING
        
        # Simulate multiple failures to test exponential backoff
        retry_manager = self.batcher._retry_manager
        
        # Test backoff delays
        delays = [retry_manager._calculate_retry_delay(i) for i in range(4)]
        expected_delays = [0.1, 0.2, 0.4, 0.8]
        
        assert delays == expected_delays, f"Exponential backoff not working: {delays}"
    
    @pytest.mark.asyncio  
    async def test_retry_limit_enforcement(self):
        """Test retry limit is enforced."""
        msg = PendingMessage(
            content={"limit": "test"}, 
            connection_id="conn1", 
            user_id="user1",
            retry_count=3,  # At max retries
            max_retries=3
        )
        msg.state = MessageState.FAILED
        
        self.batcher._pending_messages["conn1"] = [msg]
        
        retry_manager = self.batcher._retry_manager
        should_retry = retry_manager.should_retry(msg)
        
        assert should_retry is False, "Retry limit not enforced"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])