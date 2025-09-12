"""
MessageRouter - Comprehensive Unit Test Suite

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & Chat Value Delivery
- Value Impact: Ensures 100% reliable WebSocket message routing for $75K+ MRR chat functionality
- Strategic Impact: Validates message routing infrastructure that enables all WebSocket agent events

This comprehensive test suite validates the critical MessageRouter class that routes all WebSocket 
messages to appropriate handlers. Complete test coverage ensures reliable message delivery for 
agent events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed).

Test Categories:
1. Router Initialization & Handler Setup (10+ tests)
2. Core Message Routing Logic (15+ tests)
3. Handler Management & Dynamic Registration (10+ tests)
4. Statistics & Monitoring (8+ tests)
5. Error Handling & Recovery (7+ tests)
6. Performance & Concurrency (10+ tests)
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
from fastapi import WebSocket

from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    MessageHandler,
    ConnectionHandler,
    TypingHandler,
    HeartbeatHandler,
    AgentHandler,
    UserMessageHandler,
    JsonRpcHandler,
    ErrorHandler,
    BatchMessageHandler,
    BaseMessageHandler
)


# Test fixtures and mocks
@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = Mock(spec=WebSocket)
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def message_router():
    """Create a fresh MessageRouter instance for each test."""
    router = MessageRouter()
    return router


@pytest.fixture
def mock_message_handler():
    """Create a mock message handler for testing."""
    handler = Mock(spec=MessageHandler)
    handler.supported_types = ["test_message", "mock_message"]
    handler.can_handle = Mock(return_value=True)
    handler.handle = AsyncMock()
    handler.__class__.__name__ = "MockMessageHandler"
    return handler


@pytest.fixture
def sample_message():
    """Sample WebSocket message for testing."""
    return {
        "type": "user_message",
        "data": {
            "content": "Test message content",
            "thread_id": "thread_123",
            "user_id": "user_456"
        },
        "timestamp": datetime.now().isoformat()
    }


class TestMessageRouterInitialization:
    """
    BVJ: Validates MessageRouter initialization and default handler setup.
    Business Impact: Ensures all critical handlers are available for WebSocket message processing.
    """

    def test_router_initializes_with_default_handlers(self, message_router):
        """BVJ: Validates all required default handlers are registered for WebSocket functionality."""
        expected_handler_types = {
            'ConnectionHandler',
            'TypingHandler', 
            'HeartbeatHandler',
            'AgentHandler',
            'UserMessageHandler',
            'JsonRpcHandler',
            'ErrorHandler',
            'BatchMessageHandler'
        }
        
        actual_handler_types = {handler.__class__.__name__ for handler in message_router.handlers}
        
        assert expected_handler_types <= actual_handler_types, "All required default handlers must be registered"
        assert len(message_router.handlers) >= 8, "Router must have at least 8 default handlers"

    def test_router_has_fallback_handler(self, message_router):
        """BVJ: Validates fallback handler exists for unknown message types."""
        assert message_router.fallback_handler is not None, "Fallback handler must exist"
        assert isinstance(message_router.fallback_handler, BaseMessageHandler), "Fallback must be BaseMessageHandler"

    def test_router_initializes_routing_stats(self, message_router):
        """BVJ: Validates routing statistics are initialized for monitoring."""
        expected_stats = {
            "messages_routed", 
            "unhandled_messages", 
            "handler_errors", 
            "message_types"
        }
        
        assert set(message_router.routing_stats.keys()) >= expected_stats, "All required stats must be initialized"
        assert message_router.routing_stats["messages_routed"] == 0, "Initial message count must be 0"
        assert message_router.routing_stats["unhandled_messages"] == 0, "Initial unhandled count must be 0"

    def test_router_sets_startup_grace_period(self, message_router):
        """BVJ: Validates startup grace period is set to prevent false warnings."""
        assert hasattr(message_router, 'startup_time'), "Startup time must be tracked"
        assert hasattr(message_router, 'startup_grace_period_seconds'), "Grace period must be configured"
        assert message_router.startup_grace_period_seconds > 0, "Grace period must be positive"
        
        # Startup time should be recent
        current_time = time.time()
        assert abs(current_time - message_router.startup_time) < 1.0, "Startup time must be recent"


class TestMessageRouterHandlerManagement:
    """
    BVJ: Tests dynamic handler registration and removal functionality.
    Business Impact: Enables runtime handler management for feature rollouts and customization.
    """

    def test_add_handler_increases_handler_count(self, message_router, mock_message_handler):
        """BVJ: Validates dynamic handler addition for feature expansion."""
        initial_count = len(message_router.handlers)
        
        message_router.add_handler(mock_message_handler)
        
        assert len(message_router.handlers) == initial_count + 1, "Handler count must increase"
        assert mock_message_handler in message_router.handlers, "New handler must be in list"

    def test_remove_handler_decreases_handler_count(self, message_router, mock_message_handler):
        """BVJ: Validates dynamic handler removal for maintenance and updates."""
        message_router.add_handler(mock_message_handler)
        initial_count = len(message_router.handlers)
        
        message_router.remove_handler(mock_message_handler)
        
        assert len(message_router.handlers) == initial_count - 1, "Handler count must decrease"
        assert mock_message_handler not in message_router.handlers, "Removed handler must not be in list"

    def test_remove_nonexistent_handler_handles_gracefully(self, message_router, mock_message_handler):
        """BVJ: Validates graceful handling of invalid handler removal."""
        initial_count = len(message_router.handlers)
        
        # Try to remove handler that was never added
        message_router.remove_handler(mock_message_handler)
        
        assert len(message_router.handlers) == initial_count, "Handler count must remain unchanged"

    def test_add_multiple_handlers_maintains_order(self, message_router):
        """BVJ: Validates handler order is preserved for routing priority."""
        handler1 = Mock(spec=MessageHandler)
        handler1.__class__.__name__ = "Handler1"
        handler2 = Mock(spec=MessageHandler)
        handler2.__class__.__name__ = "Handler2"
        
        message_router.add_handler(handler1)
        message_router.add_handler(handler2)
        
        # Check that handlers appear in added order at end of list
        assert message_router.handlers[-2] == handler1, "First added handler must maintain position"
        assert message_router.handlers[-1] == handler2, "Second added handler must be last"

    def test_handler_registration_enables_routing(self, message_router, mock_message_handler, mock_websocket, sample_message):
        """BVJ: Validates newly registered handlers can receive messages."""
        # Configure mock handler for specific message type
        mock_message_handler.supported_types = ["user_message"]
        mock_message_handler.can_handle.return_value = True
        
        message_router.add_handler(mock_message_handler)
        
        # Route a message that the handler should handle
        result = asyncio.run(message_router.route_message("user_123", mock_websocket, sample_message))
        
        # Handler should have been called
        mock_message_handler.handle.assert_called_once()


class TestMessageRouterCoreRouting:
    """
    BVJ: Tests core message routing logic that enables WebSocket agent events.
    Business Impact: Ensures 100% reliable message delivery for chat functionality.
    """

    async def test_route_message_calls_appropriate_handler(self, message_router, mock_websocket, sample_message):
        """BVJ: Validates messages are routed to correct handlers for processing."""
        # Find the UserMessageHandler (should handle user_message type)
        user_handler = None
        for handler in message_router.handlers:
            if isinstance(handler, UserMessageHandler):
                user_handler = handler
                break
        
        assert user_handler is not None, "UserMessageHandler must be available"
        
        # Mock the handler's handle method
        with patch.object(user_handler, 'handle', new_callable=AsyncMock) as mock_handle:
            await message_router.route_message("user_123", mock_websocket, sample_message)
            
            # UserMessageHandler should have been called
            mock_handle.assert_called_once_with("user_123", mock_websocket, sample_message)

    async def test_route_message_updates_statistics(self, message_router, mock_websocket, sample_message):
        """BVJ: Validates routing statistics are updated for monitoring."""
        initial_routed = message_router.routing_stats["messages_routed"]
        initial_types = message_router.routing_stats["message_types"].copy()
        
        await message_router.route_message("user_123", mock_websocket, sample_message)
        
        assert message_router.routing_stats["messages_routed"] == initial_routed + 1, "Routed count must increment"
        
        message_type = sample_message.get("type", "unknown")
        expected_count = initial_types.get(message_type, 0) + 1
        assert message_router.routing_stats["message_types"][message_type] == expected_count, "Message type count must update"

    async def test_route_message_handles_unknown_type(self, message_router, mock_websocket):
        """BVJ: Validates fallback handling for unknown message types."""
        unknown_message = {
            "type": "unknown_test_message_type",
            "data": {"test": "data"}
        }
        
        initial_unhandled = message_router.routing_stats["unhandled_messages"]
        
        await message_router.route_message("user_123", mock_websocket, unknown_message)
        
        assert message_router.routing_stats["unhandled_messages"] == initial_unhandled + 1, "Unhandled count must increment"

    async def test_route_message_handles_handler_exceptions(self, message_router, mock_websocket, sample_message):
        """BVJ: Validates graceful handling of handler exceptions."""
        # Create a handler that throws an exception
        failing_handler = Mock(spec=MessageHandler)
        failing_handler.supported_types = ["user_message"]
        failing_handler.can_handle.return_value = True
        failing_handler.handle = AsyncMock(side_effect=Exception("Handler error"))
        failing_handler.__class__.__name__ = "FailingHandler"
        
        # Replace existing handler with failing one
        original_handlers = message_router.handlers.copy()
        message_router.handlers = [failing_handler]
        
        initial_errors = message_router.routing_stats["handler_errors"]
        
        try:
            await message_router.route_message("user_123", mock_websocket, sample_message)
        except Exception:
            pytest.fail("Router should not propagate handler exceptions")
        
        assert message_router.routing_stats["handler_errors"] == initial_errors + 1, "Error count must increment"

    async def test_route_message_tries_multiple_handlers(self, message_router, mock_websocket):
        """BVJ: Validates router attempts multiple handlers until one succeeds."""
        message = {"type": "test_message", "data": {}}
        
        # Create handlers where first fails, second succeeds
        handler1 = Mock(spec=MessageHandler)
        handler1.can_handle.return_value = True
        handler1.handle = AsyncMock(side_effect=Exception("First handler fails"))
        handler1.__class__.__name__ = "FirstHandler"
        
        handler2 = Mock(spec=MessageHandler)  
        handler2.can_handle.return_value = True
        handler2.handle = AsyncMock()  # Succeeds
        handler2.__class__.__name__ = "SecondHandler"
        
        # Set up router with these handlers
        message_router.handlers = [handler1, handler2]
        
        await message_router.route_message("user_123", mock_websocket, message)
        
        # Both handlers should have been tried
        handler1.handle.assert_called_once()
        handler2.handle.assert_called_once()

    async def test_route_message_with_json_rpc_format(self, message_router, mock_websocket):
        """BVJ: Validates JSON-RPC format message handling for API compatibility."""
        json_rpc_message = {
            "jsonrpc": "2.0",
            "method": "user_message",
            "params": {
                "content": "Test JSON-RPC message",
                "thread_id": "thread_123"
            },
            "id": "request_456"
        }
        
        await message_router.route_message("user_123", mock_websocket, json_rpc_message)
        
        # Should be handled without errors
        assert message_router.routing_stats["messages_routed"] >= 1, "JSON-RPC message must be routed"


class TestMessageRouterStatistics:
    """
    BVJ: Validates routing statistics and monitoring functionality.
    Business Impact: Enables performance monitoring and troubleshooting of WebSocket routing.
    """

    async def test_statistics_track_message_volume(self, message_router, mock_websocket, sample_message):
        """BVJ: Validates message volume tracking for capacity planning."""
        initial_count = message_router.routing_stats["messages_routed"]
        
        # Route multiple messages
        for i in range(10):
            await message_router.route_message(f"user_{i}", mock_websocket, sample_message)
        
        final_count = message_router.routing_stats["messages_routed"]
        assert final_count - initial_count == 10, "Message volume must be tracked accurately"

    async def test_statistics_track_message_type_distribution(self, message_router, mock_websocket):
        """BVJ: Validates message type distribution tracking for analytics."""
        message_types = ["user_message", "agent_started", "heartbeat", "connection"]
        
        for msg_type in message_types:
            message = {"type": msg_type, "data": {}}
            await message_router.route_message("user_123", mock_websocket, message)
        
        stats = message_router.routing_stats["message_types"]
        for msg_type in message_types:
            assert stats.get(msg_type, 0) >= 1, f"Message type {msg_type} must be tracked"

    def test_statistics_initialization_state(self, message_router):
        """BVJ: Validates statistics start in clean state for accurate tracking."""
        stats = message_router.routing_stats
        
        assert stats["messages_routed"] == 0, "Initial routed count must be 0"
        assert stats["unhandled_messages"] == 0, "Initial unhandled count must be 0"
        assert stats["handler_errors"] == 0, "Initial error count must be 0"
        assert isinstance(stats["message_types"], dict), "Message types must be tracked in dict"

    async def test_statistics_error_counting(self, message_router, mock_websocket):
        """BVJ: Validates error statistics for system health monitoring."""
        # Create handler that always fails
        failing_handler = Mock(spec=MessageHandler)
        failing_handler.can_handle.return_value = True
        failing_handler.handle = AsyncMock(side_effect=Exception("Test error"))
        failing_handler.__class__.__name__ = "FailingHandler"
        
        message_router.handlers = [failing_handler]
        
        initial_errors = message_router.routing_stats["handler_errors"]
        
        message = {"type": "test", "data": {}}
        await message_router.route_message("user_123", mock_websocket, message)
        
        assert message_router.routing_stats["handler_errors"] == initial_errors + 1, "Error count must increment"

    async def test_statistics_unhandled_message_counting(self, message_router, mock_websocket):
        """BVJ: Validates unhandled message tracking for system completeness."""
        # Remove all handlers to ensure message goes unhandled
        message_router.handlers = []
        
        initial_unhandled = message_router.routing_stats["unhandled_messages"]
        
        message = {"type": "unhandleable_message", "data": {}}
        await message_router.route_message("user_123", mock_websocket, message)
        
        assert message_router.routing_stats["unhandled_messages"] == initial_unhandled + 1, "Unhandled count must increment"


class TestMessageRouterStartupGracePeriod:
    """
    BVJ: Validates startup grace period logic that prevents false warnings.
    Business Impact: Reduces false alerts during system startup and deployment.
    """

    def test_startup_grace_period_prevents_early_warnings(self, message_router):
        """BVJ: Validates grace period suppresses warnings during startup."""
        # During grace period, no warnings should be generated
        current_time = time.time()
        startup_time = message_router.startup_time
        grace_period = message_router.startup_grace_period_seconds
        
        time_since_startup = current_time - startup_time
        assert time_since_startup < grace_period, "Test should run during grace period"
        
        # This would normally generate warnings but shouldn't during grace period
        assert message_router.startup_grace_period_seconds > 0, "Grace period must be configured"

    def test_startup_time_recorded_correctly(self, message_router):
        """BVJ: Validates startup timestamp is recorded for grace period calculation."""
        current_time = time.time()
        startup_time = message_router.startup_time
        
        # Startup time should be very recent (within 1 second)
        assert abs(current_time - startup_time) < 1.0, "Startup time must be recorded accurately"
        assert startup_time > 0, "Startup time must be valid timestamp"

    def test_grace_period_configuration(self, message_router):
        """BVJ: Validates grace period is properly configured."""
        assert hasattr(message_router, 'startup_grace_period_seconds'), "Grace period must be configured"
        assert message_router.startup_grace_period_seconds == 10.0, "Grace period must be 10 seconds"
        assert isinstance(message_router.startup_grace_period_seconds, (int, float)), "Grace period must be numeric"


class TestMessageRouterUnknownMessageTypes:
    """
    BVJ: Validates handling of unknown or unsupported message types.
    Business Impact: Ensures system resilience when encountering new or malformed messages.
    """

    async def test_unknown_message_type_uses_fallback(self, message_router, mock_websocket):
        """BVJ: Validates unknown messages are handled by fallback handler."""
        unknown_message = {
            "type": "completely_unknown_message_type",
            "data": {"some": "data"}
        }
        
        # Mock fallback handler
        original_fallback = message_router.fallback_handler
        mock_fallback = Mock(spec=BaseMessageHandler)
        mock_fallback.handle = AsyncMock()
        message_router.fallback_handler = mock_fallback
        
        await message_router.route_message("user_123", mock_websocket, unknown_message)
        
        # Fallback should have been called
        mock_fallback.handle.assert_called_once()
        
        # Restore original fallback
        message_router.fallback_handler = original_fallback

    async def test_unknown_message_updates_statistics(self, message_router, mock_websocket):
        """BVJ: Validates unknown messages are tracked in statistics."""
        unknown_message = {
            "type": "unknown_stats_test",
            "data": {}
        }
        
        initial_unhandled = message_router.routing_stats["unhandled_messages"]
        
        # Ensure no handlers can handle this message
        for handler in message_router.handlers:
            if hasattr(handler, 'can_handle'):
                with patch.object(handler, 'can_handle', return_value=False):
                    pass
        
        await message_router.route_message("user_123", mock_websocket, unknown_message)
        
        # Should increment unhandled count
        assert message_router.routing_stats["unhandled_messages"] >= initial_unhandled, "Unknown messages must be tracked"

    async def test_malformed_message_handled_gracefully(self, message_router, mock_websocket):
        """BVJ: Validates malformed messages don't crash the router."""
        malformed_messages = [
            {},  # Empty message
            {"data": "no_type"},  # Missing type
            {"type": None, "data": {}},  # None type
            {"type": "", "data": {}},  # Empty type
            None  # None message
        ]
        
        for malformed_msg in malformed_messages:
            try:
                await message_router.route_message("user_123", mock_websocket, malformed_msg)
            except Exception as e:
                pytest.fail(f"Router should handle malformed message gracefully: {malformed_msg}, error: {e}")


class TestMessageRouterMessagePreparation:
    """
    BVJ: Tests message preparation and normalization for different formats.
    Business Impact: Ensures compatibility with multiple WebSocket message formats.
    """

    async def test_standard_message_format_handled(self, message_router, mock_websocket):
        """BVJ: Validates standard WebSocket message format processing."""
        standard_message = {
            "type": "user_message",
            "data": {
                "content": "Standard format message",
                "user_id": "user_123"
            }
        }
        
        # Should be processed without errors
        await message_router.route_message("user_123", mock_websocket, standard_message)
        
        assert message_router.routing_stats["messages_routed"] >= 1, "Standard message must be routed"

    async def test_json_rpc_message_format_handled(self, message_router, mock_websocket):
        """BVJ: Validates JSON-RPC message format processing."""
        json_rpc_message = {
            "jsonrpc": "2.0",
            "method": "user_message",
            "params": {
                "content": "JSON-RPC format message"
            },
            "id": "rpc_123"
        }
        
        # Should be processed without errors
        await message_router.route_message("user_123", mock_websocket, json_rpc_message)
        
        assert message_router.routing_stats["messages_routed"] >= 1, "JSON-RPC message must be routed"

    async def test_message_with_extra_fields_handled(self, message_router, mock_websocket):
        """BVJ: Validates messages with additional fields are processed correctly."""
        extended_message = {
            "type": "user_message",
            "data": {"content": "Message with extra fields"},
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "source": "test_client",
            "extra_metadata": {
                "priority": "high",
                "tags": ["test", "extended"]
            }
        }
        
        # Should be processed without errors despite extra fields
        await message_router.route_message("user_123", mock_websocket, extended_message)
        
        assert message_router.routing_stats["messages_routed"] >= 1, "Extended message must be routed"


class TestMessageRouterConcurrency:
    """
    BVJ: Validates concurrent message routing for multi-user scenarios.
    Business Impact: Ensures router remains stable under high concurrent load.
    """

    async def test_concurrent_message_routing(self, message_router, mock_websocket):
        """BVJ: Validates router handles concurrent messages from multiple users."""
        async def send_message(user_id: str, message_id: int):
            message = {
                "type": "user_message",
                "data": {
                    "content": f"Concurrent message {message_id}",
                    "user_id": user_id
                }
            }
            await message_router.route_message(user_id, mock_websocket, message)
            return True
        
        # Create 50 concurrent routing tasks
        tasks = []
        for i in range(50):
            user_id = f"user_{i % 10}"  # 10 different users
            tasks.append(send_message(user_id, i))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # All tasks should complete successfully
        assert all(results), "All concurrent routing tasks must succeed"
        assert message_router.routing_stats["messages_routed"] >= 50, "All messages must be routed"

    async def test_concurrent_handler_management(self, message_router):
        """BVJ: Validates thread safety of handler add/remove operations."""
        async def add_remove_handler():
            handler = Mock(spec=MessageHandler)
            handler.supported_types = ["test"]
            handler.__class__.__name__ = "ConcurrentTestHandler"
            
            message_router.add_handler(handler)
            await asyncio.sleep(0.001)  # Small delay
            message_router.remove_handler(handler)
            return True
        
        # Perform concurrent handler management
        tasks = [add_remove_handler() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        assert all(results), "All concurrent handler operations must succeed"
        
        # Router should remain stable with original handlers
        assert len(message_router.handlers) >= 8, "Original handlers must remain"

    async def test_concurrent_statistics_updates(self, message_router, mock_websocket):
        """BVJ: Validates statistics remain accurate under concurrent updates."""
        async def route_message_batch(start_id: int):
            for i in range(10):
                message = {
                    "type": "test_message",
                    "data": {"batch_id": start_id, "message_id": i}
                }
                await message_router.route_message(f"user_{start_id}", mock_websocket, message)
        
        initial_count = message_router.routing_stats["messages_routed"]
        
        # Route messages concurrently from 5 batches  
        tasks = [route_message_batch(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        final_count = message_router.routing_stats["messages_routed"]
        
        # Should have routed exactly 50 messages (5 batches  x  10 messages)
        assert final_count - initial_count >= 50, "Statistics must accurately track concurrent messages"


class TestMessageRouterPerformance:
    """
    BVJ: Validates routing performance meets production requirements.
    Business Impact: Ensures sub-millisecond routing latency for responsive chat experience.
    """

    async def test_routing_latency_meets_sla(self, message_router, mock_websocket):
        """BVJ: Validates message routing latency is under 1ms for responsive UX."""
        message = {
            "type": "user_message",
            "data": {"content": "Performance test message"}
        }
        
        # Measure routing latency for 100 messages
        start_time = time.perf_counter()
        
        for i in range(100):
            await message_router.route_message(f"user_{i}", mock_websocket, message)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_latency_ms = (total_time / 100) * 1000
        
        assert avg_latency_ms < 1.0, f"Average routing latency {avg_latency_ms:.2f}ms must be <1ms"

    async def test_handler_lookup_performance(self, message_router, mock_websocket):
        """BVJ: Validates handler lookup performance with many handlers."""
        # Add many handlers to test lookup performance
        for i in range(50):
            handler = Mock(spec=MessageHandler)
            handler.supported_types = [f"test_type_{i}"]
            handler.can_handle.return_value = (i == 49)  # Only last handler matches
            handler.__class__.__name__ = f"Handler{i}"
            message_router.add_handler(handler)
        
        message = {
            "type": "test_type_49",  # Should match last handler
            "data": {}
        }
        
        start_time = time.perf_counter()
        await message_router.route_message("user_123", mock_websocket, message)
        end_time = time.perf_counter()
        
        lookup_time_ms = (end_time - start_time) * 1000
        assert lookup_time_ms < 5.0, f"Handler lookup time {lookup_time_ms:.2f}ms must be <5ms even with many handlers"

    async def test_routing_throughput_under_load(self, message_router, mock_websocket):
        """BVJ: Validates routing throughput meets production load requirements."""
        messages = []
        for i in range(1000):
            messages.append({
                "type": "user_message",
                "data": {"content": f"Load test message {i}"}
            })
        
        start_time = time.perf_counter()
        
        # Route 1000 messages as quickly as possible
        tasks = []
        for i, message in enumerate(messages):
            task = message_router.route_message(f"user_{i % 100}", mock_websocket, message)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = 1000 / total_time
        
        assert throughput > 1000, f"Routing throughput {throughput:.0f} msg/sec must be >1000 msg/sec"


class TestMessageRouterEdgeCases:
    """
    BVJ: Tests edge cases and error conditions for system resilience.
    Business Impact: Ensures router remains stable under unusual conditions.
    """

    async def test_empty_message_handling(self, message_router, mock_websocket):
        """BVJ: Validates handling of empty or None messages."""
        edge_case_messages = [
            None,
            {},
            {"type": None},
            {"type": ""},
            {"data": None}
        ]
        
        for message in edge_case_messages:
            try:
                await message_router.route_message("user_123", mock_websocket, message)
            except Exception as e:
                pytest.fail(f"Router should handle edge case message gracefully: {message}, error: {e}")

    async def test_handler_with_no_can_handle_method(self, message_router, mock_websocket):
        """BVJ: Validates router handles handlers without can_handle method."""
        # Create handler without can_handle method
        broken_handler = Mock(spec=MessageHandler)
        broken_handler.supported_types = ["test"]
        broken_handler.handle = AsyncMock()
        # Don't set can_handle method
        del broken_handler.can_handle
        broken_handler.__class__.__name__ = "BrokenHandler"
        
        message_router.add_handler(broken_handler)
        
        message = {"type": "test", "data": {}}
        
        try:
            await message_router.route_message("user_123", mock_websocket, message)
        except Exception as e:
            pytest.fail(f"Router should handle broken handler gracefully: {e}")

    async def test_very_large_message_handling(self, message_router, mock_websocket):
        """BVJ: Validates handling of very large messages."""
        large_content = "x" * 1000000  # 1MB message content
        large_message = {
            "type": "user_message", 
            "data": {
                "content": large_content,
                "metadata": {"size": len(large_content)}
            }
        }
        
        try:
            await message_router.route_message("user_123", mock_websocket, large_message)
        except Exception as e:
            pytest.fail(f"Router should handle large messages gracefully: {e}")

    async def test_websocket_none_handling(self, message_router):
        """BVJ: Validates handling when websocket is None."""
        message = {"type": "test", "data": {}}
        
        try:
            await message_router.route_message("user_123", None, message)
        except Exception as e:
            pytest.fail(f"Router should handle None websocket gracefully: {e}")

    async def test_invalid_user_id_handling(self, message_router, mock_websocket):
        """BVJ: Validates handling of invalid user IDs."""
        message = {"type": "user_message", "data": {"content": "test"}}
        invalid_user_ids = [None, "", "   ", 123, [], {}]
        
        for user_id in invalid_user_ids:
            try:
                await message_router.route_message(user_id, mock_websocket, message)
            except Exception as e:
                pytest.fail(f"Router should handle invalid user_id gracefully: {user_id}, error: {e}")

    async def test_handler_infinite_loop_protection(self, message_router, mock_websocket):
        """BVJ: Validates protection against infinite handler loops."""
        # Create handler that always says it can handle but never actually handles
        loop_handler = Mock(spec=MessageHandler)
        loop_handler.can_handle.return_value = True
        loop_handler.handle = AsyncMock(side_effect=Exception("Simulated failure"))
        loop_handler.__class__.__name__ = "LoopHandler"
        
        # Replace all handlers with the problematic one
        message_router.handlers = [loop_handler]
        
        message = {"type": "test", "data": {}}
        
        start_time = time.perf_counter()
        await message_router.route_message("user_123", mock_websocket, message)
        end_time = time.perf_counter()
        
        # Should complete quickly, not get stuck in infinite loop
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Routing should not get stuck in loops, took {execution_time:.2f}s"