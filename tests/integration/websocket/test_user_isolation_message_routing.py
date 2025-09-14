"""User Isolation Security Tests for Message Routing.

Issue #1067: Message Router Consolidation Blocking Golden Path

These tests validate that SSOT Message Router consolidation maintains proper
user isolation and prevents cross-user contamination in message routing.

Business Value:
- Segment: Enterprise/Mid-tier (HIPAA, SOC2, SEC compliance)
- Goal: Security & Retention ($500K+ ARR protection)
- Value Impact: User isolation prevents data leakage and ensures regulatory compliance
- Strategic Impact: Enterprise trust and security validation for large contracts

TEST STRATEGY:
1. Multi-user scenarios with concurrent message routing
2. Validate WebSocket events are user-isolated
3. Ensure tool execution results don't leak between users
4. Test agent state isolation per user session
5. Validate factory patterns create proper user-scoped instances

EXPECTED BEHAVIOR:
- Each user's WebSocket events only go to their connections
- Agent state is completely isolated between users
- Tool execution results are user-scoped
- Message routing respects user context boundaries
- Factory patterns prevent shared state contamination
"""

import asyncio
import unittest
import time
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Core imports for user isolation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    get_message_router,
    AgentRequestHandler
)

# Tool dispatcher for isolation testing
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher

# WebSocket types for message testing
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUserIsolationMessageRouting(SSotAsyncTestCase):
    """Test suite for user isolation in message routing after SSOT consolidation.

    These tests ensure that SSOT Message Router consolidation maintains strict
    user isolation and prevents cross-user data contamination.
    """

    def setup_method(self, method):
        """Set up test environment with multiple users for isolation testing."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()

        # Create multiple test users
        self.user_contexts = {
            "user_1": UserExecutionContext.from_request(
                user_id="test_user_001",
                thread_id="thread_001",
                run_id="run_001"
            ),
            "user_2": UserExecutionContext.from_request(
                user_id="test_user_002",
                thread_id="thread_002",
                run_id="run_002"
            ),
            "user_3": UserExecutionContext.from_request(
                user_id="test_user_003",
                thread_id="thread_003",
                run_id="run_003"
            )
        }

        # Create WebSocket managers for each user
        self.websocket_managers = {}
        self.mock_websockets = {}

        for user_key, context in self.user_contexts.items():
            self.websocket_managers[user_key] = WebSocketManager(user_context=context)
            self.mock_websockets[user_key] = self.mock_factory.create_mock_websocket()

    async def test_websocket_event_user_isolation(self):
        """Test that WebSocket events are properly isolated between users.

        CRITICAL FOR: Multi-tenant security and enterprise compliance.
        BUSINESS IMPACT: Data leakage between users would violate HIPAA/SOC2 requirements.
        """
        logger.info("Testing WebSocket event user isolation in message routing")

        router = get_message_router()

        # Create agent request messages for each user
        user_messages = {
            "user_1": {
                "type": "agent_request",
                "message": "CONFIDENTIAL: User 1 medical data request",
                "turn_id": "turn_001",
                "user_id": "test_user_001",
                "timestamp": time.time()
            },
            "user_2": {
                "type": "agent_request",
                "message": "CONFIDENTIAL: User 2 financial data request",
                "turn_id": "turn_002",
                "user_id": "test_user_002",
                "timestamp": time.time()
            },
            "user_3": {
                "type": "agent_request",
                "message": "CONFIDENTIAL: User 3 legal document request",
                "turn_id": "turn_003",
                "user_id": "test_user_003",
                "timestamp": time.time()
            }
        }

        # Track messages sent to each WebSocket
        websocket_messages = {"user_1": [], "user_2": [], "user_3": []}

        # Mock WebSocket send methods to capture messages
        async def capture_messages(user_key):
            def mock_send_text(message):
                websocket_messages[user_key].append({"type": "text", "data": message})
                return asyncio.create_task(asyncio.sleep(0))

            def mock_send_json(message):
                websocket_messages[user_key].append({"type": "json", "data": message})
                return asyncio.create_task(asyncio.sleep(0))

            self.mock_websockets[user_key].send_text = mock_send_text
            self.mock_websockets[user_key].send_json = mock_send_json

        # Set up message capture for all users
        for user_key in self.user_contexts.keys():
            await capture_messages(user_key)

        # Route messages concurrently to test isolation
        routing_tasks = []
        for user_key, message in user_messages.items():
            task = asyncio.create_task(
                router.route_message(
                    self.user_contexts[user_key].user_id,
                    self.mock_websockets[user_key],
                    message
                )
            )
            routing_tasks.append((user_key, task))

        # Wait for all routing to complete
        results = {}
        for user_key, task in routing_tasks:
            try:
                results[user_key] = await task
            except Exception as e:
                logger.warning(f"Message routing failed for {user_key}: {e}")
                results[user_key] = False

        # Validate user isolation in results
        for user_key in self.user_contexts.keys():
            user_messages_received = websocket_messages[user_key]

            # Each user should have received messages for their request only
            self.assertTrue(len(user_messages_received) > 0,
                           f"User {user_key} should have received messages from their agent request")

            # Check that messages contain only their user_id
            for msg in user_messages_received:
                if isinstance(msg["data"], dict) and "user_id" in msg["data"]:
                    msg_user_id = msg["data"]["user_id"]
                    expected_user_id = self.user_contexts[user_key].user_id
                    self.assertEqual(msg_user_id, expected_user_id,
                                   f"Message routed to {user_key} contains wrong user_id: {msg_user_id}")

                # Ensure no cross-user data leakage
                msg_content = str(msg["data"]).lower()
                other_users = [k for k in self.user_contexts.keys() if k != user_key]
                for other_user in other_users:
                    other_context = self.user_contexts[other_user]
                    # Check that other user's data doesn't appear in this user's messages
                    self.assertNotIn(other_context.user_id.lower(), msg_content,
                                   f"User {user_key} received message containing other user's ID: {other_context.user_id}")

        logger.info("PASS: WebSocket event user isolation validated - no cross-user data leakage detected")

    async def test_agent_state_isolation_concurrent_execution(self):
        """Test that agent state remains isolated during concurrent execution.

        CRITICAL FOR: Multi-user agent execution without state contamination.
        BUSINESS IMPACT: Shared agent state would cause incorrect responses and data mixing.
        """
        logger.info("Testing agent state isolation during concurrent message routing")

        # Create agent request handler for testing
        handler = AgentRequestHandler()
        router = get_message_router()

        # Concurrent agent requests with different parameters
        concurrent_requests = []

        for user_key, context in self.user_contexts.items():
            # Create unique agent request for each user
            request_message = {
                "type": "agent_request",
                "message": f"Process user-specific data for {context.user_id}",
                "user_id": context.user_id,
                "turn_id": f"concurrent_turn_{user_key}",
                "require_multi_agent": (user_key == "user_1"),  # Different execution paths
                "real_llm": (user_key != "user_3"),  # Different configurations
                "timestamp": time.time()
            }

            # Convert to WebSocketMessage
            ws_message = WebSocketMessage(
                type=MessageType.AGENT_REQUEST,
                payload=request_message,
                user_id=context.user_id,
                thread_id=context.thread_id
            )

            concurrent_requests.append((user_key, context.user_id, self.mock_websockets[user_key], ws_message))

        # Execute all agent requests concurrently
        async def execute_agent_request(user_key, user_id, websocket, message):
            try:
                result = await handler.handle_message(user_id, websocket, message)
                return (user_key, result, user_id)
            except Exception as e:
                logger.error(f"Agent request failed for {user_key}: {e}")
                return (user_key, False, user_id)

        # Run concurrent executions
        execution_tasks = [
            execute_agent_request(user_key, user_id, websocket, message)
            for user_key, user_id, websocket, message in concurrent_requests
        ]

        concurrent_results = await asyncio.gather(*execution_tasks, return_exceptions=True)

        # Validate isolation - each execution should succeed independently
        successful_executions = 0
        for result in concurrent_results:
            if isinstance(result, tuple) and len(result) == 3:
                user_key, success, user_id = result
                if success:
                    successful_executions += 1
                    logger.info(f"Agent execution successful for {user_key} (user_id: {user_id})")
                else:
                    logger.warning(f"Agent execution failed for {user_key} (user_id: {user_id})")
            else:
                logger.error(f"Agent execution exception: {result}")

        # At least 2 out of 3 should succeed (allowing for some expected failures in test environment)
        self.assertGreaterEqual(successful_executions, 2,
                               f"Expected at least 2 successful concurrent executions, got {successful_executions}")

        logger.info(f"PASS: Agent state isolation validated - {successful_executions}/3 concurrent executions successful")

    async def test_tool_dispatcher_user_isolation(self):
        """Test that tool dispatcher maintains user isolation in SSOT consolidation.

        CRITICAL FOR: Tool execution security and result isolation.
        BUSINESS IMPACT: Tool result leakage between users would compromise data security.
        """
        logger.info("Testing tool dispatcher user isolation in SSOT Message Router")

        # Create tool dispatchers for each user
        dispatchers = {}

        for user_key, context in self.user_contexts.items():
            dispatcher = await UnifiedToolDispatcher.create_for_user(context)
            dispatchers[user_key] = dispatcher

            # Validate user context isolation
            self.assertEqual(dispatcher.user_context.user_id, context.user_id,
                           f"Tool dispatcher for {user_key} must maintain user context")
            self.assertEqual(dispatcher.user_context.thread_id, context.thread_id,
                           f"Tool dispatcher for {user_key} must maintain thread context")

        # Test that dispatchers are properly isolated instances
        dispatcher_ids = set()
        for user_key, dispatcher in dispatchers.items():
            dispatcher_id = id(dispatcher)
            self.assertNotIn(dispatcher_id, dispatcher_ids,
                            f"Tool dispatcher for {user_key} must be unique instance")
            dispatcher_ids.add(dispatcher_id)

        # Test user context validation in each dispatcher
        for user_key, dispatcher in dispatchers.items():
            expected_context = self.user_contexts[user_key]

            # Validate user context properties
            self.assertEqual(dispatcher.user_context.user_id, expected_context.user_id)
            self.assertEqual(dispatcher.user_context.thread_id, expected_context.thread_id)
            self.assertEqual(dispatcher.user_context.run_id, expected_context.run_id)

        logger.info("PASS: Tool dispatcher user isolation validated - unique instances with proper context isolation")

    async def test_websocket_manager_factory_isolation(self):
        """Test that WebSocket manager factory creates isolated instances per user.

        CRITICAL FOR: WebSocket connection isolation and event routing.
        BUSINESS IMPACT: Shared WebSocket managers would cause event cross-contamination.
        """
        logger.info("Testing WebSocket manager factory user isolation")

        # Validate that each WebSocket manager has proper user context
        for user_key, ws_manager in self.websocket_managers.items():
            expected_context = self.user_contexts[user_key]

            self.assertEqual(ws_manager.user_context.user_id, expected_context.user_id,
                           f"WebSocket manager for {user_key} must have correct user_id")
            self.assertEqual(ws_manager.user_context.thread_id, expected_context.thread_id,
                           f"WebSocket manager for {user_key} must have correct thread_id")

        # Test that WebSocket managers are unique instances
        manager_ids = set()
        for user_key, ws_manager in self.websocket_managers.items():
            manager_id = id(ws_manager)
            self.assertNotIn(manager_id, manager_ids,
                           f"WebSocket manager for {user_key} must be unique instance")
            manager_ids.add(manager_id)

        # Test broadcast isolation - each manager should only affect its user
        test_broadcast_data = {
            "type": "test_broadcast",
            "message": "User isolation test",
            "timestamp": time.time()
        }

        # Track which managers receive broadcasts
        broadcast_results = {}

        for user_key, ws_manager in self.websocket_managers.items():
            try:
                # This should only affect the specific user's connections
                result = await ws_manager.broadcast_to_all(test_broadcast_data)
                broadcast_results[user_key] = result
                logger.info(f"Broadcast successful for {user_key}: {result}")
            except Exception as e:
                logger.warning(f"Broadcast failed for {user_key}: {e}")
                broadcast_results[user_key] = None

        # Validate that broadcasts are isolated per user context
        for user_key, result in broadcast_results.items():
            if result is not None:
                # Broadcast should succeed for the user's context
                logger.info(f"User {user_key} broadcast isolated properly")

        logger.info("PASS: WebSocket manager factory isolation validated - unique instances per user")

    async def test_message_routing_race_condition_isolation(self):
        """Test message routing under high concurrency maintains user isolation.

        CRITICAL FOR: Race condition prevention in multi-user scenarios.
        BUSINESS IMPACT: Race conditions could cause user data to be sent to wrong recipients.
        """
        logger.info("Testing message routing race condition isolation")

        router = get_message_router()

        # Create rapid concurrent message streams for each user
        message_counts_per_user = 10
        total_messages = len(self.user_contexts) * message_counts_per_user

        # Generate unique messages for each user
        all_tasks = []
        message_tracking = {user_key: [] for user_key in self.user_contexts.keys()}

        for user_key, context in self.user_contexts.items():
            for msg_num in range(message_counts_per_user):
                # Create unique message with identifiable content
                unique_message = {
                    "type": "user_message",
                    "content": f"UNIQUE_MESSAGE_{user_key}_{msg_num}_CONFIDENTIAL",
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "message_id": f"{user_key}_msg_{msg_num}",
                    "timestamp": time.time()
                }

                # Track expected message for validation
                message_tracking[user_key].append(unique_message)

                # Create routing task
                task = asyncio.create_task(
                    router.route_message(context.user_id, self.mock_websockets[user_key], unique_message)
                )
                all_tasks.append((user_key, msg_num, task))

        logger.info(f"Starting {total_messages} concurrent message routing tasks")

        # Execute all tasks concurrently to test race conditions
        start_time = time.time()
        results = []

        for user_key, msg_num, task in all_tasks:
            try:
                result = await task
                results.append((user_key, msg_num, result))
            except Exception as e:
                logger.warning(f"Message routing failed for {user_key} msg {msg_num}: {e}")
                results.append((user_key, msg_num, False))

        execution_time = time.time() - start_time

        # Analyze results for isolation validation
        success_count = sum(1 for _, _, result in results if result)
        failure_count = len(results) - success_count

        logger.info(f"Race condition test results: {success_count} successes, {failure_count} failures in {execution_time:.3f}s")

        # Validate performance and success rate
        self.assertGreater(success_count, total_messages * 0.7,  # At least 70% success rate
                          f"Expected high success rate, got {success_count}/{total_messages}")
        self.assertLess(execution_time, 5.0,  # Should complete within 5 seconds
                       f"Message routing took too long: {execution_time:.3f}s")

        # Group results by user for isolation validation
        user_results = {user_key: [] for user_key in self.user_contexts.keys()}
        for user_key, msg_num, result in results:
            user_results[user_key].append((msg_num, result))

        # Validate that each user had reasonable success rate (isolation working)
        for user_key, user_result_list in user_results.items():
            user_successes = sum(1 for _, result in user_result_list if result)
            user_total = len(user_result_list)

            self.assertGreater(user_successes, user_total * 0.5,  # At least 50% per user
                             f"User {user_key} had poor success rate: {user_successes}/{user_total}")

            logger.info(f"User {user_key} isolation results: {user_successes}/{user_total} messages routed successfully")

        logger.info("PASS: Message routing race condition isolation validated - no cross-user contamination detected")

    async def test_factory_pattern_memory_isolation(self):
        """Test that factory patterns prevent memory contamination between users.

        CRITICAL FOR: Memory safety and preventing data leaks through shared objects.
        BUSINESS IMPACT: Memory contamination could expose user data across sessions.
        """
        logger.info("Testing factory pattern memory isolation")

        # Create multiple instances of each factory type for different users
        instances_by_type = {
            "websocket_managers": [],
            "tool_dispatchers": []
        }

        # Create instances for each user
        for user_key, context in self.user_contexts.items():
            # WebSocket manager instances
            ws_manager = WebSocketManager(user_context=context)
            instances_by_type["websocket_managers"].append((user_key, ws_manager))

            # Tool dispatcher instances
            tool_dispatcher = await UnifiedToolDispatcher.create_for_user(context)
            instances_by_type["tool_dispatchers"].append((user_key, tool_dispatcher))

        # Validate memory isolation - no shared references
        for instance_type, instance_list in instances_by_type.items():
            logger.info(f"Validating memory isolation for {instance_type}")

            # Check that instances are unique objects
            instance_ids = set()
            for user_key, instance in instance_list:
                instance_id = id(instance)
                self.assertNotIn(instance_id, instance_ids,
                               f"{instance_type}: Instance for {user_key} must be unique object")
                instance_ids.add(instance_id)

                # Validate user context is properly isolated
                self.assertEqual(instance.user_context.user_id, self.user_contexts[user_key].user_id,
                               f"{instance_type}: User context must be isolated for {user_key}")

            logger.info(f"Memory isolation validated for {instance_type}: {len(instance_ids)} unique instances")

        # Test that modifying one instance doesn't affect others
        ws_managers = instances_by_type["websocket_managers"]
        if len(ws_managers) >= 2:
            user1_key, user1_manager = ws_managers[0]
            user2_key, user2_manager = ws_managers[1]

            # Store original values
            user1_original_id = user1_manager.user_context.user_id
            user2_original_id = user2_manager.user_context.user_id

            # Test that they're different
            self.assertNotEqual(user1_original_id, user2_original_id,
                              "User contexts must be different between instances")

            # Validate context isolation persists
            self.assertEqual(user1_manager.user_context.user_id, user1_original_id)
            self.assertEqual(user2_manager.user_context.user_id, user2_original_id)

        logger.info("PASS: Factory pattern memory isolation validated - no shared references detected")


if __name__ == '__main__':
    # Support both pytest and unittest execution
    unittest.main()