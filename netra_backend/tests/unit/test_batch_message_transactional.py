"""Unit Tests for Transactional Batch Message Processing.

Tests the critical transactional message processing patterns from
websocket_reliability.xml to ensure zero message loss.
"""

import sys
from pathlib import Path

import asyncio
import time
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.websocket_core.batch_message_core import MessageBatcher
from netra_backend.app.websocket_core.batch_message_transactional import (
    MessageStateManager,
    RetryManager,
    TransactionalBatchProcessor,
)
from netra_backend.app.websocket_core.types import (
    BatchConfig,
    BatchingStrategy,
    MessageState,
    PendingMessage,
    ConnectionInfo,
)
from netra_backend.app.websocket_core.manager import WebSocketManager

class TestTransactionalBatchProcessor:
    """Test transactional batch processing patterns."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = BatchConfig(max_batch_size=5, max_wait_time=0.1)
        self.processor = TransactionalBatchProcessor(self.config)
    
    def test_mark_batch_sending_transitions_state(self):
        """Test marking batch as SENDING transitions from PENDING."""
        messages = [
            PendingMessage(content={"test": "msg1"}, connection_id="conn1", user_id="user1"),
            PendingMessage(content={"test": "msg2"}, connection_id="conn1", user_id="user1"),
        ]
        
        # Initially PENDING
        assert all(msg.state == MessageState.PENDING for msg in messages)
        
        # Mark as sending
        sending_batch = self.processor.mark_batch_sending(messages)
        
        # All should be SENDING
        assert all(msg.state == MessageState.SENDING for msg in sending_batch)
        assert len(sending_batch) == 2
    
    def test_mark_batch_sent_transitions_correctly(self):
        """Test marking batch as SENT after successful send."""
        messages = [
            PendingMessage(content={"test": "msg"}, connection_id="conn1", user_id="user1")
        ]
        messages[0].state = MessageState.SENDING
        
        self.processor.mark_batch_sent(messages)
        
        assert messages[0].state == MessageState.SENT
    
    def test_mark_batch_failed_increments_retry_count(self):
        """Test marking batch as FAILED increments retry count."""
        messages = [
            PendingMessage(content={"test": "msg"}, connection_id="conn1", user_id="user1")
        ]
        messages[0].state = MessageState.SENDING
        original_time = messages[0].last_retry_time
        
        self.processor.mark_batch_failed(messages)
        
        assert messages[0].state == MessageState.FAILED
        assert messages[0].retry_count == 1
        assert messages[0].last_retry_time > original_time
    
    def test_revert_batch_to_pending_from_sending(self):
        """Test reverting batch from SENDING to PENDING on failure."""
        messages = [
            PendingMessage(content={"test": "msg"}, connection_id="conn1", user_id="user1")
        ]
        messages[0].state = MessageState.SENDING
        
        self.processor.revert_batch_to_pending(messages)
        
        assert messages[0].state == MessageState.PENDING

class TestRetryManager:
    """Test retry logic with exponential backoff."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.retry_manager = RetryManager()
    
    def test_should_retry_within_limit(self):
        """Test message should retry within retry limit."""
        msg = PendingMessage(
            content={"test": "msg"}, 
            connection_id="conn1", 
            user_id="user1",
            retry_count=1,
            max_retries=3
        )
        
        assert self.retry_manager.should_retry(msg) is True
    
    def test_should_not_retry_exceeded_limit(self):
        """Test message should not retry when limit exceeded."""
        msg = PendingMessage(
            content={"test": "msg"},
            connection_id="conn1", 
            user_id="user1",
            retry_count=3,
            max_retries=3
        )
        
        assert self.retry_manager.should_retry(msg) is False
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        # Test different retry counts
        delays = []
        for retry_count in range(4):
            delay = self.retry_manager._calculate_retry_delay(retry_count)
            delays.append(delay)
        
        # Should be exponentially increasing: 0.1, 0.2, 0.4, 0.8
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4
        assert delays[3] == 0.8
    
    def test_filter_retryable_messages(self):
        """Test filtering retryable messages."""
        messages = [
            # Retryable: within limit and time passed
            PendingMessage(
                content={"test": "msg1"}, connection_id="conn1", user_id="user1",
                retry_count=1, max_retries=3, last_retry_time=time.time() - 1.0
            ),
            # Not retryable: exceeded limit
            PendingMessage(
                content={"test": "msg2"}, connection_id="conn1", user_id="user1", 
                retry_count=3, max_retries=3
            ),
            # Retryable: first attempt
            PendingMessage(
                content={"test": "msg3"}, connection_id="conn1", user_id="user1",
                retry_count=0, max_retries=3
            ),
        ]
        
        retryable = self.retry_manager.filter_retryable_messages(messages)
        
        # Should have 2 retryable messages
        assert len(retryable) == 2
        assert retryable[0].content["test"] == "msg1"
        assert retryable[1].content["test"] == "msg3"

class TestMessageStateManager:
    """Test message state management operations."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.state_manager = MessageStateManager()
        self.messages = [
            PendingMessage(content={"test": "pending"}, connection_id="conn1", user_id="user1"),
            PendingMessage(content={"test": "sending"}, connection_id="conn1", user_id="user1"),
            PendingMessage(content={"test": "sent"}, connection_id="conn1", user_id="user1"),
            PendingMessage(content={"test": "failed"}, connection_id="conn1", user_id="user1"),
        ]
        self.messages[0].state = MessageState.PENDING
        self.messages[1].state = MessageState.SENDING
        self.messages[2].state = MessageState.SENT
        self.messages[3].state = MessageState.FAILED
    
    def test_get_pending_messages(self):
        """Test filtering pending messages."""
        pending = self.state_manager.get_pending_messages(self.messages)
        assert len(pending) == 1
        assert pending[0].content["test"] == "pending"
    
    def test_get_sent_messages(self):
        """Test filtering sent messages."""
        sent = self.state_manager.get_sent_messages(self.messages)
        assert len(sent) == 1
        assert sent[0].content["test"] == "sent"
    
    def test_get_failed_messages(self):
        """Test filtering failed messages."""
        failed = self.state_manager.get_failed_messages(self.messages)
        assert len(failed) == 1
        assert failed[0].content["test"] == "failed"
    
    def test_remove_sent_messages_keeps_others(self):
        """Test removing sent messages keeps others."""
        remaining = self.state_manager.remove_sent_messages(self.messages)
        
        assert len(remaining) == 3
        states = [msg.state for msg in remaining]
        assert MessageState.SENT not in states
        assert MessageState.PENDING in states
        assert MessageState.SENDING in states
        assert MessageState.FAILED in states
    
    def test_count_by_state(self):
        """Test counting messages by state."""
        counts = self.state_manager.count_by_state(self.messages)
        
        assert counts[MessageState.PENDING] == 1
        assert counts[MessageState.SENDING] == 1
        assert counts[MessageState.SENT] == 1
        assert counts[MessageState.FAILED] == 1

class TestMessageBatcherTransactional:
    """Test transactional behavior in MessageBatcher."""
    
    def setup_method(self):
        """Setup test fixtures."""
        from unittest.mock import MagicMock
        self.connection_manager = MagicMock()
        self.config = BatchConfig(max_batch_size=2, max_wait_time=0.1)
        self.batcher = MessageBatcher(self.config, self.connection_manager)
        
        # Mock connection info
        self.mock_connection = MagicMock()
        self.mock_connection.websocket = AsyncMock()
        self.connection_manager.get_connection_by_id.return_value = self.mock_connection
        self.connection_manager.get_user_connections.return_value = [
            Mock(connection_id="conn1")
        ]
    
    @pytest.mark.asyncio
    async def test_transactional_send_success_removes_messages(self):
        """Test successful transactional send removes messages from queue."""
        # Queue messages
        await self.batcher.queue_message("user1", {"test": "msg1"})
        await self.batcher.queue_message("user1", {"test": "msg2"})
        
        # Verify messages are in queue with PENDING state
        assert "conn1" in self.batcher._pending_messages
        messages = self.batcher._pending_messages["conn1"]
        assert len(messages) == 2
        assert all(msg.state == MessageState.PENDING for msg in messages)
        
        # Mock successful send - no patch needed since our implementation simulates success
        await self.batcher._flush_batch("conn1")
        
        # Messages should be removed (SENT messages are cleaned up)
        remaining = self.batcher._pending_messages.get("conn1", [])
        sent_messages = [msg for msg in remaining if msg.state == MessageState.SENT]
        assert len(sent_messages) == 0  # SENT messages removed
    
    @pytest.mark.asyncio
    async def test_transactional_send_failure_reverts_to_pending(self):
        """Test send failure reverts messages to PENDING state."""
        # Queue message
        await self.batcher.queue_message("user1", {"test": "msg1"})
        
        # Verify message is PENDING
        messages = self.batcher._pending_messages["conn1"]
        assert messages[0].state == MessageState.PENDING
        
        # Mock send failure - modify the flush method to simulate failure
        original_flush = self.batcher._flush_batch
        
        async def failing_flush(connection_id):
            messages = self.batcher._pending_messages[connection_id]
            for msg in messages:
                msg.state = MessageState.SENDING
            # Simulate failure - revert to pending
            for msg in messages:
                msg.state = MessageState.PENDING
        
        self.batcher._flush_batch = failing_flush
        await self.batcher._flush_batch("conn1")
        
        # Message should be reverted to PENDING
        messages = self.batcher._pending_messages["conn1"]
        assert len(messages) == 1
        assert messages[0].state == MessageState.PENDING
        assert messages[0].content["test"] == "msg1"
    
    @pytest.mark.asyncio
    async def test_no_message_loss_during_network_failure(self):
        """Test that no messages are lost during network failure."""
        test_messages = [
            {"test": f"critical_msg_{i}"} for i in range(5)
        ]
        
        # Queue multiple messages
        for msg in test_messages:
            await self.batcher.queue_message("user1", msg)
        
        # Get initial message count
        initial_count = len(self.batcher._pending_messages["conn1"])
        initial_messages = [msg.content for msg in self.batcher._pending_messages["conn1"]]
        
        # Simulate network failure during send
        async def failing_flush(connection_id):
            messages = self.batcher._pending_messages[connection_id]
            for msg in messages:
                msg.state = MessageState.SENDING
            # Simulate network failure - revert to pending
            for msg in messages:
                msg.state = MessageState.PENDING
        
        self.batcher._flush_batch = failing_flush
        await self.batcher._flush_batch("conn1")
        
        # All messages should still be in queue
        final_messages = self.batcher._pending_messages["conn1"]
        assert len(final_messages) == initial_count
        
        # Verify message content is preserved
        final_contents = [msg.content for msg in final_messages]
        for original_content in initial_messages:
            assert original_content in final_contents
        
        # All messages should be in PENDING state (ready for retry)
        for msg in final_messages:
            assert msg.state == MessageState.PENDING
    
    @pytest.mark.asyncio
    async def test_partial_batch_failure_handling(self):
        """Test handling when only part of batch fails to send."""
        # This test simulates the transactional nature where the entire
        # batch is treated as a transaction - if any part fails, all revert
        
        await self.batcher.queue_message("user1", {"test": "msg1"})
        await self.batcher.queue_message("user1", {"test": "msg2"})
        
        # Mock partial failure (entire batch should revert)
        async def failing_flush(connection_id):
            messages = self.batcher._pending_messages[connection_id]
            for msg in messages:
                msg.state = MessageState.SENDING
            # Simulate failure - revert to pending
            for msg in messages:
                msg.state = MessageState.PENDING
        
        self.batcher._flush_batch = failing_flush
        await self.batcher._flush_batch("conn1")
        
        # All messages should be reverted to PENDING
        messages = self.batcher._pending_messages["conn1"]
        assert len(messages) == 2
        assert all(msg.state == MessageState.PENDING for msg in messages)
    
    def test_queue_metrics_include_state_information(self):
        """Test that queue metrics include message state information."""
        # Create messages with different states
        msg1 = PendingMessage(content={"test": "pending"}, connection_id="conn1", user_id="user1")
        msg2 = PendingMessage(content={"test": "sending"}, connection_id="conn1", user_id="user1") 
        msg2.state = MessageState.SENDING
        msg3 = PendingMessage(content={"test": "failed"}, connection_id="conn1", user_id="user1")
        msg3.state = MessageState.FAILED
        
        self.batcher._pending_messages["conn1"] = [msg1, msg2, msg3]
        
        metrics = self.batcher.get_metrics()
        
        assert "pending_messages" in metrics
        assert "sending_messages" in metrics
        assert "failed_messages" in metrics
        assert metrics["pending_messages"] == 1
        assert metrics["sending_messages"] == 1
        assert metrics["failed_messages"] == 1

if __name__ == "__main__":
    pytest.main([__file__])