"""
Test 2: Factory Method Pattern Compliance

PURPOSE: Ensure all agents use proper factory methods and dependency injection patterns.
ISSUE: #709 - Agent Factory Singleton Legacy remediation
SCOPE: SSOT factory method pattern validation

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: Tests should FAIL (proving incorrect patterns exist)
- AFTER REMEDIATION: Tests should PASS (proving SSOT compliance)

Business Value: Platform/Internal - $500K+ ARR protection through proper dependency injection
"""

import asyncio
import inspect
import sys
import time
from typing import Any, Dict, List, Optional, Type, Callable
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestFactoryMethodPatternCompliance(SSotAsyncTestCase):
    """
    Test suite validating proper factory method patterns in agent creation.

    This test suite specifically targets Issue #709 by validating that:
    1. All agents use `create_agent_with_context()` pattern
    2. Dependencies flow through `UserExecutionContext`
    3. No agents use global constructor patterns
    4. SSOT dependency injection patterns are followed

    CRITICAL: These tests should FAIL before remediation and PASS after.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Track created instances for cleanup
        self._tracked_instances = []
        self._tracked_contexts = []

        # Mock dependencies for testing
        self._mock_dependencies = {
            'websocket_bridge': SSotMockFactory.create_mock_agent_websocket_bridge(),
            'llm_manager': SSotMockFactory.create_mock_llm_manager(),
            'tool_dispatcher': MagicMock(),  # Simple mock for tool dispatcher
            'agent_registry': MagicMock()   # Simple mock for agent registry
        }

        self.record_metric("test_setup_completed", True)

    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Clean up tracked instances
        for instance in self._tracked_instances:
            try:
                if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
            except Exception as e:
                print(f"Warning: Cleanup failed for instance {instance}: {e}")

        # Clean up tracked contexts
        for context in self._tracked_contexts:
            try:
                if hasattr(context, 'cleanup') and callable(context.cleanup):
                    if asyncio.iscoroutinefunction(context.cleanup):
                        asyncio.create_task(context.cleanup())
                    else:
                        context.cleanup()
            except Exception as e:
                print(f"Warning: Context cleanup failed for {context}: {e}")

        super().teardown_method(method)

    async def test_agent_factory_uses_create_agent_with_context_pattern(self):
        """
        CRITICAL TEST: Validate AgentInstanceFactory uses create_agent_with_context() pattern.

        This test should FAIL before Issue #709 remediation if agents are created
        using legacy constructor patterns instead of the factory method pattern.

        After remediation, this test should PASS by proving SSOT factory compliance.
        """
        self.record_metric("test_started", "test_agent_factory_uses_create_agent_with_context_pattern")

        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # CRITICAL CHECK 1: Verify AgentInstanceFactory has proper methods
            factory = AgentInstanceFactory()
            self._tracked_instances.append(factory)

            # Configure factory with mock dependencies
            factory.configure(
                websocket_bridge=self._mock_dependencies['websocket_bridge'],
                agent_registry=self._mock_dependencies['agent_registry'],
                llm_manager=self._mock_dependencies['llm_manager'],
                tool_dispatcher=self._mock_dependencies['tool_dispatcher']
            )

            # Verify factory has the required methods
            assert hasattr(factory, 'create_agent_instance'), (
                f"FACTORY PATTERN VIOLATION: AgentInstanceFactory missing create_agent_instance method. "
                f"Available methods: {[m for m in dir(factory) if not m.startswith('_')]}. "
                f"Expected: create_agent_instance method for SSOT factory pattern."
            )

            # CRITICAL CHECK 2: Create test user context
            user_context = UserExecutionContext.from_request_supervisor(
                user_id="test_user_factory_pattern",
                thread_id="test_thread_factory",
                run_id="test_run_factory_123"
            )
            self._tracked_contexts.append(user_context)

            # CRITICAL CHECK 3: Test agent creation uses dependency injection
            # Before remediation, this might fail due to missing dependencies or wrong patterns
            test_agent_names = [
                'TriageSubAgent',
                'DataHelperAgent',
                'OptimizationsCoreSubAgent'
            ]

            successful_creations = 0
            dependency_injection_failures = []

            for agent_name in test_agent_names:
                try:
                    # This should work after remediation with proper dependency injection
                    agent = await factory.create_agent_instance(
                        agent_name=agent_name,
                        user_context=user_context
                    )

                    self._tracked_instances.append(agent)

                    # CRITICAL CHECK 4: Verify agent has proper dependency injection
                    # Before remediation, agents might not receive dependencies properly
                    if hasattr(agent, 'llm_manager'):
                        # If agent should have LLM manager, verify it's injected
                        if agent_name in ['DataHelperAgent', 'OptimizationsCoreSubAgent']:
                            assert agent.llm_manager is not None, (
                                f"DEPENDENCY INJECTION VIOLATION: {agent_name} missing llm_manager. "
                                f"Expected: LLM manager to be injected via factory pattern."
                            )

                    # CRITICAL CHECK 5: Verify agent has WebSocket capabilities if configured
                    if hasattr(agent, '_websocket_adapter') or hasattr(agent, 'set_websocket_bridge'):
                        # Agent should have WebSocket capabilities properly set up
                        websocket_configured = (
                            hasattr(agent, '_websocket_adapter') and agent._websocket_adapter is not None
                        ) or (
                            hasattr(agent, '_websocket_bridge')
                        )

                        # This might FAIL before remediation - improper WebSocket setup
                        if not websocket_configured:
                            dependency_injection_failures.append(
                                f"{agent_name}: WebSocket bridge not properly configured"
                            )

                    successful_creations += 1

                except Exception as e:
                    dependency_injection_failures.append(f"{agent_name}: {str(e)}")

            # CRITICAL CHECK 6: Validate success rate
            # Before remediation, many agents might fail to create properly
            success_rate = successful_creations / len(test_agent_names)
            assert success_rate >= 0.5, (
                f"FACTORY PATTERN VIOLATION: Low agent creation success rate: {success_rate:.1%}. "
                f"Successful: {successful_creations}/{len(test_agent_names)}. "
                f"Failures: {dependency_injection_failures}. "
                f"Expected: High success rate with proper factory pattern implementation."
            )

            # If we have dependency injection failures, report them
            if dependency_injection_failures:
                assert len(dependency_injection_failures) == 0, (
                    f"DEPENDENCY INJECTION VIOLATIONS detected: {dependency_injection_failures}. "
                    f"These indicate improper factory pattern implementation."
                )

            self.record_metric("successful_agent_creations", successful_creations)
            self.record_metric("factory_pattern_checks_passed", 6)
            self.record_metric("test_result", "PASS")

        except ImportError as e:
            pytest.fail(f"Cannot import required modules for factory pattern testing: {e}")
        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during factory pattern validation: {e}")

    async def test_agents_use_context_dependency_injection(self):
        """
        CRITICAL TEST: Validate agents receive dependencies through UserExecutionContext.

        This test verifies that agents properly use context.get_dependency() pattern
        instead of global dependencies or constructor parameters.

        Expected to FAIL before remediation due to legacy dependency patterns.
        """
        self.record_metric("test_started", "test_agents_use_context_dependency_injection")

        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # CRITICAL CHECK 1: Create factory and user context
            factory = AgentInstanceFactory()
            self._tracked_instances.append(factory)

            # Configure with dependencies
            factory.configure(
                websocket_bridge=self._mock_dependencies['websocket_bridge'],
                llm_manager=self._mock_dependencies['llm_manager'],
                tool_dispatcher=self._mock_dependencies['tool_dispatcher']
            )

            user_context = UserExecutionContext.from_request_supervisor(
                user_id="test_user_context_injection",
                thread_id="test_thread_context",
                run_id="test_run_context_456"
            )
            self._tracked_contexts.append(user_context)

            # CRITICAL CHECK 2: Verify context can store and retrieve dependencies
            test_dependency = {"test_key": "test_value", "dependency_id": 12345}
            user_context.set_dependency('test_dependency', test_dependency)

            retrieved_dependency = user_context.get_dependency('test_dependency')
            assert retrieved_dependency == test_dependency, (
                f"CONTEXT INJECTION VIOLATION: Context dependency storage/retrieval failed. "
                f"Stored: {test_dependency}, Retrieved: {retrieved_dependency}. "
                f"Expected: Context to properly store and retrieve dependencies."
            )

            # CRITICAL CHECK 3: Test agent creation with context dependency injection
            # Create an agent that should receive dependencies through context
            agent_name = 'DataHelperAgent'

            try:
                agent = await factory.create_agent_instance(
                    agent_name=agent_name,
                    user_context=user_context
                )
                self._tracked_instances.append(agent)

                # CRITICAL CHECK 4: Verify agent has access to context
                # Before remediation, agents might not have proper context access
                if hasattr(agent, 'user_context') or hasattr(agent, '_user_context'):
                    context_attr = getattr(agent, 'user_context', None) or getattr(agent, '_user_context', None)
                    assert context_attr is not None, (
                        f"CONTEXT INJECTION VIOLATION: {agent_name} user_context is None. "
                        f"Expected: Agent to have access to UserExecutionContext."
                    )
                elif hasattr(agent, 'get_context'):
                    # Alternative context access pattern
                    try:
                        context_from_method = agent.get_context()
                        assert context_from_method is not None, (
                            f"CONTEXT INJECTION VIOLATION: {agent_name}.get_context() returns None. "
                            f"Expected: Agent to have access to UserExecutionContext."
                        )
                    except Exception as e:
                        pytest.fail(f"CONTEXT INJECTION VIOLATION: {agent_name}.get_context() failed: {e}")

                # CRITICAL CHECK 5: Verify agent can access dependencies via context
                if hasattr(agent, 'user_context') and agent.user_context:
                    # Test if agent can retrieve the test dependency we stored
                    try:
                        agent_retrieved_dependency = agent.user_context.get_dependency('test_dependency')
                        assert agent_retrieved_dependency == test_dependency, (
                            f"CONTEXT INJECTION VIOLATION: {agent_name} cannot access context dependencies. "
                            f"Expected: {test_dependency}, Got: {agent_retrieved_dependency}. "
                            f"This indicates improper context dependency injection."
                        )
                    except Exception as e:
                        # This should FAIL before remediation - agents might not have context access
                        pytest.fail(f"CONTEXT INJECTION VIOLATION: {agent_name} context dependency access failed: {e}")

                # CRITICAL CHECK 6: Verify agent uses injected dependencies
                # Check if agent has the dependencies that should have been injected
                dependency_check_results = {}

                if hasattr(agent, 'llm_manager'):
                    dependency_check_results['llm_manager'] = agent.llm_manager is not None

                if hasattr(agent, 'tool_dispatcher'):
                    dependency_check_results['tool_dispatcher'] = agent.tool_dispatcher is not None

                # Before remediation, some dependencies might be missing
                missing_dependencies = [dep for dep, present in dependency_check_results.items() if not present]
                if missing_dependencies:
                    assert len(missing_dependencies) == 0, (
                        f"DEPENDENCY INJECTION VIOLATION: {agent_name} missing dependencies: {missing_dependencies}. "
                        f"Dependency status: {dependency_check_results}. "
                        f"Expected: All required dependencies to be injected via factory pattern."
                    )

            except Exception as agent_creation_error:
                # Agent creation might fail before remediation due to improper patterns
                pytest.fail(f"FACTORY PATTERN VIOLATION: {agent_name} creation failed: {agent_creation_error}")

            self.record_metric("context_injection_checks_passed", 6)
            self.record_metric("test_result", "PASS")

        except ImportError as e:
            pytest.fail(f"Cannot import required modules for context injection testing: {e}")
        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during context injection validation: {e}")

    async def test_factory_method_signature_compliance(self):
        """
        CRITICAL TEST: Validate factory methods have proper SSOT signatures.

        This test verifies that factory methods follow the standard SSOT pattern:
        - create_agent_with_context(context: UserExecutionContext) -> Agent
        - Proper type hints and parameter validation
        - Consistent error handling patterns

        Expected to FAIL before remediation due to inconsistent method signatures.
        """
        self.record_metric("test_started", "test_factory_method_signature_compliance")

        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # CRITICAL CHECK 1: Verify AgentInstanceFactory method signatures
            factory = AgentInstanceFactory()
            self._tracked_instances.append(factory)

            # Check create_agent_instance method signature
            create_agent_method = getattr(factory, 'create_agent_instance', None)
            assert create_agent_method is not None, (
                f"FACTORY SIGNATURE VIOLATION: AgentInstanceFactory missing create_agent_instance method. "
                f"Expected: Standard factory method for agent creation."
            )

            # Inspect method signature
            sig = inspect.signature(create_agent_method)
            params = list(sig.parameters.keys())

            # CRITICAL CHECK 2: Verify required parameters
            required_params = ['agent_name', 'user_context']
            for param in required_params:
                assert param in params, (
                    f"FACTORY SIGNATURE VIOLATION: create_agent_instance missing {param} parameter. "
                    f"Actual parameters: {params}. "
                    f"Expected: {required_params} for SSOT factory pattern."
                )

            # CRITICAL CHECK 3: Verify parameter annotations (if present)
            user_context_param = sig.parameters.get('user_context')
            if user_context_param and user_context_param.annotation != inspect.Parameter.empty:
                # Check if annotation is correct
                annotation_name = getattr(user_context_param.annotation, '__name__', str(user_context_param.annotation))
                assert 'UserExecutionContext' in annotation_name, (
                    f"FACTORY SIGNATURE VIOLATION: user_context parameter has wrong type annotation. "
                    f"Expected: UserExecutionContext, Got: {annotation_name}. "
                    f"This indicates improper SSOT factory pattern implementation."
                )

            # CRITICAL CHECK 4: Test method behavior with proper inputs
            user_context = UserExecutionContext.from_request_supervisor(
                user_id="test_user_signature",
                thread_id="test_thread_signature",
                run_id="test_run_signature_789"
            )
            self._tracked_contexts.append(user_context)

            # Configure factory
            factory.configure(
                websocket_bridge=self._mock_dependencies['websocket_bridge'],
                llm_manager=self._mock_dependencies['llm_manager']
            )

            # Test method with valid inputs
            try:
                agent = await factory.create_agent_instance(
                    agent_name='TriageSubAgent',
                    user_context=user_context
                )
                self._tracked_instances.append(agent)

                # Verify agent is properly created
                assert agent is not None, (
                    f"FACTORY SIGNATURE VIOLATION: create_agent_instance returned None with valid inputs. "
                    f"Expected: Valid agent instance."
                )

            except Exception as e:
                # This should work after remediation
                pytest.fail(f"FACTORY SIGNATURE VIOLATION: create_agent_instance failed with valid inputs: {e}")

            # CRITICAL CHECK 5: Test error handling with invalid inputs
            # Test with None user_context (should raise appropriate error)
            with pytest.raises((ValueError, TypeError, RuntimeError)):
                await factory.create_agent_instance(
                    agent_name='TriageSubAgent',
                    user_context=None
                )

            # Test with invalid agent name (should raise appropriate error)
            with pytest.raises((ValueError, RuntimeError)):
                await factory.create_agent_instance(
                    agent_name='NonExistentAgent',
                    user_context=user_context
                )

            # CRITICAL CHECK 6: Verify method is async
            assert asyncio.iscoroutinefunction(create_agent_method), (
                f"FACTORY SIGNATURE VIOLATION: create_agent_instance is not async. "
                f"Expected: Async method for proper SSOT factory pattern."
            )

            self.record_metric("signature_compliance_checks_passed", 6)
            self.record_metric("test_result", "PASS")

        except ImportError as e:
            pytest.fail(f"Cannot import required modules for signature testing: {e}")
        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during signature compliance validation: {e}")

    async def test_no_global_constructor_patterns(self):
        """
        CRITICAL TEST: Validate agents don't use global constructor patterns.

        This test verifies that agents don't rely on global singletons,
        global state, or direct constructor calls without proper factory mediation.

        Expected to FAIL before remediation due to legacy global patterns.
        """
        self.record_metric("test_started", "test_no_global_constructor_patterns")

        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

            # CRITICAL CHECK 1: Verify factory doesn't create agents via direct constructors
            factory = AgentInstanceFactory()
            self._tracked_instances.append(factory)

            # Mock the AgentClassRegistry to track constructor calls
            original_get_agent_class = None
            constructor_calls = []

            def track_constructor_calls(agent_name):
                """Track if agents are created via direct constructors."""
                constructor_calls.append(agent_name)
                # Return a mock class that tracks instantiation
                class MockAgent:
                    def __init__(self, *args, **kwargs):
                        self.creation_args = args
                        self.creation_kwargs = kwargs
                        self.agent_name = agent_name
                        constructor_calls.append(f"{agent_name}_instantiated")

                return MockAgent

            # CRITICAL CHECK 2: Patch agent class registry to monitor creation patterns
            with patch.object(factory, '_agent_class_registry', None):
                # Create mock registry that tracks constructor usage
                mock_registry = Mock()
                mock_registry.get_agent_class = Mock(side_effect=track_constructor_calls)
                factory._agent_class_registry = mock_registry

                # Create test context
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                user_context = UserExecutionContext.from_request_supervisor(
                    user_id="test_user_global_check",
                    thread_id="test_thread_global",
                    run_id="test_run_global_111"
                )
                self._tracked_contexts.append(user_context)

                # Configure factory with minimal dependencies
                factory.configure(websocket_bridge=self._mock_dependencies['websocket_bridge'])

                try:
                    # Attempt to create agent
                    agent = await factory.create_agent_instance(
                        agent_name='TriageSubAgent',
                        user_context=user_context
                    )
                    self._tracked_instances.append(agent)

                    # CRITICAL CHECK 3: Verify constructor was called through registry
                    assert 'TriageSubAgent' in constructor_calls, (
                        f"GLOBAL PATTERN VIOLATION: Agent creation bypassed registry lookup. "
                        f"Constructor calls: {constructor_calls}. "
                        f"Expected: Agent creation to go through proper registry pattern."
                    )

                    # CRITICAL CHECK 4: Verify instantiation followed registry pattern
                    assert 'TriageSubAgent_instantiated' in constructor_calls, (
                        f"GLOBAL PATTERN VIOLATION: Agent instantiation bypassed factory pattern. "
                        f"Constructor calls: {constructor_calls}. "
                        f"Expected: Agent instantiation to follow factory-mediated pattern."
                    )

                    # CRITICAL CHECK 5: Verify agent has proper factory context
                    assert hasattr(agent, 'agent_name'), (
                        f"GLOBAL PATTERN VIOLATION: Agent missing factory context. "
                        f"Agent attributes: {dir(agent)}. "
                        f"Expected: Agent to have context from factory creation."
                    )

                except Exception as e:
                    # Check if error indicates global pattern violations
                    error_str = str(e).lower()
                    global_violation_indicators = [
                        'global', 'singleton', 'shared state', 'not configured'
                    ]

                    if any(indicator in error_str for indicator in global_violation_indicators):
                        pytest.fail(f"GLOBAL PATTERN VIOLATION detected in error: {e}")
                    else:
                        # Re-raise if it's not a global pattern issue
                        raise

            # CRITICAL CHECK 6: Verify no global state dependencies
            # Check if factory maintains global state that would indicate singleton patterns
            factory_state_attributes = [
                attr for attr in dir(factory)
                if not attr.startswith('__') and not callable(getattr(factory, attr))
            ]

            global_state_indicators = []
            for attr in factory_state_attributes:
                value = getattr(factory, attr, None)
                if value is not None:
                    # Check for singleton-like patterns
                    if isinstance(value, type) and hasattr(value, '__dict__'):
                        # This might indicate a stored class (singleton pattern)
                        global_state_indicators.append(f"{attr}: stored class")
                    elif hasattr(value, '__self__') and value.__self__ is not factory:
                        # This might indicate a global method reference
                        global_state_indicators.append(f"{attr}: global method reference")

            # Before remediation, we might find global state indicators
            if global_state_indicators:
                # This should FAIL before remediation
                assert len(global_state_indicators) == 0, (
                    f"GLOBAL PATTERN VIOLATIONS detected in factory state: {global_state_indicators}. "
                    f"These indicate potential singleton or global dependency patterns."
                )

            self.record_metric("global_pattern_checks_passed", 6)
            self.record_metric("test_result", "PASS")

        except ImportError as e:
            pytest.fail(f"Cannot import required modules for global pattern testing: {e}")
        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during global pattern validation: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])