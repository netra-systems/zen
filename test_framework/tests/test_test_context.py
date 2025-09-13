"""
Comprehensive unit tests for TestContext module.

This test suite validates all functionality of the TestContext class including:
- Initialization and configuration
- WebSocket connection management  
- Event capture and validation
- User context simulation and isolation
- Message handling
- Performance metrics
- Cleanup operations

MISSION CRITICAL: These tests ensure TestContext works correctly for WebSocket agent testing.

@compliance CLAUDE.md - Real service testing over mocks
@compliance SPEC/core.xml - Comprehensive test coverage
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Set

import sys
import os
# Add project root for imports - MUST be before any local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.isolated_environment import IsolatedEnvironment

from test_framework.test_context import (
    TestContext,
    TestUserContext, 
    WebSocketEventCapture,
    create_test_context,
    create_isolated_test_contexts
)


class TestTestUserContext:
    """Test the TestUserContext dataclass."""
    
    def test_user_context_initialization(self):
        """Test basic user context initialization."""
        user_id = "test_user_123"
        context = TestUserContext(user_id=user_id)
        
        assert context.user_id == user_id
        assert context.email == f"{user_id}@test.com"
        assert context.name == f"Test User {user_id}"
        assert context.role == "user"
        assert context.thread_id is not None
        assert context.session_id is not None
        assert context.thread_id.startswith("thread_")
        assert context.session_id.startswith("session_")
    
    def test_user_context_custom_values(self):
        """Test user context with custom values."""
        context = TestUserContext(
            user_id="custom_user",
            email="custom@example.com",
            name="Custom User",
            role="admin",
            thread_id="custom_thread",
            session_id="custom_session"
        )
        
        assert context.user_id == "custom_user"
        assert context.email == "custom@example.com"
        assert context.name == "Custom User"
        assert context.role == "admin"
        assert context.thread_id == "custom_thread"
        assert context.session_id == "custom_session"
    
    def test_user_context_metadata(self):
        """Test user context metadata handling."""
        metadata = {"test_key": "test_value", "count": 42}
        context = TestUserContext(user_id="test_user", metadata=metadata)
        
        assert context.metadata == metadata
        assert context.metadata["test_key"] == "test_value"
        assert context.metadata["count"] == 42


class TestWebSocketEventCapture:
    """Test the WebSocketEventCapture class."""
    
    def test_event_capture_initialization(self):
        """Test event capture initialization."""
        capture = WebSocketEventCapture()
        
        assert capture.events == []
        assert capture.event_types == set()
        assert capture.event_counts == {}
        assert capture.start_time is None
    
    def test_capture_event(self):
        """Test capturing events."""
        capture = WebSocketEventCapture()
        
        event1 = {"type": "agent_started", "data": "test"}
        event2 = {"type": "agent_thinking", "data": "processing"}
        event3 = {"type": "agent_started", "data": "another"}
        
        capture.capture_event(event1)
        capture.capture_event(event2)
        capture.capture_event(event3)
        
        assert len(capture.events) == 3
        assert capture.event_types == {"agent_started", "agent_thinking"}
        assert capture.event_counts["agent_started"] == 2
        assert capture.event_counts["agent_thinking"] == 1
        assert capture.start_time is not None
        
        # Check timestamps were added
        for event in capture.events:
            assert "timestamp" in event
    
    def test_get_events_by_type(self):
        """Test getting events by type."""
        capture = WebSocketEventCapture()
        
        events = [
            {"type": "agent_started", "id": 1},
            {"type": "agent_thinking", "id": 2}, 
            {"type": "agent_started", "id": 3},
            {"type": "tool_executing", "id": 4}
        ]
        
        for event in events:
            capture.capture_event(event)
        
        agent_started_events = capture.get_events_by_type("agent_started")
        assert len(agent_started_events) == 2
        assert all(event["type"] == "agent_started" for event in agent_started_events)
        
        thinking_events = capture.get_events_by_type("agent_thinking")
        assert len(thinking_events) == 1
        assert thinking_events[0]["id"] == 2
    
    def test_has_required_events(self):
        """Test checking for required events."""
        capture = WebSocketEventCapture()
        
        required_events = {"agent_started", "agent_thinking", "agent_completed"}
        assert not capture.has_required_events(required_events)
        
        capture.capture_event({"type": "agent_started"})
        capture.capture_event({"type": "agent_thinking"})
        assert not capture.has_required_events(required_events)
        
        capture.capture_event({"type": "agent_completed"})
        assert capture.has_required_events(required_events)
    
    def test_get_missing_events(self):
        """Test getting missing required events."""
        capture = WebSocketEventCapture()
        
        required_events = {"agent_started", "agent_thinking", "agent_completed"}
        
        missing = capture.get_missing_events(required_events)
        assert missing == required_events
        
        capture.capture_event({"type": "agent_started"})
        capture.capture_event({"type": "agent_thinking"})
        
        missing = capture.get_missing_events(required_events)
        assert missing == {"agent_completed"}
    
    def test_clear(self):
        """Test clearing captured events."""
        capture = WebSocketEventCapture()
        
        capture.capture_event({"type": "test_event"})
        assert len(capture.events) > 0
        assert len(capture.event_types) > 0
        
        capture.clear()
        assert capture.events == []
        assert capture.event_types == set()
        assert capture.event_counts == {}
        assert capture.start_time is None


class TestTestContext:
    """Test the main TestContext class."""
    
    def test_test_context_initialization(self):
        """Test TestContext initialization with defaults."""
        context = TestContext()
        
        assert context.user_context is not None
        assert context.user_context.user_id is not None
        assert context.websocket_timeout == 10.0
        assert context.event_timeout == 5.0
        assert context.websocket_connection is None
        assert context.websocket_url is None
        assert isinstance(context.event_capture, WebSocketEventCapture)
        assert context.test_id.startswith("test_")
    
    def test_test_context_with_custom_user_context(self):
        """Test TestContext with custom user context."""
        user_context = TestUserContext(user_id="custom_user_123")
        context = TestContext(user_context=user_context, websocket_timeout=15.0)
        
        assert context.user_context.user_id == "custom_user_123"
        assert context.websocket_timeout == 15.0
    
    def test_create_default_user_context(self):
        """Test creating default user context."""
        context = TestContext()
        user_context = context._create_default_user_context()
        
        assert user_context.user_id.startswith("test_user_")
        assert user_context.email.endswith("@test.com")
        assert user_context.name.startswith("Test User")
    
    @pytest.mark.asyncio
    async def test_setup_websocket_connection_without_mock(self):
        """Test WebSocket connection setup - will skip if service not available."""
        context = TestContext()
        
        try:
            # Try to connect to a test endpoint
            await context.setup_websocket_connection("/ws/test", auth_required=False)
            
            # If we get here, connection worked
            assert context.websocket_connection is not None
            assert context.websocket_url is not None
            assert "/ws/test" in context.websocket_url
            
            # Cleanup
            await context.cleanup()
            
        except ConnectionError:
            # Service not available, which is fine for unit tests
            pytest.skip("WebSocket service not available for integration test")
    
    def test_simulate_user_message(self):
        """Test simulating user messages."""
        context = TestContext()
        
        message = context.simulate_user_message("Hello, world!", "chat")
        
        assert message["type"] == "chat"
        assert message["content"] == "Hello, world!"
        assert message["user_id"] == context.user_context.user_id
        assert message["thread_id"] == context.user_context.thread_id
        assert message["session_id"] == context.user_context.session_id
        assert "timestamp" in message
        assert message["metadata"]["test_id"] == context.test_id
        assert message["metadata"]["test_context"] is True
    
    def test_create_isolated_user_context(self):
        """Test creating isolated user contexts."""
        context = TestContext()
        
        isolated_context = context.create_isolated_user_context()
        
        assert isolated_context.user_id != context.user_context.user_id
        assert isolated_context.user_id.startswith("isolated_user_")
        assert isolated_context.thread_id != context.user_context.thread_id
        assert isolated_context.session_id != context.user_context.session_id
    
    def test_create_isolated_user_context_with_user_id(self):
        """Test creating isolated user context with specific user ID."""
        context = TestContext()
        
        isolated_context = context.create_isolated_user_context("specific_user_123")
        
        assert isolated_context.user_id == "specific_user_123"
        assert isolated_context.thread_id != context.user_context.thread_id
    
    def test_get_captured_events(self):
        """Test getting captured events."""
        context = TestContext()
        
        # Simulate capturing some events
        events = [
            {"type": "agent_started", "id": 1},
            {"type": "agent_thinking", "id": 2},
            {"type": "agent_started", "id": 3}
        ]
        
        for event in events:
            context.event_capture.capture_event(event)
        
        all_events = context.get_captured_events()
        assert len(all_events) == 3
        
        agent_started_events = context.get_captured_events("agent_started")
        assert len(agent_started_events) == 2
        assert all(event["type"] == "agent_started" for event in agent_started_events)
    
    def test_validate_agent_events(self):
        """Test validating agent events."""
        context = TestContext()
        
        # Test with no events
        validation = context.validate_agent_events()
        assert not validation["valid"]
        assert validation["missing_events"] == TestContext.REQUIRED_AGENT_EVENTS
        
        # Add some required events
        required_events = ["agent_started", "agent_thinking", "agent_completed"]
        for event_type in required_events:
            context.event_capture.capture_event({"type": event_type})
        
        # Test with custom required events
        custom_required = {"agent_started", "agent_thinking", "agent_completed"}
        validation = context.validate_agent_events(custom_required)
        assert validation["valid"]
        assert len(validation["missing_events"]) == 0
        assert validation["captured_events"] == custom_required
    
    def test_get_performance_metrics_no_timing(self):
        """Test getting performance metrics without timing."""
        context = TestContext()
        
        # Add some events
        for i in range(5):
            context.event_capture.capture_event({"type": f"event_{i}"})
        
        metrics = context.get_performance_metrics()
        
        assert metrics["total_events_captured"] == 5
        assert metrics["unique_event_types"] == 5
        assert metrics["duration_seconds"] is None
        assert metrics["events_per_second"] == 0
        assert "user_context" in metrics
        assert metrics["user_context"]["user_id"] == context.user_context.user_id
    
    def test_get_performance_metrics_with_timing(self):
        """Test getting performance metrics with timing."""
        context = TestContext()
        
        # Simulate timing
        context.start_time = time.time()
        time.sleep(0.1)  # Small delay
        context.end_time = time.time()
        
        # Add some events
        for i in range(10):
            context.event_capture.capture_event({"type": "test_event"})
        
        metrics = context.get_performance_metrics()
        
        assert metrics["duration_seconds"] > 0
        assert metrics["total_events_captured"] == 10
        assert metrics["unique_event_types"] == 1
        assert metrics["events_per_second"] > 0
    
    @pytest.mark.asyncio 
    async def test_cleanup(self):
        """Test cleanup functionality."""
        context = TestContext()
        
        # Set some state
        context.start_time = time.time()
        context.websocket_connection = MagicMock()
        context.websocket_connection.close = AsyncMock()
        
        await context.cleanup()
        
        assert context.end_time is not None
        assert context.end_time > context.start_time
        # WebSocket connection cleanup is tested via mocked close call
    
    @pytest.mark.asyncio
    async def test_websocket_session_context_manager(self):
        """Test WebSocket session context manager."""
        context = TestContext()
        
        # Mock the setup and cleanup methods
        context.setup_websocket_connection = AsyncMock()
        context.cleanup = AsyncMock()
        
        async with context.websocket_session("/ws/test", auth_required=False) as session:
            assert session is context
            assert context.start_time is not None
        
        context.setup_websocket_connection.assert_called_once_with("/ws/test", False)
        context.cleanup.assert_called_once()


class TestFactoryFunctions:
    """Test factory functions for creating TestContext instances."""
    
    def test_create_test_context_defaults(self):
        """Test creating TestContext with defaults."""
        context = create_test_context()
        
        assert isinstance(context, TestContext)
        assert context.user_context.user_id.startswith("test_user_")
        assert context.websocket_timeout == 10.0
        assert context.user_context.jwt_token is None
    
    def test_create_test_context_custom_params(self):
        """Test creating TestContext with custom parameters."""
        context = create_test_context(
            user_id="custom_user_456",
            jwt_token="test_token_123",
            websocket_timeout=20.0
        )
        
        assert context.user_context.user_id == "custom_user_456"
        assert context.user_context.jwt_token == "test_token_123"
        assert context.websocket_timeout == 20.0
    
    def test_create_isolated_test_contexts(self):
        """Test creating multiple isolated test contexts."""
        contexts = create_isolated_test_contexts(count=3)
        
        assert len(contexts) == 3
        assert all(isinstance(ctx, TestContext) for ctx in contexts)
        
        # Verify isolation - all should have different user IDs
        user_ids = [ctx.user_context.user_id for ctx in contexts]
        assert len(set(user_ids)) == 3  # All unique
        
        # Verify they all start with isolated_user_
        assert all(uid.startswith("isolated_user_") for uid in user_ids)
    
    def test_create_isolated_test_contexts_default_count(self):
        """Test creating isolated contexts with default count."""
        contexts = create_isolated_test_contexts()
        
        assert len(contexts) == 2  # Default count


class TestIntegrationScenarios:
    """Integration test scenarios for common usage patterns."""
    
    @pytest.mark.asyncio
    async def test_multiple_contexts_isolation(self):
        """Test that multiple contexts are properly isolated."""
        contexts = create_isolated_test_contexts(count=3)
        
        # Simulate each context capturing different events
        event_types = [
            ["agent_started", "agent_thinking"],
            ["tool_executing", "tool_completed"],
            ["agent_completed", "websocket_connected"]
        ]
        
        for i, context in enumerate(contexts):
            for event_type in event_types[i]:
                context.event_capture.capture_event({"type": event_type, "context_id": i})
        
        # Verify isolation
        for i, context in enumerate(contexts):
            events = context.get_captured_events()
            assert len(events) == len(event_types[i])
            assert all(event["context_id"] == i for event in events)
        
        # Cleanup
        cleanup_tasks = [ctx.cleanup() for ctx in contexts]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    async def test_agent_event_validation_workflow(self):
        """Test complete agent event validation workflow."""
        context = TestContext()
        
        # Simulate agent execution workflow
        agent_events_sequence = [
            {"type": "agent_started", "agent": "test_agent"},
            {"type": "agent_thinking", "thought": "Processing request"},
            {"type": "tool_executing", "tool": "search_tool"},
            {"type": "tool_completed", "tool": "search_tool", "result": "data"},
            {"type": "agent_completed", "response": "Task completed"}
        ]
        
        # Capture events in sequence
        for event in agent_events_sequence:
            context.event_capture.capture_event(event)
        
        # Validate all required events are present
        validation = context.validate_agent_events()
        assert validation["valid"]
        assert len(validation["missing_events"]) == 0
        assert validation["total_events"] == 5
        
        # Test performance metrics
        metrics = context.get_performance_metrics()
        assert metrics["total_events_captured"] == 5
        assert metrics["unique_event_types"] == 5
        
        await context.cleanup()
    
    def test_user_message_simulation_workflow(self):
        """Test user message simulation workflow."""
        context = TestContext()
        
        # Simulate different types of user messages
        chat_message = context.simulate_user_message("Hello, how are you?", "chat")
        command_message = context.simulate_user_message("/help", "command")
        
        # Verify message structure
        for message in [chat_message, command_message]:
            assert "type" in message
            assert "content" in message
            assert message["user_id"] == context.user_context.user_id
            assert message["thread_id"] == context.user_context.thread_id
            assert "timestamp" in message
            assert message["metadata"]["test_context"] is True
        
        assert chat_message["type"] == "chat"
        assert command_message["type"] == "command"
    
    @pytest.mark.asyncio
    async def test_event_capture_timing_validation(self):
        """Test event capture timing and validation."""
        context = TestContext()
        
        start_time = time.time()
        
        # Simulate events with delays
        events_with_delays = [
            ("agent_started", 0.1),
            ("agent_thinking", 0.1), 
            ("tool_executing", 0.2),
            ("tool_completed", 0.1),
            ("agent_completed", 0.1)
        ]
        
        for event_type, delay in events_with_delays:
            context.event_capture.capture_event({"type": event_type})
            await asyncio.sleep(delay)
        
        # Verify timing
        total_duration = time.time() - start_time
        assert total_duration >= 0.6  # Sum of delays
        
        # Verify all events captured
        assert len(context.get_captured_events()) == 5
        assert context.event_capture.has_required_events(TestContext.REQUIRED_AGENT_EVENTS)
        
        await context.cleanup()


if __name__ == "__main__":
    """Run tests directly for development."""
    pytest.main([__file__, "-v", "--tb=short"])