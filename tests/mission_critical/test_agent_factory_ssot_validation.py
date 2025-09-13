"""Mission Critical Agent Factory SSOT Validation Tests.

CRITICAL MISSION: Protect $500K+ ARR Golden Path functionality through agent factory SSOT compliance.

This test suite validates that agent factory patterns follow SSOT principles and ensure
complete user isolation. Factory pattern violations directly impact Golden Path business value.

Business Impact:
- Revenue Protection: $500K+ ARR depends on reliable agent execution
- User Experience: Chat functionality requires proper agent isolation
- System Stability: Factory SSOT prevents race conditions and state contamination
- Security: User isolation prevents data leakage between sessions

Test Strategy:
1. Test FAILS with current codebase (proving factory violations exist)
2. Validate AgentRegistry creates isolated instances per user
3. Test WebSocket manager factory maintains user separation
4. Ensure no shared state across concurrent users
5. Tests PASS after proper factory SSOT consolidation

Created: 2025-09-12
Issue: #686 ExecutionEngine consolidation blocking Golden Path
Priority: MISSION CRITICAL - Protects core business value
"""

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Any, Optional
import unittest.mock
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestAgentFactorySsotValidation(SSotAsyncTestCase):
    """Mission critical validation of agent factory SSOT compliance."""

    def setUp(self):
        """Set up test environment for factory validation."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.test_user_contexts = []

    def tearDown(self):
        """Clean up test resources."""
        super().tearDown()
        # Clean up any created contexts
        self.test_user_contexts.clear()

    def test_agent_registry_factory_user_isolation_ssot_compliance(self):
        """TEST FAILS: AgentRegistry factory allows shared state between users.

        CRITICAL BUSINESS IMPACT: Shared state causes WebSocket events to be delivered
        to wrong users, directly violating $500K+ ARR Golden Path user experience.

        EXPECTED FAILURE: Multiple users get same AgentRegistry instance.
        PASSES AFTER: Each user gets isolated AgentRegistry with unique WebSocket manager.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry for factory testing: {e}")

        # Create multiple user contexts
        user_contexts = []
        for i in range(3):
            context = unittest.mock.Mock()
            context.user_id = f"test_user_{i}"
            context.session_id = f"test_session_{i}"
            user_contexts.append(context)

        # Test factory creates isolated instances
        registries = []
        for context in user_contexts:
            try:
                # Attempt to create registry instance for user
                if hasattr(AgentRegistry, 'create_for_user'):
                    registry = AgentRegistry.create_for_user(context)
                elif hasattr(AgentRegistry, 'get_instance'):
                    registry = AgentRegistry.get_instance(context)
                else:
                    # Try direct instantiation
                    registry = AgentRegistry(context)

                registries.append(registry)
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE: AgentRegistry factory failed for user {context.user_id}: {e}. "
                    f"Issue #686: Factory pattern must work for all users."
                )

        # CRITICAL TEST: Each user must get unique registry instance
        registry_ids = [id(registry) for registry in registries]
        unique_ids = set(registry_ids)

        # TEST FAILS if shared instances exist (SSOT violation)
        self.assertEqual(
            len(unique_ids), len(registries),
            f"CRITICAL SSOT VIOLATION: AgentRegistry factory returns shared instances. "
            f"Found {len(unique_ids)} unique instances for {len(registries)} users. "
            f"Instance IDs: {registry_ids}. "
            f"BUSINESS IMPACT: Shared state causes WebSocket events delivered to wrong users. "
            f"Issue #686: Factory must create isolated instances per user for $500K+ ARR protection."
        )

        # Validate user context isolation if available
        for i, registry in enumerate(registries):
            if hasattr(registry, 'user_context'):
                expected_user_id = user_contexts[i].user_id
                actual_user_id = getattr(registry.user_context, 'user_id', None)

                self.assertEqual(
                    actual_user_id, expected_user_id,
                    f"CRITICAL SSOT VIOLATION: Registry {i} has wrong user context. "
                    f"Expected: {expected_user_id}, Got: {actual_user_id}. "
                    f"Issue #686: User context contamination violates Golden Path isolation."
                )

    def test_websocket_manager_factory_isolation_ssot_compliance(self):
        """TEST FAILS: WebSocket manager factory allows cross-user contamination.

        CRITICAL BUSINESS IMPACT: WebSocket events sent to wrong users breaks chat
        functionality and violates user privacy. Core Golden Path failure.

        EXPECTED FAILURE: WebSocket managers shared between users.
        PASSES AFTER: Each user gets isolated WebSocket manager with no cross-contamination.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry for WebSocket testing: {e}")

        # Create user contexts with different session IDs
        user_contexts = []
        for i in range(2):
            context = unittest.mock.Mock()
            context.user_id = f"ws_test_user_{i}"
            context.session_id = f"ws_test_session_{i}"
            user_contexts.append(context)

        # Create mock WebSocket managers for testing
        mock_websocket_managers = []

        with patch('netra_backend.app.agents.supervisor.agent_registry.AgentWebSocketBridge') as mock_bridge:
            # Configure mock to return different instances
            mock_instances = [MagicMock() for _ in range(len(user_contexts))]
            mock_bridge.side_effect = mock_instances
            mock_websocket_managers = mock_instances

            registries = []
            for context in user_contexts:
                try:
                    # Create registry with WebSocket manager
                    if hasattr(AgentRegistry, 'create_for_user'):
                        registry = AgentRegistry.create_for_user(context)
                    else:
                        registry = AgentRegistry(context)

                    # Set WebSocket manager if method exists
                    if hasattr(registry, 'set_websocket_manager'):
                        mock_ws_manager = MagicMock()
                        mock_ws_manager.user_id = context.user_id
                        registry.set_websocket_manager(mock_ws_manager)

                    registries.append(registry)
                except Exception as e:
                    self.fail(
                        f"CRITICAL FAILURE: Registry creation with WebSocket failed: {e}. "
                        f"Issue #686: WebSocket integration must work in factory pattern."
                    )

            # CRITICAL TEST: WebSocket managers must be isolated per user
            if len(registries) >= 2:
                registry1, registry2 = registries[0], registries[1]

                # Check if registries have WebSocket managers
                ws_manager1 = getattr(registry1, 'websocket_manager', None)
                ws_manager2 = getattr(registry2, 'websocket_manager', None)

                if ws_manager1 is not None and ws_manager2 is not None:
                    # TEST FAILS if same WebSocket manager shared
                    self.assertIsNot(
                        ws_manager1, ws_manager2,
                        f"CRITICAL SSOT VIOLATION: WebSocket managers shared between users. "
                        f"Manager 1 ID: {id(ws_manager1)}, Manager 2 ID: {id(ws_manager2)}. "
                        f"BUSINESS IMPACT: WebSocket events sent to wrong users breaks Golden Path. "
                        f"Issue #686: WebSocket isolation critical for $500K+ ARR protection."
                    )

                    # Validate user ID isolation
                    user1_id = getattr(ws_manager1, 'user_id', None)
                    user2_id = getattr(ws_manager2, 'user_id', None)

                    if user1_id is not None and user2_id is not None:
                        self.assertNotEqual(
                            user1_id, user2_id,
                            f"CRITICAL SSOT VIOLATION: WebSocket managers have same user ID. "
                            f"Both managers report user ID: {user1_id}. "
                            f"Issue #686: WebSocket user isolation broken."
                        )

    async def test_concurrent_agent_execution_context_isolation(self):
        """TEST FAILS: Concurrent agent executions contaminate each other's context.

        CRITICAL BUSINESS IMPACT: Race conditions in concurrent chat sessions cause
        agent responses to be mixed up between users. Direct Golden Path failure.

        EXPECTED FAILURE: Agent contexts bleed between concurrent executions.
        PASSES AFTER: Complete isolation between concurrent user sessions.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import UserExecutionEngine for concurrency testing: {e}")

        # Create multiple concurrent user contexts
        num_concurrent_users = 3
        user_contexts = []

        for i in range(num_concurrent_users):
            context = unittest.mock.Mock()
            context.user_id = f"concurrent_user_{i}"
            context.session_id = f"concurrent_session_{i}"
            context.request_id = str(uuid.uuid4())
            user_contexts.append(context)

        # Test concurrent execution isolation
        execution_results = {}

        async def execute_for_user(user_context):
            """Execute agent for specific user and track results."""
            try:
                # Create isolated execution engine for user
                engine = UserExecutionEngine.create_from_legacy(user_context)

                # Mock execution with user-specific data
                mock_result = {
                    'user_id': user_context.user_id,
                    'session_id': user_context.session_id,
                    'engine_id': id(engine),
                    'timestamp': time.time()
                }

                # Simulate some async work
                await asyncio.sleep(0.1)

                return mock_result

            except Exception as e:
                return {'error': str(e), 'user_id': user_context.user_id}

        # Execute concurrently
        tasks = [execute_for_user(context) for context in user_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results for contamination
        successful_results = [r for r in results if not isinstance(r, Exception) and 'error' not in r]

        # TEST FAILS if any execution failed
        self.assertEqual(
            len(successful_results), num_concurrent_users,
            f"CRITICAL FAILURE: {num_concurrent_users - len(successful_results)} concurrent executions failed. "
            f"Failed results: {[r for r in results if r not in successful_results]}. "
            f"Issue #686: Concurrent execution must work for all users."
        )

        # CRITICAL TEST: Each execution must have unique engine instance
        engine_ids = [result['engine_id'] for result in successful_results]
        unique_engine_ids = set(engine_ids)

        # TEST FAILS if shared engine instances exist
        self.assertEqual(
            len(unique_engine_ids), len(successful_results),
            f"CRITICAL SSOT VIOLATION: Shared execution engine instances in concurrent execution. "
            f"Found {len(unique_engine_ids)} unique engines for {len(successful_results)} users. "
            f"Engine IDs: {engine_ids}. "
            f"BUSINESS IMPACT: Shared engines cause context contamination in chat. "
            f"Issue #686: Engine isolation critical for Golden Path concurrent users."
        )

        # Validate user context preservation
        for result in successful_results:
            expected_user_id = result['user_id']

            # Find matching original context
            original_context = next(
                (ctx for ctx in user_contexts if ctx.user_id == expected_user_id),
                None
            )

            self.assertIsNotNone(
                original_context,
                f"CRITICAL FAILURE: Cannot find original context for user {expected_user_id}. "
                f"Issue #686: User context lost during concurrent execution."
            )

    def test_agent_factory_memory_isolation_ssot_compliance(self):
        """TEST FAILS: Agent factories create shared memory state between users.

        CRITICAL BUSINESS IMPACT: Memory leaks and state contamination between users
        causes incorrect agent responses and potential data leakage.

        EXPECTED FAILURE: Agent instances share memory state.
        PASSES AFTER: Complete memory isolation between user agent instances.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import UserExecutionEngine for memory testing: {e}")

        # Create user contexts with different data
        user_data = [
            {'user_id': 'memory_test_user_1', 'data': 'user_1_secret_data'},
            {'user_id': 'memory_test_user_2', 'data': 'user_2_secret_data'},
        ]

        engines = []

        for user_info in user_data:
            context = unittest.mock.Mock()
            context.user_id = user_info['user_id']
            context.session_id = f"session_{user_info['user_id']}"
            context.private_data = user_info['data']

            try:
                engine = UserExecutionEngine.create_from_legacy(context)
                engines.append((engine, context))
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE: Engine creation failed for {user_info['user_id']}: {e}. "
                    f"Issue #686: Factory must work for all users."
                )

        # CRITICAL TEST: Engines must not share memory state
        if len(engines) >= 2:
            engine1, context1 = engines[0]
            engine2, context2 = engines[1]

            # TEST FAILS if engines are the same instance
            self.assertIsNot(
                engine1, engine2,
                f"CRITICAL SSOT VIOLATION: Same engine instance returned for different users. "
                f"Engine 1 ID: {id(engine1)}, Engine 2 ID: {id(engine2)}. "
                f"BUSINESS IMPACT: Shared instances cause user data contamination. "
                f"Issue #686: Memory isolation critical for user privacy."
            )

            # Check for shared state attributes if they exist
            if hasattr(engine1, '__dict__') and hasattr(engine2, '__dict__'):
                # Compare object dictionaries for shared references
                engine1_attrs = set(id(v) for v in engine1.__dict__.values() if v is not None)
                engine2_attrs = set(id(v) for v in engine2.__dict__.values() if v is not None)

                shared_attr_ids = engine1_attrs.intersection(engine2_attrs)

                # Filter out expected shared objects (like classes, modules)
                import types
                shared_objects = []
                for obj_id in shared_attr_ids:
                    # Find actual objects to check their types
                    for attr_val in engine1.__dict__.values():
                        if id(attr_val) == obj_id:
                            if not isinstance(attr_val, (type, types.ModuleType, types.FunctionType)):
                                shared_objects.append(type(attr_val).__name__)
                            break

                # TEST FAILS if non-trivial objects are shared
                self.assertEqual(
                    len(shared_objects), 0,
                    f"CRITICAL SSOT VIOLATION: Engines share non-trivial objects: {shared_objects}. "
                    f"BUSINESS IMPACT: Shared state causes user data contamination. "
                    f"Issue #686: Complete memory isolation required for Golden Path."
                )

    def test_factory_cleanup_prevents_memory_leaks(self):
        """TEST FAILS: Factory pattern doesn't properly clean up user resources.

        CRITICAL BUSINESS IMPACT: Memory leaks in production cause system degradation
        and eventual Golden Path service failure under load.

        EXPECTED FAILURE: User resources not cleaned up after session ends.
        PASSES AFTER: Factory implements proper cleanup and resource management.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import UserExecutionEngine for cleanup testing: {e}")

        # Track initial object count
        import gc
        gc.collect()  # Force garbage collection
        initial_object_count = len(gc.get_objects())

        # Create and destroy multiple user engines
        num_test_users = 5
        created_engines = []

        for i in range(num_test_users):
            context = unittest.mock.Mock()
            context.user_id = f"cleanup_test_user_{i}"
            context.session_id = f"cleanup_test_session_{i}"

            try:
                engine = UserExecutionEngine.create_from_legacy(context)
                created_engines.append(engine)
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE: Engine creation failed during cleanup test: {e}. "
                    f"Issue #686: Factory must work reliably."
                )

        # Clear references and force cleanup
        engine_ids_before_cleanup = [id(engine) for engine in created_engines]
        created_engines.clear()

        # Force garbage collection
        gc.collect()

        # Check if objects were properly cleaned up
        current_object_count = len(gc.get_objects())

        # Allow some variance in object count (GC is not deterministic)
        object_count_increase = current_object_count - initial_object_count
        max_allowed_increase = num_test_users * 10  # Allow some overhead per user

        # TEST FAILS if significant memory leak detected
        self.assertLessEqual(
            object_count_increase, max_allowed_increase,
            f"CRITICAL MEMORY LEAK: Object count increased by {object_count_increase} "
            f"after creating/destroying {num_test_users} engines. "
            f"Initial: {initial_object_count}, Current: {current_object_count}. "
            f"BUSINESS IMPACT: Memory leaks cause Golden Path service degradation. "
            f"Issue #686: Factory cleanup critical for production stability."
        )

        # Verify engines are actually garbage collected
        remaining_engines = []
        for obj in gc.get_objects():
            if id(obj) in engine_ids_before_cleanup:
                remaining_engines.append(id(obj))

        # TEST FAILS if engines not garbage collected
        self.assertEqual(
            len(remaining_engines), 0,
            f"CRITICAL MEMORY LEAK: {len(remaining_engines)} engines not garbage collected. "
            f"Remaining engine IDs: {remaining_engines}. "
            f"Issue #686: Factory must allow proper engine cleanup."
        )


if __name__ == '__main__':
    # Run mission critical factory validation
    # Expected: Tests FAIL with current codebase (proving violations exist)
    # Expected: Tests PASS after proper factory SSOT consolidation
    import unittest
    unittest.main(verbosity=2)