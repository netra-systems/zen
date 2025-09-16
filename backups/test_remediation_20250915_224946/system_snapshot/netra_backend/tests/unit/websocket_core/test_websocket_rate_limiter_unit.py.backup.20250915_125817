"""
Unit tests for WebSocket Rate Limiter - Testing connection and message rate limiting.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform stability and abuse prevention  
- Value Impact: Prevents system overload from excessive WebSocket usage
- Strategic Impact: Protects infrastructure for all users, ensures fair resource usage

These tests focus on rate limiting algorithms, user isolation, and protection
against both connection flooding and message spam attacks.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
from netra_backend.app.websocket_core.rate_limiter import (
    WebSocketRateLimiter,
    RateLimitExceededException,
    RateLimitConfig,
    UserRateLimitState
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketRateLimiter:
    """Unit tests for WebSocket rate limiting."""
    
    @pytest.fixture
    def rate_limit_config(self):
        """Create rate limit configuration."""
        return RateLimitConfig(
            max_connections_per_user=3,
            max_messages_per_minute=60,
            max_messages_per_hour=1000,
            connection_window_seconds=60,
            message_window_seconds=60
        )
    
    @pytest.fixture
    def rate_limiter(self, rate_limit_config):
        """Create WebSocketRateLimiter instance."""
        return WebSocketRateLimiter(config=rate_limit_config)
    
    @pytest.fixture
    def sample_message(self):
        """Create sample WebSocket message."""
        return WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "test message"},
            user_id="user_123"
        )
    
    def test_initializes_with_correct_config(self, rate_limiter, rate_limit_config):
        """Test RateLimiter initializes with proper configuration."""
        assert rate_limiter.config == rate_limit_config
        assert len(rate_limiter._user_states) == 0
        assert rate_limiter._cleanup_lock is not None
        assert rate_limiter._state_lock is not None
    
    @pytest.mark.asyncio
    async def test_allows_connections_within_limit(self, rate_limiter):
        """Test connection allowance within configured limits."""
        user_id = "user_123"
        
        # Should allow connections up to limit
        for i in range(3):  # max_connections_per_user = 3
            allowed = await rate_limiter.check_connection_limit(user_id)
            assert allowed is True
            await rate_limiter.record_connection(user_id, f"conn_{i}")
        
        # Verify connection count
        user_state = rate_limiter._user_states[user_id]
        assert len(user_state.active_connections) == 3
    
    @pytest.mark.asyncio
    async def test_blocks_connections_exceeding_limit(self, rate_limiter):
        """Test connection blocking when limit exceeded."""
        user_id = "user_123"
        
        # Fill up to limit
        for i in range(3):
            await rate_limiter.record_connection(user_id, f"conn_{i}")
        
        # Next connection should be blocked
        allowed = await rate_limiter.check_connection_limit(user_id)
        assert allowed is False
        
        with pytest.raises(RateLimitExceededException) as exc_info:
            await rate_limiter.record_connection(user_id, "conn_excess")
        
        assert "connection limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_allows_messages_within_rate_limit(self, rate_limiter, sample_message):
        """Test message allowance within rate limits."""
        user_id = "user_123"
        
        # Should allow messages up to per-minute limit
        for i in range(60):  # max_messages_per_minute = 60
            allowed = await rate_limiter.check_message_rate_limit(user_id)
            assert allowed is True
            await rate_limiter.record_message(user_id, sample_message)
        
        # Verify message count tracking
        user_state = rate_limiter._user_states[user_id]
        assert len(user_state.message_timestamps) == 60
    
    @pytest.mark.asyncio
    async def test_blocks_messages_exceeding_rate_limit(self, rate_limiter, sample_message):
        """Test message blocking when rate limit exceeded."""
        user_id = "user_123"
        
        # Fill up to per-minute limit
        for i in range(60):
            await rate_limiter.record_message(user_id, sample_message)
        
        # Next message should be blocked
        allowed = await rate_limiter.check_message_rate_limit(user_id)
        assert allowed is False
        
        with pytest.raises(RateLimitExceededException) as exc_info:
            await rate_limiter.record_message(user_id, sample_message)
        
        assert "message rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self, rate_limiter, sample_message):
        """Test sliding window rate limiting behavior."""
        user_id = "user_123"
        
        # Fill half the limit
        for i in range(30):
            await rate_limiter.record_message(user_id, sample_message)
        
        # Fast-forward time by manipulating timestamps (simulating time passage)
        user_state = rate_limiter._user_states[user_id]
        old_time = datetime.now(timezone.utc) - timedelta(seconds=61)
        
        # Age out some messages
        for i in range(15):
            user_state.message_timestamps[i] = old_time
        
        # Should allow more messages after cleanup
        await rate_limiter._cleanup_expired_data()
        
        allowed = await rate_limiter.check_message_rate_limit(user_id)
        assert allowed is True
        
        # Should be able to send more messages
        for i in range(45):  # Should allow up to 60 total in current window
            allowed = await rate_limiter.check_message_rate_limit(user_id)
            assert allowed is True
            await rate_limiter.record_message(user_id, sample_message)
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self, rate_limiter):
        """Test connection cleanup when user disconnects."""
        user_id = "user_123"
        connection_id = "conn_123"
        
        # Record connection
        await rate_limiter.record_connection(user_id, connection_id)
        assert len(rate_limiter._user_states[user_id].active_connections) == 1
        
        # Remove connection
        await rate_limiter.remove_connection(user_id, connection_id)
        
        # Verify cleanup
        user_state = rate_limiter._user_states.get(user_id)
        if user_state:  # May be cleaned up entirely
            assert connection_id not in user_state.active_connections
    
    @pytest.mark.asyncio
    async def test_isolates_users_independently(self, rate_limiter, sample_message):
        """Test independent rate limiting per user."""
        user1_id = "user_123"
        user2_id = "user_456"
        
        # Fill user1's message limit
        for i in range(60):
            await rate_limiter.record_message(user1_id, sample_message)
        
        # User1 should be blocked
        allowed1 = await rate_limiter.check_message_rate_limit(user1_id)
        assert allowed1 is False
        
        # User2 should still be allowed (independent limits)
        allowed2 = await rate_limiter.check_message_rate_limit(user2_id)
        assert allowed2 is True
        
        # User2 can still send messages
        message2 = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "user2 message"},
            user_id=user2_id
        )
        await rate_limiter.record_message(user2_id, message2)
        
        # Verify independent state tracking
        assert len(rate_limiter._user_states) == 2
        assert len(rate_limiter._user_states[user1_id].message_timestamps) == 60
        assert len(rate_limiter._user_states[user2_id].message_timestamps) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_user_states(self, rate_limiter):
        """Test cleanup of inactive user states."""
        user_id = "inactive_user"
        connection_id = "conn_123"
        
        # Create user state
        await rate_limiter.record_connection(user_id, connection_id)
        assert user_id in rate_limiter._user_states
        
        # Simulate user disconnection and time passage
        await rate_limiter.remove_connection(user_id, connection_id)
        
        # Manipulate last activity to make it old
        user_state = rate_limiter._user_states[user_id]
        user_state.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Cleanup should remove inactive user
        await rate_limiter._cleanup_expired_data()
        
        # Verify cleanup (depends on implementation)
        # User with no connections and old activity should be cleaned up
        if rate_limiter.config.cleanup_inactive_after_seconds:
            assert user_id not in rate_limiter._user_states
    
    @pytest.mark.asyncio
    async def test_different_message_types_counted_equally(self, rate_limiter):
        """Test all message types count toward rate limit equally."""
        user_id = "user_123"
        
        message_types = [
            MessageType.USER_MESSAGE,
            MessageType.START_AGENT,
            MessageType.CHAT,
            MessageType.AGENT_COMPLETED
        ]
        
        # Send different message types
        for msg_type in message_types:
            for i in range(15):  # 15 * 4 = 60 total
                message = WebSocketMessage(
                    message_type=msg_type,
                    payload={"content": f"message {i}"},
                    user_id=user_id
                )
                await rate_limiter.record_message(user_id, message)
        
        # Should hit rate limit
        allowed = await rate_limiter.check_message_rate_limit(user_id)
        assert allowed is False
        
        # Verify all messages counted
        user_state = rate_limiter._user_states[user_id]
        assert len(user_state.message_timestamps) == 60
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_operations(self, rate_limiter, sample_message):
        """Test thread-safe concurrent rate limit operations."""
        user_id = "user_123"
        
        # Create concurrent message recording tasks
        tasks = []
        for i in range(50):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"iteration": i},
                user_id=user_id
            )
            task = asyncio.create_task(
                rate_limiter.record_message(user_id, message)
            )
            tasks.append(task)
        
        # Wait for all operations
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify correct count despite concurrent access
        user_state = rate_limiter._user_states[user_id]
        assert len(user_state.message_timestamps) == 50
        
        # Should still enforce limits correctly
        allowed = await rate_limiter.check_message_rate_limit(user_id)
        assert allowed is True  # Still under limit