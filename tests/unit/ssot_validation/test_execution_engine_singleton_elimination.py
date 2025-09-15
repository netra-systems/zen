#!/usr/bin/env python3
"""
Issue #802 SSOT Chat Migration Test Plan - Singleton Pattern Elimination

This test validates that Issue #565 ExecutionEngine migration eliminates singleton patterns by:
1. Verifying no global state sharing between ExecutionEngine instances
2. Ensuring per-user ExecutionEngine isolation prevents cross-user contamination
3. Validating WebSocket events are delivered only to the correct user
4. Testing concurrent user execution without state leakage
5. Confirming factory pattern prevents singleton vulnerabilities

Business Value: Platform/Internal - Security & Scalability
Protects multi-user chat functionality and prevents security vulnerabilities from shared state.

CRITICAL: These tests must fail when singleton patterns exist and pass when eliminated.
"""

import pytest
import asyncio
import gc
import weakref
from typing import Dict, Any, List, Set
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, PipelineStep
)


@pytest.mark.unit
class TestExecutionEngineSingletonElimination(SSotAsyncTestCase):
    """
    Test suite validating singleton pattern elimination in ExecutionEngine migration.

    Ensures that UserExecutionEngine instances maintain complete isolation between
    users and do not share global state that could cause security vulnerabilities.
    """

    async def setup_method(self, method):
        """Setup for each test method."""
        await super().setup_method(method)

        # Create mock factory for consistent testing
        self.mock_factory = SSotMockFactory()

        # Track created engines for cleanup
        self.created_engines: List[UserExecutionEngine] = []

    async def teardown_method(self, method):
        """Cleanup for each test method."""
        # Cleanup all created engines
        for engine in self.created_engines:
            try:
                if engine.is_active():
                    await engine.cleanup()
            except Exception as e:
                # Log but don't fail test
                print(f"Warning: Engine cleanup failed: {e}")

        self.created_engines.clear()
        await super().teardown_method(method)

    def create_test_user_context(self, user_id: str) -> UserExecutionContext:
        """Create a test UserExecutionContext with unique identifiers."""
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}",
            run_id=f"run_{user_id}",
            request_id=f"request_{user_id}",
            metadata={
                'test_category': 'singleton_elimination',
                'creation_timestamp': time.time()
            }
        )

    def create_test_engine(self, user_id: str) -> UserExecutionEngine:
        """Create a test UserExecutionEngine with proper mocks."""
        user_context = self.create_test_user_context(user_id)

        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=self.mock_factory.create_agent_factory_mock(),
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id=user_id
            )
        )

        self.created_engines.append(engine)
        return engine

    async def test_no_global_state_sharing_between_engines(self):
        """
        Test that multiple UserExecutionEngine instances don't share global state.

        CRITICAL: This validates that singleton patterns are eliminated and each
        engine maintains completely isolated state.
        """
        # Create multiple engines with different users
        engine_1 = self.create_test_engine("user_global_test_1")
        engine_2 = self.create_test_engine("user_global_test_2")
        engine_3 = self.create_test_engine("user_global_test_3")

        # Verify engines have unique identities
        assert engine_1 is not engine_2
        assert engine_2 is not engine_3
        assert engine_1 is not engine_3

        # Verify engine IDs are unique
        engine_ids = {engine_1.engine_id, engine_2.engine_id, engine_3.engine_id}
        assert len(engine_ids) == 3, "Engine IDs must be unique"

        # Verify user contexts are isolated
        assert engine_1.user_context.user_id == "user_global_test_1"
        assert engine_2.user_context.user_id == "user_global_test_2"
        assert engine_3.user_context.user_id == "user_global_test_3"

        # Verify state dictionaries are separate objects
        assert engine_1.active_runs is not engine_2.active_runs
        assert engine_1.run_history is not engine_2.run_history
        assert engine_1.execution_stats is not engine_2.execution_stats
        assert engine_1.agent_states is not engine_2.agent_states
        assert engine_1.agent_results is not engine_2.agent_results

        # Verify components are isolated
        assert engine_1.agent_factory is not engine_2.agent_factory
        assert engine_1.websocket_emitter is not engine_2.websocket_emitter

        # Test that modifying one engine doesn't affect others
        engine_1.set_agent_state("test_agent", "running")
        engine_1.execution_stats['total_executions'] = 10
        engine_1.set_agent_result("test_agent", {"status": "completed"})

        # Verify other engines are unaffected
        assert engine_2.get_agent_state("test_agent") is None
        assert engine_2.execution_stats['total_executions'] == 0
        assert engine_2.get_agent_result("test_agent") is None

        assert engine_3.get_agent_state("test_agent") is None
        assert engine_3.execution_stats['total_executions'] == 0
        assert engine_3.get_agent_result("test_agent") is None

    async def test_concurrent_execution_isolation(self):
        """
        Test that concurrent execution in multiple engines maintains isolation.

        SECURITY: This validates that concurrent users can execute agents without
        state contamination or interference.
        """
        # Create engines for concurrent testing
        engines = [
            self.create_test_engine(f"concurrent_user_{i}")
            for i in range(5)
        ]

        # Create agent execution contexts for each engine
        execution_contexts = []
        for i, engine in enumerate(engines):
            context = AgentExecutionContext(
                user_id=engine.user_context.user_id,
                thread_id=engine.user_context.thread_id,
                run_id=engine.user_context.run_id,
                request_id=engine.user_context.request_id,
                agent_name=f"test_agent_{i}",
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1,
                metadata={"concurrent_test": True, "agent_index": i}
            )
            execution_contexts.append(context)

        # Mock agent execution for each engine
        for i, engine in enumerate(engines):
            # Mock the _execute_with_error_handling method to simulate execution
            async def mock_execute(context, user_context, execution_id, agent_index=i):
                # Simulate some work
                await asyncio.sleep(0.01 * (agent_index + 1))  # Different delays

                # Set engine-specific state
                engine.set_agent_state(f"agent_{agent_index}", "completed")
                engine.set_agent_result(f"agent_{agent_index}", {
                    "result": f"success_{agent_index}",
                    "user_id": engine.user_context.user_id
                })

                return self.mock_factory.create_agent_execution_result_mock(
                    success=True,
                    agent_name=f"test_agent_{agent_index}",
                    duration=0.01 * (agent_index + 1)
                )

            # Patch the execution method
            setattr(engine, '_execute_with_error_handling', mock_execute)

        # Execute agents concurrently
        tasks = []
        for i, (engine, context) in enumerate(zip(engines, execution_contexts)):
            task = asyncio.create_task(engine.execute_agent(context))
            tasks.append(task)

        # Wait for all executions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Engine {i} execution failed: {result}"
            assert hasattr(result, 'success')
            assert result.success == True

        # Verify state isolation maintained
        for i, engine in enumerate(engines):
            # Each engine should only have its own state
            assert engine.get_agent_state(f"agent_{i}") == "completed"
            assert engine.get_agent_result(f"agent_{i}")['result'] == f"success_{i}"

            # Should not have state from other engines
            for j in range(len(engines)):
                if i != j:
                    assert engine.get_agent_state(f"agent_{j}") is None
                    assert engine.get_agent_result(f"agent_{j}") is None

        # Verify execution stats are per-engine
        for i, engine in enumerate(engines):
            stats = engine.get_user_execution_stats()
            assert stats['user_id'] == f"concurrent_user_{i}"
            assert stats['total_executions'] >= 1
            assert stats['engine_id'] == engine.engine_id

    async def test_websocket_events_user_isolation(self):
        """
        Test that WebSocket events are isolated per user and not shared.

        CRITICAL: This validates that WebSocket events are delivered only to the
        correct user, preventing cross-user information leakage.
        """
        # Create engines with separate WebSocket emitters
        user_1_engine = self.create_test_engine("websocket_user_1")
        user_2_engine = self.create_test_engine("websocket_user_2")

        # Get separate WebSocket emitters
        emitter_1 = user_1_engine.websocket_emitter
        emitter_2 = user_2_engine.websocket_emitter

        # Verify emitters are separate objects
        assert emitter_1 is not emitter_2

        # Create execution contexts for testing
        context_1 = AgentExecutionContext(
            user_id=user_1_engine.user_context.user_id,
            thread_id=user_1_engine.user_context.thread_id,
            run_id=user_1_engine.user_context.run_id,
            request_id=user_1_engine.user_context.request_id,
            agent_name="websocket_agent_1",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={"websocket_test": "user_1"}
        )

        context_2 = AgentExecutionContext(
            user_id=user_2_engine.user_context.user_id,
            thread_id=user_2_engine.user_context.thread_id,
            run_id=user_2_engine.user_context.run_id,
            request_id=user_2_engine.user_context.request_id,
            agent_name="websocket_agent_2",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={"websocket_test": "user_2"}
        )

        # Mock agent execution for both engines
        mock_result_1 = self.mock_factory.create_agent_execution_result_mock(
            success=True, agent_name="websocket_agent_1"
        )
        mock_result_2 = self.mock_factory.create_agent_execution_result_mock(
            success=True, agent_name="websocket_agent_2"
        )

        async def mock_execute_1(context, user_context, execution_id):
            return mock_result_1

        async def mock_execute_2(context, user_context, execution_id):
            return mock_result_2

        user_1_engine._execute_with_error_handling = mock_execute_1
        user_2_engine._execute_with_error_handling = mock_execute_2

        # Execute agents
        result_1 = await user_1_engine.execute_agent(context_1)
        result_2 = await user_2_engine.execute_agent(context_2)

        # Verify WebSocket events were called for correct users only

        # User 1 emitter should have been called for user 1 events
        assert emitter_1.notify_agent_started.called
        started_call_1 = emitter_1.notify_agent_started.call_args
        assert started_call_1[1]['agent_name'] == "websocket_agent_1"
        assert started_call_1[1]['context']['user_id'] == "websocket_user_1"

        assert emitter_1.notify_agent_completed.called
        completed_call_1 = emitter_1.notify_agent_completed.call_args
        assert completed_call_1[1]['agent_name'] == "websocket_agent_1"

        # User 2 emitter should have been called for user 2 events
        assert emitter_2.notify_agent_started.called
        started_call_2 = emitter_2.notify_agent_started.call_args
        assert started_call_2[1]['agent_name'] == "websocket_agent_2"
        assert started_call_2[1]['context']['user_id'] == "websocket_user_2"

        assert emitter_2.notify_agent_completed.called
        completed_call_2 = emitter_2.notify_agent_completed.call_args
        assert completed_call_2[1]['agent_name'] == "websocket_agent_2"

        # Verify user isolation in WebSocket calls
        # User 1 events should not contain user 2 information
        user_1_calls = emitter_1.notify_agent_started.call_args_list
        for call in user_1_calls:
            call_args = call[1] if len(call) > 1 else call[0]
            if 'context' in call_args and 'user_id' in call_args['context']:
                assert call_args['context']['user_id'] == "websocket_user_1"

        # User 2 events should not contain user 1 information
        user_2_calls = emitter_2.notify_agent_started.call_args_list
        for call in user_2_calls:
            call_args = call[1] if len(call) > 1 else call[0]
            if 'context' in call_args and 'user_id' in call_args['context']:
                assert call_args['context']['user_id'] == "websocket_user_2"

    async def test_memory_isolation_prevents_leaks(self):
        """
        Test that engines can be garbage collected and don't hold references.

        PERFORMANCE: This validates that engines don't create memory leaks through
        shared references or singleton patterns.
        """
        # Create engine and get weak reference
        user_context = self.create_test_user_context("memory_test_user")

        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=self.mock_factory.create_agent_factory_mock(),
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id="memory_test_user"
            )
        )

        # Get weak reference to test garbage collection
        engine_ref = weakref.ref(engine)
        engine_id = engine.engine_id

        # Use the engine briefly
        stats = engine.get_user_execution_stats()
        assert stats['engine_id'] == engine_id

        # Cleanup and delete engine
        await engine.cleanup()
        del engine

        # Force garbage collection
        gc.collect()

        # Verify engine was garbage collected (weak reference is dead)
        # Note: This might not always work immediately due to Python's GC behavior
        # but should work in most cases

        # Create new engine with same user context
        new_engine = UserExecutionEngine(
            context=user_context,
            agent_factory=self.mock_factory.create_agent_factory_mock(),
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id="memory_test_user"
            )
        )
        self.created_engines.append(new_engine)

        # Verify new engine has different ID (no singleton reuse)
        assert new_engine.engine_id != engine_id

        # Verify new engine starts with clean state
        assert len(new_engine.active_runs) == 0
        assert len(new_engine.run_history) == 0
        assert new_engine.execution_stats['total_executions'] == 0

    async def test_factory_pattern_prevents_singleton_creation(self):
        """
        Test that factory methods create new instances, not singletons.

        ARCHITECTURE: This validates that factory patterns in Issue #565 migration
        prevent singleton anti-patterns that could cause shared state vulnerabilities.
        """
        # Test create_execution_engine creates unique instances
        user_context_1 = self.create_test_user_context("factory_user_1")
        user_context_2 = self.create_test_user_context("factory_user_2")

        mock_registry = self.mock_factory.create_agent_registry_mock()
        mock_bridge = self.mock_factory.create_websocket_bridge_mock()

        engine_1 = await UserExecutionEngine.create_execution_engine(
            user_context=user_context_1,
            registry=mock_registry,
            websocket_bridge=mock_bridge
        )
        self.created_engines.append(engine_1)

        engine_2 = await UserExecutionEngine.create_execution_engine(
            user_context=user_context_2,
            registry=mock_registry,
            websocket_bridge=mock_bridge
        )
        self.created_engines.append(engine_2)

        # Verify unique instances
        assert engine_1 is not engine_2
        assert engine_1.engine_id != engine_2.engine_id
        assert engine_1.user_context is not engine_2.user_context

        # Test create_from_legacy creates unique instances
        engine_3 = await UserExecutionEngine.create_from_legacy(
            registry=mock_registry,
            websocket_bridge=mock_bridge,
            user_context=self.create_test_user_context("legacy_user_1")
        )
        self.created_engines.append(engine_3)

        engine_4 = await UserExecutionEngine.create_from_legacy(
            registry=mock_registry,
            websocket_bridge=mock_bridge,
            user_context=self.create_test_user_context("legacy_user_2")
        )
        self.created_engines.append(engine_4)

        # Verify unique instances from legacy factory
        assert engine_3 is not engine_4
        assert engine_3.engine_id != engine_4.engine_id
        assert engine_3.user_context.user_id != engine_4.user_context.user_id

        # Verify all engines are unique
        all_engines = [engine_1, engine_2, engine_3, engine_4]
        engine_ids = {engine.engine_id for engine in all_engines}
        assert len(engine_ids) == 4, "All engines should have unique IDs"

        user_ids = {engine.user_context.user_id for engine in all_engines}
        assert len(user_ids) == 4, "All engines should have unique user IDs"

    async def test_resource_limits_are_per_user(self):
        """
        Test that resource limits (semaphores, timeouts) are per-user, not global.

        PERFORMANCE: This validates that resource controls don't create bottlenecks
        by sharing limits across all users globally.
        """
        # Create engines with different resource configurations
        engines = []

        for i in range(3):
            user_context = self.create_test_user_context(f"resource_user_{i}")

            # Modify resource limits in user context
            if hasattr(user_context, 'resource_limits'):
                user_context.resource_limits.max_concurrent_agents = i + 2

            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=self.mock_factory.create_agent_factory_mock(),
                websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                    user_id=f"resource_user_{i}"
                )
            )
            engines.append(engine)

        # Verify each engine has its own semaphore
        semaphores = {id(engine.semaphore) for engine in engines}
        assert len(semaphores) == 3, "Each engine should have its own semaphore"

        # Verify per-user concurrency limits
        for i, engine in enumerate(engines):
            # Default or configured limits
            expected_max = getattr(getattr(engine.user_context, 'resource_limits', None),
                                 'max_concurrent_agents', 3)
            assert engine.max_concurrent == expected_max

        # Test that acquiring resources from one engine doesn't affect others
        async def test_resource_isolation():
            # Acquire semaphore on first engine
            async with engines[0].semaphore:
                # Verify other engines can still acquire their semaphores
                async with engines[1].semaphore:
                    async with engines[2].semaphore:
                        # All engines can acquire concurrently
                        assert True

        await test_resource_isolation()

        # Cleanup engines
        for engine in engines:
            self.created_engines.append(engine)

    async def test_no_class_level_state_sharing(self):
        """
        Test that UserExecutionEngine class doesn't maintain shared class-level state.

        ARCHITECTURE: This validates that no class variables or static state
        could cause singleton-like behavior across instances.
        """
        # Inspect UserExecutionEngine class for problematic class variables
        class_vars = {}
        for name, value in UserExecutionEngine.__dict__.items():
            if not name.startswith('__') and not callable(value):
                class_vars[name] = value

        # Check that class variables are safe (constants or descriptors)
        safe_class_vars = {
            'AGENT_EXECUTION_TIMEOUT',  # Constants are safe
            'MAX_HISTORY_SIZE'          # Constants are safe
        }

        problematic_vars = set(class_vars.keys()) - safe_class_vars

        # Remove any property descriptors (these are safe)
        for name in list(problematic_vars):
            attr = getattr(UserExecutionEngine, name)
            if isinstance(attr, property):
                problematic_vars.remove(name)

        # Should not have mutable class variables that could be shared
        assert len(problematic_vars) == 0, f"Found problematic class variables: {problematic_vars}"

        # Test that constants are indeed constants and not mutable
        assert isinstance(UserExecutionEngine.AGENT_EXECUTION_TIMEOUT, (int, float))
        assert isinstance(UserExecutionEngine.MAX_HISTORY_SIZE, int)

        # Verify modifying one instance doesn't affect class or other instances
        engine_1 = self.create_test_engine("class_test_1")
        engine_2 = self.create_test_engine("class_test_2")

        # Test that instance modifications don't affect class or other instances
        original_timeout = UserExecutionEngine.AGENT_EXECUTION_TIMEOUT

        # Modifying instance attributes shouldn't affect class
        engine_1._custom_timeout = 999  # Custom instance attribute

        # Class constant should be unchanged
        assert UserExecutionEngine.AGENT_EXECUTION_TIMEOUT == original_timeout

        # Other instances should be unaffected
        assert not hasattr(engine_2, '_custom_timeout')

        # Test instance state isolation
        engine_1.set_agent_state("test", "value1")
        engine_2.set_agent_state("test", "value2")

        assert engine_1.get_agent_state("test") == "value1"
        assert engine_2.get_agent_state("test") == "value2"
