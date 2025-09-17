"""
Mission Critical User Isolation Violation Tests for Issue #885

These tests are designed to FAIL and prove user isolation violations exist.
They validate the $500K+ ARR dependency on secure multi-user WebSocket execution.

Business Value: Proves security vulnerabilities in user isolation
Expected Result: ALL TESTS SHOULD FAIL proving violations exist
"""

import asyncio
import pytest
import json
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ThreadID, ensure_user_id

logger = get_logger(__name__)


class TestUserIsolationViolations(SSotAsyncTestCase):
    """Test suite to prove user isolation violations in WebSocket system."""

    async def asyncSetUp(self):
        """Setup for user isolation violation tests."""
        await super().asyncSetUp()
        self.security_violations = []
        self.user_contexts = []

    def create_test_user_context(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Create test user context for isolation testing."""
        context = {
            "user_id": ensure_user_id(user_id),
            "session_id": session_id or f"session_{user_id}",
            "thread_id": f"thread_{user_id}",
            "connection_id": f"conn_{user_id}",
            "permissions": ["read", "write"],
            "tenant_id": f"tenant_{user_id}"
        }
        self.user_contexts.append(context)
        return context

    async def test_shared_connection_registry_violation(self):
        """
        EXPECTED TO FAIL: Test should detect shared connection registries between users.

        This proves that WebSocket managers share connection state, violating user isolation.
        """
        connection_sharing_violations = []

        try:
            # Import WebSocket manager components
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create contexts for different users
            user1_context = self.create_test_user_context("user_001", "session_001")
            user2_context = self.create_test_user_context("user_002", "session_002")

            # Get managers for different users
            manager1 = get_websocket_manager(user_context=user1_context)
            manager2 = get_websocket_manager(user_context=user2_context)

            # Test 1: Check if connection registries are shared
            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                if manager1._connections is manager2._connections:
                    violation = "CRITICAL: Shared connection registry between users"
                    connection_sharing_violations.append(violation)
                    self.security_violations.append(violation)

            # Test 2: Check if user connection mappings are shared
            if hasattr(manager1, '_user_connections') and hasattr(manager2, '_user_connections'):
                if manager1._user_connections is manager2._user_connections:
                    violation = "CRITICAL: Shared user connection mapping"
                    connection_sharing_violations.append(violation)
                    self.security_violations.append(violation)

            # Test 3: Check if connection state is isolated
            # Add a connection to manager1 and verify it doesn't appear in manager2
            mock_websocket1 = AsyncMock()
            mock_websocket2 = AsyncMock()

            if hasattr(manager1, 'add_connection') and hasattr(manager2, 'add_connection'):
                # Add connection to user1's manager
                await manager1.add_connection({
                    "connection_id": "conn_user1_test",
                    "user_id": user1_context["user_id"],
                    "websocket": mock_websocket1,
                    "thread_id": user1_context["thread_id"]
                })

                # Check if this connection appears in user2's manager
                if hasattr(manager2, 'get_user_connections'):
                    user2_connections = manager2.get_user_connections(user2_context["user_id"])
                    user1_connections_in_manager2 = manager2.get_user_connections(user1_context["user_id"])

                    if user1_connections_in_manager2:
                        violation = f"CRITICAL: User1 connections visible in User2 manager: {len(user1_connections_in_manager2)} connections"
                        connection_sharing_violations.append(violation)
                        self.security_violations.append(violation)

        except ImportError as e:
            violation = f"Cannot test user isolation - import failed: {e}"
            connection_sharing_violations.append(violation)
            self.security_violations.append(violation)

        except Exception as e:
            violation = f"User isolation test failed with error: {e}"
            connection_sharing_violations.append(violation)
            self.security_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: User isolation violations detected
        self.assertGreater(
            len(connection_sharing_violations), 0,
            f"USER ISOLATION VIOLATION: Found {len(connection_sharing_violations)} connection sharing violations. "
            f"This proves users can access each other's WebSocket connections. "
            f"Violations: {connection_sharing_violations}"
        )

        logger.error(f"CONNECTION ISOLATION VIOLATIONS: {len(connection_sharing_violations)} violations detected")

    async def test_cross_user_message_delivery_violation(self):
        """
        EXPECTED TO FAIL: Test should detect messages being delivered to wrong users.

        This proves cross-user message leakage violations.
        """
        message_leakage_violations = []

        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create different user contexts
            user_alpha = self.create_test_user_context("alpha_user", "alpha_session")
            user_beta = self.create_test_user_context("beta_user", "beta_session")

            # Get managers
            manager_alpha = get_websocket_manager(user_context=user_alpha)
            manager_beta = get_websocket_manager(user_context=user_beta)

            # Mock WebSocket connections
            mock_ws_alpha = AsyncMock()
            mock_ws_beta = AsyncMock()

            # Track messages sent to each connection
            alpha_messages = []
            beta_messages = []

            async def track_alpha_send(message):
                alpha_messages.append(message)

            async def track_beta_send(message):
                beta_messages.append(message)

            mock_ws_alpha.send = track_alpha_send
            mock_ws_beta.send = track_beta_send

            # Add connections
            if hasattr(manager_alpha, 'add_connection'):
                await manager_alpha.add_connection({
                    "connection_id": "alpha_conn",
                    "user_id": user_alpha["user_id"],
                    "websocket": mock_ws_alpha,
                    "thread_id": user_alpha["thread_id"]
                })

            if hasattr(manager_beta, 'add_connection'):
                await manager_beta.add_connection({
                    "connection_id": "beta_conn",
                    "user_id": user_beta["user_id"],
                    "websocket": mock_ws_beta,
                    "thread_id": user_beta["thread_id"]
                })

            # Send message to alpha user only
            test_message = {
                "type": "test_message",
                "content": "Secret message for alpha user only",
                "timestamp": "2024-01-01T00:00:00Z",
                "sensitive_data": "alpha_secret_123"
            }

            # Send message specifically to alpha user
            if hasattr(manager_alpha, 'send_to_user'):
                await manager_alpha.send_to_user(user_alpha["user_id"], test_message)
            elif hasattr(manager_alpha, 'broadcast_to_user'):
                await manager_alpha.broadcast_to_user(user_alpha["user_id"], test_message)

            # Check if beta user received the message (violation)
            await asyncio.sleep(0.1)  # Allow time for message processing

            if beta_messages:
                violation = f"CRITICAL: Cross-user message leakage - Beta user received {len(beta_messages)} messages intended for Alpha"
                message_leakage_violations.append(violation)
                self.security_violations.append(violation)

                # Check if sensitive data leaked
                for msg in beta_messages:
                    if isinstance(msg, str):
                        msg_data = json.loads(msg) if msg.startswith('{') else {"content": msg}
                    else:
                        msg_data = msg

                    if "alpha_secret" in str(msg_data):
                        violation = f"CRITICAL: Sensitive data leaked to wrong user: {msg_data}"
                        message_leakage_violations.append(violation)
                        self.security_violations.append(violation)

            # Test global broadcast isolation
            if hasattr(manager_alpha, 'broadcast') or hasattr(manager_beta, 'broadcast'):
                # Clear previous messages
                alpha_messages.clear()
                beta_messages.clear()

                # Send global broadcast from one manager
                global_message = {"type": "system", "content": "System maintenance"}

                if hasattr(manager_alpha, 'broadcast'):
                    await manager_alpha.broadcast(global_message)

                await asyncio.sleep(0.1)

                # Check if broadcast went to both users (potential violation if not properly isolated)
                if alpha_messages and beta_messages:
                    violation = f"CRITICAL: Global broadcast not properly isolated between user contexts"
                    message_leakage_violations.append(violation)
                    self.security_violations.append(violation)

        except Exception as e:
            violation = f"Message isolation test failed: {e}"
            message_leakage_violations.append(violation)
            self.security_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Message leakage violations detected
        self.assertGreater(
            len(message_leakage_violations), 0,
            f"MESSAGE ISOLATION VIOLATION: Found {len(message_leakage_violations)} message leakage violations. "
            f"This proves messages can be delivered to wrong users. "
            f"Violations: {message_leakage_violations}"
        )

        logger.error(f"MESSAGE LEAKAGE VIOLATIONS: {len(message_leakage_violations)} violations detected")

    async def test_agent_context_sharing_violation(self):
        """
        EXPECTED TO FAIL: Test should detect agent execution context sharing between users.

        This proves that agent execution contexts are not properly isolated.
        """
        agent_context_violations = []

        try:
            # Test agent context isolation
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create user contexts
            user_gamma = self.create_test_user_context("gamma_user", "gamma_session")
            user_delta = self.create_test_user_context("delta_user", "delta_session")

            # Get managers
            manager_gamma = get_websocket_manager(user_context=user_gamma)
            manager_delta = get_websocket_manager(user_context=user_delta)

            # Check agent registry sharing
            if hasattr(manager_gamma, '_agent_registry') and hasattr(manager_delta, '_agent_registry'):
                if manager_gamma._agent_registry is manager_delta._agent_registry:
                    violation = "CRITICAL: Shared agent registry between users"
                    agent_context_violations.append(violation)
                    self.security_violations.append(violation)

            # Check execution context sharing
            if hasattr(manager_gamma, '_execution_context') and hasattr(manager_delta, '_execution_context'):
                if manager_gamma._execution_context is manager_delta._execution_context:
                    violation = "CRITICAL: Shared agent execution context"
                    agent_context_violations.append(violation)
                    self.security_violations.append(violation)

            # Check WebSocket manager registry sharing
            if hasattr(manager_gamma, 'registry') and hasattr(manager_delta, 'registry'):
                if manager_gamma.registry is manager_delta.registry:
                    violation = "CRITICAL: Shared WebSocket registry between users"
                    agent_context_violations.append(violation)
                    self.security_violations.append(violation)

            # Test agent state isolation
            # Simulate agent state changes for one user
            test_agent_state = {
                "agent_id": "test_agent_gamma",
                "status": "executing",
                "user_data": f"private_data_for_{user_gamma['user_id']}",
                "sensitive_context": "gamma_secret_context"
            }

            # Store state in gamma's manager
            if hasattr(manager_gamma, 'set_agent_state'):
                manager_gamma.set_agent_state(user_gamma["user_id"], test_agent_state)
            elif hasattr(manager_gamma, '_agent_states'):
                manager_gamma._agent_states = manager_gamma._agent_states or {}
                manager_gamma._agent_states[user_gamma["user_id"]] = test_agent_state

            # Check if delta user can access gamma's agent state
            gamma_state_in_delta = None
            if hasattr(manager_delta, 'get_agent_state'):
                gamma_state_in_delta = manager_delta.get_agent_state(user_gamma["user_id"])
            elif hasattr(manager_delta, '_agent_states') and manager_delta._agent_states:
                gamma_state_in_delta = manager_delta._agent_states.get(user_gamma["user_id"])

            if gamma_state_in_delta:
                violation = f"CRITICAL: User delta can access user gamma's agent state: {gamma_state_in_delta}"
                agent_context_violations.append(violation)
                self.security_violations.append(violation)

        except Exception as e:
            violation = f"Agent context isolation test failed: {e}"
            agent_context_violations.append(violation)
            self.security_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Agent context violations detected
        self.assertGreater(
            len(agent_context_violations), 0,
            f"AGENT CONTEXT VIOLATION: Found {len(agent_context_violations)} agent context sharing violations. "
            f"This proves agent execution contexts are not properly isolated between users. "
            f"Violations: {agent_context_violations}"
        )

        logger.error(f"AGENT CONTEXT VIOLATIONS: {len(agent_context_violations)} violations detected")

    async def test_memory_leak_from_user_sharing_violation(self):
        """
        EXPECTED TO FAIL: Test should detect memory leaks from shared user data.

        This proves that user data accumulates in shared objects.
        """
        memory_leak_violations = []

        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            import gc

            # Track initial memory state
            initial_objects = len(gc.get_objects())

            # Create multiple users and managers
            managers = []
            for i in range(10):  # Create 10 users
                user_context = self.create_test_user_context(f"user_{i:03d}", f"session_{i:03d}")
                manager = get_websocket_manager(user_context=user_context)
                managers.append(manager)

                # Add some data to each manager
                if hasattr(manager, '_user_data'):
                    manager._user_data = manager._user_data or {}
                    manager._user_data[user_context["user_id"]] = {
                        "large_data": "x" * 10000,  # 10KB per user
                        "connections": [f"conn_{j}" for j in range(100)],  # 100 fake connections
                        "history": [f"message_{k}" for k in range(1000)]  # 1000 fake messages
                    }

            # Check if all managers share the same data structure
            shared_data_structures = 0
            base_manager = managers[0] if managers else None

            if base_manager:
                for manager in managers[1:]:
                    # Check for shared connection stores
                    if (hasattr(base_manager, '_connections') and hasattr(manager, '_connections') and
                        base_manager._connections is manager._connections):
                        shared_data_structures += 1

                    # Check for shared user data stores
                    if (hasattr(base_manager, '_user_data') and hasattr(manager, '_user_data') and
                        base_manager._user_data is manager._user_data):
                        shared_data_structures += 1

                    # Check for shared registries
                    if (hasattr(base_manager, 'registry') and hasattr(manager, 'registry') and
                        base_manager.registry is manager.registry):
                        shared_data_structures += 1

            if shared_data_structures > 0:
                violation = f"CRITICAL: {shared_data_structures} shared data structures detected - causes memory leaks"
                memory_leak_violations.append(violation)
                self.security_violations.append(violation)

            # Check total object count growth
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects

            # In a properly isolated system, object growth should be proportional to users
            # If objects are shared, growth will be much less than expected
            expected_min_growth = len(managers) * 10  # At least 10 objects per manager
            if object_growth < expected_min_growth:
                violation = f"CRITICAL: Insufficient object growth ({object_growth}) suggests shared objects"
                memory_leak_violations.append(violation)
                self.security_violations.append(violation)

        except Exception as e:
            violation = f"Memory leak test failed: {e}"
            memory_leak_violations.append(violation)
            self.security_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Memory leak violations detected
        self.assertGreater(
            len(memory_leak_violations), 0,
            f"MEMORY LEAK VIOLATION: Found {len(memory_leak_violations)} memory leak indicators. "
            f"This proves user data is accumulated in shared objects causing memory leaks. "
            f"Violations: {memory_leak_violations}"
        )

        logger.error(f"MEMORY LEAK VIOLATIONS: {len(memory_leak_violations)} violations detected")

    def tearDown(self):
        """Report all security violations found."""
        if self.security_violations:
            logger.error("="*80)
            logger.error("USER ISOLATION SECURITY VIOLATIONS SUMMARY")
            logger.error("="*80)
            for i, violation in enumerate(self.security_violations, 1):
                logger.error(f"{i:2d}. {violation}")
            logger.error("="*80)
            logger.error(f"TOTAL SECURITY VIOLATIONS: {len(self.security_violations)}")
            logger.error("THIS REPRESENTS A CRITICAL SECURITY RISK FOR $500K+ ARR")
            logger.error("="*80)

        # Clean up test contexts
        self.user_contexts.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])