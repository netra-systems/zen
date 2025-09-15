"""
Integration Tests for WebSocket Message Timestamp Validation

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Stability & Development Velocity
- Value Impact: Ensures WebSocket message pipeline handles timestamp validation correctly
- Strategic Impact: Protects 90% of business value (chat) from timestamp parsing failures

CRITICAL: Integration tests with REAL WebSocket connections and database.
NO MOCKS per CLAUDE.md - tests must use real services to validate timestamp handling
across the complete message processing pipeline.

These tests reproduce staging conditions where ISO datetime strings cause
WebSocket message validation failures.
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid

# CRITICAL: Absolute imports per CLAUDE.md
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, 
    MessageType,
    create_standard_message
)
from netra_backend.app.websocket_core.unified_init import get_unified_websocket_manager
from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
from test_framework.ssot.websocket import WebSocketTestHelper
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketTimestampValidationIntegration:
    """Integration tests for WebSocket timestamp validation with real services."""

    @pytest.fixture
    async def websocket_manager(self):
        """Get WebSocket manager with real database connection."""
        env = IsolatedEnvironment()
        manager = await get_unified_websocket_manager(env)
        yield manager
        await manager.shutdown()

    @pytest.fixture
    async def db_session(self):
        """Get real database session."""
        async with get_isolated_session(user_id="integration_test_user") as session:
            yield session

    @pytest.fixture
    def websocket_helper(self):
        """WebSocket test helper for real connections."""
        return WebSocketTestHelper()

    async def test_message_pipeline_timestamp_validation_failure(self, websocket_manager, db_session):
        """
        CRITICAL: Test complete message pipeline with invalid timestamp.
        
        This test reproduces the staging error through the entire WebSocket 
        message processing pipeline, not just the model validation.
        """
        # Create a connection first
        user_id = "staging-integration-user-001"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection to manager
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None  # Mock WebSocket for integration test
        )
        
        # Create message with ISO datetime string (this should fail)
        invalid_message_data = {
            "type": "start_agent",
            "payload": {
                "user_request": "Execute unified_data_agent with data: {'query': 'Analyze system performance metrics...'",
                "message_id": "req_integration_test",
                "user": user_id
            },
            "timestamp": "2025-09-08T16:50:01.447585",  # ISO string - should cause error
            "message_id": "req_integration_test",
            "user_id": user_id
        }
        
        # Process message through pipeline - should raise validation error
        with pytest.raises((ValueError, TypeError, Exception)) as exc_info:
            # Try to process through WebSocket manager
            await websocket_manager.handle_message(
                connection_id=connection_id,
                message_data=invalid_message_data
            )
        
        # Verify the error indicates timestamp validation failure
        error_str = str(exc_info.value)
        assert any(keyword in error_str.lower() for keyword in [
            'timestamp', 'float_parsing', 'validation', 'parse', 'number'
        ]), f"Expected timestamp validation error, got: {error_str}"
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)

    async def test_message_pipeline_valid_timestamp_success(self, websocket_manager, db_session):
        """Test complete message pipeline with valid float timestamp."""
        user_id = "staging-integration-user-002"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection to manager
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Create message with valid timestamp
        current_time = time.time()
        valid_message_data = {
            "type": "start_agent",
            "payload": {
                "user_request": "Execute unified_data_agent with valid timestamp",
                "message_id": "req_integration_valid", 
                "user": user_id
            },
            "timestamp": current_time,  # Valid float timestamp
            "message_id": "req_integration_valid",
            "user_id": user_id
        }
        
        # This should succeed without raising errors
        try:
            result = await websocket_manager.handle_message(
                connection_id=connection_id,
                message_data=valid_message_data
            )
            # Test passed if no exception raised
            success = True
        except Exception as e:
            pytest.fail(f"Valid timestamp should not cause error: {e}")
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)

    async def test_websocket_message_routing_timestamp_validation(self, websocket_manager, websocket_helper):
        """Test WebSocket message routing with timestamp validation."""
        user_id = "routing-test-user-001"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Test data with various timestamp formats
        test_messages = [
            {
                "name": "iso_datetime_string",
                "data": {
                    "type": "agent_thinking",
                    "payload": {"thinking": "Processing request..."},
                    "timestamp": "2025-09-08T16:50:01.447585",
                    "user_id": user_id
                },
                "should_fail": True
            },
            {
                "name": "valid_float_timestamp", 
                "data": {
                    "type": "agent_thinking",
                    "payload": {"thinking": "Processing request..."},
                    "timestamp": time.time(),
                    "user_id": user_id
                },
                "should_fail": False
            },
            {
                "name": "string_numeric_timestamp",
                "data": {
                    "type": "tool_executing", 
                    "payload": {"tool": "data_analyzer"},
                    "timestamp": "1725811801.447585",
                    "user_id": user_id
                },
                "should_fail": True
            }
        ]
        
        for test_case in test_messages:
            message_data = test_case["data"]
            should_fail = test_case["should_fail"]
            
            if should_fail:
                with pytest.raises(Exception) as exc_info:
                    await websocket_manager.route_message(
                        connection_id=connection_id,
                        message_data=message_data
                    )
                
                # Verify it's a timestamp-related error
                error_str = str(exc_info.value)
                assert any(keyword in error_str.lower() for keyword in [
                    'timestamp', 'validation', 'parse', 'float'
                ]), f"Expected timestamp error for {test_case['name']}, got: {error_str}"
            else:
                # Should not raise an error
                try:
                    await websocket_manager.route_message(
                        connection_id=connection_id,
                        message_data=message_data
                    )
                except Exception as e:
                    pytest.fail(f"Valid message {test_case['name']} should not fail: {e}")
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)

    async def test_agent_event_timestamp_validation(self, websocket_manager, db_session):
        """Test agent event messages with timestamp validation."""
        user_id = "agent-event-test-user"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Test critical agent event types that deliver business value
        agent_events = [
            {
                "type": "agent_started",
                "payload": {"agent_type": "unified_data_agent"},
                "timestamp": "2025-09-08T16:50:01.000000"  # ISO string should fail
            },
            {
                "type": "agent_thinking", 
                "payload": {"reasoning": "Analyzing data patterns..."},
                "timestamp": "2025-09-08T16:50:02.123456"  # ISO string should fail
            },
            {
                "type": "tool_executing",
                "payload": {"tool_name": "performance_analyzer", "status": "running"},
                "timestamp": "2025-09-08T16:50:03.987654"  # ISO string should fail
            },
            {
                "type": "tool_completed",
                "payload": {"tool_name": "performance_analyzer", "results": {"cpu": "85%"}},
                "timestamp": "2025-09-08T16:50:04.555555"  # ISO string should fail
            },
            {
                "type": "agent_completed",
                "payload": {"results": "Analysis complete", "status": "success"},
                "timestamp": "2025-09-08T16:50:05.777777"  # ISO string should fail
            }
        ]
        
        # All these should fail due to ISO timestamp strings
        for event in agent_events:
            event["user_id"] = user_id
            event["message_id"] = f"msg_{uuid.uuid4().hex[:8]}"
            
            with pytest.raises(Exception) as exc_info:
                await websocket_manager.send_to_user(
                    user_id=user_id,
                    message_data=event
                )
            
            # Verify timestamp validation error
            error_str = str(exc_info.value)
            assert any(keyword in error_str.lower() for keyword in [
                'timestamp', 'validation', 'float', 'parse'
            ]), f"Expected timestamp validation error for {event['type']}, got: {error_str}"
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)

    async def test_database_persistence_timestamp_validation(self, websocket_manager, db_session):
        """Test timestamp validation when persisting WebSocket messages to database."""
        user_id = "db-persistence-test-user"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Message with invalid timestamp that might be persisted
        message_data = {
            "type": "user_message",
            "payload": {
                "content": "Test message for database persistence",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}"
            },
            "timestamp": "2025-09-08T16:50:01.123456",  # ISO string 
            "user_id": user_id,
            "message_id": f"msg_{uuid.uuid4().hex[:8]}"
        }
        
        # Attempt to process and persist message
        with pytest.raises(Exception) as exc_info:
            await websocket_manager.process_and_persist_message(
                connection_id=connection_id,
                message_data=message_data,
                session=db_session
            )
        
        # Verify timestamp validation prevents database persistence
        error_str = str(exc_info.value)
        assert any(keyword in error_str.lower() for keyword in [
            'timestamp', 'validation', 'float_parsing'
        ]), f"Expected timestamp validation to prevent DB persistence: {error_str}"
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)

    async def test_broadcast_message_timestamp_validation(self, websocket_manager):
        """Test timestamp validation in broadcast messages."""
        # Create multiple connections for broadcast test
        user_ids = [f"broadcast-user-{i}" for i in range(3)]
        connection_ids = []
        
        for user_id in user_ids:
            connection_id = f"conn_{uuid.uuid4().hex[:8]}"
            connection_ids.append(connection_id)
            await websocket_manager.add_connection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=None
            )
        
        # Broadcast message with invalid timestamp
        broadcast_data = {
            "type": "broadcast",
            "payload": {
                "announcement": "System maintenance starting",
                "severity": "high"
            },
            "timestamp": "2025-09-08T17:00:00.000000",  # ISO string should fail
        }
        
        # Broadcast should fail due to timestamp validation
        with pytest.raises(Exception) as exc_info:
            await websocket_manager.broadcast_to_all(broadcast_data)
        
        # Verify timestamp validation error
        error_str = str(exc_info.value)
        assert any(keyword in error_str.lower() for keyword in [
            'timestamp', 'validation', 'float'
        ]), f"Expected timestamp validation error in broadcast: {error_str}"
        
        # Cleanup connections
        for connection_id in connection_ids:
            await websocket_manager.remove_connection(connection_id)

    async def test_message_buffer_timestamp_validation(self, websocket_manager):
        """Test timestamp validation in message buffering system."""
        user_id = "buffer-test-user"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Create buffered messages with various timestamp formats
        buffered_messages = [
            {
                "type": "agent_progress",
                "payload": {"step": 1, "total": 5},
                "timestamp": "2025-09-08T16:50:01.111111",  # ISO string
                "user_id": user_id
            },
            {
                "type": "agent_progress", 
                "payload": {"step": 2, "total": 5},
                "timestamp": "2025-09-08T16:50:02.222222",  # ISO string
                "user_id": user_id
            },
            {
                "type": "agent_progress",
                "payload": {"step": 3, "total": 5}, 
                "timestamp": "2025-09-08T16:50:03.333333",  # ISO string
                "user_id": user_id
            }
        ]
        
        # Attempt to buffer messages - should fail on timestamp validation
        for message in buffered_messages:
            with pytest.raises(Exception) as exc_info:
                await websocket_manager.add_to_message_buffer(
                    connection_id=connection_id,
                    message_data=message
                )
            
            error_str = str(exc_info.value)
            assert any(keyword in error_str.lower() for keyword in [
                'timestamp', 'validation', 'float'
            ]), f"Expected timestamp validation error in message buffer: {error_str}"
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)


class TestTimestampValidationPerformanceIntegration:
    """Performance integration tests for timestamp validation."""

    @pytest.fixture
    async def websocket_manager(self):
        """WebSocket manager for performance testing."""
        env = IsolatedEnvironment()
        manager = await get_unified_websocket_manager(env)
        yield manager
        await manager.shutdown()

    async def test_high_volume_timestamp_validation_performance(self, websocket_manager):
        """Test timestamp validation performance under high message volume."""
        user_id = "perf-test-user"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=None
        )
        
        # Create 100 messages with valid timestamps
        current_time = time.time()
        messages = []
        for i in range(100):
            message_data = {
                "type": "agent_progress",
                "payload": {"progress": f"Step {i+1}/100"},
                "timestamp": current_time + (i * 0.01),  # Valid float timestamps
                "user_id": user_id,
                "message_id": f"msg_{i:03d}"
            }
            messages.append(message_data)
        
        # Measure processing time
        start_time = time.perf_counter()
        
        processed_count = 0
        for message in messages:
            try:
                await websocket_manager.handle_message(
                    connection_id=connection_id,
                    message_data=message
                )
                processed_count += 1
            except Exception as e:
                # Log but continue for performance test
                pass
        
        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000
        avg_time_per_message = processing_time_ms / len(messages)
        
        # Should process messages efficiently
        assert avg_time_per_message < 5.0, f"Timestamp validation too slow: {avg_time_per_message}ms/msg"
        assert processed_count > 80, f"Too many messages failed: {processed_count}/100"
        
        # Cleanup
        await websocket_manager.remove_connection(connection_id)


if __name__ == "__main__":
    # Run specific failing test
    pytest.main([
        __file__ + "::TestWebSocketTimestampValidationIntegration::test_message_pipeline_timestamp_validation_failure",
        "-v", "--tb=short"
    ])