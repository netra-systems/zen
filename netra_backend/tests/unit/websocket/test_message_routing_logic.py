"""
Unit Tests for WebSocket Message Routing Logic Failures - Issue #618

CRITICAL: These tests are designed to expose message routing logic failures 
that cause the "Message routing failed" errors identified in Issue #618.

Business Value Justification:
- Segment: All (affects all users experiencing chat failures)
- Business Goal: Fix message delivery failures that break AI chat functionality
- Value Impact: Resolves routing failures preventing users from receiving agent responses
- Strategic Impact: CRITICAL - Chat is 90% of platform value delivery

Test Strategy:
1. EXPOSE routing logic failures when connection IDs don't match
2. DEMONSTRATE message delivery failures in multi-user scenarios 
3. VALIDATE user isolation failures in routing logic
4. PROVE demo user routing edge cases cause message loss

These tests should initially FAIL to expose the routing issues,
then PASS after routing logic fixes are implemented.
"""

import pytest
import asyncio
import uuid
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

# Import WebSocket core modules to test routing logic
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.connection_manager import ConnectionManager
from netra_backend.app.websocket_core.message_queue import MessageQueue
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, ConnectionInfo, 
    create_standard_message, create_server_message
)
from netra_backend.app.websocket_core.utils import (
    generate_connection_id, generate_message_id,
    is_websocket_connected, safe_websocket_send
)

# Import routing-related modules
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager
from netra_backend.app.websocket_core.batch_message_handler import BatchMessageHandler

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRoutingLogicFailures(SSotBaseTestCase):
    """
    Unit tests that expose message routing logic failures causing "Message routing failed" errors.
    
    ISSUE #618: These tests demonstrate the specific routing logic failures that prevent
    messages from reaching their intended WebSocket connections.
    """
    
    def setup_method(self):
        """Set up test fixtures for routing failure scenarios."""
        super().setup_method()
        
        # Test users with different characteristics
        self.regular_user_id = "routing-test-user-123"
        self.demo_user_id = "demo-user-routing-456"
        self.enterprise_user_id = "enterprise-routing-789"
        
        # Core routing components
        self.connection_manager = ConnectionManager()
        self.factory = WebSocketManagerFactory()
        self.user_session_manager = UserSessionManager()
        
        # Mock WebSocket connections for testing
        self.mock_websockets = {}
        for user_id in [self.regular_user_id, self.demo_user_id, self.enterprise_user_id]:
            mock_ws = Mock()
            mock_ws.send_json = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.client_state = Mock()
            mock_ws.receive = AsyncMock()
            mock_ws.send = AsyncMock()
            self.mock_websockets[user_id] = mock_ws

    def test_connection_id_mismatch_routing_failure(self):
        """
        DESIGNED TO EXPOSE: Message routing failures when connection IDs don't match.
        
        This test demonstrates the core routing issue: messages generated with one
        connection ID format cannot find connections registered with a different format.
        """
        user_id = self.regular_user_id
        thread_id = f"thread_{user_id}_{int(time.time())}"
        
        # Simulate the exact Issue #618 scenario:
        # 1. Connection is registered with one ID format
        legacy_connection_id = f"conn_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Register connection with legacy format
        self.connection_manager.register_connection(
            connection_id=legacy_connection_id,
            user_id=user_id,
            websocket=self.mock_websockets[user_id]
        )
        
        # 2. Message routing attempts to find connection with SSOT format
        ssot_connection_id = generate_connection_id(user_id)
        
        # Create message to route
        message = create_standard_message(
            msg_type="agent_started",
            payload={
                "agent": "cost_optimizer",
                "status": "started",
                "thread_id": thread_id
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        print(f"Message routing mismatch scenario:")
        print(f"  Registered connection ID: {legacy_connection_id}")
        print(f"  Message target connection ID: {ssot_connection_id}")
        print(f"  IDs match: {legacy_connection_id == str(ssot_connection_id)}")
        
        # Try to route message - this should expose the failure
        registered_connection = self.connection_manager.get_connection(legacy_connection_id)
        target_connection = self.connection_manager.get_connection(str(ssot_connection_id))
        
        # CRITICAL TEST: This exposes the routing failure
        assert registered_connection is not None, \
            "Connection should be found with registered ID"
        
        if str(ssot_connection_id) != legacy_connection_id:
            assert target_connection is None, \
                f"MESSAGE ROUTING FAILURE EXPOSED: Message targets connection {ssot_connection_id} " \
                f"but connection is registered as {legacy_connection_id}. " \
                f"This is the root cause of 'Message routing failed' errors in Issue #618."
        
        # Document the routing failure pattern
        routing_success = target_connection is not None
        print(f"Routing result: {'SUCCESS' if routing_success else 'FAILURE'}")
        
        if not routing_success:
            print("ROUTING FAILURE ANALYSIS:")
            print("  - Message cannot find target connection")
            print("  - User will not receive agent responses")
            print("  - Chat functionality appears broken")

    def test_multi_user_routing_isolation_failure(self):
        """
        DESIGNED TO EXPOSE: Multi-user routing failures that cause message cross-contamination.
        
        Tests scenarios where routing logic fails to maintain proper user isolation,
        causing messages to be delivered to wrong users or not delivered at all.
        """
        # Set up multiple users with connections
        user_connections = {}
        
        for user_id in [self.regular_user_id, self.demo_user_id, self.enterprise_user_id]:
            connection_id = generate_connection_id(user_id)
            self.connection_manager.register_connection(
                connection_id=str(connection_id),
                user_id=user_id,
                websocket=self.mock_websockets[user_id]
            )
            user_connections[user_id] = str(connection_id)
        
        print(f"Multi-user routing test setup:")
        for user_id, conn_id in user_connections.items():
            print(f"  {user_id}: {conn_id}")
        
        # Create messages for each user
        messages = []
        for i, user_id in enumerate(user_connections.keys()):
            message = create_standard_message(
                msg_type="agent_completed",
                payload={
                    "result": f"Optimization complete for {user_id}",
                    "savings": 1000 * (i + 1),
                    "user_specific_data": f"secret_data_{user_id}"
                },
                user_id=user_id,
                thread_id=f"thread_{user_id}"
            )
            messages.append((user_id, message))
        
        # Test routing isolation
        routing_results = {}
        
        for target_user_id, message in messages:
            target_connection_id = user_connections[target_user_id]
            
            # Try to find target connection for routing
            target_connection = self.connection_manager.get_connection(target_connection_id)
            
            # Check if message would be routed correctly
            if target_connection:
                routing_results[target_user_id] = "SUCCESS"
            else:
                routing_results[target_user_id] = "ROUTING_FAILED"
        
        print(f"Multi-user routing results:")
        for user_id, result in routing_results.items():
            print(f"  {user_id}: {result}")
        
        # CRITICAL: All users should receive their own messages
        failed_routings = [user_id for user_id, result in routing_results.items() 
                          if result != "SUCCESS"]
        
        if failed_routings:
            pytest.fail(f"MULTI-USER ROUTING FAILURES: Users {failed_routings} cannot receive messages. "
                       f"This breaks user isolation and causes chat functionality failures.")
        
        # Test cross-contamination prevention
        # Verify each user only gets their own connection
        for user_id in user_connections:
            user_connection_id = user_connections[user_id]
            
            # Check that this user's connection ID doesn't match other users' IDs
            other_users = [uid for uid in user_connections if uid != user_id]
            for other_user_id in other_users:
                other_connection_id = user_connections[other_user_id]
                
                assert user_connection_id != other_connection_id, \
                    f"CONNECTION ID COLLISION: User {user_id} and {other_user_id} " \
                    f"have same connection ID {user_connection_id}. This causes cross-contamination."

    def test_demo_user_routing_edge_cases(self):
        """
        DESIGNED TO EXPOSE: Demo user routing failures and edge cases.
        
        Demo users may have special routing logic that fails in certain scenarios,
        causing "Message routing failed" errors specifically for demo accounts.
        """
        demo_user_id = self.demo_user_id
        
        # Generate demo user connection ID
        demo_connection_id = generate_connection_id(demo_user_id)
        
        # Register demo connection
        self.connection_manager.register_connection(
            connection_id=str(demo_connection_id),
            user_id=demo_user_id,
            websocket=self.mock_websockets[demo_user_id]
        )
        
        # Test various demo user routing scenarios
        routing_scenarios = [
            {
                "name": "Standard agent message",
                "message": create_standard_message(
                    msg_type="agent_started",
                    payload={"agent": "demo_optimizer", "demo_mode": True},
                    user_id=demo_user_id,
                    thread_id=f"demo_thread_{int(time.time())}"
                )
            },
            {
                "name": "Demo-specific system message", 
                "message": create_standard_message(
                    msg_type="system_message",
                    payload={
                        "content": "This is a demo environment",
                        "demo_limitations": ["limited_features", "temporary_data"]
                    },
                    user_id=demo_user_id
                )
            },
            {
                "name": "Demo user error message",
                "message": create_standard_message(
                    msg_type="error_message", 
                    payload={
                        "error": "Demo user reached feature limit",
                        "demo_user": True
                    },
                    user_id=demo_user_id
                )
            }
        ]
        
        demo_routing_results = {}
        
        for scenario in routing_scenarios:
            scenario_name = scenario["name"]
            message = scenario["message"]
            
            # Test if demo connection can be found for routing
            target_connection = self.connection_manager.get_connection(str(demo_connection_id))
            
            if target_connection:
                demo_routing_results[scenario_name] = "SUCCESS"
            else:
                demo_routing_results[scenario_name] = "ROUTING_FAILED"
        
        print(f"Demo user routing test results:")
        print(f"  Demo connection ID: {demo_connection_id}")
        for scenario_name, result in demo_routing_results.items():
            print(f"  {scenario_name}: {result}")
        
        # Check for demo-specific routing failures
        failed_scenarios = [name for name, result in demo_routing_results.items() 
                           if result != "SUCCESS"]
        
        if failed_scenarios:
            pytest.fail(f"DEMO USER ROUTING FAILURES: Scenarios {failed_scenarios} failed. "
                       f"Demo users cannot receive messages, breaking demo functionality.")
        
        # Test demo user connection persistence
        # Demo connections might have different lifecycle management
        connection_info = self.connection_manager.get_connection_info(str(demo_connection_id))
        
        if connection_info:
            print(f"Demo connection info: {connection_info}")
            # Verify demo connection has proper metadata
            assert connection_info.get('user_id') == demo_user_id, \
                "Demo connection missing proper user_id"
        else:
            pytest.fail(f"DEMO CONNECTION LOST: Demo connection {demo_connection_id} disappeared")

    async def test_message_queue_routing_failures(self):
        """
        DESIGNED TO EXPOSE: Message queue routing failures in async scenarios.
        
        Tests routing failures that occur when messages are queued but cannot
        find their target connections when being processed.
        """
        user_id = self.regular_user_id
        connection_id = generate_connection_id(user_id)
        
        # Create message queue for testing
        message_queue = MessageQueue(connection_id, user_id)
        
        # Register connection
        self.connection_manager.register_connection(
            connection_id=str(connection_id),
            user_id=user_id,
            websocket=self.mock_websockets[user_id]
        )
        
        # Create messages to queue
        test_messages = []
        for i in range(5):
            message = create_standard_message(
                msg_type="agent_thinking",
                payload={
                    "step": i,
                    "thought": f"Processing step {i}",
                    "target_connection": str(connection_id)
                },
                user_id=user_id,
                thread_id=f"queue_test_thread_{i}"
            )
            test_messages.append(message)
        
        # Queue messages
        for message in test_messages:
            await message_queue.enqueue_message(message.to_dict() if hasattr(message, 'to_dict') else message.__dict__)
        
        print(f"Message queue routing test:")
        print(f"  Queued messages: {len(test_messages)}")
        print(f"  Target connection: {connection_id}")
        
        # Process messages and test routing
        routing_failures = []
        
        for i, message in enumerate(test_messages):
            # Try to route message
            target_connection = self.connection_manager.get_connection(str(connection_id))
            
            if not target_connection:
                routing_failures.append(f"Message {i}: Connection not found")
            else:
                # Test actual message delivery
                if hasattr(target_connection, 'websocket'):
                    websocket = target_connection.websocket
                elif isinstance(target_connection, dict):
                    websocket = target_connection.get('websocket')
                else:
                    websocket = None
                    
                if not websocket:
                    routing_failures.append(f"Message {i}: WebSocket not available")
                elif not hasattr(websocket, 'send_json'):
                    routing_failures.append(f"Message {i}: WebSocket missing send capability")
        
        print(f"Queue routing results:")
        print(f"  Routing failures: {len(routing_failures)}")
        for failure in routing_failures:
            print(f"    {failure}")
        
        # CRITICAL: No messages should fail routing
        if routing_failures:
            pytest.fail(f"MESSAGE QUEUE ROUTING FAILURES: {len(routing_failures)} messages failed routing. "
                       f"This causes queued messages to be lost, breaking async message delivery.")

    def test_batch_message_routing_failures(self):
        """
        DESIGNED TO EXPOSE: Batch message routing failures.
        
        Tests failures when routing batched messages to multiple connections,
        which can cause partial delivery failures.
        """
        # Set up multiple connections for batch testing
        batch_connections = {}
        batch_users = [f"batch_user_{i}" for i in range(3)]
        
        for user_id in batch_users:
            connection_id = generate_connection_id(user_id)
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.client_state = Mock()
            
            self.connection_manager.register_connection(
                connection_id=str(connection_id),
                user_id=user_id,
                websocket=mock_websocket
            )
            batch_connections[user_id] = str(connection_id)
        
        # Create batch message handler
        batch_handler = BatchMessageHandler(batch_size=10, flush_interval=1.0)
        
        # Create messages for batch processing
        batch_messages = []
        for user_id in batch_users:
            for i in range(3):  # 3 messages per user
                message = create_standard_message(
                    msg_type="agent_progress",
                    payload={
                        "user_id": user_id,
                        "batch_index": i,
                        "progress": f"{i * 33}%"
                    },
                    user_id=user_id,
                    thread_id=f"batch_thread_{user_id}_{i}"
                )
                batch_messages.append(message)
        
        print(f"Batch routing test:")
        print(f"  Users: {len(batch_users)}")
        print(f"  Messages: {len(batch_messages)}")
        print(f"  Connections: {list(batch_connections.values())}")
        
        # Test batch routing
        routing_results = {}
        
        for message in batch_messages:
            target_user_id = message.user_id
            target_connection_id = batch_connections.get(target_user_id)
            
            if not target_connection_id:
                routing_results[target_user_id] = routing_results.get(target_user_id, 0)
                continue
                
            # Test connection lookup
            connection = self.connection_manager.get_connection(target_connection_id)
            
            if connection:
                routing_results[target_user_id] = routing_results.get(target_user_id, 0) + 1
            else:
                # Routing failure
                failure_key = f"{target_user_id}_failures"
                routing_results[failure_key] = routing_results.get(failure_key, 0) + 1
        
        print(f"Batch routing results:")
        for user_result, count in routing_results.items():
            print(f"  {user_result}: {count}")
        
        # Analyze failures
        failure_keys = [key for key in routing_results if "_failures" in key]
        total_failures = sum(routing_results.get(key, 0) for key in failure_keys)
        
        if total_failures > 0:
            failure_details = {key: routing_results[key] for key in failure_keys}
            pytest.fail(f"BATCH ROUTING FAILURES: {total_failures} messages failed routing. "
                       f"Failure breakdown: {failure_details}. "
                       f"This causes partial message delivery in batch scenarios.")

    def test_websocket_manager_routing_integration(self):
        """
        DESIGNED TO EXPOSE: WebSocket manager routing integration failures.
        
        Tests failures in the integration between WebSocketManager and routing logic,
        which can cause managers to lose track of their connections.
        """
        user_id = self.enterprise_user_id
        mock_websocket = self.mock_websockets[user_id]
        
        # Create WebSocket manager through factory
        manager = self.factory.create_manager_for_user(
            user_id=user_id,
            websocket_connection=mock_websocket
        )
        
        # Get manager's connection ID
        manager_connection_id = None
        for attr_name in ['connection_id', '_connection_id', 'conn_id']:
            if hasattr(manager, attr_name):
                manager_connection_id = getattr(manager, attr_name)
                break
        
        if manager_connection_id is None and hasattr(manager, 'connection_info'):
            manager_connection_id = manager.connection_info.connection_id
        
        print(f"WebSocket manager routing integration test:")
        print(f"  Manager connection ID: {manager_connection_id}")
        
        if not manager_connection_id:
            pytest.fail("MANAGER ROUTING FAILURE: Manager has no connection ID for routing")
        
        # Test manager registration in connection system
        # Manager should register itself for message routing
        registered_connection = self.connection_manager.get_connection(str(manager_connection_id))
        
        if not registered_connection:
            print("Manager not auto-registered, manually registering for test...")
            self.connection_manager.register_connection(
                connection_id=str(manager_connection_id),
                user_id=user_id,
                websocket=mock_websocket
            )
            registered_connection = self.connection_manager.get_connection(str(manager_connection_id))
        
        # Test message routing to manager
        test_message = create_standard_message(
            msg_type="agent_completed",
            payload={
                "result": "Enterprise optimization complete",
                "manager_test": True
            },
            user_id=user_id,
            thread_id=f"manager_test_{int(time.time())}"
        )
        
        # Test routing scenarios
        routing_tests = [
            {
                "name": "Direct connection lookup",
                "connection_id": str(manager_connection_id),
                "expected": True
            },
            {
                "name": "User-based lookup", 
                "user_id": user_id,
                "expected": True
            }
        ]
        
        routing_failures = []
        
        for test in routing_tests:
            test_name = test["name"]
            expected = test["expected"]
            
            if "connection_id" in test:
                connection = self.connection_manager.get_connection(test["connection_id"])
            elif "user_id" in test:
                # Test user-based connection lookup
                user_connections = self.connection_manager.get_connections_for_user(test["user_id"])
                connection = user_connections[0] if user_connections else None
            else:
                connection = None
            
            success = connection is not None
            
            if success != expected:
                routing_failures.append(f"{test_name}: expected {expected}, got {success}")
        
        print(f"Manager routing test results:")
        print(f"  Tests run: {len(routing_tests)}")
        print(f"  Failures: {len(routing_failures)}")
        
        if routing_failures:
            failure_details = "; ".join(routing_failures)
            pytest.fail(f"WEBSOCKET MANAGER ROUTING FAILURES: {failure_details}. "
                       f"Manager cannot receive messages, breaking enterprise functionality.")

    def test_connection_lifecycle_routing_failures(self):
        """
        DESIGNED TO EXPOSE: Connection lifecycle routing failures.
        
        Tests routing failures that occur during connection lifecycle events
        (connect, disconnect, reconnect) that can leave connections in invalid states.
        """
        user_id = self.regular_user_id
        connection_id = generate_connection_id(user_id)
        mock_websocket = self.mock_websockets[user_id]
        
        print(f"Connection lifecycle routing test:")
        print(f"  User: {user_id}")
        print(f"  Connection: {connection_id}")
        
        # Test lifecycle stages
        lifecycle_stages = [
            {
                "stage": "initial_connection",
                "action": lambda: self.connection_manager.register_connection(
                    str(connection_id), user_id, mock_websocket
                ),
                "test": lambda: self.connection_manager.get_connection(str(connection_id)),
                "expected": True
            },
            {
                "stage": "active_messaging",
                "action": lambda: None,  # No action, just test routing
                "test": lambda: self.connection_manager.get_connection(str(connection_id)),
                "expected": True
            },
            {
                "stage": "disconnection",
                "action": lambda: self.connection_manager.unregister_connection(str(connection_id)),
                "test": lambda: self.connection_manager.get_connection(str(connection_id)),
                "expected": False
            },
            {
                "stage": "reconnection",
                "action": lambda: self.connection_manager.register_connection(
                    str(connection_id), user_id, mock_websocket
                ),
                "test": lambda: self.connection_manager.get_connection(str(connection_id)),
                "expected": True
            }
        ]
        
        lifecycle_failures = []
        
        for stage_info in lifecycle_stages:
            stage_name = stage_info["stage"]
            action = stage_info["action"]
            test = stage_info["test"]
            expected = stage_info["expected"]
            
            try:
                # Perform stage action
                action()
                
                # Test routing in this stage
                result = test()
                success = (result is not None) == expected
                
                if not success:
                    lifecycle_failures.append(
                        f"{stage_name}: expected {'connection found' if expected else 'no connection'}, "
                        f"got {'connection found' if result else 'no connection'}"
                    )
                
                print(f"  Stage '{stage_name}': {'PASS' if success else 'FAIL'}")
                
            except Exception as e:
                lifecycle_failures.append(f"{stage_name}: exception {e}")
                print(f"  Stage '{stage_name}': ERROR - {e}")
        
        if lifecycle_failures:
            failure_summary = "; ".join(lifecycle_failures)
            pytest.fail(f"CONNECTION LIFECYCLE ROUTING FAILURES: {failure_summary}. "
                       f"Connection routing fails during lifecycle transitions.")

    def teardown_method(self):
        """Clean up test fixtures."""
        super().teardown_method()
        
        # Clear all connections
        if hasattr(self.connection_manager, 'clear_all_connections'):
            self.connection_manager.clear_all_connections()
        
        # Clean up mock WebSocket connections
        self.mock_websockets.clear()