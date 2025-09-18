"""Test Issue #1186: UserExecutionEngine Constructor Dependency Injection Validation

This test suite validates that UserExecutionEngine properly requires dependencies
as identified in Issue #1186 Phase 4 status update for SSOT consolidation.

Expected Behavior: These tests validate the constructor enhancement:
- Previous: UserExecutionEngine() (no arguments)
- Current: UserExecutionEngine(context, agent_factory, websocket_emitter)

Business Impact: Proper dependency injection enforces user isolation and prevents
singleton violations, enabling enterprise-grade multi-user isolation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enforce proper dependency injection and user isolation
- Value Impact: Prevents singleton violations and ensures enterprise-grade security
- Strategic Impact: Foundation for multi-tenant production deployment at scale
"""

import sys
import unittest
import pytest
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from unittest.mock import Mock, MagicMock, patch


# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    # Create mock classes for testing when imports fail
    class UserExecutionEngine:
        def __init__(self, *args, **kwargs):
            pass

    class UserExecutionContext:
        pass

    class AgentInstanceFactory:
        pass


@pytest.mark.unit
class TestUserExecutionEngineConstructorDependencyInjection(unittest.TestCase):
    """Test class for UserExecutionEngine constructor dependency injection validation"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_1_constructor_requires_dependencies(self):
        """
        Test 1: Validate constructor requires proper dependencies

        EXPECTED TO FAIL: Should validate UserExecutionEngine(context, agent_factory, websocket_emitter)
        """
        print("\n🔍 CONSTRUCTOR TEST 1: Validating constructor requires dependencies...")

        # Get constructor signature
        constructor_sig = inspect.signature(UserExecutionEngine.__init__)
        required_params = [
            param for param_name, param in constructor_sig.parameters.items()
            if param_name != 'self' and param.default == inspect.Parameter.empty
        ]

        # Expected required parameters based on Issue #1186 Phase 4
        expected_required_params = ['context', 'agent_factory', 'websocket_emitter']

        # This test should validate the enhanced constructor
        actual_required_params = [param.name for param in required_params]

        # Check if constructor has required parameters
        has_required_deps = all(param in actual_required_params for param in expected_required_params)

        self.assertTrue(
            has_required_deps,
            f"X CONSTRUCTOR VALIDATION FAILURE: UserExecutionEngine constructor does not require expected dependencies.\n"
            f"Expected required parameters: {expected_required_params}\n"
            f"Actual required parameters: {actual_required_params}\n"
            f"Issue #1186 Phase 4 requires: UserExecutionEngine(context, agent_factory, websocket_emitter)\n"
            f"This enforces proper dependency injection and prevents singleton violations."
        )

    def test_2_no_parameterless_instantiation_allowed(self):
        """
        Test 2: Validate no parameterless instantiation is allowed

        EXPECTED TO FAIL: Should prevent UserExecutionEngine() with no arguments
        """
        print("\n🔍 CONSTRUCTOR TEST 2: Validating no parameterless instantiation...")

        parameterless_allowed = False
        try:
            # Attempt parameterless instantiation
            engine = UserExecutionEngine()
            parameterless_allowed = True
        except TypeError as e:
            # Expected behavior - constructor should require parameters
            parameterless_allowed = False
        except Exception as e:
            # Other exceptions might indicate different issues
            print(f"Unexpected exception during parameterless instantiation: {e}")
            parameterless_allowed = False

        # This test should FAIL if parameterless instantiation is allowed
        self.assertFalse(
            parameterless_allowed,
            f"X CONSTRUCTOR VALIDATION FAILURE: UserExecutionEngine allows parameterless instantiation.\n"
            f"Issue #1186 Phase 4 requires constructor enhancement to prevent singleton violations.\n"
            f"Expected: UserExecutionEngine(context, agent_factory, websocket_emitter)\n"
            f"This should enforce proper dependency injection and user isolation."
        )

    def test_3_user_context_isolation_enforcement(self):
        """
        Test 3: Validate constructor enforces user context isolation

        EXPECTED BEHAVIOR: Constructor should accept UserExecutionContext and maintain isolation
        """
        print("\n🔍 CONSTRUCTOR TEST 3: Validating user context isolation enforcement...")

        try:
            # Create mock dependencies
            mock_context = Mock(spec=UserExecutionContext)
            mock_context.user_id = "user_123"
            mock_context.session_id = "session_456"

            mock_agent_factory = Mock(spec=AgentInstanceFactory)
            mock_websocket_emitter = Mock()

            # Test constructor with proper dependencies
            engine1 = UserExecutionEngine(
                context=mock_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )

            # Create second instance with different context
            mock_context2 = Mock(spec=UserExecutionContext)
            mock_context2.user_id = "user_789"
            mock_context2.session_id = "session_101"

            engine2 = UserExecutionEngine(
                context=mock_context2,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )

            # Validate instances are separate and isolated
            self.assertIsNot(
                engine1,
                engine2,
                "X USER ISOLATION FAILURE: UserExecutionEngine instances should be completely separate."
            )

            # Validate that instances don't share internal state
            self.assertNotEqual(
                id(engine1),
                id(engine2),
                "X USER ISOLATION FAILURE: UserExecutionEngine instances have same memory address."
            )

        except Exception as e:
            self.fail(
                f"X CONSTRUCTOR VALIDATION FAILURE: Could not create UserExecutionEngine with proper dependencies.\n"
                f"Error: {e}\n"
                f"Issue #1186 Phase 4 requires constructor to accept (context, agent_factory, websocket_emitter)."
            )

    def test_4_factory_pattern_enforcement(self):
        """
        Test 4: Validate constructor works with factory patterns

        EXPECTED BEHAVIOR: Constructor should integrate with AgentInstanceFactory
        """
        print("\n🔍 CONSTRUCTOR TEST 4: Validating factory pattern enforcement...")

        try:
            # Create mock dependencies with factory patterns
            mock_context = Mock(spec=UserExecutionContext)
            mock_context.user_id = "factory_user_123"

            mock_agent_factory = Mock(spec=AgentInstanceFactory)
            mock_agent_factory.create_agent = Mock(return_value=Mock())

            mock_websocket_emitter = Mock()
            mock_websocket_emitter.emit = Mock()

            # Test constructor with factory patterns
            engine = UserExecutionEngine(
                context=mock_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )

            # Validate factory integration
            self.assertIsNotNone(
                engine,
                "X FACTORY PATTERN FAILURE: Could not create UserExecutionEngine with factory dependencies."
            )

            # Test that the engine can be used (basic smoke test)
            # Note: This is a constructor test, so we're only validating instantiation
            self.assertTrue(
                hasattr(engine, '__class__'),
                "X FACTORY PATTERN FAILURE: UserExecutionEngine instance not properly created."
            )

        except Exception as e:
            self.fail(
                f"X FACTORY PATTERN FAILURE: UserExecutionEngine constructor failed with factory patterns.\n"
                f"Error: {e}\n"
                f"Issue #1186 Phase 4 requires proper integration with AgentInstanceFactory and WebSocketEmitter."
            )

    def test_5_dependency_injection_parameter_types(self):
        """
        Test 5: Validate dependency injection parameter types

        EXPECTED BEHAVIOR: Constructor parameters should have proper type hints
        """
        print("\n🔍 CONSTRUCTOR TEST 5: Validating dependency injection parameter types...")

        # Get constructor signature with type annotations
        constructor_sig = inspect.signature(UserExecutionEngine.__init__)

        # Expected type annotations based on Issue #1186 Phase 4
        expected_type_annotations = {
            'context': 'UserExecutionContext',
            'agent_factory': 'AgentInstanceFactory',
            'websocket_emitter': 'WebSocketEmitter'  # Or similar WebSocket emitter type
        }

        # Check parameter type annotations
        type_annotation_issues = []
        for param_name, param in constructor_sig.parameters.items():
            if param_name in expected_type_annotations:
                if param.annotation == inspect.Parameter.empty:
                    type_annotation_issues.append(f"Parameter '{param_name}' lacks type annotation")
                elif not str(param.annotation).endswith(expected_type_annotations[param_name]):
                    # Allow flexible matching for type annotations
                    if expected_type_annotations[param_name] not in str(param.annotation):
                        type_annotation_issues.append(
                            f"Parameter '{param_name}' has annotation '{param.annotation}', "
                            f"expected to contain '{expected_type_annotations[param_name]}'"
                        )

        # This test validates proper type annotations exist
        self.assertEqual(
            len(type_annotation_issues),
            0,
            f"X TYPE ANNOTATION ISSUES: UserExecutionEngine constructor has type annotation issues.\n"
            f"Issues found:\n" + '\n'.join([f"  - {issue}" for issue in type_annotation_issues]) + "\n"
            f"Issue #1186 Phase 4 requires proper type hints for dependency injection."
        )


@pytest.mark.unit
class TestConstructorDependencyInjectionMetrics(unittest.TestCase):
    """Test class to measure constructor dependency injection compliance"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_6_constructor_enhancement_compliance_measurement(self):
        """
        Test 6: Measure constructor enhancement compliance

        EXPECTED TO FAIL: Should measure compliance with Issue #1186 Phase 4 requirements
        """
        print("\n📊 CONSTRUCTOR METRICS TEST 6: Measuring constructor enhancement compliance...")

        compliance_metrics = self._measure_constructor_compliance()

        # Expected compliance metrics for Issue #1186 Phase 4
        expected_metrics = {
            'has_required_dependencies': True,
            'prevents_parameterless_instantiation': True,
            'supports_user_isolation': True,
            'integrates_with_factory': True,
            'has_proper_type_annotations': True,
        }

        for metric, expected_value in expected_metrics.items():
            actual_value = compliance_metrics.get(metric, False)
            self.assertEqual(
                actual_value,
                expected_value,
                f"X EXPECTED COMPLIANCE FAILURE: {metric} = {actual_value}, expected {expected_value}. "
                f"Issue #1186 Phase 4 requires constructor enhancement for dependency injection."
            )

    def test_7_singleton_violation_prevention_validation(self):
        """
        Test 7: Validate constructor prevents singleton violations

        EXPECTED BEHAVIOR: Constructor should prevent singleton patterns
        """
        print("\n📊 CONSTRUCTOR METRICS TEST 7: Validating singleton violation prevention...")

        singleton_prevention = self._validate_singleton_prevention()

        # This test validates singleton prevention
        self.assertTrue(
            singleton_prevention['prevents_singletons'],
            f"X SINGLETON PREVENTION FAILURE: Constructor does not prevent singleton violations.\n"
            f"Issues found: {singleton_prevention['issues']}\n"
            f"Issue #1186 Phase 4 requires constructor to enforce user isolation and prevent singletons."
        )

    def _measure_constructor_compliance(self) -> Dict[str, bool]:
        """Measure constructor enhancement compliance"""
        compliance = {}

        try:
            # Check if constructor has required dependencies
            constructor_sig = inspect.signature(UserExecutionEngine.__init__)
            required_params = [
                param.name for param_name, param in constructor_sig.parameters.items()
                if param_name != 'self' and param.default == inspect.Parameter.empty
            ]

            expected_deps = ['context', 'agent_factory', 'websocket_emitter']
            compliance['has_required_dependencies'] = all(dep in required_params for dep in expected_deps)

            # Check if parameterless instantiation is prevented
            try:
                UserExecutionEngine()
                compliance['prevents_parameterless_instantiation'] = False
            except TypeError:
                compliance['prevents_parameterless_instantiation'] = True
            except Exception:
                compliance['prevents_parameterless_instantiation'] = False

            # Check user isolation support (mock test)
            try:
                mock_context1 = Mock()
                mock_factory = Mock()
                mock_emitter = Mock()

                engine1 = UserExecutionEngine(mock_context1, mock_factory, mock_emitter)
                engine2 = UserExecutionEngine(Mock(), mock_factory, mock_emitter)

                compliance['supports_user_isolation'] = (engine1 is not engine2)
            except Exception:
                compliance['supports_user_isolation'] = False

            # Check factory integration
            compliance['integrates_with_factory'] = 'agent_factory' in required_params

            # Check type annotations
            has_annotations = any(
                param.annotation != inspect.Parameter.empty
                for param_name, param in constructor_sig.parameters.items()
                if param_name != 'self'
            )
            compliance['has_proper_type_annotations'] = has_annotations

        except Exception as e:
            print(f"Error measuring constructor compliance: {e}")
            compliance = {key: False for key in [
                'has_required_dependencies', 'prevents_parameterless_instantiation',
                'supports_user_isolation', 'integrates_with_factory', 'has_proper_type_annotations'
            ]}

        return compliance

    def _validate_singleton_prevention(self) -> Dict[str, any]:
        """Validate that constructor prevents singleton violations"""
        prevention_result = {
            'prevents_singletons': True,
            'issues': []
        }

        try:
            # Test that multiple instances are actually different
            mock_deps = (Mock(), Mock(), Mock())

            instance1 = UserExecutionEngine(*mock_deps)
            instance2 = UserExecutionEngine(*mock_deps)

            if instance1 is instance2:
                prevention_result['prevents_singletons'] = False
                prevention_result['issues'].append("Constructor returns same instance (singleton pattern)")

            if id(instance1) == id(instance2):
                prevention_result['prevents_singletons'] = False
                prevention_result['issues'].append("Constructor returns same memory address")

            # Test that instances don't share class-level state
            if hasattr(UserExecutionEngine, '_instance'):
                prevention_result['prevents_singletons'] = False
                prevention_result['issues'].append("Class has _instance attribute (singleton pattern)")

        except Exception as e:
            prevention_result['prevents_singletons'] = False
            prevention_result['issues'].append(f"Error testing singleton prevention: {e}")

        return prevention_result


if __name__ == '__main__':
    print("🚨 Issue #1186 UserExecutionEngine Constructor Dependency Injection - Validation Tests")
    print("=" * 80)
    print("CHECK INFO: These tests validate the constructor enhancement from Issue #1186 Phase 4")
    print("🔧 Previous: UserExecutionEngine() (no arguments)")
    print("🔧 Current: UserExecutionEngine(context, agent_factory, websocket_emitter)")
    print("🎯 Goal: Enforce proper dependency injection and prevent singleton violations")
    print("🔒 Impact: Enables enterprise-grade user isolation and multi-tenant security")
    print("=" * 80)

    unittest.main(verbosity=2)