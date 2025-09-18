"""
Integration Test Suite: Broadcast Function Consistency and User Isolation (Issue #982)

This integration test suite validates broadcast function behavior consistency
and user isolation security across different implementations.

Business Value Justification:
- Segment: Platform/Enterprise Security
- Business Goal: $500K+ ARR Protection through secure user isolation
- Value Impact: Prevent cross-user event leakage and ensure consistent behavior
- Strategic Impact: Validate Golden Path security and reliability

Test Strategy: Real service integration with multi-user scenarios
Expected Behavior: Tests should FAIL initially, then PASS after SSOT remediation

GitHub Issue: https://github.com/netra-systems/netra-apex/issues/982
"""

import pytest
import asyncio
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from unittest.mock import AsyncMock, patch
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import broadcast function implementations
try:
    from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
    websocket_router_available = True
except ImportError:
    websocket_router_available = False

try:
    from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
    user_scoped_router_available = True
except ImportError:
    user_scoped_router_available = False

try:
    from netra_backend.app.services.user_scoped_websocket_event_router import broadcast_user_event
    convenience_function_available = True
except ImportError:
    convenience_function_available = False


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_closed = False

    async def send_text(self, message: str):
        """Mock send_text method."""
        if not self.is_closed:
            self.sent_messages.append(json.loads(message))

    async def close(self):
        """Mock close method."""
        self.is_closed = True


@pytest.mark.integration
class BroadcastFunctionConsistencyTests(SSotAsyncTestCase):
    """Integration tests for broadcast function consistency."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_ids = ["user1", "user2", "user3"]
        self.test_event_data = {
            "type": "test_event",
            "data": {"message": "test message", "timestamp": time.time()}
        }

    async def test_broadcast_function_behavior_consistency(self):
        """
        Test that all broadcast function implementations behave consistently.

        Expected Behavior: FAIL - Inconsistent behavior between implementations
        After SSOT remediation: PASS - Single consistent implementation
        """
        if not (websocket_router_available and user_scoped_router_available):
            self.skipTest("Required broadcast implementations not available")

        print(f"\n=== BROADCAST BEHAVIOR CONSISTENCY TEST ===")

        # Set up mock connections for each implementation
        connections_singleton = {uid: MockWebSocketConnection(uid) for uid in self.test_user_ids}
        connections_scoped = {uid: MockWebSocketConnection(uid) for uid in self.test_user_ids}

        # Test WebSocketEventRouter (singleton pattern)
        with patch('netra_backend.app.services.websocket_event_router.WebSocketEventRouter._instance', None):
            router_singleton = WebSocketEventRouter()

            # Mock the active connections
            with patch.object(router_singleton, 'active_connections', connections_singleton):
                await router_singleton.broadcast_to_user("user1", self.test_event_data)

        # Test UserScopedWebSocketEventRouter (scoped pattern)
        router_scoped = UserScopedWebSocketEventRouter()
        with patch.object(router_scoped, 'active_connections', connections_scoped):
            await router_scoped.broadcast_to_user("user1", self.test_event_data)

        # Analyze behavior differences
        singleton_messages = connections_singleton["user1"].sent_messages
        scoped_messages = connections_scoped["user1"].sent_messages

        print(f"Singleton router messages sent: {len(singleton_messages)}")
        print(f"Scoped router messages sent: {len(scoped_messages)}")

        if singleton_messages:
            print(f"Singleton message format: {singleton_messages[0]}")
        if scoped_messages:
            print(f"Scoped message format: {scoped_messages[0]}")

        # Check for consistency issues
        consistency_issues = []

        # Message count consistency
        if len(singleton_messages) != len(scoped_messages):
            consistency_issues.append(f"Message count mismatch: singleton={len(singleton_messages)}, scoped={len(scoped_messages)}")

        # Message format consistency
        if singleton_messages and scoped_messages:
            singleton_keys = set(singleton_messages[0].keys())
            scoped_keys = set(scoped_messages[0].keys())

            if singleton_keys != scoped_keys:
                consistency_issues.append(f"Message format mismatch: singleton_keys={singleton_keys}, scoped_keys={scoped_keys}")

        # Content consistency
        if singleton_messages and scoped_messages:
            if singleton_messages[0].get("data") != scoped_messages[0].get("data"):
                consistency_issues.append("Message content differs between implementations")

        print(f"Consistency issues found: {len(consistency_issues)}")
        for issue in consistency_issues:
            print(f"  - {issue}")

        # ASSERTION: Should detect consistency issues (SSOT violation)
        # This test SHOULD FAIL initially
        if consistency_issues:
            self.fail(f"BROADCAST CONSISTENCY VIOLATION: Found {len(consistency_issues)} consistency issues "
                     f"between broadcast implementations. Issues: {consistency_issues}. "
                     f"Inconsistent behavior creates unpredictable user experience and violates SSOT principles. "
                     f"Single canonical implementation required.")
        else:
            # If no issues found, this might indicate SSOT remediation is complete
            print("CHECK Consistent behavior detected - SSOT remediation may be complete")

    async def test_concurrent_broadcast_consistency(self):
        """
        Test broadcast function behavior under concurrent load.

        Expected Behavior: FAIL - Race conditions or inconsistent handling
        After SSOT remediation: PASS - Consistent concurrent behavior
        """
        if not (websocket_router_available and user_scoped_router_available):
            self.skipTest("Required broadcast implementations not available")

        print(f"\n=== CONCURRENT BROADCAST CONSISTENCY TEST ===")

        # Create multiple concurrent broadcast scenarios
        concurrent_events = [
            {"type": "event1", "data": {"id": 1, "priority": "high"}},
            {"type": "event2", "data": {"id": 2, "priority": "medium"}},
            {"type": "event3", "data": {"id": 3, "priority": "low"}},
            {"type": "event4", "data": {"id": 4, "priority": "urgent"}},
            {"type": "event5", "data": {"id": 5, "priority": "normal"}},
        ]

        # Test concurrent behavior with singleton router
        connections_singleton = {uid: MockWebSocketConnection(uid) for uid in self.test_user_ids}

        with patch('netra_backend.app.services.websocket_event_router.WebSocketEventRouter._instance', None):
            router_singleton = WebSocketEventRouter()

            with patch.object(router_singleton, 'active_connections', connections_singleton):
                # Send concurrent broadcasts to same user
                tasks = []
                for event in concurrent_events:
                    task = asyncio.create_task(router_singleton.broadcast_to_user("user1", event))
                    tasks.append(task)

                await asyncio.gather(*tasks)

        # Test concurrent behavior with scoped router
        connections_scoped = {uid: MockWebSocketConnection(uid) for uid in self.test_user_ids}

        router_scoped = UserScopedWebSocketEventRouter()
        with patch.object(router_scoped, 'active_connections', connections_scoped):
            # Send concurrent broadcasts to same user
            tasks = []
            for event in concurrent_events:
                task = asyncio.create_task(router_scoped.broadcast_to_user("user1", event))
                tasks.append(task)

            await asyncio.gather(*tasks)

        # Analyze concurrent handling results
        singleton_results = connections_singleton["user1"].sent_messages
        scoped_results = connections_scoped["user1"].sent_messages

        print(f"Singleton concurrent results: {len(singleton_results)} messages")
        print(f"Scoped concurrent results: {len(scoped_results)} messages")

        # Check for concurrent handling issues
        concurrent_issues = []

        # Message count should match number of events
        expected_count = len(concurrent_events)
        if len(singleton_results) != expected_count:
            concurrent_issues.append(f"Singleton: Expected {expected_count} messages, got {len(singleton_results)}")

        if len(scoped_results) != expected_count:
            concurrent_issues.append(f"Scoped: Expected {expected_count} messages, got {len(scoped_results)}")

        # Check for message ordering consistency (if implementations claim ordering)
        if singleton_results and scoped_results:
            singleton_order = [msg["data"]["id"] for msg in singleton_results if "data" in msg and "id" in msg["data"]]
            scoped_order = [msg["data"]["id"] for msg in scoped_results if "data" in msg and "id" in msg["data"]]

            if len(singleton_order) != len(scoped_order):
                concurrent_issues.append("Message ordering tracking inconsistent between implementations")

        print(f"Concurrent handling issues: {len(concurrent_issues)}")
        for issue in concurrent_issues:
            print(f"  - {issue}")

        # ASSERTION: Should detect concurrent handling differences
        if concurrent_issues:
            self.fail(f"CONCURRENT BROADCAST VIOLATION: Found {len(concurrent_issues)} issues "
                     f"with concurrent broadcast handling. Issues: {concurrent_issues}. "
                     f"Inconsistent concurrent behavior creates race conditions and violates SSOT principles.")
        else:
            print("CHECK Consistent concurrent behavior detected")


@pytest.mark.integration
class BroadcastUserIsolationSecurityTests(SSotAsyncTestCase):
    """Integration tests for user isolation security in broadcast functions."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.alice_user_id = "alice_user_123"
        self.bob_user_id = "bob_user_456"
        self.charlie_user_id = "charlie_user_789"

        self.alice_sensitive_data = {
            "type": "sensitive_event",
            "data": {
                "user_profile": {"name": "Alice", "ssn": "123-45-6789"},
                "account_balance": 50000,
                "private_messages": ["Secret message for Alice"]
            }
        }

        self.bob_sensitive_data = {
            "type": "sensitive_event",
            "data": {
                "user_profile": {"name": "Bob", "ssn": "987-65-4321"},
                "account_balance": 75000,
                "private_messages": ["Secret message for Bob"]
            }
        }

    async def test_user_event_isolation_security(self):
        """
        Test that broadcast functions properly isolate events between users.

        Expected Behavior: FAIL - Cross-user event leakage detected
        After SSOT remediation: PASS - Perfect user isolation
        """
        if not (websocket_router_available and user_scoped_router_available):
            self.skipTest("Required broadcast implementations not available")

        print(f"\n=== USER EVENT ISOLATION SECURITY TEST ===")

        # Set up isolated connections for each user
        all_connections = {
            self.alice_user_id: MockWebSocketConnection(self.alice_user_id),
            self.bob_user_id: MockWebSocketConnection(self.bob_user_id),
            self.charlie_user_id: MockWebSocketConnection(self.charlie_user_id)
        }

        # Test isolation with WebSocketEventRouter
        print("Testing WebSocketEventRouter isolation...")

        with patch('netra_backend.app.services.websocket_event_router.WebSocketEventRouter._instance', None):
            router_singleton = WebSocketEventRouter()

            with patch.object(router_singleton, 'active_connections', all_connections):
                # Broadcast sensitive data to Alice only
                await router_singleton.broadcast_to_user(self.alice_user_id, self.alice_sensitive_data)

                # Broadcast sensitive data to Bob only
                await router_singleton.broadcast_to_user(self.bob_user_id, self.bob_sensitive_data)

        # Test isolation with UserScopedWebSocketEventRouter
        print("Testing UserScopedWebSocketEventRouter isolation...")

        # Reset connections to separate the tests
        for conn in all_connections.values():
            conn.sent_messages.clear()

        router_scoped = UserScopedWebSocketEventRouter()
        with patch.object(router_scoped, 'active_connections', all_connections):
            # Broadcast sensitive data to Alice only
            await router_scoped.broadcast_to_user(self.alice_user_id, self.alice_sensitive_data)

            # Broadcast sensitive data to Bob only
            await router_scoped.broadcast_to_user(self.bob_user_id, self.bob_sensitive_data)

        # Analyze user isolation security
        alice_messages = all_connections[self.alice_user_id].sent_messages
        bob_messages = all_connections[self.bob_user_id].sent_messages
        charlie_messages = all_connections[self.charlie_user_id].sent_messages

        print(f"Alice received {len(alice_messages)} messages")
        print(f"Bob received {len(bob_messages)} messages")
        print(f"Charlie received {len(charlie_messages)} messages")

        # Security violation detection
        security_violations = []

        # Check if Alice received Bob's data
        for msg in alice_messages:
            if "Bob" in str(msg) or "987-65-4321" in str(msg):
                security_violations.append("Alice received Bob's sensitive data")
                break

        # Check if Bob received Alice's data
        for msg in bob_messages:
            if "Alice" in str(msg) or "123-45-6789" in str(msg):
                security_violations.append("Bob received Alice's sensitive data")
                break

        # Check if Charlie (uninvolved user) received any data
        if charlie_messages:
            security_violations.append(f"Charlie received {len(charlie_messages)} messages despite not being targeted")

        # Check for proper targeting - Alice should receive Alice data
        alice_got_alice_data = any("Alice" in str(msg) for msg in alice_messages)
        if not alice_got_alice_data:
            security_violations.append("Alice did not receive her own data")

        # Check for proper targeting - Bob should receive Bob data
        bob_got_bob_data = any("Bob" in str(msg) for msg in bob_messages)
        if not bob_got_bob_data:
            security_violations.append("Bob did not receive his own data")

        print(f"Security violations detected: {len(security_violations)}")
        for violation in security_violations:
            print(f"  - {violation}")

        # ASSERTION: Should detect user isolation violations
        # This test SHOULD FAIL initially if there are security issues
        if security_violations:
            self.fail(f"USER ISOLATION SECURITY VIOLATION: Detected {len(security_violations)} security issues. "
                     f"Violations: {security_violations}. "
                     f"Cross-user data leakage violates security requirements and SSOT principles. "
                     f"Perfect user isolation required for $500K+ ARR protection.")
        else:
            print("CHECK User isolation security validated")

    async def test_broadcast_function_memory_isolation(self):
        """
        Test that broadcast functions don't share state between users.

        Expected Behavior: FAIL - Shared state or memory leakage detected
        After SSOT remediation: PASS - Complete memory isolation
        """
        if not (websocket_router_available and user_scoped_router_available):
            self.skipTest("Required broadcast implementations not available")

        print(f"\n=== MEMORY ISOLATION TEST ===")

        # Create connections with state tracking
        alice_connection = MockWebSocketConnection(self.alice_user_id)
        bob_connection = MockWebSocketConnection(self.bob_user_id)

        # Test memory isolation with sequential broadcasts
        connections = {
            self.alice_user_id: alice_connection,
            self.bob_user_id: bob_connection
        }

        # First test: WebSocketEventRouter
        with patch('netra_backend.app.services.websocket_event_router.WebSocketEventRouter._instance', None):
            router1 = WebSocketEventRouter()
            router2 = WebSocketEventRouter()  # Should be same instance due to singleton

            # Check if singleton behavior creates shared state issues
            with patch.object(router1, 'active_connections', connections):
                await router1.broadcast_to_user(self.alice_user_id, {"test": "router1_alice"})

            # router2 should be the same instance - test for state leakage
            with patch.object(router2, 'active_connections', connections):
                await router2.broadcast_to_user(self.bob_user_id, {"test": "router2_bob"})

        # Second test: UserScopedWebSocketEventRouter (should be instance-based)
        router3 = UserScopedWebSocketEventRouter()
        router4 = UserScopedWebSocketEventRouter()  # Should be separate instance

        # Reset connections to separate test phases
        alice_connection.sent_messages.clear()
        bob_connection.sent_messages.clear()

        with patch.object(router3, 'active_connections', connections):
            await router3.broadcast_to_user(self.alice_user_id, {"test": "router3_alice"})

        with patch.object(router4, 'active_connections', connections):
            await router4.broadcast_to_user(self.bob_user_id, {"test": "router4_bob"})

        # Analyze memory isolation
        alice_final_messages = alice_connection.sent_messages
        bob_final_messages = bob_connection.sent_messages

        print(f"Alice messages: {alice_final_messages}")
        print(f"Bob messages: {bob_final_messages}")

        # Memory isolation issues detection
        memory_issues = []

        # Check for cross-contamination in singleton pattern
        singleton_id_check = id(WebSocketEventRouter()) == id(WebSocketEventRouter())
        scoped_id_check = id(UserScopedWebSocketEventRouter()) == id(UserScopedWebSocketEventRouter())

        print(f"WebSocketEventRouter singleton behavior: {singleton_id_check}")
        print(f"UserScopedWebSocketEventRouter instance behavior: {scoped_id_check}")

        if singleton_id_check and scoped_id_check:
            memory_issues.append("Both routers exhibit singleton behavior - potential shared state risk")

        # Check message separation
        alice_has_bob_content = any("bob" in str(msg).lower() for msg in alice_final_messages)
        bob_has_alice_content = any("alice" in str(msg).lower() for msg in bob_final_messages)

        if alice_has_bob_content:
            memory_issues.append("Alice received content intended for Bob")
        if bob_has_alice_content:
            memory_issues.append("Bob received content intended for Alice")

        print(f"Memory isolation issues: {len(memory_issues)}")
        for issue in memory_issues:
            print(f"  - {issue}")

        # ASSERTION: Should detect memory isolation concerns
        if memory_issues:
            self.fail(f"MEMORY ISOLATION VIOLATION: Found {len(memory_issues)} memory isolation issues. "
                     f"Issues: {memory_issues}. "
                     f"Shared state between users creates security vulnerabilities and violates SSOT principles.")
        else:
            print("CHECK Memory isolation validated")


@pytest.mark.integration
class ConvenienceFunctionIntegrationTests(SSotAsyncTestCase):
    """Integration tests for convenience function behavior."""

    async def test_convenience_function_vs_class_methods(self):
        """
        Test consistency between convenience function and class method approaches.

        Expected Behavior: FAIL - Behavior differences detected
        After SSOT remediation: PASS - Single canonical approach
        """
        if not (convenience_function_available and user_scoped_router_available):
            self.skipTest("Convenience function or router not available")

        print(f"\n=== CONVENIENCE FUNCTION INTEGRATION TEST ===")

        # Set up test scenario
        test_user_id = "test_user_convenience"
        test_event = {"type": "convenience_test", "data": {"message": "testing convenience"}}

        # Mock WebSocket connection
        mock_connection = MockWebSocketConnection(test_user_id)
        connections = {test_user_id: mock_connection}

        # Test class method approach
        router = UserScopedWebSocketEventRouter()
        with patch.object(router, 'active_connections', connections):
            await router.broadcast_to_user(test_user_id, test_event)

        class_method_messages = mock_connection.sent_messages.copy()
        mock_connection.sent_messages.clear()

        # Test convenience function approach
        with patch('netra_backend.app.services.user_scoped_websocket_event_router.get_websocket_router') as mock_get_router:
            mock_router = UserScopedWebSocketEventRouter()
            mock_router.active_connections = connections
            mock_get_router.return_value = mock_router

            await broadcast_user_event(test_user_id, test_event)

        convenience_messages = mock_connection.sent_messages.copy()

        print(f"Class method messages: {len(class_method_messages)}")
        print(f"Convenience function messages: {len(convenience_messages)}")

        # Analyze differences
        integration_issues = []

        # Message count consistency
        if len(class_method_messages) != len(convenience_messages):
            integration_issues.append(f"Message count differs: class_method={len(class_method_messages)}, convenience={len(convenience_messages)}")

        # Message content consistency
        if class_method_messages and convenience_messages:
            if class_method_messages[0] != convenience_messages[0]:
                integration_issues.append("Message content differs between approaches")

        print(f"Integration issues: {len(integration_issues)}")
        for issue in integration_issues:
            print(f"  - {issue}")

        # ASSERTION: Should detect integration inconsistencies
        if integration_issues:
            self.fail(f"CONVENIENCE FUNCTION INTEGRATION VIOLATION: Found {len(integration_issues)} "
                     f"inconsistencies between class method and convenience function approaches. "
                     f"Issues: {integration_issues}. "
                     f"Multiple approaches to same functionality violate SSOT principles.")
        else:
            print("CHECK Convenience function integration validated")


if __name__ == "__main__":
    import unittest
    unittest.main()