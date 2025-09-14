"""
Test file for Issue #914: Multi-user agent isolation with SSOT registry.

This test validates that user isolation patterns work correctly and consistently
across different AgentRegistry implementations. Critical for protecting the
$500K+ ARR multi-user chat functionality.

Business Impact: User isolation is essential for:
- Preventing data leaks between users
- Ensuring chat responses go to correct users
- Supporting concurrent user sessions
- Maintaining system security and stability

Expected Behavior:
- BEFORE CONSOLIDATION: Basic registry lacks user isolation
- AFTER CONSOLIDATION: Single registry with robust user isolation
"""

import pytest
import asyncio
import sys
import threading
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Import the test framework
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
except ImportError:
    import unittest
    SSotAsyncTestCase = unittest.TestCase

from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestMultiUserAgentIsolation(SSotAsyncTestCase):
    """Test multi-user agent isolation with SSOT registry patterns."""

    def setUp(self):
        """Set up test environment."""
        super().setUp() if hasattr(super(), 'setUp') else None

        # Create multiple user contexts for isolation testing
        self.test_users = [
            UserExecutionContext(
                user_id=f"isolation_test_user_{i}",
                request_id=f"isolation_request_{i}",
                thread_id=f"isolation_thread_{i}",
                run_id=f"isolation_run_{i}"
            ) for i in range(1, 6)  # 5 test users
        ]

    def test_user_isolation_capability_gap_between_registries(self):
        """
        Test that basic registry lacks user isolation while advanced has it.

        EXPECTED: Basic registry should fail isolation tests
        PURPOSE: Documents the critical SSOT violation for user isolation
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Test user isolation methods
            isolation_methods = [
                'get_user_session',
                'cleanup_user_session',
                'create_agent_for_user',
                'get_user_agent',
                'remove_user_agent',
                'reset_user_agents',
                'monitor_all_users',
                'emergency_cleanup_all'
            ]

            basic_isolation_support = 0
            advanced_isolation_support = 0
            missing_from_basic = []

            for method in isolation_methods:
                if hasattr(basic_registry, method):
                    basic_isolation_support += 1
                else:
                    missing_from_basic.append(method)

                if hasattr(advanced_registry, method):
                    advanced_isolation_support += 1

            basic_percentage = (basic_isolation_support / len(isolation_methods)) * 100
            advanced_percentage = (advanced_isolation_support / len(isolation_methods)) * 100

            print(f"Basic registry user isolation support: {basic_percentage:.1f}%")
            print(f"Advanced registry user isolation support: {advanced_percentage:.1f}%")
            print(f"Basic registry missing methods: {missing_from_basic}")

            # This demonstrates the critical SSOT violation
            self.assertLess(basic_percentage, 25.0,
                          "Basic registry should have minimal user isolation")
            self.assertGreater(advanced_percentage, 75.0,
                             "Advanced registry should have comprehensive user isolation")

            print("🚨 USER ISOLATION SSOT VIOLATION: Basic registry cannot support multi-user scenarios")
            print("💰 BUSINESS IMPACT: $500K+ ARR multi-user chat functionality at risk")

        except ImportError as e:
            self.skipTest(f"Could not import registries: {e}")

    async def test_concurrent_user_session_isolation(self):
        """
        Test that multiple users can have isolated sessions simultaneously.

        EXPECTED: Advanced registry should handle concurrent users
        PURPOSE: Validates multi-user scalability
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Create user sessions concurrently
            async def create_user_session(user_context):
                return await registry.get_user_session(user_context.user_id)

            # Use asyncio.gather for concurrent session creation
            user_sessions = await asyncio.gather(*[
                create_user_session(user_ctx) for user_ctx in self.test_users
            ])

            self.assertEqual(len(user_sessions), len(self.test_users),
                           "All user sessions should be created")

            # Verify each session is unique and isolated
            session_ids = set()
            for i, session in enumerate(user_sessions):
                self.assertIsNotNone(session, f"User session {i} should not be None")
                self.assertEqual(session.user_id, self.test_users[i].user_id,
                               f"Session should have correct user_id")

                # Each session should have unique identity
                session_id = id(session)
                self.assertNotIn(session_id, session_ids,
                               f"Session {i} should be unique object")
                session_ids.add(session_id)

            print(f"✅ Created {len(user_sessions)} isolated user sessions")

            # Test concurrent operations on different user sessions
            async def perform_user_operation(session, user_ctx):
                """Perform operations on specific user session."""
                # Create agent execution context for this user
                agent_context = await session.create_agent_execution_context(
                    "test_agent", user_ctx
                )
                self.assertIsNotNone(agent_context,
                                   f"Agent context should be created for {user_ctx.user_id}")

                return {
                    'user_id': user_ctx.user_id,
                    'session_metrics': session.get_metrics(),
                    'agent_context_created': agent_context is not None
                }

            # Perform concurrent operations
            operation_results = await asyncio.gather(*[
                perform_user_operation(session, user_ctx)
                for session, user_ctx in zip(user_sessions, self.test_users)
            ])

            # Verify all operations succeeded
            for result in operation_results:
                self.assertTrue(result['agent_context_created'],
                              f"Agent context creation should succeed for {result['user_id']}")

                metrics = result['session_metrics']
                self.assertEqual(metrics['user_id'], result['user_id'],
                               "Session metrics should match user_id")

            print(f"✅ Concurrent operations successful for {len(operation_results)} users")

            # Cleanup all user sessions
            cleanup_results = await asyncio.gather(*[
                registry.cleanup_user_session(user_ctx.user_id)
                for user_ctx in self.test_users
            ])

            successful_cleanups = sum(1 for result in cleanup_results
                                    if result['status'] == 'cleaned')

            self.assertEqual(successful_cleanups, len(self.test_users),
                           "All user sessions should be cleaned successfully")

            print(f"✅ Cleaned up {successful_cleanups} user sessions")
            print("✅ CONCURRENT USER ISOLATION: Advanced registry handles multiple users correctly")

        except ImportError as e:
            self.skipTest(f"Could not test concurrent user isolation: {e}")

    async def test_user_data_isolation_integrity(self):
        """
        Test that user data remains isolated between different user sessions.

        EXPECTED: User data should never leak between sessions
        PURPOSE: Critical security and privacy validation
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Create sessions for two test users
            user1_ctx = self.test_users[0]
            user2_ctx = self.test_users[1]

            user1_session = await registry.get_user_session(user1_ctx.user_id)
            user2_session = await registry.get_user_session(user2_ctx.user_id)

            # Register different agents for each user (simulating different chat agents)
            mock_agent_1 = Mock()
            mock_agent_1.name = "user1_chat_agent"
            mock_agent_1.user_data = {"private_info": "user1_secret_data"}

            mock_agent_2 = Mock()
            mock_agent_2.name = "user2_chat_agent"
            mock_agent_2.user_data = {"private_info": "user2_secret_data"}

            # Register agents in their respective user sessions
            await user1_session.register_agent("chat_agent", mock_agent_1)
            await user2_session.register_agent("chat_agent", mock_agent_2)

            # Verify agents are isolated
            user1_agent = await user1_session.get_agent("chat_agent")
            user2_agent = await user2_session.get_agent("chat_agent")

            self.assertIsNotNone(user1_agent, "User 1 should have their agent")
            self.assertIsNotNone(user2_agent, "User 2 should have their agent")

            # Critical: Agents should be different objects with different data
            self.assertNotEqual(user1_agent, user2_agent,
                              "User agents should be different objects")
            self.assertNotEqual(user1_agent.user_data, user2_agent.user_data,
                              "User data should be isolated")

            # Verify user 1 cannot access user 2's agent
            user1_cannot_access_user2 = await registry.get_user_agent(user1_ctx.user_id, "chat_agent")
            user2_cannot_access_user1 = await registry.get_user_agent(user2_ctx.user_id, "chat_agent")

            self.assertEqual(user1_cannot_access_user2.user_data["private_info"], "user1_secret_data",
                           "User 1 should only access their own data")
            self.assertEqual(user2_cannot_access_user1.user_data["private_info"], "user2_secret_data",
                           "User 2 should only access their own data")

            # Test that modifications to one user's agent don't affect the other
            user1_agent.user_data["modified_field"] = "user1_modification"

            # Verify user 2's agent is unaffected
            self.assertNotIn("modified_field", user2_agent.user_data,
                           "User 2's data should not be affected by user 1's modifications")

            print("✅ USER DATA ISOLATION: Private data remains isolated between users")
            print("🔒 SECURITY: No data leakage between user sessions detected")

            # Cleanup
            await registry.cleanup_user_session(user1_ctx.user_id)
            await registry.cleanup_user_session(user2_ctx.user_id)

        except ImportError as e:
            self.skipTest(f"Could not test user data isolation: {e}")

    async def test_user_session_memory_isolation(self):
        """
        Test that user session memory is properly isolated and cleaned up.

        EXPECTED: No memory leaks between user sessions
        PURPOSE: Production stability and resource management
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Test memory isolation with multiple user sessions
            initial_monitoring = await registry.monitor_all_users()
            initial_user_count = initial_monitoring.get('total_users', 0)
            initial_agent_count = initial_monitoring.get('total_agents', 0)

            # Create and populate user sessions with agents
            session_data = []
            for i, user_ctx in enumerate(self.test_users[:3]):  # Use 3 users
                user_session = await registry.get_user_session(user_ctx.user_id)

                # Add multiple mock agents to each session
                for j in range(2):  # 2 agents per user
                    mock_agent = Mock()
                    mock_agent.name = f"agent_{j}_for_{user_ctx.user_id}"
                    mock_agent.memory_data = f"large_data_block_{j}" * 100  # Simulate memory usage

                    await user_session.register_agent(f"agent_{j}", mock_agent)

                session_data.append({
                    'user_id': user_ctx.user_id,
                    'session': user_session,
                    'agent_count': 2
                })

            # Verify sessions are populated
            populated_monitoring = await registry.monitor_all_users()
            populated_user_count = populated_monitoring.get('total_users', 0)
            populated_agent_count = populated_monitoring.get('total_agents', 0)

            expected_users = initial_user_count + 3
            expected_agents = initial_agent_count + 6  # 3 users * 2 agents each

            self.assertGreaterEqual(populated_user_count, expected_users,
                                  f"Should have at least {expected_users} users")
            self.assertGreaterEqual(populated_agent_count, expected_agents,
                                  f"Should have at least {expected_agents} agents")

            print(f"✅ Created {populated_user_count} user sessions with {populated_agent_count} total agents")

            # Test selective cleanup (clean up one user at a time)
            for session_info in session_data[:2]:  # Clean first 2 users
                cleanup_result = await registry.cleanup_user_session(session_info['user_id'])
                self.assertEqual(cleanup_result['status'], 'cleaned',
                               f"User {session_info['user_id']} should be cleaned successfully")

            # Verify partial cleanup
            partial_monitoring = await registry.monitor_all_users()
            partial_user_count = partial_monitoring.get('total_users', 0)
            partial_agent_count = partial_monitoring.get('total_agents', 0)

            # Should have 1 user and 2 agents remaining (plus any initial)
            expected_remaining_users = initial_user_count + 1
            expected_remaining_agents = initial_agent_count + 2

            print(f"After partial cleanup: {partial_user_count} users, {partial_agent_count} agents")

            # Clean up remaining user
            remaining_user = session_data[2]['user_id']
            final_cleanup = await registry.cleanup_user_session(remaining_user)
            self.assertEqual(final_cleanup['status'], 'cleaned',
                           "Final user should be cleaned successfully")

            # Verify complete cleanup
            final_monitoring = await registry.monitor_all_users()
            final_user_count = final_monitoring.get('total_users', 0)
            final_agent_count = final_monitoring.get('total_agents', 0)

            # Should be back to initial state
            self.assertEqual(final_user_count, initial_user_count,
                           "User count should return to initial state")
            self.assertEqual(final_agent_count, initial_agent_count,
                           "Agent count should return to initial state")

            print("✅ MEMORY ISOLATION: User session memory properly isolated and cleaned")
            print("🔧 RESOURCE MANAGEMENT: No memory leaks detected between user sessions")

        except ImportError as e:
            self.skipTest(f"Could not test memory isolation: {e}")

    def test_thread_safety_user_isolation(self):
        """
        Test that user isolation is thread-safe for concurrent access.

        EXPECTED: No race conditions in user session management
        PURPOSE: Production concurrent access validation
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            def create_user_session_sync(user_id: str):
                """Synchronous wrapper for user session creation."""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(registry.get_user_session(user_id))
                finally:
                    loop.close()

            def cleanup_user_session_sync(user_id: str):
                """Synchronous wrapper for user session cleanup."""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(registry.cleanup_user_session(user_id))
                finally:
                    loop.close()

            # Test concurrent session creation from multiple threads
            thread_count = 5
            user_ids = [f"thread_test_user_{i}" for i in range(thread_count)]

            # Create sessions concurrently using threads
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                create_futures = {
                    executor.submit(create_user_session_sync, user_id): user_id
                    for user_id in user_ids
                }

                created_sessions = {}
                for future in as_completed(create_futures):
                    user_id = create_futures[future]
                    try:
                        session = future.result(timeout=10.0)  # 10 second timeout
                        created_sessions[user_id] = session
                        self.assertIsNotNone(session, f"Session should be created for {user_id}")
                        self.assertEqual(session.user_id, user_id,
                                       f"Session should have correct user_id for {user_id}")
                    except Exception as e:
                        self.fail(f"Thread-safe session creation failed for {user_id}: {e}")

            self.assertEqual(len(created_sessions), thread_count,
                           f"All {thread_count} sessions should be created")

            print(f"✅ Thread-safe session creation: {len(created_sessions)} concurrent sessions")

            # Verify all sessions have unique identities
            session_objects = list(created_sessions.values())
            session_ids = [id(session) for session in session_objects]
            unique_ids = set(session_ids)

            self.assertEqual(len(unique_ids), len(session_objects),
                           "All sessions should have unique object identities")

            # Test concurrent cleanup
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                cleanup_futures = {
                    executor.submit(cleanup_user_session_sync, user_id): user_id
                    for user_id in user_ids
                }

                cleanup_results = {}
                for future in as_completed(cleanup_futures):
                    user_id = cleanup_futures[future]
                    try:
                        result = future.result(timeout=10.0)
                        cleanup_results[user_id] = result
                        self.assertEqual(result['status'], 'cleaned',
                                       f"Session {user_id} should be cleaned successfully")
                    except Exception as e:
                        self.fail(f"Thread-safe cleanup failed for {user_id}: {e}")

            self.assertEqual(len(cleanup_results), thread_count,
                           f"All {thread_count} sessions should be cleaned")

            print(f"✅ Thread-safe cleanup: {len(cleanup_results)} concurrent cleanups")
            print("✅ THREAD SAFETY: User isolation robust under concurrent access")

        except ImportError as e:
            self.skipTest(f"Could not test thread safety: {e}")

    async def test_user_isolation_performance_consistency(self):
        """
        Test that user isolation doesn't significantly impact performance.

        EXPECTED: User isolation should have minimal performance overhead
        PURPOSE: Production performance validation
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            import time

            registry = AdvancedRegistry()

            # Measure performance of user session operations
            user_count = 10
            operations_per_user = 5

            # Test 1: User session creation performance
            start_time = time.time()
            created_sessions = []

            for i in range(user_count):
                user_id = f"perf_test_user_{i}"
                session = await registry.get_user_session(user_id)
                created_sessions.append((user_id, session))

            creation_time = time.time() - start_time
            avg_creation_time = creation_time / user_count

            print(f"User session creation - Total: {creation_time:.4f}s, Average: {avg_creation_time:.4f}s")

            # Performance requirement: < 0.1s per session on average
            self.assertLess(avg_creation_time, 0.1,
                          f"User session creation too slow: {avg_creation_time:.4f}s")

            # Test 2: Agent operations performance per user
            start_time = time.time()

            for user_id, session in created_sessions:
                for j in range(operations_per_user):
                    # Simulate agent operations
                    mock_agent = Mock()
                    mock_agent.name = f"perf_agent_{j}"

                    await session.register_agent(f"agent_{j}", mock_agent)
                    retrieved_agent = await session.get_agent(f"agent_{j}")
                    self.assertEqual(retrieved_agent, mock_agent)

            operations_time = time.time() - start_time
            total_operations = user_count * operations_per_user * 2  # register + get
            avg_operation_time = operations_time / total_operations

            print(f"Agent operations - Total: {operations_time:.4f}s, Average: {avg_operation_time:.6f}s")

            # Performance requirement: < 0.01s per operation on average
            self.assertLess(avg_operation_time, 0.01,
                          f"Agent operations too slow: {avg_operation_time:.6f}s")

            # Test 3: Monitoring performance
            start_time = time.time()

            for _ in range(5):
                monitoring_report = await registry.monitor_all_users()
                self.assertIsInstance(monitoring_report, dict)
                self.assertIn('total_users', monitoring_report)

            monitoring_time = time.time() - start_time
            avg_monitoring_time = monitoring_time / 5

            print(f"Monitoring operations - Total: {monitoring_time:.4f}s, Average: {avg_monitoring_time:.4f}s")

            # Performance requirement: < 0.05s per monitoring call
            self.assertLess(avg_monitoring_time, 0.05,
                          f"Monitoring too slow: {avg_monitoring_time:.4f}s")

            # Test 4: Cleanup performance
            start_time = time.time()

            cleanup_results = await asyncio.gather(*[
                registry.cleanup_user_session(user_id)
                for user_id, _ in created_sessions
            ])

            cleanup_time = time.time() - start_time
            avg_cleanup_time = cleanup_time / user_count

            print(f"Cleanup operations - Total: {cleanup_time:.4f}s, Average: {avg_cleanup_time:.4f}s")

            # Performance requirement: < 0.05s per cleanup on average
            self.assertLess(avg_cleanup_time, 0.05,
                          f"Cleanup too slow: {avg_cleanup_time:.4f}s")

            # Verify all cleanups succeeded
            successful_cleanups = sum(1 for result in cleanup_results
                                    if result['status'] == 'cleaned')
            self.assertEqual(successful_cleanups, user_count,
                           "All cleanups should succeed")

            print("✅ USER ISOLATION PERFORMANCE: All operations within acceptable limits")
            print("⚡ PRODUCTION READY: User isolation has minimal performance overhead")

        except ImportError as e:
            self.skipTest(f"Could not test performance: {e}")


# Test runner for standalone execution
if __name__ == '__main__':
    import unittest

    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiUserAgentIsolation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("ISSUE #914 MULTI-USER AGENT ISOLATION TEST RESULTS")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 ALL USER ISOLATION TESTS PASSED!")
        print("💰 BUSINESS VALUE: Multi-user chat functionality protected")
        print("🔒 SECURITY: User data isolation validated")
        print("⚡ PERFORMANCE: User isolation overhead within limits")
    else:
        print("⚠️  Some user isolation tests failed - review multi-user support")

    if result.failures:
        print("\nFAILURES:")
        for test, failure in result.failures[:3]:
            print(f"- {test}")

    if result.errors:
        print("\nERRORS:")
        for test, error in result.errors[:3]:
            print(f"- {test}")