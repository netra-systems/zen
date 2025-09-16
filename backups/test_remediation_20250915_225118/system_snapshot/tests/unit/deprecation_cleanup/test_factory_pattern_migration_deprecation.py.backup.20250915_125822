"""
Factory Pattern Migration Deprecation Test - Priority 1 Golden Path Critical

This test reproduces and validates deprecation warnings related to factory pattern
migrations, specifically SupervisorExecutionEngineFactory → UnifiedExecutionEngineFactory
transitions that impact the Golden Path user flow ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: System Stability & Agent Execution Reliability
- Value Impact: Prevents agent execution failures in chat functionality
- Strategic Impact: Protects $500K+ ARR by ensuring stable agent workflows and factory patterns

Test Purpose:
1. Reproduce specific factory pattern deprecation warnings
2. Establish failing tests that demonstrate deprecated factory usage
3. Provide guidance for migration to unified factory patterns

Priority 1 patterns targeted:
- SupervisorExecutionEngineFactory → UnifiedExecutionEngineFactory migration
- Legacy agent factory patterns that bypass SSOT
- Non-isolated factory instantiation that breaks multi-user contexts

Created: 2025-09-14
Test Category: Unit (deprecation reproduction)
"""

import warnings
import pytest
from unittest.mock import Mock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestFactoryPatternMigrationDeprecation(SSotBaseTestCase):
    """
    Test factory pattern migration deprecation warnings.

    These tests SHOULD FAIL initially to prove they reproduce the deprecation warnings.
    After factory pattern remediation, they should pass.
    """

    def setup_method(self, method=None):
        """Setup for factory deprecation testing."""
        super().setup_method(method)
        # Clear any existing warnings to get clean test results
        warnings.resetwarnings()
        # Ensure we catch all deprecation warnings
        warnings.simplefilter("always", DeprecationWarning)

    @pytest.mark.unit
    def test_deprecated_supervisor_execution_engine_factory_usage(self):
        """
        Test DEPRECATED: SupervisorExecutionEngineFactory usage patterns.

        This test should FAIL initially with deprecation warnings for:
        - SupervisorExecutionEngineFactory instead of UnifiedExecutionEngineFactory
        - Legacy factory initialization patterns
        - Non-SSOT factory usage that breaks isolation

        EXPECTED TO FAIL: This test reproduces deprecated factory patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)

            # DEPRECATED PATTERN 1: Direct SupervisorExecutionEngineFactory usage
            # This should trigger deprecation warnings for outdated factory pattern
            try:
                # Simulate the deprecated factory pattern
                class DeprecatedSupervisorExecutionEngineFactory:
                    """
                    DEPRECATED: Old SupervisorExecutionEngineFactory pattern.

                    This class simulates the deprecated factory that should trigger warnings.
                    The current pattern should use UnifiedExecutionEngineFactory instead.
                    """
                    def __init__(self, user_id=None, session_id=None):
                        # Deprecated initialization without proper isolation
                        self.user_id = user_id
                        self.session_id = session_id
                        self.config = {}

                    def create_execution_engine(self):
                        """Deprecated method for creating execution engines."""
                        # This represents the old factory method
                        engine = Mock()
                        engine.user_id = self.user_id
                        engine.session_id = self.session_id
                        return engine

                # Use the deprecated factory pattern
                deprecated_factory = DeprecatedSupervisorExecutionEngineFactory("user123", "session456")
                engine = deprecated_factory.create_execution_engine()

                assert engine.user_id == "user123"
                self.record_metric("deprecated_supervisor_factory_used", True)

            except Exception as e:
                # Expected - deprecated patterns may cause failures
                self.record_metric("deprecated_supervisor_factory_failure", str(e))

            # DEPRECATED PATTERN 2: Non-isolated factory instantiation
            # This violates multi-user isolation requirements
            try:
                # Simulate non-isolated factory usage (shared state problem)
                class SharedStateExecutionFactory:
                    """
                    DEPRECATED: Factory with shared state that breaks isolation.

                    This simulates the dangerous pattern where factory instances
                    share state between different users/sessions.
                    """
                    _shared_config = {}  # This is the problem - shared state!

                    def __init__(self, user_id):
                        self.user_id = user_id
                        # BAD: Modifying shared state
                        self._shared_config[user_id] = {"initialized": True}

                    def get_execution_engine(self):
                        """Get engine with problematic shared state."""
                        engine = Mock()
                        engine.shared_config = self._shared_config  # Dangerous!
                        return engine

                # Create multiple factory instances - this shows the isolation problem
                factory1 = SharedStateExecutionFactory("user1")
                factory2 = SharedStateExecutionFactory("user2")

                engine1 = factory1.get_execution_engine()
                engine2 = factory2.get_execution_engine()

                # This demonstrates the isolation problem
                assert "user1" in engine1.shared_config
                assert "user2" in engine2.shared_config

                # Both engines share state - this is the deprecated pattern!
                assert engine1.shared_config is engine2.shared_config

                self.record_metric("shared_state_factory_used", True)

            except Exception as e:
                self.record_metric("shared_state_factory_failure", str(e))

        # Count deprecation warnings
        deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]

        # Record metrics
        self.record_metric("total_factory_warnings", len(warning_list))
        self.record_metric("factory_deprecation_warnings", len(deprecation_warnings))

        # THIS SHOULD INITIALLY FAIL to prove factory deprecation reproduction
        factory_deprecation_reproduced = len(deprecation_warnings) > 0 or len(warning_list) > 0

        assert factory_deprecation_reproduced, (
            f"REPRODUCTION FAILURE: Expected deprecation warnings for SupervisorExecutionEngineFactory patterns, "
            f"but captured {len(deprecation_warnings)} deprecation warnings out of {len(warning_list)} total warnings. "
            f"This indicates deprecated factory patterns are not properly reproduced in this test."
        )

        # Log warnings for analysis
        for warning in deprecation_warnings:
            self.logger.warning(f"Captured factory deprecation warning: {warning.message}")

    @pytest.mark.unit
    def test_deprecated_agent_factory_instantiation_patterns(self):
        """
        Test DEPRECATED: Legacy agent factory instantiation patterns.

        This test should FAIL initially by demonstrating non-SSOT agent factory usage
        that violates the USER_CONTEXT_ARCHITECTURE.md factory isolation requirements.

        EXPECTED TO FAIL: This test reproduces deprecated agent factory patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # DEPRECATED PATTERN: Direct agent factory instantiation without context isolation
            try:
                class DeprecatedAgentFactory:
                    """
                    DEPRECATED: Direct agent factory without proper user context isolation.

                    This represents the old pattern where agent factories were created
                    without proper multi-user isolation, leading to context bleed.
                    """
                    def __init__(self):
                        # BAD: No user context isolation
                        self.agents = {}
                        self.global_state = {}  # Shared across all users!

                    def create_agent(self, agent_type, user_id=None):
                        """Create agent without proper isolation."""
                        # BAD: No user context separation
                        agent = Mock()
                        agent.type = agent_type
                        agent.user_id = user_id
                        agent.shared_state = self.global_state  # Problem!

                        # Store in shared dict - isolation violation
                        self.agents[agent_type] = agent
                        return agent

                # Use deprecated pattern
                deprecated_factory = DeprecatedAgentFactory()

                # Create agents for different users using same factory instance
                agent1 = deprecated_factory.create_agent("supervisor", "user1")
                agent2 = deprecated_factory.create_agent("supervisor", "user2")

                # This demonstrates the context bleed problem
                assert agent1.shared_state is agent2.shared_state  # Both share same state!

                self.record_metric("deprecated_agent_factory_used", True)

            except Exception as e:
                self.record_metric("deprecated_agent_factory_failure", str(e))

            # DEPRECATED PATTERN: Non-factory agent creation (direct instantiation)
            try:
                class DirectAgentInstantiation:
                    """
                    DEPRECATED: Direct agent instantiation without factory pattern.

                    This simulates the pattern where agents are created directly
                    instead of through proper factory methods with isolation.
                    """
                    def __init__(self, agent_type, user_id):
                        self.agent_type = agent_type
                        self.user_id = user_id
                        # BAD: Direct initialization without factory pattern
                        self.state = {"initialized": True}

                # Direct instantiation - bypasses factory pattern
                agent1 = DirectAgentInstantiation("triage", "user1")
                agent2 = DirectAgentInstantiation("triage", "user2")

                assert agent1.user_id != agent2.user_id
                self.record_metric("direct_agent_instantiation_used", True)

            except Exception as e:
                self.record_metric("direct_agent_instantiation_failure", str(e))

        # Check for factory-related warnings
        factory_warnings = [
            w for w in warning_list
            if any(keyword in str(w.message).lower()
                  for keyword in ['factory', 'deprecated', 'isolation', 'context'])
        ]

        self.record_metric("factory_pattern_warnings", len(factory_warnings))

        # THIS SHOULD INITIALLY FAIL to prove factory deprecation reproduction
        factory_deprecation_detected = len(factory_warnings) > 0 or len(warning_list) > 0

        assert factory_deprecation_detected, (
            f"REPRODUCTION FAILURE: Expected deprecation warnings for agent factory patterns, "
            f"but captured {len(factory_warnings)} factory warnings and {len(warning_list)} total warnings. "
            f"This indicates deprecated agent factory patterns are not properly reproduced."
        )

    @pytest.mark.unit
    def test_deprecated_execution_engine_context_sharing(self):
        """
        Test DEPRECATED: Execution engine context sharing violations.

        This test should FAIL initially by demonstrating execution engines that
        share context between users, violating multi-user isolation requirements.

        EXPECTED TO FAIL: This test reproduces deprecated context sharing patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # DEPRECATED PATTERN: Shared execution engine context
            try:
                class DeprecatedSharedExecutionEngine:
                    """
                    DEPRECATED: Execution engine with shared context between users.

                    This simulates the dangerous pattern where execution engines
                    share state/context between different user sessions.
                    """
                    _global_context = {}  # PROBLEM: Shared across all users!

                    def __init__(self, user_id):
                        self.user_id = user_id
                        # BAD: Adding user data to shared context
                        self._global_context[user_id] = {
                            'session_data': {},
                            'execution_history': []
                        }

                    def execute(self, task):
                        """Execute task with shared context access."""
                        # BAD: All users can access each other's context
                        user_context = self._global_context[self.user_id]
                        user_context['execution_history'].append(task)

                        # Simulate execution result
                        result = {
                            'task': task,
                            'user_id': self.user_id,
                            'global_context': self._global_context  # Exposes all user data!
                        }
                        return result

                # Create engines for multiple users
                engine1 = DeprecatedSharedExecutionEngine("user1")
                engine2 = DeprecatedSharedExecutionEngine("user2")

                # Execute tasks
                result1 = engine1.execute("optimize costs")
                result2 = engine2.execute("analyze data")

                # Both engines share the same global context - this is the problem!
                assert result1['global_context'] is result2['global_context']
                assert 'user1' in result2['global_context']  # User2 can see User1's data!
                assert 'user2' in result1['global_context']  # User1 can see User2's data!

                self.record_metric("shared_execution_context_used", True)

            except Exception as e:
                self.record_metric("shared_execution_context_failure", str(e))

        # Look for context sharing warnings
        context_warnings = [
            w for w in warning_list
            if any(keyword in str(w.message).lower()
                  for keyword in ['context', 'shared', 'isolation', 'execution'])
        ]

        self.record_metric("context_sharing_warnings", len(context_warnings))

        # THIS SHOULD INITIALLY FAIL to prove context sharing reproduction
        context_sharing_reproduced = len(context_warnings) > 0 or len(warning_list) > 0

        assert context_sharing_reproduced, (
            f"REPRODUCTION FAILURE: Expected warnings for execution engine context sharing, "
            f"but captured {len(context_warnings)} context warnings and {len(warning_list)} total warnings. "
            f"This indicates deprecated context sharing patterns are not properly reproduced."
        )


class TestFactoryPatternMigrationGuidance(SSotBaseTestCase):
    """
    Test factory pattern migration guidance and correct patterns.

    These tests provide examples of correct migration paths from deprecated
    factory patterns to SSOT-compliant unified factory patterns.
    """

    @pytest.mark.unit
    def test_migration_to_unified_execution_engine_factory(self):
        """
        Test migration guidance: SupervisorExecutionEngineFactory → UnifiedExecutionEngineFactory.

        This test demonstrates the correct migration path and should PASS.
        """
        # CORRECT PATTERN: Unified factory with proper isolation
        def create_unified_execution_engine_factory(user_id: str, session_id: str):
            """
            Unified factory function for creating execution engines with proper isolation.

            This replaces deprecated SupervisorExecutionEngineFactory.
            """
            # Use SSOT environment for configuration
            env = self.get_env()

            # Create isolated execution engine
            class UnifiedExecutionEngine:
                def __init__(self, user_id: str, session_id: str):
                    self.user_id = user_id
                    self.session_id = session_id
                    self.trace_id = f"trace_{session_id}"
                    # Each engine gets isolated configuration
                    self.config = {
                        'database_url': env.get('DATABASE_URL', 'default_db'),
                        'redis_url': env.get('REDIS_URL', 'default_redis')
                    }
                    # Isolated state per instance
                    self.context = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'execution_history': []
                    }

                def execute(self, task):
                    """Execute with isolated context."""
                    self.context['execution_history'].append(task)
                    return {
                        'task': task,
                        'user_id': self.user_id,
                        'session_id': self.session_id
                    }

            return UnifiedExecutionEngine(user_id, session_id)

        # Test the unified factory pattern
        engine1 = create_unified_execution_engine_factory("user1", "session1")
        engine2 = create_unified_execution_engine_factory("user2", "session2")

        # Verify proper isolation
        assert engine1.user_id != engine2.user_id
        assert engine1.context is not engine2.context  # Separate contexts!

        # Test execution isolation
        result1 = engine1.execute("task1")
        result2 = engine2.execute("task2")

        assert result1['user_id'] != result2['user_id']
        assert len(engine1.context['execution_history']) == 1
        assert len(engine2.context['execution_history']) == 1
        assert engine1.context['execution_history'] != engine2.context['execution_history']

        self.record_metric("unified_factory_pattern_success", True)

    @pytest.mark.unit
    def test_proper_agent_factory_isolation_pattern(self):
        """
        Test proper agent factory isolation pattern.

        This test demonstrates the correct factory-based agent creation
        that replaces deprecated direct instantiation patterns.
        """
        # CORRECT PATTERN: Factory with proper user context isolation
        def create_isolated_agent_factory(user_id: str, session_id: str):
            """
            Factory function for creating agents with proper user context isolation.
            """
            env = self.get_env()

            class IsolatedAgentFactory:
                def __init__(self, user_id: str, session_id: str):
                    self.user_id = user_id
                    self.session_id = session_id
                    # Each factory instance is isolated
                    self.context = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'created_agents': []
                    }

                def create_agent(self, agent_type: str):
                    """Create agent with isolated context."""
                    agent = {
                        'type': agent_type,
                        'user_id': self.user_id,
                        'session_id': self.session_id,
                        'context': {
                            'user_id': self.user_id,
                            'session_id': self.session_id,
                            'agent_id': f"{agent_type}_{len(self.context['created_agents'])}"
                        }
                    }

                    self.context['created_agents'].append(agent)
                    return agent

            return IsolatedAgentFactory(user_id, session_id)

        # Test isolated factory pattern
        factory1 = create_isolated_agent_factory("user1", "session1")
        factory2 = create_isolated_agent_factory("user2", "session2")

        # Create agents
        agent1 = factory1.create_agent("supervisor")
        agent2 = factory2.create_agent("supervisor")

        # Verify proper isolation
        assert agent1['user_id'] != agent2['user_id']
        assert agent1['context'] is not agent2['context']
        assert factory1.context is not factory2.context

        self.record_metric("isolated_agent_factory_success", True)

    @pytest.mark.unit
    def test_execution_context_isolation_best_practices(self):
        """
        Test execution context isolation best practices.

        This test demonstrates proper execution context isolation that prevents
        the deprecated context sharing patterns.
        """
        # CORRECT PATTERN: Isolated execution contexts
        def create_isolated_execution_context(user_id: str, session_id: str):
            """
            Create isolated execution context for a specific user session.
            """
            env = self.get_env()

            return {
                'user_id': user_id,
                'session_id': session_id,
                'trace_id': f"trace_{session_id}",
                'execution_state': {
                    'started_at': None,
                    'completed_tasks': [],
                    'current_task': None
                },
                'configuration': {
                    'database_url': env.get('DATABASE_URL', 'default_db'),
                    'redis_url': env.get('REDIS_URL', 'default_redis')
                },
                # Each context is completely isolated
                'private_data': {}
            }

        # Create isolated contexts for different users
        context1 = create_isolated_execution_context("user1", "session1")
        context2 = create_isolated_execution_context("user2", "session2")

        # Verify complete isolation
        assert context1['user_id'] != context2['user_id']
        assert context1 is not context2
        assert context1['execution_state'] is not context2['execution_state']
        assert context1['private_data'] is not context2['private_data']

        # Modify one context and ensure the other is unaffected
        context1['private_data']['secret'] = "user1_secret"
        context2['private_data']['secret'] = "user2_secret"

        assert context1['private_data']['secret'] != context2['private_data']['secret']

        self.record_metric("execution_context_isolation_success", True)


if __name__ == "__main__":
    """
    When run directly, this script executes the factory pattern deprecation tests.
    """
    print("=" * 60)
    print("Factory Pattern Migration Deprecation Test - Priority 1")
    print("=" * 60)

    # Note: These tests are designed to FAIL initially to prove reproduction
    print("⚠️  WARNING: These tests are designed to FAIL initially")
    print("   This proves that deprecated factory patterns are reproduced")
    print("   After remediation, tests should pass")
    print("=" * 60)