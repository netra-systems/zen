#!/usr/bin/env python3
"""
Issue #802 SSOT Chat Migration Test Plan - ExecutionEngine Factory Compliance

This test validates that ExecutionEngine factory patterns comply with SSOT principles:
1. Factory methods create properly isolated UserExecutionEngine instances
2. No shared state or singleton patterns in factory creation
3. Factory-created engines maintain full user isolation
4. Compatibility factories function correctly during migration
5. Resource management and cleanup work properly with factory patterns

Business Value: Platform/Internal - Architecture Compliance & Security
Ensures factory patterns support secure multi-user execution protecting chat functionality
and the Golden Path user flow delivering $500K+ ARR value.

CRITICAL: These tests validate that factory patterns eliminate architectural
anti-patterns that could compromise user isolation or system stability.
"""

import asyncio
import inspect
import warnings
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine,
    create_request_scoped_engine,
    create_execution_context_manager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestExecutionFactoryCompliance(SSotAsyncTestCase):
    """
    Test suite validating ExecutionEngine factory pattern compliance with SSOT.

    Ensures that all factory methods create properly isolated UserExecutionEngine
    instances without shared state or singleton anti-patterns.
    """

    async def setup_method(self, method):
        """Setup for each test method."""
        await super().setup_method(method)

        # Create mock factory for consistent testing
        self.mock_factory = SSotMockFactory()

        # Track created engines and contexts for cleanup
        self.created_engines: List[UserExecutionEngine] = []
        self.async_contexts: List = []

        # Create test components for factory testing
        self.mock_registry = self.mock_factory.create_agent_registry_mock()
        self.mock_websocket_bridge = self.mock_factory.create_websocket_bridge_mock()

    async def teardown_method(self, method):
        """Cleanup for each test method."""
        # Cleanup all created engines
        for engine in self.created_engines:
            try:
                if hasattr(engine, 'is_active') and engine.is_active():
                    await engine.cleanup()
            except Exception as e:
                print(f"Warning: Engine cleanup failed: {e}")

        # Cleanup any async contexts
        for context in self.async_contexts:
            try:
                if hasattr(context, '__aexit__'):
                    await context.__aexit__(None, None, None)
            except Exception as e:
                print(f"Warning: Context cleanup failed: {e}")

        self.created_engines.clear()
        self.async_contexts.clear()
        await super().teardown_method(method)

    def create_test_user_context(self, user_id: str) -> UserExecutionContext:
        """Create a test UserExecutionContext with unique identifiers."""
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}",
            run_id=f"run_{user_id}",
            request_id=f"request_{user_id}",
            metadata={
                'test_category': 'factory_compliance',
                'created_by': 'test_execution_factory_compliance'
            }
        )

    async def test_create_request_scoped_engine_factory_compliance(self):
        """
        Test create_request_scoped_engine factory creates compliant engines.

        FACTORY COMPLIANCE: Validates that the SSOT factory function creates
        properly isolated UserExecutionEngine instances.
        """
        # Test factory function creates unique engines
        user_context_1 = self.create_test_user_context("factory_user_1")
        user_context_2 = self.create_test_user_context("factory_user_2")

        engine_1 = await create_request_scoped_engine(user_context_1)
        engine_2 = await create_request_scoped_engine(user_context_2)

        self.created_engines.extend([engine_1, engine_2])

        # Verify engines are unique instances
        assert engine_1 is not engine_2
        assert engine_1.engine_id != engine_2.engine_id
        assert engine_1.user_context.user_id != engine_2.user_context.user_id

        # Verify both are UserExecutionEngine instances
        assert isinstance(engine_1, UserExecutionEngine)
        assert isinstance(engine_2, UserExecutionEngine)

        # Verify proper user context association
        assert engine_1.user_context == user_context_1
        assert engine_2.user_context == user_context_2

        # Verify isolation between engines
        assert engine_1.active_runs is not engine_2.active_runs
        assert engine_1.run_history is not engine_2.run_history
        assert engine_1.execution_stats is not engine_2.execution_stats

        # Verify engines are active and functional
        assert engine_1.is_active()
        assert engine_2.is_active()

        # Test factory creates engines with proper component integration
        assert engine_1.websocket_emitter is not None
        assert engine_2.websocket_emitter is not None
        assert engine_1.agent_factory is not None
        assert engine_2.agent_factory is not None

    async def test_create_execution_engine_factory_method_compliance(self):
        """
        Test UserExecutionEngine.create_execution_engine factory method compliance.

        FACTORY API: Validates that the create_execution_engine class method
        maintains proper factory pattern compliance.
        """
        # Test factory method with different user contexts
        user_contexts = [
            self.create_test_user_context("create_engine_user_1"),
            self.create_test_user_context("create_engine_user_2"),
            self.create_test_user_context("create_engine_user_3")
        ]

        engines = []
        for user_context in user_contexts:
            engine = await UserExecutionEngine.create_execution_engine(
                user_context=user_context,
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            engines.append(engine)

        self.created_engines.extend(engines)

        # Verify all engines are unique
        engine_ids = {engine.engine_id for engine in engines}
        assert len(engine_ids) == len(engines), "Factory should create unique engines"

        user_ids = {engine.user_context.user_id for engine in engines}
        assert len(user_ids) == len(engines), "Each engine should have unique user"

        # Verify factory method signature compliance
        create_method = UserExecutionEngine.create_execution_engine
        signature = inspect.signature(create_method)

        # Should be async method
        assert asyncio.iscoroutinefunction(create_method)

        # Should have expected parameters
        expected_params = {'user_context', 'registry', 'websocket_bridge'}
        actual_params = set(signature.parameters.keys())
        assert expected_params.issubset(actual_params)

        # Verify created engines maintain proper component access
        for engine in engines:
            # Should have registry access
            registry = engine.agent_registry
            # May be None in test scenario, but should not raise exception

            # Should have websocket bridge access
            bridge = engine.websocket_bridge
            # May be None in test scenario, but should not raise exception

            # Should maintain proper user context
            assert engine.user_context in user_contexts

    async def test_create_from_legacy_factory_compliance(self):
        """
        Test UserExecutionEngine.create_from_legacy factory compliance.

        LEGACY COMPATIBILITY: Validates that the legacy compatibility factory
        maintains proper isolation while providing backward compatibility.
        """
        # Test legacy factory creates unique engines
        user_contexts = [
            self.create_test_user_context("legacy_user_1"),
            self.create_test_user_context("legacy_user_2")
        ]

        engines = []

        # Test legacy factory with different user contexts
        for user_context in user_contexts:
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")

                engine = await UserExecutionEngine.create_from_legacy(
                    registry=self.mock_registry,
                    websocket_bridge=self.mock_websocket_bridge,
                    user_context=user_context
                )
                engines.append(engine)

                # Verify deprecation warning is issued
                deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
                assert len(deprecation_warnings) >= 1

        self.created_engines.extend(engines)

        # Verify engines are properly isolated
        assert engines[0] is not engines[1]
        assert engines[0].engine_id != engines[1].engine_id
        assert engines[0].user_context.user_id != engines[1].user_context.user_id

        # Verify compatibility mode is properly set
        for engine in engines:
            assert engine.is_compatibility_mode() == True

            # Get compatibility info
            compat_info = engine.get_compatibility_info()
            assert compat_info['compatibility_mode'] == True
            assert compat_info['migration_issue'] == '#565'

        # Test legacy factory without user context (anonymous user creation)
        anonymous_engine = await UserExecutionEngine.create_from_legacy(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=None  # Should create anonymous user context
        )
        self.created_engines.append(anonymous_engine)

        # Verify anonymous engine is properly created
        assert isinstance(anonymous_engine, UserExecutionEngine)
        assert anonymous_engine.is_compatibility_mode() == True
        assert anonymous_engine.user_context.user_id.startswith('legacy_compat_')

        # Verify anonymous engine is isolated from others
        assert anonymous_engine not in engines
        assert anonymous_engine.engine_id not in {e.engine_id for e in engines}

    async def test_create_execution_context_manager_compliance(self):
        """
        Test create_execution_context_manager factory compliance.

        CONTEXT MANAGER: Validates that the context manager factory creates
        proper UserExecutionEngine instances with automatic cleanup.
        """
        # Test context manager factory creates proper engines
        engines_created = []

        async def capture_engine_in_context():
            async with create_execution_context_manager(
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge,
                max_concurrent_per_request=2,
                execution_timeout=25.0
            ) as engine:
                engines_created.append(engine)

                # Verify engine is properly created
                assert isinstance(engine, UserExecutionEngine)
                assert engine.is_active()
                assert engine.is_compatibility_mode() == True

                # Verify engine has proper configuration
                assert engine.max_concurrent == 3  # Default or from context
                assert engine.user_context is not None

                # Test engine functionality within context
                stats = engine.get_user_execution_stats()
                assert isinstance(stats, dict)
                assert 'engine_id' in stats
                assert 'user_id' in stats

                return engine

        # Execute context manager
        engine_in_context = await capture_engine_in_context()

        # Verify engine was captured
        assert len(engines_created) == 1
        captured_engine = engines_created[0]

        # Verify engine is the same instance returned
        assert captured_engine is engine_in_context

        # Test multiple context managers create different engines
        async def create_another_context():
            async with create_execution_context_manager(
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge
            ) as engine:
                return engine

        another_engine = await create_another_context()

        # Engines should be different instances
        assert captured_engine is not another_engine
        assert captured_engine.engine_id != another_engine.engine_id
        assert captured_engine.user_context.user_id != another_engine.user_context.user_id

    async def test_factory_created_engines_maintain_isolation(self):
        """
        Test that factory-created engines maintain proper user isolation.

        USER ISOLATION: Validates that engines created through different
        factory methods maintain complete user isolation.
        """
        # Create engines through different factory methods
        user_context_1 = self.create_test_user_context("isolation_user_1")
        user_context_2 = self.create_test_user_context("isolation_user_2")
        user_context_3 = self.create_test_user_context("isolation_user_3")

        # Factory method 1: create_request_scoped_engine
        engine_1 = await create_request_scoped_engine(user_context_1)

        # Factory method 2: create_execution_engine
        engine_2 = await UserExecutionEngine.create_execution_engine(
            user_context=user_context_2,
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )

        # Factory method 3: create_from_legacy
        engine_3 = await UserExecutionEngine.create_from_legacy(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=user_context_3
        )

        self.created_engines.extend([engine_1, engine_2, engine_3])

        # Test isolation between engines
        engines = [engine_1, engine_2, engine_3]
        user_contexts = [user_context_1, user_context_2, user_context_3]

        # Verify each engine has correct user context
        for engine, expected_context in zip(engines, user_contexts):
            assert engine.user_context.user_id == expected_context.user_id
            assert engine.user_context.run_id == expected_context.run_id

        # Test state isolation
        for i, engine in enumerate(engines):
            # Set unique state per engine
            engine.set_agent_state(f"test_agent_{i}", f"state_{i}")
            engine.set_agent_result(f"test_result_{i}", f"result_{i}")
            engine.execution_stats['total_executions'] = i + 10

        # Verify state isolation maintained
        for i, engine in enumerate(engines):
            # Engine should have its own state
            assert engine.get_agent_state(f"test_agent_{i}") == f"state_{i}"
            assert engine.get_agent_result(f"test_result_{i}") == f"result_{i}"
            assert engine.execution_stats['total_executions'] == i + 10

            # Engine should not have state from other engines
            for j in range(len(engines)):
                if i != j:
                    assert engine.get_agent_state(f"test_agent_{j}") is None
                    assert engine.get_agent_result(f"test_result_{j}") is None

    async def test_factory_resource_management_compliance(self):
        """
        Test that factory-created engines properly manage resources.

        RESOURCE MANAGEMENT: Validates that factories create engines with
        proper resource limits and cleanup capabilities.
        """
        # Test resource management with different factory methods
        user_context = self.create_test_user_context("resource_test_user")

        # Create engine through factory
        engine = await UserExecutionEngine.create_execution_engine(
            user_context=user_context,
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        self.created_engines.append(engine)

        # Verify resource management components
        assert hasattr(engine, 'semaphore')
        assert hasattr(engine, 'max_concurrent')
        assert hasattr(engine, 'active_runs')

        # Test semaphore is properly configured
        assert isinstance(engine.semaphore, asyncio.Semaphore)
        assert engine.semaphore._value == engine.max_concurrent

        # Test resource limits are enforced
        assert engine.max_concurrent >= 1  # Should have reasonable limit

        # Test cleanup functionality
        assert callable(getattr(engine, 'cleanup', None))
        assert engine.is_active() == True

        # Test cleanup actually works
        await engine.cleanup()
        assert engine.is_active() == False

    async def test_factory_method_error_handling_compliance(self):
        """
        Test that factory methods handle errors properly and maintain compliance.

        ERROR HANDLING: Validates that factory methods fail gracefully and
        provide meaningful error messages.
        """
        # Test factory method with invalid parameters
        invalid_cases = [
            # Case 1: None user context
            {
                'factory': UserExecutionEngine.create_execution_engine,
                'kwargs': {
                    'user_context': None,
                    'registry': self.mock_registry,
                    'websocket_bridge': self.mock_websocket_bridge
                },
                'expected_error': (ValueError, TypeError)
            },
            # Case 2: Invalid user context type
            {
                'factory': create_request_scoped_engine,
                'kwargs': {
                    'context': "invalid_context_string"
                },
                'expected_error': (ValueError, TypeError, AttributeError)
            }
        ]

        for case in invalid_cases:
            factory_func = case['factory']
            kwargs = case['kwargs']
            expected_errors = case['expected_error']

            # Test that factory raises appropriate error
            with self.assertRaises(expected_errors):
                if asyncio.iscoroutinefunction(factory_func):
                    await factory_func(**kwargs)
                else:
                    factory_func(**kwargs)

        # Test that valid factory calls don't raise errors
        valid_user_context = self.create_test_user_context("valid_error_test_user")

        try:
            valid_engine = await UserExecutionEngine.create_execution_engine(
                user_context=valid_user_context,
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            self.created_engines.append(valid_engine)
            assert isinstance(valid_engine, UserExecutionEngine)
        except Exception as e:
            self.fail(f"Valid factory call should not raise error: {e}")

    async def test_factory_pattern_prevents_global_state_sharing(self):
        """
        Test that factory patterns prevent global state sharing between instances.

        GLOBAL STATE: Validates that no factory method creates engines that
        share global state variables or singleton instances.
        """
        # Create multiple engines through different factory methods
        factories_and_configs = [
            {
                'name': 'create_request_scoped_engine',
                'factory': create_request_scoped_engine,
                'config': {'context': self.create_test_user_context("global_test_1")}
            },
            {
                'name': 'create_execution_engine',
                'factory': UserExecutionEngine.create_execution_engine,
                'config': {
                    'user_context': self.create_test_user_context("global_test_2"),
                    'registry': self.mock_registry,
                    'websocket_bridge': self.mock_websocket_bridge
                }
            },
            {
                'name': 'create_from_legacy',
                'factory': UserExecutionEngine.create_from_legacy,
                'config': {
                    'registry': self.mock_registry,
                    'websocket_bridge': self.mock_websocket_bridge,
                    'user_context': self.create_test_user_context("global_test_3")
                }
            }
        ]

        # Create engines from each factory
        factory_engines = []
        for factory_config in factories_and_configs:
            factory_func = factory_config['factory']
            config = factory_config['config']

            engine = await factory_func(**config)
            factory_engines.append({
                'engine': engine,
                'factory_name': factory_config['name']
            })

        # Add engines to cleanup list
        self.created_engines.extend([fe['engine'] for fe in factory_engines])

        # Verify no global state sharing
        engines = [fe['engine'] for fe in factory_engines]

        # Test that modifying one engine doesn't affect others
        for i, engine_info in enumerate(factory_engines):
            engine = engine_info['engine']
            factory_name = engine_info['factory_name']

            # Set unique state for this engine
            unique_key = f"global_state_test_{factory_name}_{i}"
            unique_value = f"value_{factory_name}_{i}"

            engine.set_agent_state(unique_key, unique_value)
            engine.execution_stats['factory_test_counter'] = i

        # Verify state isolation
        for i, engine_info in enumerate(factory_engines):
            engine = engine_info['engine']
            factory_name = engine_info['factory_name']

            # Engine should have its own state
            unique_key = f"global_state_test_{factory_name}_{i}"
            expected_value = f"value_{factory_name}_{i}"

            assert engine.get_agent_state(unique_key) == expected_value
            assert engine.execution_stats['factory_test_counter'] == i

            # Engine should not have state from other engines
            for j, other_engine_info in enumerate(factory_engines):
                if i != j:
                    other_factory_name = other_engine_info['factory_name']
                    other_key = f"global_state_test_{other_factory_name}_{j}"

                    assert engine.get_agent_state(other_key) is None

        # Verify class-level state is not shared
        for engine in engines:
            # Verify each engine has its own instance variables
            assert hasattr(engine, 'active_runs')
            assert hasattr(engine, 'run_history')
            assert hasattr(engine, 'execution_stats')

        # Test that engines from same factory are still isolated
        same_factory_engine_1 = await create_request_scoped_engine(
            self.create_test_user_context("same_factory_1")
        )
        same_factory_engine_2 = await create_request_scoped_engine(
            self.create_test_user_context("same_factory_2")
        )

        self.created_engines.extend([same_factory_engine_1, same_factory_engine_2])

        # Even engines from same factory should be isolated
        assert same_factory_engine_1 is not same_factory_engine_2
        assert same_factory_engine_1.engine_id != same_factory_engine_2.engine_id
        assert same_factory_engine_1.active_runs is not same_factory_engine_2.active_runs