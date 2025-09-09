"""
Mission Critical Tests for WebSocket Timestamp Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & System Stability
- Value Impact: CRITICAL protection of WebSocket-based chat (90% of business value)
- Strategic Impact: Non-negotiable functionality that must NEVER break

MISSION CRITICAL REQUIREMENTS:
- Fast execution for CI/CD pipeline (<30s total)
- No external dependencies beyond essential services
- Hard failures on any timestamp validation regression
- Protection of core WebSocket chat functionality

This test suite validates the staging error:
"WebSocketMessage timestamp - Input should be a valid number, unable to parse string as a number 
[type=float_parsing, input_value='2025-09-08T16:50:01.447585', input_type=str]"

CRITICAL: If these tests fail, WebSocket chat is BROKEN and deployment must be BLOCKED.
"""

import pytest
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import ValidationError

# CRITICAL: Absolute imports per CLAUDE.md
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, 
    MessageType,
    create_standard_message,
    normalize_message_type
)


class TestWebSocketTimestampValidationCritical:
    """Mission critical tests for timestamp validation - MUST NEVER FAIL."""

    def test_iso_datetime_string_rejection_critical(self):
        """
        MISSION CRITICAL: ISO datetime strings MUST be rejected.
        
        This test MUST FAIL initially to prove timestamp validation is broken.
        After fix, this test MUST ALWAYS PASS or chat is broken.
        """
        # Exact staging error timestamp
        staging_timestamp = "2025-09-08T16:50:01.447585"
        
        message_data = {
            "type": "start_agent",
            "payload": {
                "user_request": "CRITICAL: This timestamp validation MUST work",
                "agent_type": "unified_data_agent"
            },
            "timestamp": staging_timestamp,  # This MUST cause ValidationError
            "user_id": "mission-critical-user",
            "message_id": "critical-test-001"
        }
        
        # HARD REQUIREMENT: This MUST raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(**message_data)
        
        # CRITICAL: Verify exact error type
        error = exc_info.value
        timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
        
        assert len(timestamp_errors) > 0, "CRITICAL: Timestamp validation is BROKEN"
        assert timestamp_errors[0]['type'] == 'float_parsing', "CRITICAL: Wrong error type"
        assert timestamp_errors[0]['input'] == staging_timestamp, "CRITICAL: Wrong input value"

    def test_float_timestamp_acceptance_critical(self):
        """
        MISSION CRITICAL: Float timestamps MUST be accepted.
        
        If this fails, chat is completely broken.
        """
        valid_timestamps = [
            time.time(),  # Current time
            1725811801.447585,  # Staging equivalent timestamp
            0.0,  # Unix epoch
            time.time() + 3600  # Future timestamp
        ]
        
        for timestamp in valid_timestamps:
            message_data = {
                "type": "user_message",
                "payload": {"content": "Test message"},
                "timestamp": timestamp,
                "user_id": "critical-user"
            }
            
            # This MUST NOT raise an error
            try:
                message = WebSocketMessage(**message_data)
                assert message.timestamp == timestamp, "CRITICAL: Timestamp not preserved"
            except Exception as e:
                pytest.fail(f"CRITICAL: Valid timestamp {timestamp} rejected: {e}")

    def test_critical_agent_events_timestamp_validation(self):
        """
        MISSION CRITICAL: Agent events that deliver business value must validate timestamps.
        
        These are the 5 critical events that enable chat functionality:
        1. agent_started - User sees agent began
        2. agent_thinking - Real-time reasoning
        3. tool_executing - Tool usage transparency  
        4. tool_completed - Results delivery
        5. agent_completed - Final response ready
        """
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        iso_timestamp = "2025-09-08T16:50:01.123456"
        
        for event_type in critical_events:
            message_data = {
                "type": event_type,
                "payload": {"status": "critical_test"},
                "timestamp": iso_timestamp,  # ISO string should fail
                "user_id": "critical-events-user"
            }
            
            # Each critical event MUST fail timestamp validation
            with pytest.raises(ValidationError) as exc_info:
                WebSocketMessage(**message_data)
            
            # CRITICAL: Must be timestamp error
            error = exc_info.value
            timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
            assert len(timestamp_errors) > 0, f"CRITICAL: {event_type} timestamp validation broken"

    def test_create_standard_message_timestamp_safety(self):
        """
        MISSION CRITICAL: Standard message creation must generate safe timestamps.
        
        The create_standard_message function MUST generate float timestamps.
        """
        message = create_standard_message(
            msg_type="agent_started",
            payload={"agent": "critical_test"},
            user_id="safety-test-user"
        )
        
        # CRITICAL: Must generate float timestamp
        assert isinstance(message.timestamp, float), "CRITICAL: Non-float timestamp generated"
        assert message.timestamp > 0, "CRITICAL: Invalid timestamp value"
        
        # Must be close to current time (within 2 seconds)
        time_diff = abs(message.timestamp - time.time())
        assert time_diff < 2.0, f"CRITICAL: Generated timestamp too far from current: {time_diff}s"

    def test_timestamp_validation_performance_critical(self):
        """
        MISSION CRITICAL: Timestamp validation must not impact performance.
        
        Validation overhead must be <0.1ms per message to avoid chat lag.
        """
        message_data = {
            "type": "heartbeat",
            "payload": {},
            "timestamp": time.time(),
            "user_id": "perf-user"
        }
        
        # Measure validation time
        start_time = time.perf_counter()
        iterations = 100
        
        for _ in range(iterations):
            WebSocketMessage(**message_data)
            message_data["timestamp"] = time.time()  # Update for next iteration
        
        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000
        
        # CRITICAL: Must be under 0.1ms per validation
        assert avg_time_ms < 0.1, f"CRITICAL: Timestamp validation too slow: {avg_time_ms}ms"

    def test_message_type_normalization_with_timestamp(self):
        """
        MISSION CRITICAL: Message type normalization must work with timestamp validation.
        
        Legacy message types must still validate timestamps correctly.
        """
        legacy_message_types = [
            "agent",  # Maps to AGENT_REQUEST
            "user",   # Maps to USER_MESSAGE  
            "chat",   # Maps to CHAT
            "start_agent",  # Maps to START_AGENT
        ]
        
        iso_timestamp = "2025-09-08T16:50:01.000000"
        
        for legacy_type in legacy_message_types:
            message_data = {
                "type": legacy_type,
                "payload": {"test": "normalization"},
                "timestamp": iso_timestamp,  # Should fail
                "user_id": "normalization-user"
            }
            
            # Legacy types should still enforce timestamp validation
            with pytest.raises(ValidationError) as exc_info:
                WebSocketMessage(**message_data)
            
            # Verify timestamp error (not type error)
            error = exc_info.value
            timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
            assert len(timestamp_errors) > 0, f"CRITICAL: Legacy type {legacy_type} timestamp validation broken"

    def test_none_timestamp_handling_critical(self):
        """
        MISSION CRITICAL: None timestamps must be handled correctly.
        
        Optional timestamps (None) must be allowed without breaking validation.
        """
        message_data = {
            "type": "ping",
            "payload": {},
            "timestamp": None,  # Explicitly None
            "user_id": "none-timestamp-user"
        }
        
        # This MUST work - None is explicitly allowed
        try:
            message = WebSocketMessage(**message_data)
            assert message.timestamp is None, "CRITICAL: None timestamp not preserved"
        except Exception as e:
            pytest.fail(f"CRITICAL: None timestamp rejected: {e}")

    def test_string_numeric_rejection_critical(self):
        """
        MISSION CRITICAL: String numeric values must be rejected.
        
        Even if strings contain valid numbers, they must be rejected to enforce type safety.
        """
        string_numeric_values = [
            "1725811801.447585",  # Staging timestamp as string
            "0.0",
            "123.456",
            "1234567890"
        ]
        
        for string_timestamp in string_numeric_values:
            message_data = {
                "type": "user_typing",
                "payload": {"typing": True},
                "timestamp": string_timestamp,  # String numeric should fail
                "user_id": "string-numeric-user"
            }
            
            with pytest.raises(ValidationError) as exc_info:
                WebSocketMessage(**message_data)
            
            # Must be float parsing error
            error = exc_info.value
            timestamp_errors = [err for err in error.errors() if err['loc'] == ('timestamp',)]
            assert len(timestamp_errors) > 0, f"CRITICAL: String numeric {string_timestamp} not rejected"
            assert timestamp_errors[0]['type'] == 'float_parsing', "CRITICAL: Wrong error type for string numeric"

    def test_edge_case_timestamps_critical(self):
        """
        MISSION CRITICAL: Edge case timestamps must be handled safely.
        
        System must gracefully handle extreme values without crashing.
        """
        # Valid edge cases
        valid_edge_cases = [
            0.0,  # Unix epoch
            -1.0,  # Pre-1970 (should be allowed)
        ]
        
        for timestamp in valid_edge_cases:
            message_data = {
                "type": "system_message",
                "payload": {"message": "edge case test"},
                "timestamp": timestamp,
                "user_id": "edge-case-user"
            }
            
            try:
                message = WebSocketMessage(**message_data)
                assert message.timestamp == timestamp, f"CRITICAL: Edge case {timestamp} not preserved"
            except Exception as e:
                pytest.fail(f"CRITICAL: Valid edge case {timestamp} rejected: {e}")
        
        # Invalid edge cases (should fail gracefully)
        invalid_edge_cases = [
            float('inf'),
            float('-inf')
        ]
        
        for timestamp in invalid_edge_cases:
            message_data = {
                "type": "error_message", 
                "payload": {"error": "test"},
                "timestamp": timestamp,
                "user_id": "invalid-edge-user"
            }
            
            # Should fail validation, not crash
            with pytest.raises(ValidationError):
                WebSocketMessage(**message_data)


class TestCriticalTimestampValidationRegressionPrevention:
    """Regression prevention tests - these must NEVER regress."""

    def test_staging_error_exact_reproduction(self):
        """
        REGRESSION PREVENTION: Exact staging error must be reproducible.
        
        This test locks in the exact error that occurred in staging.
        If this test stops failing after a fix, the fix is working.
        If this test starts passing before a fix, something is wrong.
        """
        # Exact data from staging logs
        exact_staging_data = {
            "type": "start_agent",
            "payload": {
                "user_request": "Execute unified_data_agent with data: {'query': 'Analyze system performance metrics for Q4 2024', 'metrics': ['cpu', 'memory', 'disk'], 'timeframe': '3_months'}",
                "message_id": "req_61eebcb6",
                "user": "staging-e2e-user-001"
            },
            "timestamp": "2025-09-08T16:50:01.447585",  # Exact problematic value
            "message_id": "req_61eebcb6",
            "user_id": "staging-e2e-user-001"
        }
        
        # This MUST raise the exact error
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(**exact_staging_data)
        
        # Lock in exact error characteristics
        error = exc_info.value
        assert len(error.errors()) > 0, "REGRESSION: No validation error raised"
        
        timestamp_error = None
        for err in error.errors():
            if err['loc'] == ('timestamp',):
                timestamp_error = err
                break
        
        assert timestamp_error is not None, "REGRESSION: No timestamp error found"
        assert timestamp_error['type'] == 'float_parsing', "REGRESSION: Wrong error type"
        assert timestamp_error['input'] == '2025-09-08T16:50:01.447585', "REGRESSION: Wrong input value"
        assert 'unable to parse string as a number' in timestamp_error['msg'], "REGRESSION: Wrong error message"

    def test_chat_functionality_protection_critical(self):
        """
        REGRESSION PREVENTION: Chat functionality must be protected from timestamp failures.
        
        The core business value (chat) must never break due to timestamp validation.
        """
        # Simulate chat message with problematic timestamp
        chat_data = {
            "type": "user_message",
            "payload": {
                "content": "Help me analyze my business metrics",
                "thread_id": "chat_thread_001"
            },
            "timestamp": "2025-09-08T16:50:01.999999",  # ISO string
            "user_id": "chat-protection-user"
        }
        
        # Chat MUST be protected by timestamp validation
        with pytest.raises(ValidationError):
            WebSocketMessage(**chat_data)
        
        # But valid chat MUST work
        chat_data["timestamp"] = time.time()
        
        try:
            message = WebSocketMessage(**chat_data)
            assert message.type == MessageType.USER_MESSAGE, "REGRESSION: Chat message type wrong"
            assert isinstance(message.timestamp, float), "REGRESSION: Chat timestamp not float"
        except Exception as e:
            pytest.fail(f"REGRESSION: Valid chat message failed: {e}")


if __name__ == "__main__":
    # Run all critical tests
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=1", "--timeout=30"])