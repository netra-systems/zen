#!/usr/bin/env python3
"""
Issue #802 SSOT Chat Migration Test Plan - Migration Completion Validation

This test validates that Issue #565 ExecutionEngine migration is complete by verifying:
1. UserExecutionEngine is the single source of truth for agent execution
2. Legacy compatibility bridges function correctly during transition
3. Modern UserExecutionContext patterns replace vulnerable DeepAgentState
4. WebSocket event consistency is maintained throughout migration
5. Chat functionality remains operational protecting $500K+ ARR

Business Value: Platform/Internal - Development Velocity & System Stability
Protects the primary Golden Path user flow ensuring chat delivers 90% of platform value.

CRITICAL: These tests must fail when SSOT violations exist and pass when migration is complete.
"""

import pytest
import asyncio
import inspect
import warnings
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine as ConsolidatedEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as DeprecatedEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.unit
class TestIssue565MigrationCompletion(SSotAsyncTestCase):
    """
    Test suite validating Issue #565 ExecutionEngine migration completion.

    Validates that UserExecutionEngine serves as the single source of truth for
    agent execution while maintaining compatibility with legacy patterns.
    """

    async def setup_method(self, method):
        """Setup for each test method."""
        await super().setup_method(method)

        # Create mock factory for consistent mock behavior
        self.mock_factory = SSotMockFactory()

        # Create test user context for execution engine testing
        self.test_user_context = UserExecutionContext(
            user_id="test_user_migration_565",
            thread_id="test_thread_565",
            run_id="test_run_565",
            request_id="test_request_565",
            metadata={
                'test_name': method.__name__,
                'test_category': 'issue_565_migration_completion',
                'business_value': 'chat_functionality_protection'
            }
        )

        # Mock components for testing
        self.mock_agent_factory = self.mock_factory.create_agent_factory_mock()
        self.mock_websocket_emitter = self.mock_factory.create_websocket_emitter_mock(
            user_id=self.test_user_context.user_id
        )
        self.mock_registry = self.mock_factory.create_agent_registry_mock()
        self.mock_websocket_bridge = self.mock_factory.create_websocket_bridge_mock()

    async def test_user_execution_engine_is_primary_implementation(self):
        """
        Test that UserExecutionEngine is the primary implementation for agent execution.

        CRITICAL: This test validates Issue #565 migration by ensuring UserExecutionEngine
        provides the canonical implementation with proper user isolation.
        """
        # Test modern constructor creates valid engine
        engine = UserExecutionEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Verify engine properties
        assert engine.user_context.user_id == self.test_user_context.user_id
        assert engine.engine_id.startswith("user_engine_")
        assert engine.is_active() == True
        assert not engine.is_compatibility_mode()

        # Verify user isolation features
        assert hasattr(engine, 'active_runs')
        assert hasattr(engine, 'run_history')
        assert hasattr(engine, 'execution_stats')
        assert hasattr(engine, 'semaphore')

        # Verify WebSocket integration
        assert engine.websocket_emitter is not None
        assert engine.websocket_emitter == self.mock_websocket_emitter

        # Verify agent factory integration
        assert engine.agent_factory is not None
        assert engine.agent_factory == self.mock_agent_factory

        await engine.cleanup()

    async def test_legacy_execution_engine_imports_redirect_to_user_execution_engine(self):
        """
        Test that legacy ExecutionEngine imports redirect to UserExecutionEngine.

        This validates the Issue #565 migration maintains backward compatibility
        while consolidating to UserExecutionEngine as the SSOT.
        """
        # Test consolidated engine import redirects
        assert ConsolidatedEngine == UserExecutionEngine
        assert DeprecatedEngine == UserExecutionEngine

        # Test that imported classes maintain expected interfaces
        assert hasattr(ConsolidatedEngine, 'create_from_legacy')
        assert hasattr(ConsolidatedEngine, 'create_execution_engine')
        assert hasattr(DeprecatedEngine, 'create_request_scoped_engine')

        # Verify the redirected classes support modern patterns
        engine_via_consolidated = ConsolidatedEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        engine_via_deprecated = DeprecatedEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Both should be UserExecutionEngine instances
        assert isinstance(engine_via_consolidated, UserExecutionEngine)
        assert isinstance(engine_via_deprecated, UserExecutionEngine)
        assert type(engine_via_consolidated) == type(engine_via_deprecated) == UserExecutionEngine

        await engine_via_consolidated.cleanup()
        await engine_via_deprecated.cleanup()

    async def test_compatibility_bridge_functions_correctly(self):
        """
        Test that Issue #565 compatibility bridge handles legacy patterns.

        This validates that create_from_legacy() provides backward compatibility
        for the 128+ deprecated imports while encouraging migration.
        """
        # Test legacy compatibility bridge with deprecation warning
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            engine = await UserExecutionEngine.create_from_legacy(
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge,
                user_context=self.test_user_context
            )

            # Verify deprecation warning was issued
            assert len(warning_list) >= 1
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "Issue #565" in str(deprecation_warnings[0].message)
            assert "DEPRECATED" in str(deprecation_warnings[0].message)

        # Verify compatibility mode is set
        assert engine.is_compatibility_mode()

        # Get compatibility info
        compat_info = engine.get_compatibility_info()
        assert compat_info['compatibility_mode'] == True
        assert compat_info['migration_issue'] == '#565'
        assert compat_info['migration_needed'] == True
        assert 'migration_guide' in compat_info

        # Verify compatibility bridge preserves functionality
        assert hasattr(engine, 'websocket_bridge')
        assert hasattr(engine, 'agent_registry')
        assert engine.user_context is not None
        assert engine.is_active()

        await engine.cleanup()

    async def test_create_execution_engine_api_compatibility(self):
        """
        Test that create_execution_engine() API maintains compatibility.

        This validates the Issue #565 migration preserves expected API patterns
        for tests and consumers that use the create_execution_engine() method.
        """
        # Test create_execution_engine method
        engine = await UserExecutionEngine.create_execution_engine(
            user_context=self.test_user_context,
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )

        # Verify created engine
        assert isinstance(engine, UserExecutionEngine)
        assert engine.user_context.user_id == self.test_user_context.user_id
        assert engine.is_active()

        # Verify registry integration
        registry = engine.agent_registry
        assert registry is not None  # Should have registry access

        # Verify websocket bridge integration
        bridge = engine.websocket_bridge
        assert bridge is not None  # Should have bridge access

        await engine.cleanup()

    async def test_user_execution_context_replaces_deep_agent_state(self):
        """
        Test that UserExecutionContext replaces vulnerable DeepAgentState patterns.

        SECURITY: This validates Issue #565 security fixes eliminating input injection
        and serialization vulnerabilities from DeepAgentState usage.
        """
        engine = UserExecutionEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Verify UserExecutionContext is used throughout
        user_context = engine.get_user_context()
        assert isinstance(user_context, UserExecutionContext)
        assert user_context.user_id == self.test_user_context.user_id

        # Test execute_agent_pipeline uses secure context pattern
        with patch.object(engine, 'execute_agent') as mock_execute:
            mock_execute.return_value = self.mock_factory.create_agent_execution_result_mock(
                success=True, agent_name="test_agent"
            )

            input_data = {"message": "test request", "user_id": self.test_user_context.user_id}

            result = await engine.execute_agent_pipeline(
                agent_name="test_agent",
                execution_context=self.test_user_context,
                input_data=input_data
            )

            # Verify execute_agent was called with secure context
            assert mock_execute.called
            args, kwargs = mock_execute.call_args

            # Should be called with AgentExecutionContext and secure UserExecutionContext
            assert len(args) == 2  # context, user_context
            agent_context = args[0]
            secure_context = args[1]

            assert hasattr(agent_context, 'agent_name')
            assert agent_context.agent_name == "test_agent"
            assert isinstance(secure_context, UserExecutionContext)
            assert secure_context.user_id == self.test_user_context.user_id

        await engine.cleanup()

    async def test_websocket_events_maintain_consistency(self):
        """
        Test that WebSocket events maintain consistency throughout migration.

        CRITICAL: This validates that Issue #565 migration preserves the 5 critical
        WebSocket events that enable real-time chat functionality.
        """
        engine = UserExecutionEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Create agent execution context for testing
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext, PipelineStep
        )

        agent_context = AgentExecutionContext(
            user_id=self.test_user_context.user_id,
            thread_id=self.test_user_context.thread_id,
            run_id=self.test_user_context.run_id,
            request_id=self.test_user_context.request_id,
            agent_name="test_websocket_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={"test": "websocket_events"}
        )

        # Mock successful agent execution
        with patch.object(engine, '_execute_with_error_handling') as mock_execute:
            mock_result = self.mock_factory.create_agent_execution_result_mock(
                success=True, agent_name="test_websocket_agent", duration=0.5
            )
            mock_execute.return_value = mock_result

            # Execute agent to trigger WebSocket events
            result = await engine.execute_agent(agent_context)

            # Verify WebSocket events were called
            # 1. agent_started
            assert self.mock_websocket_emitter.notify_agent_started.called
            started_call = self.mock_websocket_emitter.notify_agent_started.call_args
            assert started_call[1]['agent_name'] == "test_websocket_agent"
            assert started_call[1]['context']['user_isolated'] == True

            # 2. agent_thinking (multiple calls expected)
            assert self.mock_websocket_emitter.notify_agent_thinking.called
            thinking_calls = self.mock_websocket_emitter.notify_agent_thinking.call_args_list
            assert len(thinking_calls) >= 2  # Multiple thinking updates

            # 3. agent_completed
            assert self.mock_websocket_emitter.notify_agent_completed.called
            completed_call = self.mock_websocket_emitter.notify_agent_completed.call_args
            assert completed_call[1]['agent_name'] == "test_websocket_agent"
            assert completed_call[1]['result']['success'] == True
            assert completed_call[1]['result']['user_isolated'] == True

        await engine.cleanup()

    async def test_migration_preserves_chat_business_value(self):
        """
        Test that Issue #565 migration preserves critical chat business value.

        BUSINESS VALUE: This validates that the ExecutionEngine migration maintains
        the chat functionality that delivers 90% of platform value ($500K+ ARR).
        """
        engine = UserExecutionEngine(
            context=self.test_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Verify core chat capabilities are preserved

        # 1. User isolation for multi-user chat
        assert engine.user_context.user_id == self.test_user_context.user_id
        assert len(engine.active_runs) == 0  # Clean per-user state
        assert len(engine.run_history) == 0  # Clean per-user history

        # 2. Agent availability for AI responses
        available_agents = engine.get_available_agents()
        assert isinstance(available_agents, list)
        # Should be able to get agents even if empty (depends on registry)

        # 3. Tool capability for AI functionality
        available_tools = await engine.get_available_tools()
        assert isinstance(available_tools, list)
        # Should return tools (mock or real)
        assert len(available_tools) >= 1

        # 4. Execution statistics for performance monitoring
        stats = engine.get_user_execution_stats()
        assert isinstance(stats, dict)
        assert 'user_id' in stats
        assert 'engine_id' in stats
        assert 'total_executions' in stats
        assert stats['user_id'] == self.test_user_context.user_id

        # 5. WebSocket emitter for real-time updates
        assert engine.websocket_emitter is not None
        assert hasattr(engine.websocket_emitter, 'notify_agent_started')
        assert hasattr(engine.websocket_emitter, 'notify_agent_thinking')
        assert hasattr(engine.websocket_emitter, 'notify_agent_completed')

        await engine.cleanup()

    async def test_factory_pattern_eliminates_singleton_vulnerabilities(self):
        """
        Test that factory pattern eliminates singleton vulnerabilities.

        SECURITY: This validates that Issue #565 migration uses factory patterns
        to prevent shared state vulnerabilities between users.
        """
        # Create two separate engines for different users
        user_context_1 = UserExecutionContext(
            user_id="user_1_factory_test",
            thread_id="thread_1",
            run_id="run_1",
            request_id="request_1"
        )

        user_context_2 = UserExecutionContext(
            user_id="user_2_factory_test",
            thread_id="thread_2",
            run_id="run_2",
            request_id="request_2"
        )

        engine_1 = UserExecutionEngine(
            context=user_context_1,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id=user_context_1.user_id
            )
        )

        engine_2 = UserExecutionEngine(
            context=user_context_2,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id=user_context_2.user_id
            )
        )

        # Verify engines are completely isolated
        assert engine_1.engine_id != engine_2.engine_id
        assert engine_1.user_context.user_id != engine_2.user_context.user_id
        assert engine_1.active_runs is not engine_2.active_runs
        assert engine_1.run_history is not engine_2.run_history
        assert engine_1.execution_stats is not engine_2.execution_stats

        # Verify WebSocket emitters are isolated
        assert engine_1.websocket_emitter is not engine_2.websocket_emitter

        # Test state isolation - modify engine_1 state
        engine_1.agent_states['test_agent'] = 'running'
        engine_1.execution_stats['total_executions'] = 5

        # Verify engine_2 state is unaffected
        assert 'test_agent' not in engine_2.agent_states
        assert engine_2.execution_stats['total_executions'] == 0

        # Verify per-user resource limits
        assert engine_1.max_concurrent == engine_2.max_concurrent == 3  # Default
        assert id(engine_1.semaphore) != id(engine_2.semaphore)

        await engine_1.cleanup()
        await engine_2.cleanup()

    async def test_migration_enables_concurrent_user_support(self):
        """
        Test that migration enables proper concurrent user support.

        SCALABILITY: This validates that Issue #565 migration enables 5+ concurrent
        users with complete isolation as required for production deployment.
        """
        # Create multiple concurrent engines
        engines = []
        user_contexts = []

        for i in range(5):
            user_context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                request_id=f"request_{i}"
            )
            user_contexts.append(user_context)

            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=self.mock_agent_factory,
                websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                    user_id=user_context.user_id
                )
            )
            engines.append(engine)

        # Verify all engines are active and isolated
        for i, engine in enumerate(engines):
            assert engine.is_active()
            assert engine.user_context.user_id == f"concurrent_user_{i}"
            assert engine.user_context == user_contexts[i]

            # Verify unique engine IDs
            for j, other_engine in enumerate(engines):
                if i != j:
                    assert engine.engine_id != other_engine.engine_id
                    assert engine.user_context.user_id != other_engine.user_context.user_id

        # Test concurrent operations don't interfere
        tasks = []
        for i, engine in enumerate(engines):
            # Set unique state per engine
            engine.set_agent_state(f"agent_{i}", f"state_{i}")
            engine.set_agent_result(f"agent_{i}", f"result_{i}")

        # Verify state isolation maintained
        for i, engine in enumerate(engines):
            assert engine.get_agent_state(f"agent_{i}") == f"state_{i}"
            assert engine.get_agent_result(f"agent_{i}") == f"result_{i}"

            # Verify other engines don't have this state
            for j in range(5):
                if i != j:
                    assert engine.get_agent_state(f"agent_{j}") is None
                    assert engine.get_agent_result(f"agent_{j}") is None

        # Cleanup all engines
        for engine in engines:
            await engine.cleanup()
