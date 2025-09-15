"""
Unit tests for WebSocket Message Buffer - Testing message queuing and delivery reliability.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Message delivery reliability for real-time chat
- Value Impact: Ensures messages aren't lost during connection instability
- Strategic Impact: Core infrastructure for reliable AI chat interactions

These tests focus on message buffering, queue management, and message ordering
to ensure reliable delivery of critical agent events to users.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
from netra_backend.app.websocket_core.message_buffer import MessageBuffer, BufferedMessage
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestMessageBuffer:
    """Unit tests for WebSocket message buffering."""
    
    @pytest.fixture
    def message_buffer(self):
        """Create MessageBuffer instance."""
        return MessageBuffer(max_buffer_size=100, max_age_seconds=300)
    
    @pytest.fixture
    def sample_message(self):
        """Create sample WebSocket message."""
        return WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload={
                "agent_name": "cost_optimizer", 
                "result": {"savings": 1000},
                "status": "completed"
            },
            user_id="user_123",
            thread_id="thread_456"
        )
    
    def test_initializes_with_correct_defaults(self, message_buffer):
        """Test MessageBuffer initializes with proper default state."""
        assert message_buffer.max_buffer_size == 100
        assert message_buffer.max_age_seconds == 300
        assert len(message_buffer._user_buffers) == 0
        assert message_buffer._buffer_lock is not None
        assert message_buffer._cleanup_task is None
    
    @pytest.mark.asyncio
    async def test_buffers_message_for_user(self, message_buffer, sample_message):
        """Test message buffering for specific user."""
        user_id = "user_123"
        
        # Buffer message
        await message_buffer.buffer_message(user_id, sample_message)
        
        # Verify buffered
        assert user_id in message_buffer._user_buffers
        user_buffer = message_buffer._user_buffers[user_id]
        assert len(user_buffer) == 1
        
        buffered_msg = user_buffer[0]
        assert isinstance(buffered_msg, BufferedMessage)
        assert buffered_msg.message == sample_message
        assert buffered_msg.user_id == user_id
        assert isinstance(buffered_msg.buffered_at, datetime)
    
    @pytest.mark.asyncio
    async def test_retrieves_buffered_messages(self, message_buffer, sample_message):
        """Test retrieving buffered messages for user."""
        user_id = "user_123"
        
        # Buffer multiple messages
        message1 = sample_message
        message2 = WebSocketMessage(
            message_type=MessageType.AGENT_THINKING,
            payload={"thinking": "analyzing costs..."},
            user_id=user_id
        )
        
        await message_buffer.buffer_message(user_id, message1)
        await message_buffer.buffer_message(user_id, message2)
        
        # Retrieve messages
        messages = await message_buffer.get_buffered_messages(user_id)
        
        # Verify order preserved (FIFO)
        assert len(messages) == 2
        assert messages[0].message == message1
        assert messages[1].message == message2
        
        # Verify buffer cleared after retrieval
        assert len(message_buffer._user_buffers.get(user_id, [])) == 0
    
    @pytest.mark.asyncio
    async def test_enforces_buffer_size_limit(self, message_buffer):
        """Test buffer size limit enforcement with LRU eviction."""
        message_buffer.max_buffer_size = 3
        user_id = "user_123"
        
        # Add messages exceeding limit
        for i in range(5):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={"iteration": i},
                user_id=user_id
            )
            await message_buffer.buffer_message(user_id, message)
        
        # Verify only latest messages kept (LRU eviction)
        user_buffer = message_buffer._user_buffers[user_id]
        assert len(user_buffer) == 3
        
        # Verify correct messages kept (latest ones)
        assert user_buffer[0].message.payload["iteration"] == 2
        assert user_buffer[1].message.payload["iteration"] == 3
        assert user_buffer[2].message.payload["iteration"] == 4
    
    @pytest.mark.asyncio
    async def test_cleans_up_expired_messages(self, message_buffer):
        """Test cleanup of expired messages based on age."""
        message_buffer.max_age_seconds = 1  # 1 second expiry
        user_id = "user_123"
        
        # Add message
        await message_buffer.buffer_message(user_id, sample_message)
        assert len(message_buffer._user_buffers[user_id]) == 1
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        # Trigger cleanup
        await message_buffer._cleanup_expired_messages()
        
        # Verify expired message removed
        assert len(message_buffer._user_buffers.get(user_id, [])) == 0
    
    @pytest.mark.asyncio
    async def test_handles_multiple_users_independently(self, message_buffer):
        """Test independent buffering for multiple users."""
        user1_id = "user_123"
        user2_id = "user_456"
        
        message1 = WebSocketMessage(
            message_type=MessageType.AGENT_STARTED,
            payload={"agent": "optimizer"},
            user_id=user1_id
        )
        
        message2 = WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload={"agent": "analyzer"},
            user_id=user2_id
        )
        
        # Buffer messages for different users
        await message_buffer.buffer_message(user1_id, message1)
        await message_buffer.buffer_message(user2_id, message2)
        
        # Verify independent buffers
        assert len(message_buffer._user_buffers) == 2
        assert len(message_buffer._user_buffers[user1_id]) == 1
        assert len(message_buffer._user_buffers[user2_id]) == 1
        
        # Verify correct message isolation
        user1_messages = await message_buffer.get_buffered_messages(user1_id)
        user2_messages = await message_buffer.get_buffered_messages(user2_id)
        
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        assert user1_messages[0].message.payload["agent"] == "optimizer"
        assert user2_messages[0].message.payload["agent"] == "analyzer"
    
    @pytest.mark.asyncio
    async def test_handles_empty_buffer_gracefully(self, message_buffer):
        """Test graceful handling of empty buffer retrieval."""
        user_id = "nonexistent_user"
        
        # Attempt to get messages from empty buffer
        messages = await message_buffer.get_buffered_messages(user_id)
        
        # Should return empty list, not fail
        assert messages == []
        assert isinstance(messages, list)
    
    @pytest.mark.asyncio
    async def test_concurrent_buffer_operations(self, message_buffer):
        """Test thread-safe concurrent buffer operations."""
        user_id = "user_123"
        
        # Create multiple concurrent buffer operations
        tasks = []
        for i in range(10):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={"iteration": i},
                user_id=user_id
            )
            task = asyncio.create_task(
                message_buffer.buffer_message(user_id, message)
            )
            tasks.append(task)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks)
        
        # Verify all messages buffered correctly
        user_buffer = message_buffer._user_buffers[user_id]
        assert len(user_buffer) == 10
        
        # Verify no corruption from concurrent access
        iterations = {msg.message.payload["iteration"] for msg in user_buffer}
        assert iterations == set(range(10))