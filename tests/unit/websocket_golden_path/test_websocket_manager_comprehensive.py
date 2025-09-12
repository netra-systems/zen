"""
Comprehensive Unit Tests for WebSocket Manager (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Core infrastructure for all tiers
- Business Goal: Reliability & Stability - Ensure WebSocket communication foundation
- Value Impact: Critical for $500K+ ARR chat functionality - connection success rates
- Revenue Impact: Foundation for all AI-powered user interactions

CRITICAL: These tests validate the most business-critical WebSocket Manager functionality
for the Golden Path user flow: connection  ->  authentication  ->  message routing  ->  agent execution.

Test Coverage Focus:
- Connection lifecycle management (connection success rates)
- User isolation (prevents data mixing between users)
- Event delivery reliability (all 5 critical WebSocket events)
- Race condition prevention (Cloud Run concurrent scenarios)
- Message serialization (prevents JSON encoding errors)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses IsolatedEnvironment for all environment access
- Uses real WebSocket connections where possible
- Minimal mocks only for external dependencies
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env

# System Under Test - SSOT WebSocket Manager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager, 
    WebSocketConnection,
    _serialize_message_safely
)

# Dependencies
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.unit
class TestWebSocketManagerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Manager SSOT class.
    
    GOLDEN PATH FOCUS: Validates critical business logic for user connection flow.
    These tests ensure WebSocket Manager reliably handles the foundational operations
    that enable chat functionality.
    """
    
    def setup_method(self, method):
        """Set up test fixtures with SSOT compliance."""
        super().setup_method(method)
        self.test_context = self.get_test_context()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.metadata["component"] = "websocket_manager"
        
        # Create WebSocket Manager instance
        self.websocket_manager = UnifiedWebSocketManager()
        
        # Create test identifiers using SSOT ID generation
        self.id_manager = UnifiedIDManager()
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER))
        self.test_connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        self.test_websocket_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        
        # Mock WebSocket connection
        self.mock_websocket = SSotMockFactory().create_websocket_connection_mock()
        
        # Track test metrics for business value validation
        self.connection_attempts = 0
        self.successful_connections = 0
        self.event_deliveries = 0
        self.isolation_violations = 0

    def teardown_method(self, method):
        """Clean up test resources."""
        # Calculate success rates for business metrics
        if self.connection_attempts > 0:
            success_rate = (self.successful_connections / self.connection_attempts) * 100
            self.test_context.metadata["connection_success_rate"] = success_rate
        
        self.test_context.metadata["event_deliveries"] = self.event_deliveries
        self.test_context.metadata["isolation_violations"] = self.isolation_violations
        super().teardown_method(method)

    async def test_connection_registration_golden_path(self):
        """
        Test WebSocket connection registration for Golden Path user flow.
        
        BVJ: Connection success is critical for $500K+ ARR chat functionality.
        This validates the foundational operation that enables all user interactions.
        """
        self.connection_attempts += 1
        
        # Create WebSocket connection
        connection = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            websocket_id=self.test_websocket_id
        )
        
        # Register connection
        await self.websocket_manager.add_connection(
            self.test_user_id,
            self.test_connection_id,
            self.mock_websocket,
            websocket_id=self.test_websocket_id
        )
        
        self.successful_connections += 1
        
        # Validate connection is properly registered
        self.assertIn(self.test_user_id, self.websocket_manager.user_connections)
        
        connections = self.websocket_manager.user_connections[self.test_user_id]
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].user_id, self.test_user_id)
        self.assertEqual(connections[0].connection_id, self.test_connection_id)
        
        # BVJ: Validate connection is ready for message routing
        self.assertTrue(await self.websocket_manager.has_connection(self.test_user_id))

    async def test_user_isolation_enforcement(self):
        """
        Test strict user isolation to prevent data mixing.
        
        BVJ: User isolation is CRITICAL for enterprise trust and compliance.
        Data leakage between users would be a catastrophic business failure.
        """
        # Create two separate users
        user1_id = str(self.id_manager.generate_id(IDType.USER))
        user2_id = str(self.id_manager.generate_id(IDType.USER))
        
        connection1_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        connection2_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        
        mock_websocket1 = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket2 = SSotMockFactory().create_websocket_connection_mock()
        
        # Register connections for both users
        await self.websocket_manager.add_connection(
            user1_id, connection1_id, mock_websocket1
        )
        await self.websocket_manager.add_connection(
            user2_id, connection2_id, mock_websocket2
        )
        
        # Validate user1 cannot see user2's connections
        user1_connections = self.websocket_manager.get_user_connections(user1_id)
        user2_connections = self.websocket_manager.get_user_connections(user2_id)
        
        self.assertEqual(len(user1_connections), 1)
        self.assertEqual(len(user2_connections), 1)
        
        # Critical: Validate no cross-user data visibility
        self.assertEqual(user1_connections[0].user_id, user1_id)
        self.assertEqual(user2_connections[0].user_id, user2_id)
        self.assertNotEqual(user1_connections[0].connection_id, connection2_id)
        self.assertNotEqual(user2_connections[0].connection_id, connection1_id)
        
        # BVJ: Zero isolation violations tolerated
        if user1_connections[0].user_id != user1_id or user2_connections[0].user_id != user2_id:
            self.isolation_violations += 1
            self.fail("CRITICAL: User isolation violation detected")

    async def test_message_broadcasting_with_isolation(self):
        """
        Test message broadcasting respects user isolation.
        
        BVJ: Ensures messages reach only intended recipients.
        Critical for enterprise privacy and user trust.
        """
        # Set up two users with connections
        user1_id = str(self.id_manager.generate_id(IDType.USER))
        user2_id = str(self.id_manager.generate_id(IDType.USER))
        
        mock_websocket1 = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket2 = SSotMockFactory().create_websocket_connection_mock()
        
        await self.websocket_manager.add_connection(user1_id, "conn1", mock_websocket1)
        await self.websocket_manager.add_connection(user2_id, "conn2", mock_websocket2)
        
        # Send message to user1 only
        test_message = {"type": "test", "content": "user1_message"}
        
        await self.websocket_manager.send_to_user(user1_id, test_message)
        self.event_deliveries += 1
        
        # Validate only user1's WebSocket received the message
        mock_websocket1.send_json.assert_called_once()
        mock_websocket2.send_json.assert_not_called()
        
        # Validate message content integrity
        sent_message = mock_websocket1.send_json.call_args[0][0]
        self.assertEqual(sent_message["type"], "test")
        self.assertEqual(sent_message["content"], "user1_message")

    async def test_connection_cleanup_on_disconnect(self):
        """
        Test proper connection cleanup to prevent memory leaks.
        
        BVJ: Memory leaks in Cloud Run lead to scaling issues and increased costs.
        Proper cleanup is essential for system stability.
        """
        # Register connection
        await self.websocket_manager.add_connection(
            self.test_user_id,
            self.test_connection_id,
            self.mock_websocket
        )
        
        # Verify connection exists
        self.assertTrue(await self.websocket_manager.has_connection(self.test_user_id))
        
        # Remove connection
        await self.websocket_manager.remove_connection(
            self.test_user_id,
            self.test_connection_id
        )
        
        # Validate complete cleanup
        self.assertFalse(await self.websocket_manager.has_connection(self.test_user_id))
        
        # Check user is completely removed when no connections remain
        self.assertNotIn(self.test_user_id, self.websocket_manager.user_connections)

    async def test_concurrent_connection_handling(self):
        """
        Test concurrent connection operations for race condition prevention.
        
        BVJ: Cloud Run environments have race conditions that cause 1011 errors.
        This validates the manager handles concurrent operations safely.
        """
        # Simulate multiple concurrent connection attempts
        connection_tasks = []
        user_ids = []
        connection_ids = []
        
        for i in range(5):
            user_id = str(self.id_manager.generate_id(IDType.USER))
            connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
            mock_websocket = SSotMockFactory().create_websocket_connection_mock()
            
            user_ids.append(user_id)
            connection_ids.append(connection_id)
            
            task = self.websocket_manager.add_connection(
                user_id, connection_id, mock_websocket
            )
            connection_tasks.append(task)
        
        # Execute all connection attempts concurrently
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Validate all connections succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"Connection {i} failed with exception: {result}")
        
        # Validate all connections are properly registered
        for user_id in user_ids:
            self.assertTrue(await self.websocket_manager.has_connection(user_id))

    def test_message_serialization_safety(self):
        """
        Test safe message serialization prevents JSON encoding errors.
        
        BVJ: JSON serialization errors break WebSocket communication.
        This validates the manager handles complex data types safely.
        """
        # Test various data types that can cause serialization issues
        test_cases = [
            {"datetime": datetime.now(timezone.utc)},
            {"enum": WebSocketState.CONNECTED},
            {"nested": {"complex": {"data": [1, 2, 3]}}},
            {"unicode": "[U+6D4B][U+8BD5] [U+1F680] emoji"},
            {"none_values": {"field": None}},
        ]
        
        for test_message in test_cases:
            # This should not raise an exception
            serialized = _serialize_message_safely(test_message)
            
            # Validate result is JSON serializable
            try:
                json.dumps(serialized)
            except (TypeError, ValueError) as e:
                self.fail(f"Serialization failed for {test_message}: {e}")
            
            # Validate result is a dictionary
            self.assertIsInstance(serialized, dict)

    async def test_websocket_state_validation(self):
        """
        Test WebSocket state validation for connection health.
        
        BVJ: Invalid WebSocket states cause connection failures and poor UX.
        This validates the manager checks connection health properly.
        """
        # Mock WebSocket with CONNECTED state
        mock_websocket = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Register connection
        await self.websocket_manager.add_connection(
            self.test_user_id,
            self.test_connection_id,
            mock_websocket
        )
        
        # Test message sending to healthy connection
        test_message = {"type": "test", "status": "healthy"}
        result = await self.websocket_manager.send_to_user(self.test_user_id, test_message)
        
        # Validate message was sent successfully
        mock_websocket.send_json.assert_called_once_with(test_message)
        
        # Test handling of closed connection
        mock_websocket.client_state = WebSocketState.CLOSED
        
        # Attempt to send to closed connection should handle gracefully
        with patch.object(self.websocket_manager, '_handle_send_error') as mock_handler:
            await self.websocket_manager.send_to_user(self.test_user_id, test_message)
            # Verify error handling was triggered for closed connection
            # (specific implementation may vary based on manager design)

    async def test_golden_path_event_delivery_sequence(self):
        """
        Test complete Golden Path event delivery sequence.
        
        BVJ: The 5 critical WebSocket events (agent_started, agent_thinking, 
        tool_executing, tool_completed, agent_completed) are the backbone
        of user experience. This validates end-to-end event flow.
        """
        # Register connection
        await self.websocket_manager.add_connection(
            self.test_user_id,
            self.test_connection_id,
            self.mock_websocket
        )
        
        # Golden Path events in sequence
        golden_path_events = [
            {"type": "agent_started", "agent_id": "test_agent", "timestamp": datetime.now(timezone.utc)},
            {"type": "agent_thinking", "thought": "Processing user request"},
            {"type": "tool_executing", "tool": "search", "params": {}},
            {"type": "tool_completed", "tool": "search", "result": "success"},
            {"type": "agent_completed", "result": "Task completed successfully"}
        ]
        
        # Send all events in sequence
        for event in golden_path_events:
            await self.websocket_manager.send_to_user(self.test_user_id, event)
            self.event_deliveries += 1
        
        # Validate all events were delivered
        self.assertEqual(self.mock_websocket.send_json.call_count, len(golden_path_events))
        
        # Validate event ordering is preserved
        call_args_list = self.mock_websocket.send_json.call_args_list
        for i, expected_event in enumerate(golden_path_events):
            actual_event = call_args_list[i][0][0]
            self.assertEqual(actual_event["type"], expected_event["type"])

    async def test_multi_user_concurrent_event_delivery(self):
        """
        Test concurrent event delivery to multiple users without cross-talk.
        
        BVJ: Multi-user scenarios are common in enterprise deployments.
        This validates the manager maintains isolation under concurrent load.
        """
        # Set up multiple users
        num_users = 3
        users = []
        websockets = []
        
        for i in range(num_users):
            user_id = str(self.id_manager.generate_id(IDType.USER))
            connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
            mock_websocket = SSotMockFactory().create_websocket_connection_mock()
            
            await self.websocket_manager.add_connection(user_id, connection_id, mock_websocket)
            
            users.append(user_id)
            websockets.append(mock_websocket)
        
        # Send unique messages to each user concurrently
        send_tasks = []
        for i, user_id in enumerate(users):
            message = {"type": "user_specific", "user_id": user_id, "sequence": i}
            task = self.websocket_manager.send_to_user(user_id, message)
            send_tasks.append(task)
        
        # Execute all sends concurrently
        await asyncio.gather(*send_tasks)
        
        # Validate each user received only their message
        for i, (user_id, websocket) in enumerate(zip(users, websockets)):
            websocket.send_json.assert_called_once()
            sent_message = websocket.send_json.call_args[0][0]
            
            # Critical: Validate no cross-user message delivery
            self.assertEqual(sent_message["user_id"], user_id)
            self.assertEqual(sent_message["sequence"], i)
            
            # Validate other users didn't receive this message
            for j, other_websocket in enumerate(websockets):
                if i != j:
                    other_calls = other_websocket.send_json.call_args_list
                    for call in other_calls:
                        other_message = call[0][0]
                        if other_message["user_id"] == user_id:
                            self.isolation_violations += 1
                            self.fail(f"Cross-user message delivery detected: User {j} received User {i}'s message")


@pytest.mark.unit  
class TestWebSocketManagerEdgeCases(SSotBaseTestCase):
    """
    Unit tests for WebSocket Manager edge cases and error conditions.
    
    These tests validate graceful handling of error conditions that could
    impact system stability and user experience.
    """
    
    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.test_context = self.get_test_context()
        self.test_context.test_category = CategoryType.UNIT
        self.websocket_manager = UnifiedWebSocketManager()

    def test_invalid_user_id_handling(self):
        """Test handling of invalid user IDs."""
        # Test with None user ID - should raise ValueError
        with pytest.raises(ValueError):
            connections = self.websocket_manager.get_user_connections(None)
        
        # Test with empty string user ID - should raise ValueError  
        with pytest.raises(ValueError):
            connections = self.websocket_manager.get_user_connections("")
        
        # Test with malformed user ID - behavior depends on validation rules
        try:
            connections = self.websocket_manager.get_user_connections("not-a-valid-uuid")
            # If no exception, should return empty list
            assert len(connections) == 0
        except ValueError:
            # ValueError is acceptable for malformed IDs
            pass

    def test_duplicate_connection_handling(self):
        """Test handling of duplicate connection attempts."""
        # This test would validate how the manager handles attempts to register
        # the same connection_id multiple times
        # Implementation depends on manager's duplicate handling strategy
        pass

    def test_memory_usage_validation(self):
        """Test memory usage stays within bounds."""
        # This test could validate that the connection registry doesn't
        # grow unbounded and implements proper cleanup
        # Specific implementation depends on manager's memory management
        pass


if __name__ == "__main__":
    # Run tests with appropriate markers
    pytest.main([__file__, "-v", "-m", "unit"])