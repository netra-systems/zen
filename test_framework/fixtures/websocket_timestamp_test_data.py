"""
WebSocket Timestamp Test Data Fixtures

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Consistency  
- Value Impact: Centralized test data ensures consistent timestamp validation testing
- Strategic Impact: Prevents test duplication and ensures comprehensive coverage

Test data fixtures for WebSocket timestamp validation tests covering:
- Staging error reproduction data
- Valid/invalid timestamp formats
- Performance test data
- Edge case scenarios
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


class WebSocketTimestampTestData:
    """Centralized test data for WebSocket timestamp validation."""
    
    # EXACT STAGING ERROR DATA
    STAGING_ERROR_TIMESTAMP = "2025-09-08T16:50:01.447585"
    STAGING_ERROR_MESSAGE = {
        "type": "start_agent",
        "payload": {
            "user_request": "Execute unified_data_agent with data: {'query': 'Analyze system performance metrics for Q4 2024', 'metrics': ['cpu', 'memory', 'disk'], 'timeframe': '3_months'}",
            "message_id": "req_61eebcb6",
            "user": "staging-e2e-user-001"
        },
        "timestamp": STAGING_ERROR_TIMESTAMP,
        "message_id": "req_61eebcb6", 
        "user_id": "staging-e2e-user-001"
    }
    
    # ISO DATETIME STRINGS (Should all fail)
    INVALID_ISO_TIMESTAMPS = [
        "2025-09-08T16:50:01.447585",      # Exact staging error
        "2025-01-01T00:00:00.000000",      # New Year
        "2024-12-31T23:59:59.999999",      # Year end
        "2025-09-08T16:50:01Z",            # Zulu time
        "2025-09-08T16:50:01+00:00",       # UTC offset
        "2025-09-08T16:50:01.123+05:00",   # Timezone offset
        "2025-09-08T16:50:01.123456+00:00" # Full precision with timezone
    ]
    
    # VALID FLOAT TIMESTAMPS (Should all pass)
    @classmethod
    def get_valid_timestamps(cls) -> List[float]:
        """Get list of valid float timestamps."""
        current_time = time.time()
        return [
            current_time,                    # Current time
            1725811801.447585,              # Staging equivalent timestamp  
            current_time - 3600,            # 1 hour ago
            current_time + 3600,            # 1 hour from now
            0.0,                            # Unix epoch
            1234567890.123456,              # Arbitrary valid timestamp
            time.time() - 86400,            # 1 day ago
            time.time() + 86400,            # 1 day from now
        ]
    
    # STRING NUMERIC VALUES (Should fail - must be actual floats)
    STRING_NUMERIC_TIMESTAMPS = [
        "1725811801.447585",  # Staging timestamp as string
        "0.0",                # Zero as string
        "123.456",            # Decimal as string
        "1234567890",         # Integer as string
        "-1.0",               # Negative as string
    ]
    
    # INVALID TYPES (Should fail)
    INVALID_TIMESTAMP_TYPES = [
        "not-a-timestamp",    # Non-numeric string
        "123abc",             # Mixed alphanumeric
        [],                   # Empty list
        {},                   # Empty dict
        True,                 # Boolean
        False,                # Boolean
    ]
    
    # EDGE CASE TIMESTAMPS
    VALID_EDGE_CASES = [
        0.0,     # Unix epoch
        -1.0,    # Pre-1970 (should be allowed)
    ]
    
    INVALID_EDGE_CASES = [
        float('inf'),   # Positive infinity
        float('-inf'),  # Negative infinity
        # Note: float('nan') excluded due to testing complexity
    ]
    
    # CRITICAL AGENT EVENT TYPES (for business value testing)
    CRITICAL_AGENT_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    # MESSAGE TEMPLATES
    @classmethod
    def create_message_template(cls, message_type: str = "start_agent", user_id: str = None) -> Dict[str, Any]:
        """Create a message template with placeholders."""
        return {
            "type": message_type,
            "payload": {
                "test": "timestamp_validation",
                "message_id": f"msg_{uuid.uuid4().hex[:8]}"
            },
            "timestamp": None,  # To be filled by test
            "user_id": user_id or f"test_user_{uuid.uuid4().hex[:8]}",
            "message_id": f"msg_{uuid.uuid4().hex[:8]}"
        }
    
    @classmethod
    def create_critical_agent_event_template(cls, event_type: str, user_id: str = None) -> Dict[str, Any]:
        """Create template for critical agent events."""
        payload_map = {
            "agent_started": {"agent_type": "unified_data_agent", "status": "initializing"},
            "agent_thinking": {"reasoning": "Analyzing user request...", "step": 1},
            "tool_executing": {"tool": "performance_analyzer", "status": "running"},
            "tool_completed": {"tool": "performance_analyzer", "results": {"cpu": "85%"}},
            "agent_completed": {"status": "success", "results": "Analysis complete"}
        }
        
        return {
            "type": event_type,
            "payload": payload_map.get(event_type, {"event": event_type}),
            "timestamp": None,  # To be filled by test
            "user_id": user_id or f"agent_test_user_{uuid.uuid4().hex[:8]}",
            "message_id": f"agent_{event_type}_{uuid.uuid4().hex[:8]}"
        }
    
    @classmethod
    def create_chat_message_template(cls, user_id: str = None) -> Dict[str, Any]:
        """Create template for chat messages (90% of business value)."""
        return {
            "type": "user_message",
            "payload": {
                "content": "Help me analyze my business metrics",
                "thread_id": f"chat_thread_{uuid.uuid4().hex[:8]}",
                "conversation_id": f"conv_{uuid.uuid4().hex[:8]}"
            },
            "timestamp": None,  # To be filled by test
            "user_id": user_id or f"chat_user_{uuid.uuid4().hex[:8]}",
            "message_id": f"chat_{uuid.uuid4().hex[:8]}"
        }
    
    @classmethod
    def create_performance_test_messages(cls, count: int = 100) -> List[Dict[str, Any]]:
        """Create batch of messages for performance testing."""
        base_time = time.time()
        messages = []
        
        for i in range(count):
            message = {
                "type": "agent_progress",
                "payload": {
                    "step": i + 1,
                    "total": count,
                    "status": f"processing_{i}",
                    "progress_percent": ((i + 1) / count) * 100
                },
                "timestamp": base_time + (i * 0.01),  # Valid timestamps
                "user_id": f"perf_user_{uuid.uuid4().hex[:8]}",
                "message_id": f"perf_msg_{i:03d}",
                "thread_id": f"perf_thread_{uuid.uuid4().hex[:8]}"
            }
            messages.append(message)
        
        return messages
    
    @classmethod
    def create_multi_user_test_data(cls, user_count: int = 3) -> List[Tuple[str, Dict[str, Any]]]:
        """Create test data for multiple users."""
        test_data = []
        
        for i in range(user_count):
            user_id = f"multi_user_{i}_{uuid.uuid4().hex[:8]}"
            message = {
                "type": "agent_thinking",
                "payload": {
                    "reasoning": f"User {i} processing request...",
                    "step": 1,
                    "total_steps": 5
                },
                "timestamp": cls.STAGING_ERROR_TIMESTAMP,  # Invalid ISO string
                "user_id": user_id,
                "thread_id": f"thread_user_{i}_{uuid.uuid4().hex[:8]}",
                "message_id": f"multi_user_msg_{i}"
            }
            test_data.append((user_id, message))
        
        return test_data
    
    @classmethod
    def get_staging_environment_timestamps(cls) -> List[Dict[str, Any]]:
        """Get various timestamp formats that might appear in staging."""
        return [
            {
                "format": "iso_microseconds",
                "value": "2025-09-08T16:50:01.447585",
                "should_fail": True,
                "description": "Exact staging error format"
            },
            {
                "format": "iso_with_timezone",
                "value": "2025-09-08T16:50:01.447585+00:00", 
                "should_fail": True,
                "description": "ISO with UTC timezone"
            },
            {
                "format": "iso_zulu",
                "value": "2025-09-08T16:50:01.447585Z",
                "should_fail": True,
                "description": "ISO with Zulu time designation"
            },
            {
                "format": "unix_float",
                "value": 1725811801.447585,
                "should_fail": False,
                "description": "Unix timestamp with microseconds"
            },
            {
                "format": "unix_int",
                "value": 1725811801,
                "should_fail": False,
                "description": "Unix timestamp as integer"
            }
        ]


# Convenience functions for test modules
def get_staging_error_data() -> Dict[str, Any]:
    """Get the exact staging error message data."""
    return WebSocketTimestampTestData.STAGING_ERROR_MESSAGE.copy()


def get_invalid_iso_timestamps() -> List[str]:
    """Get list of invalid ISO timestamp strings."""
    return WebSocketTimestampTestData.INVALID_ISO_TIMESTAMPS.copy()


def get_valid_timestamps() -> List[float]:
    """Get list of valid float timestamps."""
    return WebSocketTimestampTestData.get_valid_timestamps()


def create_test_message(message_type: str, timestamp: Any, user_id: str = None) -> Dict[str, Any]:
    """Create a test message with specified timestamp."""
    template = WebSocketTimestampTestData.create_message_template(message_type, user_id)
    template["timestamp"] = timestamp
    return template


def create_critical_agent_event(event_type: str, timestamp: Any, user_id: str = None) -> Dict[str, Any]:
    """Create a critical agent event message with specified timestamp."""
    template = WebSocketTimestampTestData.create_critical_agent_event_template(event_type, user_id)
    template["timestamp"] = timestamp
    return template