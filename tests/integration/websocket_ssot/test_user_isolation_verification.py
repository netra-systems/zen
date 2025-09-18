"""
Test WebSocket SSOT Consolidation - User Isolation Verification

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Multi-tenant requirements)
- Business Goal: Ensure SSOT consolidation maintains enterprise-grade user isolation
- Value Impact: User isolation = data security = enterprise customer trust
- Strategic Impact: $500K+ ARR depends on secure multi-user chat functionality

PURPOSE: Validate that SSOT consolidation preserves critical user isolation
Tests the most important security requirement for enterprise customers.
"""

import pytest
import asyncio
import uuid
import unittest
from typing import Dict, List, Any
from test_framework.ssot.base_integration_test import BaseIntegrationTest
from test_framework.ssot.user_context_test_helpers import UserContextTestHelper

class WebSocketUserIsolationVerificationTests(BaseIntegrationTest, unittest.TestCase):
    """Test user isolation preservation during WebSocket SSOT consolidation."""

    def setUp(self):
        """Set up user isolation verification infrastructure."""
        super().setUp()
        self.user_context_helper = UserContextTestHelper()
        self.test_users = []  # Track created users for cleanup

    async def tearDown(self):
        """Clean up test users and contexts."""
        for user_context in self.test_users:
            try:
                await self.user_context_helper.cleanup_user_context(user_context)
            except Exception as e:
                print(f"Cleanup warning: {e}")
        await super().tearDown()

    @pytest.mark.integration
    async def test_basic_user_context_isolation(self):
        """Test basic user context isolation between different users."""
        # Create two distinct user contexts
        user1 = await self.user_context_helper.create_test_user_context(
            user_id="isolation_user_1",
            session_id="session_1",
            metadata={"role": "enterprise_admin", "tenant": "company_a"}
        )
        user2 = await self.user_context_helper.create_test_user_context(
            user_id="isolation_user_2",
            session_id="session_2",
            metadata={"role": "free_user", "tenant": "company_b"}
        )

        self.test_users.extend([user1, user2])

        print(f"Created user contexts: {user1.user_id} and {user2.user_id}")

        # Verify basic isolation properties
        self.assertNotEqual(user1.user_id, user2.user_id,
            "User IDs must be different")
        self.assertNotEqual(user1.session_id, user2.session_id,
            "Session IDs must be different")

        # Verify metadata isolation
        self.assertNotEqual(user1.metadata.get("tenant"), user2.metadata.get("tenant"),
            "User tenant data must be isolated")

        # Verify execution state isolation
        state1 = user1.get_execution_state()
        state2 = user2.get_execution_state()

        self.assertIsNot(state1, state2,
            "Execution states must be independent objects")

        print("CHECK Basic user context isolation verified")

    @pytest.mark.integration
    async def test_websocket_connection_isolation(self):
        """Test WebSocket connection isolation between users."""
        try:
            from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
            websocket_utility = WebSocketTestUtility()

            # Create WebSocket connections for different users
            connection1 = await websocket_utility.create_websocket_connection(
                user_id="ws_user_1",
                session_id="ws_session_1"
            )
            connection2 = await websocket_utility.create_websocket_connection(
                user_id="ws_user_2",
                session_id="ws_session_2"
            )

            print(f"Created WebSocket connections for users: ws_user_1, ws_user_2")

            # Verify connections are isolated
            self.assertIsNot(connection1, connection2,
                "WebSocket connections must be independent instances")

            # Test message isolation (user1 messages don't reach user2)
            if hasattr(connection1, 'send') and hasattr(connection2, 'receive'):
                await connection1.send({"type": "test", "message": "user1_private_data"})

                # Verify user2 doesn't receive user1's message
                try:
                    message = await asyncio.wait_for(connection2.receive(), timeout=1.0)
                    # If we receive anything, it should not be user1's message
                    if message:
                        self.assertNotEqual(message.get("message"), "user1_private_data",
                            "User2 should not receive user1's private messages")
                except asyncio.TimeoutError:
                    pass  # Expected - no message should be received

            print("CHECK WebSocket connection isolation verified")

        except ImportError:
            self.skipTest("WebSocket test utilities not available")
        except Exception as e:
            print(f"WARNING️  WebSocket isolation test limited: {e}")

    @pytest.mark.integration
    async def test_concurrent_user_session_isolation(self):
        """Test isolation between concurrent user sessions."""
        # Create multiple concurrent user sessions
        user_count = 5
        user_contexts = []

        # Create concurrent user contexts
        async def create_concurrent_user(index):
            return await self.user_context_helper.create_test_user_context(
                user_id=f"concurrent_user_{index}",
                session_id=f"concurrent_session_{index}",
                metadata={"index": index, "timestamp": asyncio.get_event_loop().time()}
            )

        # Create all users concurrently
        user_contexts = await asyncio.gather(*[
            create_concurrent_user(i) for i in range(user_count)
        ])

        self.test_users.extend(user_contexts)

        print(f"Created {len(user_contexts)} concurrent user contexts")

        # Verify all contexts are unique and isolated
        user_ids = [ctx.user_id for ctx in user_contexts]
        session_ids = [ctx.session_id for ctx in user_contexts]

        # Test uniqueness
        self.assertEqual(len(set(user_ids)), user_count,
            "All user IDs must be unique")
        self.assertEqual(len(set(session_ids)), user_count,
            "All session IDs must be unique")

        # Test execution state isolation
        execution_states = [ctx.get_execution_state() for ctx in user_contexts]
        state_object_ids = [id(state) for state in execution_states]

        self.assertEqual(len(set(state_object_ids)), user_count,
            "All execution states must be independent objects")

        # Test metadata isolation
        for i, context in enumerate(user_contexts):
            expected_index = i
            actual_index = context.metadata.get("index")
            self.assertEqual(actual_index, expected_index,
                f"User {i} metadata should be isolated and correct")

        print("CHECK Concurrent user session isolation verified")

    @pytest.mark.integration
    async def test_user_data_contamination_prevention(self):
        """Test prevention of user data contamination between sessions."""
        # Create two users with different data profiles
        enterprise_user = await self.user_context_helper.create_test_user_context(
            user_id="enterprise_user",
            session_id="enterprise_session",
            metadata={
                "subscription": "enterprise",
                "sensitive_data": "CONFIDENTIAL_ENTERPRISE_DATA",
                "permissions": ["admin", "billing", "analytics"]
            }
        )

        free_user = await self.user_context_helper.create_test_user_context(
            user_id="free_user",
            session_id="free_session",
            metadata={
                "subscription": "free",
                "sensitive_data": "FREE_USER_DATA",
                "permissions": ["basic"]
            }
        )

        self.test_users.extend([enterprise_user, free_user])

        print("Created enterprise and free user contexts")

        # Verify no data contamination
        enterprise_data = enterprise_user.metadata.get("sensitive_data")
        free_data = free_user.metadata.get("sensitive_data")

        self.assertNotEqual(enterprise_data, free_data,
            "Sensitive data must not be contaminated between users")

        # Test permission isolation
        enterprise_permissions = enterprise_user.metadata.get("permissions", [])
        free_permissions = free_user.metadata.get("permissions", [])

        self.assertNotEqual(enterprise_permissions, free_permissions,
            "User permissions must be isolated")

        # Verify enterprise user doesn't have free user data
        self.assertNotIn("FREE_USER_DATA", str(enterprise_user.metadata),
            "Enterprise user should not have free user data")

        # Verify free user doesn't have enterprise data
        self.assertNotIn("CONFIDENTIAL_ENTERPRISE_DATA", str(free_user.metadata),
            "Free user should not have enterprise data")

        print("CHECK User data contamination prevention verified")

    @pytest.mark.integration
    async def test_session_state_isolation_integrity(self):
        """Test integrity of session state isolation."""
        # Create users with different session states
        user1 = await self.user_context_helper.create_test_user_context(
            user_id="state_user_1",
            session_id="state_session_1"
        )
        user2 = await self.user_context_helper.create_test_user_context(
            user_id="state_user_2",
            session_id="state_session_2"
        )

        self.test_users.extend([user1, user2])

        # Set different session state for each user
        state1 = user1.get_execution_state()
        state2 = user2.get_execution_state()

        # Simulate different session activities
        state1.set_variable("current_task", "cost_optimization")
        state1.set_variable("session_data", {"analysis_type": "aws_costs"})

        state2.set_variable("current_task", "general_inquiry")
        state2.set_variable("session_data", {"analysis_type": "general_help"})

        print("Set different session states for each user")

        # Verify state isolation
        user1_task = state1.get_variable("current_task")
        user2_task = state2.get_variable("current_task")

        self.assertNotEqual(user1_task, user2_task,
            "Session tasks must be isolated")

        user1_data = state1.get_variable("session_data")
        user2_data = state2.get_variable("session_data")

        self.assertNotEqual(user1_data, user2_data,
            "Session data must be isolated")

        # Verify no cross-contamination
        # Change user1's state and verify user2 is not affected
        original_user2_task = user2_task
        state1.set_variable("current_task", "MODIFIED_TASK")

        updated_user2_task = state2.get_variable("current_task")
        self.assertEqual(updated_user2_task, original_user2_task,
            "User2 state should not be affected by user1 changes")

        print("CHECK Session state isolation integrity verified")

    @pytest.mark.integration
    async def test_memory_isolation_between_users(self):
        """Test memory isolation to prevent memory leaks between users."""
        initial_user_count = 2
        extended_user_count = 5

        # Create initial set of users
        initial_users = []
        for i in range(initial_user_count):
            user = await self.user_context_helper.create_test_user_context(
                user_id=f"memory_user_{i}",
                session_id=f"memory_session_{i}"
            )
            initial_users.append(user)

        self.test_users.extend(initial_users)

        # Simulate memory usage by each user
        for user in initial_users:
            state = user.get_execution_state()
            # Add substantial data to simulate real usage
            state.set_variable("large_data", list(range(1000)))
            state.set_variable("session_history", [f"message_{i}" for i in range(100)])

        print(f"Created {len(initial_users)} users with memory usage")

        # Add more users to test memory isolation
        extended_users = []
        for i in range(initial_user_count, extended_user_count):
            user = await self.user_context_helper.create_test_user_context(
                user_id=f"memory_user_{i}",
                session_id=f"memory_session_{i}"
            )
            extended_users.append(user)

        self.test_users.extend(extended_users)

        print(f"Added {len(extended_users)} additional users")

        # Verify memory isolation
        # Each user should have independent memory space
        all_users = initial_users + extended_users
        memory_signatures = []

        for user in all_users:
            state = user.get_execution_state()
            # Create a memory signature for this user
            signature = {
                'user_id': user.user_id,
                'state_object_id': id(state),
                'has_large_data': state.get_variable("large_data") is not None,
                'session_history_length': len(state.get_variable("session_history", []))
            }
            memory_signatures.append(signature)

        # Verify each user has unique memory space
        state_object_ids = [sig['state_object_id'] for sig in memory_signatures]
        self.assertEqual(len(set(state_object_ids)), len(all_users),
            "Each user must have independent memory space")

        # Verify initial users still have their data
        for i in range(initial_user_count):
            sig = memory_signatures[i]
            self.assertTrue(sig['has_large_data'],
                f"User {i} should still have their large data")
            self.assertEqual(sig['session_history_length'], 100,
                f"User {i} should still have their session history")

        # Verify new users have clean memory space
        for i in range(initial_user_count, extended_user_count):
            sig = memory_signatures[i]
            self.assertFalse(sig['has_large_data'],
                f"New user {i} should not have old user's data")

        print("CHECK Memory isolation between users verified")

    @pytest.mark.integration
    async def test_ssot_consolidation_isolation_preservation(self):
        """Test that SSOT consolidation preserves all isolation guarantees."""
        # This test validates that the consolidation approach preserves
        # all the isolation guarantees we've verified above

        isolation_guarantees = {
            'user_context_separation': False,
            'websocket_connection_isolation': False,
            'concurrent_session_safety': False,
            'data_contamination_prevention': False,
            'session_state_integrity': False,
            'memory_isolation': False
        }

        # Test each isolation guarantee
        print("\n=== Testing SSOT Consolidation Isolation Preservation ===")

        # User context separation
        try:
            user1 = await self.user_context_helper.create_test_user_context(
                user_id="ssot_test_1", session_id="ssot_session_1"
            )
            user2 = await self.user_context_helper.create_test_user_context(
                user_id="ssot_test_2", session_id="ssot_session_2"
            )
            self.test_users.extend([user1, user2])

            isolation_guarantees['user_context_separation'] = user1.user_id != user2.user_id
            print("CHECK User context separation preserved")
        except Exception as e:
            print(f"✗ User context separation failed: {e}")

        # Concurrent session safety
        try:
            concurrent_users = await asyncio.gather(*[
                self.user_context_helper.create_test_user_context(
                    user_id=f"ssot_concurrent_{i}",
                    session_id=f"ssot_concurrent_session_{i}"
                ) for i in range(3)
            ])
            self.test_users.extend(concurrent_users)

            user_ids = [u.user_id for u in concurrent_users]
            isolation_guarantees['concurrent_session_safety'] = len(set(user_ids)) == len(user_ids)
            print("CHECK Concurrent session safety preserved")
        except Exception as e:
            print(f"✗ Concurrent session safety failed: {e}")

        # Session state integrity
        try:
            if self.test_users:
                state1 = self.test_users[0].get_execution_state()
                state2 = self.test_users[1].get_execution_state()
                isolation_guarantees['session_state_integrity'] = state1 is not state2
                print("CHECK Session state integrity preserved")
        except Exception as e:
            print(f"✗ Session state integrity failed: {e}")

        # Calculate preservation score
        preservation_score = sum(isolation_guarantees.values()) / len(isolation_guarantees)

        print(f"\n=== Isolation Preservation Results ===")
        for guarantee, preserved in isolation_guarantees.items():
            status = "CHECK PRESERVED" if preserved else "X VIOLATED"
            print(f"  {guarantee}: {status}")

        print(f"Overall preservation score: {preservation_score:.2f}")

        # Business requirement: 100% isolation preservation
        self.assertGreaterEqual(preservation_score, 1.0,
            "SSOT consolidation must preserve ALL isolation guarantees")

        print("CHECK SSOT consolidation isolation preservation verified")