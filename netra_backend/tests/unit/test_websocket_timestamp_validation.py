"""
Test WebSocket Timestamp Validation Fix

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Infrastructure Stability  
- Value Impact: Ensures WebSocket messages process correctly with various timestamp formats
- Strategic Impact: Prevents chat UI failures that break 90% of business value delivery

Tests the specific staging error case and comprehensive timestamp conversion scenarios.
"""

import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any

from netra_backend.app.websocket_core.timestamp_utils import (
    convert_to_unix_timestamp,
    safe_convert_timestamp,
    validate_timestamp_format,
    cached_convert_timestamp
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.handlers import MessageRouter


class TestTimestampConversion:
    """Test timestamp conversion utility functions."""
    
    def test_staging_error_case(self):
        """Test the exact staging error case: '2025-09-08T16:50:01.447585'"""
        staging_timestamp = '2025-09-08T16:50:01.447585'
        
        # Should not raise an exception
        result = safe_convert_timestamp(staging_timestamp)
        
        # Should return a valid Unix timestamp float
        assert isinstance(result, float)
        assert result > 0
        
        # Verify it converts back to reasonable datetime
        converted_dt = datetime.fromtimestamp(result, tz=timezone.utc)
        assert converted_dt.year == 2025
        assert converted_dt.month == 9
        assert converted_dt.day == 8
    
    def test_unix_timestamp_passthrough(self):
        """Test that existing Unix timestamps work unchanged."""
        unix_float = 1693567801.447585
        unix_int = 1693567801
        
        # Float timestamps should pass through
        assert convert_to_unix_timestamp(unix_float) == unix_float
        assert convert_to_unix_timestamp(unix_int) == float(unix_int)
    
    def test_none_timestamp_uses_current_time(self):
        """Test that None timestamp uses current time."""
        before = time.time()
        result = convert_to_unix_timestamp(None)
        after = time.time()
        
        assert before <= result <= after
    
    def test_datetime_object_conversion(self):
        """Test datetime object conversion."""
        dt = datetime(2025, 9, 8, 16, 50, 1, 447585, tzinfo=timezone.utc)
        result = convert_to_unix_timestamp(dt)
        
        assert isinstance(result, float)
        # Verify round-trip conversion
        converted_back = datetime.fromtimestamp(result, tz=timezone.utc)
        assert abs((converted_back - dt).total_seconds()) < 0.001
    
    def test_iso_timezone_variations(self):
        """Test various ISO timezone formats."""
        test_cases = [
            '2025-09-08T16:50:01.447585',        # No timezone (assumes UTC)
            '2025-09-08T16:50:01.447585Z',       # Zulu time
            '2025-09-08T16:50:01.447585+00:00',  # UTC offset
            '2025-09-08T16:50:01.447585-05:00',  # EST offset
        ]
        
        for timestamp_str in test_cases:
            result = convert_to_unix_timestamp(timestamp_str)
            assert isinstance(result, float)
            assert result > 0
    
    def test_unix_timestamp_string(self):
        """Test Unix timestamp as string."""
        unix_str = '1693567801.447585'
        result = convert_to_unix_timestamp(unix_str)
        
        assert result == 1693567801.447585
    
    def test_invalid_timestamp_handling(self):
        """Test handling of invalid timestamp formats."""
        invalid_cases = [
            'not-a-timestamp',
            'invalid-date-format',
            '2025-13-45T99:99:99',  # Invalid date/time
        ]
        
        for invalid_timestamp in invalid_cases:
            # Should raise ValueError in strict mode
            with pytest.raises(ValueError):
                convert_to_unix_timestamp(invalid_timestamp)
            
            # Should return fallback in safe mode
            result = safe_convert_timestamp(invalid_timestamp, fallback_to_current=True)
            assert isinstance(result, float)
            
            # Should return None when fallback disabled
            result = safe_convert_timestamp(invalid_timestamp, fallback_to_current=False)
            assert result is None
    
    def test_timestamp_validation(self):
        """Test timestamp format validation."""
        valid_cases = [
            '2025-09-08T16:50:01.447585',
            1693567801.447585,
            None,
            datetime.now(timezone.utc)
        ]
        
        invalid_cases = [
            'invalid-timestamp',
            'not-a-date'
        ]
        
        for valid_case in valid_cases:
            assert validate_timestamp_format(valid_case) is True
        
        for invalid_case in invalid_cases:
            assert validate_timestamp_format(invalid_case) is False
    
    def test_cached_conversion_performance(self):
        """Test cached conversion for performance."""
        timestamp_str = '2025-09-08T16:50:01.447585'
        
        # First call should cache
        result1 = cached_convert_timestamp(timestamp_str)
        
        # Second call should use cache
        result2 = cached_convert_timestamp(timestamp_str)
        
        assert result1 == result2
        assert isinstance(result1, float)


class TestWebSocketMessageTimestampHandling:
    """Test WebSocket message processing with timestamp conversion."""
    
    @pytest.fixture
    def message_router(self):
        """Create message router for testing."""
        return MessageRouter()
    
    async def test_websocket_message_with_iso_timestamp(self, message_router):
        """Test WebSocket message creation with ISO timestamp."""
        raw_message = {
            "type": "user_message",
            "payload": {"content": "test message"},
            "timestamp": "2025-09-08T16:50:01.447585",
            "user_id": "test_user_123"
        }
        
        # Should not raise exception
        ws_message = await message_router._prepare_message(raw_message)
        
        assert isinstance(ws_message, WebSocketMessage)
        assert ws_message.type == MessageType.USER_MESSAGE
        assert isinstance(ws_message.timestamp, float)
        assert ws_message.timestamp > 0
        assert ws_message.user_id == "test_user_123"
    
    async def test_websocket_message_with_unix_timestamp(self, message_router):
        """Test WebSocket message creation with Unix timestamp."""
        unix_timestamp = time.time()
        raw_message = {
            "type": "agent_response",
            "payload": {"content": "agent response"},
            "timestamp": unix_timestamp,
            "user_id": "test_user_123"
        }
        
        ws_message = await message_router._prepare_message(raw_message)
        
        assert isinstance(ws_message, WebSocketMessage)
        assert ws_message.timestamp == unix_timestamp
    
    async def test_websocket_message_without_timestamp(self, message_router):
        """Test WebSocket message creation without timestamp (should use current time)."""
        raw_message = {
            "type": "system_message",
            "payload": {"content": "system message"},
            "user_id": "test_user_123"
        }
        
        before = time.time()
        ws_message = await message_router._prepare_message(raw_message)
        after = time.time()
        
        assert isinstance(ws_message, WebSocketMessage)
        assert before <= ws_message.timestamp <= after
    
    async def test_websocket_message_with_invalid_timestamp(self, message_router):
        """Test WebSocket message with invalid timestamp (should use fallback)."""
        raw_message = {
            "type": "error_message",
            "payload": {"error": "test error"},
            "timestamp": "invalid-timestamp-format",
            "user_id": "test_user_123"
        }
        
        # Should not raise exception, should use current time as fallback
        before = time.time()
        ws_message = await message_router._prepare_message(raw_message)
        after = time.time()
        
        assert isinstance(ws_message, WebSocketMessage)
        assert before <= ws_message.timestamp <= after


class TestBusinessValuePreservation:
    """Test that the fix preserves all business value functionality."""
    
    async def test_chat_message_flow_preserved(self):
        """Test that chat message flow continues to work with timestamp fix."""
        router = MessageRouter()
        
        # Simulate chat message with problematic timestamp from staging
        chat_message = {
            "type": "chat",
            "payload": {
                "content": "User's AI question",
                "thread_id": "thread_123"
            },
            "timestamp": "2025-09-08T16:50:01.447585",  # Staging error case
            "user_id": "user_123",
            "thread_id": "thread_123"
        }
        
        # Should process without errors
        ws_message = await router._prepare_message(chat_message)
        
        # Should preserve all business logic
        assert ws_message.type == MessageType.CHAT
        assert ws_message.payload["content"] == "User's AI question"
        assert ws_message.user_id == "user_123"
        assert ws_message.thread_id == "thread_123"
        assert isinstance(ws_message.timestamp, float)
    
    async def test_agent_event_flow_preserved(self):
        """Test that agent event messages work with timestamp fix."""
        router = MessageRouter()
        
        # Agent events are critical for business value (Section 6.1 of CLAUDE.md)
        agent_events = [
            {"type": "agent_started", "timestamp": "2025-09-08T16:50:01.447585"},
            {"type": "agent_thinking", "timestamp": "2025-09-08T16:50:02.123456"},
            {"type": "tool_executing", "timestamp": "2025-09-08T16:50:03.789012"},
            {"type": "tool_completed", "timestamp": "2025-09-08T16:50:04.345678"},
            {"type": "agent_completed", "timestamp": "2025-09-08T16:50:05.901234"}
        ]
        
        for event_data in agent_events:
            event_data.update({
                "payload": {"status": "processing"},
                "user_id": "user_123",
                "thread_id": "thread_123"
            })
            
            # Should process all agent events without errors
            ws_message = await router._prepare_message(event_data)
            
            assert isinstance(ws_message, WebSocketMessage)
            assert isinstance(ws_message.timestamp, float)
            assert ws_message.user_id == "user_123"


class TestPerformanceValidation:
    """Test that timestamp conversion meets performance requirements."""
    
    def test_conversion_performance(self):
        """Test that timestamp conversion is <1ms as required."""
        timestamp_cases = [
            "2025-09-08T16:50:01.447585",
            1693567801.447585,
            None,
            datetime.now(timezone.utc)
        ]
        
        for timestamp_input in timestamp_cases:
            start_time = time.perf_counter()
            result = safe_convert_timestamp(timestamp_input)
            end_time = time.perf_counter()
            
            # Should be under 1ms (0.001 seconds)
            conversion_time = end_time - start_time
            assert conversion_time < 0.001, f"Conversion took {conversion_time:.6f}s, expected <0.001s"
            assert isinstance(result, float)
    
    def test_cached_performance_improvement(self):
        """Test that caching improves performance for repeated conversions."""
        timestamp_str = "2025-09-08T16:50:01.447585"
        
        # First conversion (no cache)
        start_time = time.perf_counter()
        result1 = cached_convert_timestamp(timestamp_str)
        first_time = time.perf_counter() - start_time
        
        # Second conversion (should use cache)
        start_time = time.perf_counter()
        result2 = cached_convert_timestamp(timestamp_str)
        cached_time = time.perf_counter() - start_time
        
        assert result1 == result2
        # Cached version should be faster (though times may be very small)
        assert cached_time <= first_time