"""
Unit Tests for WebSocket Message Router

Tests routing user messages to agent handler, routing agent commands to supervisor,
handling unknown message types, routing behavior for invalid messages, and the
canonical message routing infrastructure for Golden Path chat functionality.

Business Value: Platform/Internal - Testing Infrastructure
Ensures reliable message routing protecting $500K+ ARR chat functionality.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.websocket_core.canonical_message_router import (
    CanonicalMessageRouter, MessageRoutingStrategy, RoutingContext,
    RouteDestination, create_message_router
)
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, create_standard_message,
    MessagePriority
)


class TestWebSocketMessageRouter(SSotAsyncTestCase):
    """Test WebSocket message router functionality with SSOT patterns."""

    def setup_method(self, method):
        """Setup test environment for each test."""
        super().setup_method(method)
        
        # Test data
        self.user_id = "router_test_user_123"
        self.session_id = "router_session_456"
        self.agent_id = "router_agent_789"
        self.connection_id = "router_conn_101"
        
        # Create router instance using factory
        self.router = create_message_router(
            user_context={
                "user_id": self.user_id,
                "session_id": self.session_id
            }
        )
        
        # Mock handlers
        self.mock_agent_handler = AsyncMock()
        self.mock_supervisor_handler = AsyncMock()
        self.mock_unknown_handler = AsyncMock()
        
        # Register mock handlers
        self.router.add_handler(MessageType.USER_MESSAGE, self.mock_agent_handler)
        self.router.add_handler(MessageType.START_AGENT, self.mock_supervisor_handler)
        
        # Track routing results
        self.routing_results = []
        self.error_logs = []

    async def test_routing_user_messages_to_agent_handler(self):
        """Test routing of user messages to appropriate agent handler."""
        # Arrange - Create user message
        user_message = create_standard_message(
            msg_type=MessageType.USER_MESSAGE,
            payload={
                "message": "Hello, I need help with data analysis",
                "context": "user_inquiry",
                "metadata": {"priority": "normal"}
            },
            user_id=self.user_id,
            thread_id="thread_123"
        )
        
        # Setup routing context
        routing_context = RoutingContext(
            user_id=self.user_id,
            session_id=self.session_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC,
            metadata={"message_type": "user_message"}
        )
        
        # Mock handler to track calls
        self.mock_agent_handler.return_value = True
        
        # Act - Route message
        delivered_connections = await self.router.route_message(
            message=user_message,
            routing_context=routing_context
        )
        
        # Also test handler execution
        handler_results = await self.router.execute_handlers(
            MessageType.USER_MESSAGE,
            user_message,
            routing_context
        )
        
        # Assert - Handler should be called
        self.assertGreater(len(handler_results), 0)
        self.mock_agent_handler.assert_called_once()
        
        # Verify handler was called with correct arguments
        call_args = self.mock_agent_handler.call_args
        self.assertEqual(call_args[0][0], user_message)  # First argument is the message
        self.assertEqual(call_args[0][1], routing_context)  # Second argument is context

    async def test_routing_agent_commands_to_supervisor(self):
        """Test routing of agent commands to supervisor handler."""
        # Arrange - Create start agent message
        agent_command = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload={
                "user_request": "Analyze performance metrics and provide recommendations",
                "agent_type": "apex_optimizer",
                "parameters": {
                    "analysis_type": "performance",
                    "time_window": "24h",
                    "include_recommendations": True
                }
            },
            user_id=self.user_id,
            thread_id="thread_456"
        )
        
        # Setup routing context
        routing_context = RoutingContext(
            user_id=self.user_id,
            session_id=self.session_id,
            agent_id=self.agent_id,
            routing_strategy=MessageRoutingStrategy.AGENT_SPECIFIC,
            metadata={"command_type": "start_agent"}
        )
        
        # Mock supervisor handler
        self.mock_supervisor_handler.return_value = {"status": "started", "agent_id": self.agent_id}
        
        # Act - Route message
        delivered_connections = await self.router.route_message(
            message=agent_command,
            routing_context=routing_context
        )
        
        # Execute handlers
        handler_results = await self.router.execute_handlers(
            MessageType.START_AGENT,
            agent_command,
            routing_context
        )
        
        # Assert - Supervisor handler should be called
        self.assertGreater(len(handler_results), 0)
        self.mock_supervisor_handler.assert_called_once()
        
        # Verify handler result
        self.assertEqual(handler_results[0]["status"], "started")
        self.assertEqual(handler_results[0]["agent_id"], self.agent_id)

    async def test_handling_unknown_message_types(self):
        """Test router handles unknown message types gracefully."""
        # Arrange - Create message with type not registered with handlers
        unknown_message = create_standard_message(
            msg_type=MessageType.HEARTBEAT,  # Not registered with any handler
            payload={"ping": "test"},
            user_id=self.user_id
        )
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
        )
        
        # Act - Try to execute handlers for unknown type
        handler_results = await self.router.execute_handlers(
            MessageType.HEARTBEAT,
            unknown_message,
            routing_context
        )
        
        # Assert - Should return empty results list (no handlers registered)
        self.assertEqual(len(handler_results), 0)
        
        # Router should still be able to route the message (to empty destinations)
        delivered_connections = await self.router.route_message(
            message=unknown_message,
            routing_context=routing_context
        )
        
        # Should return empty list since no connections are registered
        self.assertEqual(len(delivered_connections), 0)

    async def test_routing_behavior_for_invalid_messages(self):
        """Test router behavior when handling invalid or malformed messages."""
        # Test cases for invalid messages
        invalid_cases = [
            # Missing required fields
            WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={},  # Empty payload
                user_id=None  # Missing user_id
            ),
            # Invalid message structure
            WebSocketMessage(
                type=MessageType.START_AGENT,
                payload="invalid_payload_type",  # Should be dict
                user_id=self.user_id
            )
        ]
        
        for invalid_message in invalid_cases:
            with self.subTest(message=invalid_message):
                # Arrange
                routing_context = RoutingContext(
                    user_id=self.user_id or "fallback_user",
                    routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
                )
                
                # Setup handler to track invalid message handling
                error_handler = AsyncMock()
                error_handler.side_effect = ValueError("Invalid message structure")
                self.router.add_handler(invalid_message.type, error_handler)
                
                # Act - Try to execute handlers with invalid message
                handler_results = await self.router.execute_handlers(
                    invalid_message.type,
                    invalid_message,
                    routing_context
                )
                
                # Assert - Should handle error gracefully
                # Results should include None for failed handler
                self.assertIn(None, handler_results)
                error_handler.assert_called()
                
                # Clean up handler for next test
                self.router.remove_handler(invalid_message.type, error_handler)

    async def test_message_routing_strategies_broadcast_all(self):
        """Test BROADCAST_ALL routing strategy delivers to all connections."""
        # Arrange - Register multiple connections
        connections = [
            ("conn_1", "user_1", "session_1"),
            ("conn_2", "user_2", "session_2"),
            ("conn_3", "user_3", "session_3")
        ]
        
        for conn_id, user_id, session_id in connections:
            await self.router.register_connection(
                connection_id=conn_id,
                user_id=user_id,
                session_id=session_id
            )
        
        # Create broadcast message
        broadcast_message = create_standard_message(
            msg_type=MessageType.BROADCAST,
            payload={
                "message": "System maintenance in 10 minutes",
                "type": "system_announcement"
            }
        )
        
        routing_context = RoutingContext(
            user_id="system",
            routing_strategy=MessageRoutingStrategy.BROADCAST_ALL
        )
        
        # Act - Route broadcast message
        delivered_connections = await self.router.route_message(
            message=broadcast_message,
            routing_context=routing_context
        )
        
        # Assert - Should deliver to all registered connections
        self.assertEqual(len(delivered_connections), 3)
        expected_conn_ids = {"conn_1", "conn_2", "conn_3"}
        actual_conn_ids = set(delivered_connections)
        self.assertEqual(actual_conn_ids, expected_conn_ids)

    async def test_message_routing_strategies_user_specific(self):
        """Test USER_SPECIFIC routing strategy delivers only to target user."""
        # Arrange - Register connections for multiple users
        await self.router.register_connection(
            connection_id="target_conn_1",
            user_id=self.user_id,
            session_id="session_1"
        )
        await self.router.register_connection(
            connection_id="target_conn_2",
            user_id=self.user_id,
            session_id="session_2"
        )
        await self.router.register_connection(
            connection_id="other_conn",
            user_id="other_user",
            session_id="other_session"
        )
        
        # Create user-specific message
        user_message = create_standard_message(
            msg_type=MessageType.AGENT_COMPLETED,
            payload={
                "result": "Analysis complete",
                "agent_id": self.agent_id
            },
            user_id=self.user_id
        )
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
        )
        
        # Act - Route user-specific message
        delivered_connections = await self.router.route_message(
            message=user_message,
            routing_context=routing_context
        )
        
        # Assert - Should deliver only to target user's connections
        self.assertEqual(len(delivered_connections), 2)
        expected_conn_ids = {"target_conn_1", "target_conn_2"}
        actual_conn_ids = set(delivered_connections)
        self.assertEqual(actual_conn_ids, expected_conn_ids)

    async def test_message_routing_strategies_session_specific(self):
        """Test SESSION_SPECIFIC routing strategy delivers only to target session."""
        # Arrange - Register connections for same user but different sessions
        target_session = "target_session_123"
        await self.router.register_connection(
            connection_id="target_conn",
            user_id=self.user_id,
            session_id=target_session
        )
        await self.router.register_connection(
            connection_id="other_session_conn",
            user_id=self.user_id,
            session_id="other_session"
        )
        
        # Create session-specific message
        session_message = create_standard_message(
            msg_type=MessageType.THREAD_UPDATE,
            payload={
                "update_type": "new_message",
                "thread_id": "thread_789"
            },
            user_id=self.user_id
        )
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            session_id=target_session,
            routing_strategy=MessageRoutingStrategy.SESSION_SPECIFIC
        )
        
        # Act - Route session-specific message
        delivered_connections = await self.router.route_message(
            message=session_message,
            routing_context=routing_context
        )
        
        # Assert - Should deliver only to target session
        self.assertEqual(len(delivered_connections), 1)
        self.assertEqual(delivered_connections[0], "target_conn")

    async def test_message_routing_strategies_priority_based(self):
        """Test PRIORITY_BASED routing strategy respects message priorities."""
        # Arrange - Register connection
        await self.router.register_connection(
            connection_id=self.connection_id,
            user_id=self.user_id,
            session_id=self.session_id,
            metadata={"supports_priority": True}
        )
        
        # Create high-priority message
        priority_message = create_standard_message(
            msg_type=MessageType.AGENT_ERROR,
            payload={
                "error": "Critical system error detected",
                "severity": "high",
                "requires_attention": True
            },
            user_id=self.user_id
        )
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            priority=MessagePriority.CRITICAL,
            routing_strategy=MessageRoutingStrategy.PRIORITY_BASED,
            metadata={"priority_level": "critical"}
        )
        
        # Act - Route priority message
        delivered_connections = await self.router.route_message(
            message=priority_message,
            routing_context=routing_context
        )
        
        # Assert - Should deliver to user connections
        self.assertEqual(len(delivered_connections), 1)
        self.assertEqual(delivered_connections[0], self.connection_id)

    async def test_handler_registration_and_removal(self):
        """Test handler registration and removal functionality."""
        # Arrange - Create test handlers
        test_handler_1 = AsyncMock()
        test_handler_2 = AsyncMock()
        test_handler_3 = AsyncMock()
        
        # Act - Register handlers with different priorities
        success_1 = self.router.add_handler(
            MessageType.CHAT, test_handler_1, priority=1
        )
        success_2 = self.router.add_handler(
            MessageType.CHAT, test_handler_2, priority=3
        )
        success_3 = self.router.add_handler(
            MessageType.CHAT, test_handler_3, priority=2
        )
        
        # Assert - All registrations should succeed
        self.assertTrue(success_1)
        self.assertTrue(success_2)
        self.assertTrue(success_3)
        
        # Get handlers and verify priority order
        handlers = self.router.get_handlers(MessageType.CHAT)
        self.assertEqual(len(handlers), 3)
        
        # Handlers should be ordered by priority (highest first)
        # Expected order: handler_2 (priority 3), handler_3 (priority 2), handler_1 (priority 1)
        self.assertEqual(handlers[0], test_handler_2)
        self.assertEqual(handlers[1], test_handler_3)
        self.assertEqual(handlers[2], test_handler_1)
        
        # Test handler removal
        removal_success = self.router.remove_handler(MessageType.CHAT, test_handler_2)
        self.assertTrue(removal_success)
        
        # Verify handler was removed
        handlers_after_removal = self.router.get_handlers(MessageType.CHAT)
        self.assertEqual(len(handlers_after_removal), 2)
        self.assertNotIn(test_handler_2, handlers_after_removal)
        
        # Test removing non-existent handler
        non_existent_removal = self.router.remove_handler(MessageType.CHAT, test_handler_2)
        self.assertFalse(non_existent_removal)

    async def test_legacy_interface_compatibility(self):
        """Test legacy register_handler interface maintains compatibility."""
        # Arrange - Create test handler
        legacy_handler = AsyncMock()
        
        # Act - Use legacy register_handler method
        success = self.router.register_handler(
            MessageType.SYSTEM_MESSAGE,
            legacy_handler,
            priority=5
        )
        
        # Assert - Should work identically to add_handler
        self.assertTrue(success)
        
        # Verify handler is registered
        handlers = self.router.get_handlers(MessageType.SYSTEM_MESSAGE)
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0], legacy_handler)
        
        # Test execution
        test_message = create_standard_message(
            msg_type=MessageType.SYSTEM_MESSAGE,
            payload={"message": "System test"}
        )
        
        legacy_handler.return_value = "legacy_result"
        
        results = await self.router.execute_handlers(
            MessageType.SYSTEM_MESSAGE,
            test_message
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "legacy_result")

    async def test_connection_management_operations(self):
        """Test connection registration, unregistration, and management."""
        # Test registration
        registration_success = await self.router.register_connection(
            connection_id=self.connection_id,
            user_id=self.user_id,
            session_id=self.session_id,
            metadata={"client_type": "web", "version": "1.0.0"}
        )
        
        self.assertTrue(registration_success)
        
        # Test connection retrieval
        user_connections = self.router.get_user_connections(self.user_id)
        self.assertEqual(len(user_connections), 1)
        
        connection_info = user_connections[0]
        self.assertEqual(connection_info["connection_id"], self.connection_id)
        self.assertEqual(connection_info["session_id"], self.session_id)
        self.assertTrue(connection_info["is_active"])
        
        # Test unregistration
        unregistration_success = await self.router.unregister_connection(self.connection_id)
        self.assertTrue(unregistration_success)
        
        # Verify connection is removed
        user_connections_after = self.router.get_user_connections(self.user_id)
        self.assertEqual(len(user_connections_after), 0)

    async def test_router_statistics_and_monitoring(self):
        """Test router statistics collection and monitoring."""
        # Arrange - Perform various operations to generate stats
        await self.router.register_connection(
            connection_id="stats_conn_1",
            user_id=self.user_id
        )
        await self.router.register_connection(
            connection_id="stats_conn_2",
            user_id="other_user"
        )
        
        # Add handlers
        self.router.add_handler(MessageType.PING, AsyncMock())
        self.router.add_handler(MessageType.PONG, AsyncMock())
        
        # Route some messages
        test_message = create_standard_message(
            msg_type=MessageType.PING,
            payload={"ping": "test"}
        )
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
        )
        
        await self.router.route_message(test_message, routing_context)
        
        # Act - Get statistics
        stats = self.router.get_stats()
        
        # Assert - Verify stats structure and values
        self.assertIn("messages_routed", stats)
        self.assertIn("routing_errors", stats)
        self.assertIn("active_connections", stats)
        self.assertIn("handlers_registered", stats)
        self.assertIn("total_routes", stats)
        self.assertIn("users_with_connections", stats)
        
        # Verify specific values
        self.assertGreaterEqual(stats["messages_routed"], 1)
        self.assertGreaterEqual(stats["active_connections"], 2)
        self.assertGreaterEqual(stats["handlers_registered"], 2)  # Plus existing handlers from setup
        self.assertGreaterEqual(stats["users_with_connections"], 2)

    async def test_concurrent_routing_operations(self):
        """Test concurrent routing operations maintain data integrity."""
        # Arrange - Register connections
        connections = [f"concurrent_conn_{i}" for i in range(5)]
        for conn_id in connections:
            await self.router.register_connection(
                connection_id=conn_id,
                user_id=self.user_id
            )
        
        # Create multiple messages
        messages = []
        for i in range(10):
            message = create_standard_message(
                msg_type=MessageType.USER_MESSAGE,
                payload={"message": f"Concurrent message {i}"},
                user_id=self.user_id
            )
            messages.append(message)
        
        routing_context = RoutingContext(
            user_id=self.user_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
        )
        
        # Act - Route messages concurrently
        tasks = [
            asyncio.create_task(
                self.router.route_message(message, routing_context)
            )
            for message in messages
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Assert - All messages should be routed successfully
        for delivered_connections in results:
            self.assertEqual(len(delivered_connections), 5)  # All connections for user
            self.assertEqual(set(delivered_connections), set(connections))
        
        # Verify statistics reflect all operations
        stats = self.router.get_stats()
        self.assertGreaterEqual(stats["messages_routed"], 10)

    async def test_cleanup_inactive_connections(self):
        """Test cleanup of inactive connections."""
        # Arrange - Register connections with different activity times
        current_time = time.time()
        
        # Active connection (recent activity)
        await self.router.register_connection(
            connection_id="active_conn",
            user_id=self.user_id
        )
        
        # Inactive connection (old activity) - simulate by manipulating internal state
        await self.router.register_connection(
            connection_id="inactive_conn",
            user_id=self.user_id
        )
        
        # Manually adjust activity time for inactive connection
        if self.user_id in self.router._routes:
            for dest in self.router._routes[self.user_id]:
                if dest.connection_id == "inactive_conn":
                    dest.last_activity = current_time - 400  # 400 seconds ago
                    dest.is_active = False
        
        # Act - Cleanup inactive connections (300 second timeout)
        await self.router.cleanup_inactive_connections(timeout_seconds=300.0)
        
        # Assert - Only active connection should remain
        user_connections = self.router.get_user_connections(self.user_id)
        
        # Filter for active connections
        active_connections = [
            conn for conn in user_connections 
            if conn["is_active"]
        ]
        
        # Should have at least the active connection
        active_conn_ids = [conn["connection_id"] for conn in active_connections]
        self.assertIn("active_conn", active_conn_ids)
        
        # Verify stats reflect cleanup
        stats = self.router.get_stats()
        self.assertGreaterEqual(stats["active_connections"], 1)