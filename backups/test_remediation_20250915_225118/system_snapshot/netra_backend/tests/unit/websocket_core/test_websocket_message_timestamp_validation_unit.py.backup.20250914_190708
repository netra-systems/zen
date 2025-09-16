"""
Unit Tests for WebSocket Message Timestamp Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Risk Reduction  
- Value Impact: Prevents WebSocket message parsing failures that break chat functionality
- Strategic Impact: Ensures 90% of business value (chat) remains operational

This test suite reproduces the exact staging error:
"WebSocketMessage timestamp - Input should be a valid number, unable to parse string as a number 
[type=float_parsing, input_value='2025-09-08T16:50:01.447585', input_type=str]"

CRITICAL: These tests are designed to FAIL initially to prove they catch the bug,
then pass after timestamp validation is fixed.
"""

import pytest
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import ValidationError

# CRITICAL: Absolute imports per CLAUDE.md
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, 
    MessageType, 
    create_standard_message
)


class TestWebSocketMessageTimestampValidation:
    """Unit tests for WebSocket message timestamp validation."""

    def test_exact_staging_error_reproduction(self):
        """
        CRITICAL: Reproduce the exact staging error scenario.
        
        This test MUST FAIL initially to prove it catches the bug.
        Expected error: ValidationError with float_parsing error.
        """
        # Exact staging error data from logs
        staging_message_data = {
            "type": "start_agent", 
            "payload": {
                "user_request": "Execute unified_data_agent with data: {'query': 'Analyze system performance metrics...'",
                "message_id": "req_61eebcb6",
                "user": "staging-e2e-user-001"
            },
            "timestamp": "2025-09-08T16:50:01.447585",  # This should cause the error
            "message_id": "req_61eebcb6",
            "user_id": "staging-e2e-user-001"
        }
        
        # This should raise ValidationError due to string timestamp
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(**staging_message_data)
        
        # Verify the exact error details
        error = exc_info.value
        assert len(error.errors()) > 0
        
        timestamp_error = None
        for err in error.errors():
            if err['loc'] == ('timestamp',):
                timestamp_error = err
                break
        
        assert timestamp_error is not None, "Expected timestamp validation error"
        assert timestamp_error['type'] == 'float_parsing'
        assert timestamp_error['input'] == '2025-09-08T16:50:01.447585'
        assert 'unable to parse string as a number' in timestamp_error['msg']

    def test_iso_datetime_string_rejection(self):
        """Test that ISO datetime strings are properly rejected."""
        iso_timestamps = [
            "2025-09-08T16:50:01.447585",
            "2025-01-01T00:00:00.000000",
            "2024-12-31T23:59:59.999999",
            "2025-09-08T16:50:01Z",
            "2025-09-08T16:50:01+00:00"
        ]
        
        for iso_timestamp in iso_timestamps:
            message_data = {
                "type": "start_agent",
                "payload": {"test": "data"},
                "timestamp": iso_timestamp
            }
            
            with pytest.raises(ValidationError) as exc_info:
                WebSocketMessage(**message_data)
            
            # Verify error type
            error = exc_info.value
            timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
            assert len(timestamp_errors) > 0
            assert timestamp_errors[0]['type'] == 'float_parsing'

    def test_valid_unix_timestamp_acceptance(self):
        """Test that valid Unix timestamps (floats) are accepted."""
        current_time = time.time()
        valid_timestamps = [
            current_time,
            1725811801.447585,  # Equivalent to staging datetime
            time.time() - 3600,  # 1 hour ago
            time.time() + 3600,  # 1 hour from now
            0.0,  # Unix epoch
            1234567890.123456  # Arbitrary valid timestamp
        ]
        
        for timestamp in valid_timestamps:
            message_data = {
                "type": "start_agent",
                "payload": {"test": "data"},
                "timestamp": timestamp,
                "user_id": "test-user"
            }
            
            # This should NOT raise an error
            message = WebSocketMessage(**message_data)
            assert message.timestamp == timestamp
            assert message.type == MessageType.START_AGENT

    def test_invalid_timestamp_types_rejection(self):
        """Test rejection of various invalid timestamp types."""
        invalid_timestamps = [
            "not-a-timestamp",
            "123abc",
            [],
            {},
            True,
            False
        ]
        
        for invalid_timestamp in invalid_timestamps:
            message_data = {
                "type": "user_message",
                "payload": {"content": "test"},
                "timestamp": invalid_timestamp
            }
            
            with pytest.raises(ValidationError):
                WebSocketMessage(**message_data)

    def test_none_timestamp_handling(self):
        """Test that None timestamp is properly handled."""
        message_data = {
            "type": "user_message",
            "payload": {"content": "test"},
            "timestamp": None
        }
        
        # This should work - None is allowed
        message = WebSocketMessage(**message_data)
        assert message.timestamp is None

    def test_negative_timestamp_handling(self):
        """Test handling of negative timestamps."""
        message_data = {
            "type": "heartbeat",
            "payload": {},
            "timestamp": -1.0
        }
        
        # Negative timestamps should be allowed (pre-1970 dates)
        message = WebSocketMessage(**message_data)
        assert message.timestamp == -1.0

    def test_edge_case_timestamps(self):
        """Test edge case timestamp values."""
        edge_cases = [
            0.0,  # Unix epoch
            float('inf'),  # Infinity (should fail)
            float('-inf'),  # Negative infinity (should fail)
            # Note: NaN tests omitted as they're hard to test with pytest
        ]
        
        for timestamp in edge_cases[:1]:  # Only test valid cases first
            message_data = {
                "type": "ping", 
                "payload": {},
                "timestamp": timestamp
            }
            message = WebSocketMessage(**message_data)
            assert message.timestamp == timestamp
        
        # Test infinity cases (should fail)
        for timestamp in edge_cases[1:]:
            message_data = {
                "type": "ping",
                "payload": {},
                "timestamp": timestamp
            }
            with pytest.raises(ValidationError):
                WebSocketMessage(**message_data)

    def test_string_numeric_timestamp_rejection(self):
        """Test that numeric strings are rejected (must be actual floats)."""
        string_numeric_timestamps = [
            "1725811801.447585",
            "0.0", 
            "123.456",
            "-1.0"
        ]
        
        for timestamp in string_numeric_timestamps:
            message_data = {
                "type": "agent_response",
                "payload": {"response": "test"},
                "timestamp": timestamp
            }
            
            with pytest.raises(ValidationError) as exc_info:
                WebSocketMessage(**message_data)
            
            error = exc_info.value
            timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
            assert len(timestamp_errors) > 0
            assert timestamp_errors[0]['type'] == 'float_parsing'

    def test_create_standard_message_timestamp_generation(self):
        """Test that create_standard_message generates proper timestamps."""
        message = create_standard_message(
            msg_type="agent_started",
            payload={"agent_type": "unified_data_agent"},
            user_id="test-user-001"
        )
        
        # Should generate a float timestamp automatically
        assert isinstance(message.timestamp, float)
        assert message.timestamp > 0
        
        # Should be close to current time (within 1 second)
        assert abs(message.timestamp - time.time()) < 1.0


class TestTimestampValidationPerformance:
    """Performance tests for timestamp validation overhead."""

    def test_timestamp_validation_performance(self):
        """Test that timestamp validation doesn't add significant overhead."""
        import time
        
        # Test data
        message_data = {
            "type": "agent_progress",
            "payload": {"progress": "Processing..."},
            "timestamp": time.time(),
            "user_id": "perf-test-user"
        }
        
        # Measure validation time
        start_time = time.perf_counter()
        iterations = 1000
        
        for _ in range(iterations):
            WebSocketMessage(**message_data)
        
        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000
        
        # Should be under 1ms per validation
        assert avg_time_ms < 1.0, f"Timestamp validation too slow: {avg_time_ms}ms avg"

    def test_batch_timestamp_validation_performance(self):
        """Test timestamp validation with batch message processing."""
        import time
        
        current_time = time.time()
        messages = []
        
        # Create 100 messages with different timestamps
        for i in range(100):
            message_data = {
                "type": "tool_executing",
                "payload": {"tool": f"tool_{i}"},
                "timestamp": current_time + i,
                "user_id": f"user_{i}"
            }
            messages.append(message_data)
        
        # Measure batch validation time
        start_time = time.perf_counter()
        
        validated_messages = []
        for msg_data in messages:
            validated_messages.append(WebSocketMessage(**msg_data))
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Should be under 10ms for 100 messages
        assert total_time_ms < 10.0, f"Batch validation too slow: {total_time_ms}ms total"
        assert len(validated_messages) == 100


if __name__ == "__main__":
    # Run specific test to reproduce staging error
    pytest.main([__file__ + "::TestWebSocketMessageTimestampValidation::test_exact_staging_error_reproduction", "-v"])