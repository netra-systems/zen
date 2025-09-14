"""
Test file for Issue #914: Reproduce SSOT violations in duplicate AgentRegistry classes.

This test file is designed to FAIL and expose the SSOT violations caused by
having two different AgentRegistry implementations:
1. Basic registry at /netra_backend/app/agents/registry.py
2. Advanced registry at /netra_backend/app/agents/supervisor/agent_registry.py

Business Impact: $500K+ ARR chat functionality is compromised by import confusion
and inconsistent registry behavior.

Expected Behavior:
- BEFORE CONSOLIDATION: Tests in this file should FAIL due to SSOT violations
- AFTER CONSOLIDATION: Tests should PASS with single authoritative registry

Test Categories:
- Import conflict detection
- Functionality inconsistency detection
- WebSocket integration mismatch
- User isolation capability gaps
"""

import pytest
import asyncio
import sys
import importlib
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

# Import the test framework
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
except ImportError:
    # Fallback for environments where SSOT test framework is not available
    import unittest
    SSotAsyncTestCase = unittest.TestCase

from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentRegistrySSotViolations(SSotAsyncTestCase):
    """Test class to reproduce and validate SSOT violations in AgentRegistry classes."""

    def setUp(self):
        """Set up test environment."""
        super().setUp() if hasattr(super(), 'setUp') else None

        self.user_context = UserExecutionContext(
            user_id="test_ssot_violation_user",
            request_id="test_ssot_request",
            thread_id="test_ssot_thread",
            run_id="test_ssot_run"
        )

        # Clear any cached modules to ensure fresh imports
        modules_to_clear = [
            'netra_backend.app.agents.registry',
            'netra_backend.app.agents.supervisor.agent_registry'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

    def test_duplicate_class_names_detected(self):
        """
        Test that both AgentRegistry implementations exist with the same name.

        EXPECTED: This test should PASS (both classes exist)
        PURPOSE: Confirms the SSOT violation exists
        """
        try:
            # Import basic registry
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            basic_registry = BasicRegistry()

            # Import advanced registry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            advanced_registry = AdvancedRegistry()

            # Verify both exist but are different classes
            self.assertNotEqual(type(basic_registry), type(advanced_registry))
            self.assertEqual(type(basic_registry).__name__, "AgentRegistry")
            self.assertEqual(type(advanced_registry).__name__, "AgentRegistry")

            # Both have same name but different capabilities
            self.assertTrue(hasattr(basic_registry, 'register_agent'))
            self.assertTrue(hasattr(advanced_registry, 'register_agent'))

            # But advanced has user isolation features basic lacks
            self.assertFalse(hasattr(basic_registry, 'get_user_session'))
            self.assertTrue(hasattr(advanced_registry, 'get_user_session'))

            print("✅ SSOT VIOLATION DETECTED: Two AgentRegistry classes with same name but different capabilities")

        except ImportError as e:
            self.fail(f"Could not import both AgentRegistry classes: {e}")

    def test_import_path_confusion(self):
        """
        Test that import paths create developer confusion.

        EXPECTED: This test should HIGHLIGHT confusion
        PURPOSE: Shows the import path problem
        """
        basic_import_path = "netra_backend.app.agents.registry"
        advanced_import_path = "netra_backend.app.agents.supervisor.agent_registry"

        try:
            # Import via basic path
            basic_module = importlib.import_module(basic_import_path)
            BasicRegistryClass = getattr(basic_module, 'AgentRegistry')

            # Import via advanced path
            advanced_module = importlib.import_module(advanced_import_path)
            AdvancedRegistryClass = getattr(advanced_module, 'AgentRegistry')

            # Create instances
            basic_instance = BasicRegistryClass()
            advanced_instance = AdvancedRegistryClass()

            # Test capability differences
            basic_methods = set(dir(basic_instance))
            advanced_methods = set(dir(advanced_instance))

            # Advanced should have user isolation methods that basic lacks
            user_isolation_methods = {
                'get_user_session', 'cleanup_user_session', 'create_agent_for_user',
                'monitor_all_users', 'emergency_cleanup_all', 'set_websocket_manager_async'
            }

            basic_has_isolation = user_isolation_methods.intersection(basic_methods)
            advanced_has_isolation = user_isolation_methods.intersection(advanced_methods)

            # This shows the SSOT violation - same name, different capabilities
            self.assertEqual(len(basic_has_isolation), 0, "Basic registry should not have user isolation")
            self.assertGreater(len(advanced_has_isolation), 4, "Advanced registry should have user isolation")

            print(f"🚨 IMPORT CONFUSION: Basic registry missing {len(user_isolation_methods)} user isolation methods")
            print(f"📊 Capability Gap: {user_isolation_methods - basic_methods}")

        except Exception as e:
            self.fail(f"Import path test failed: {e}")

    def test_websocket_integration_inconsistency(self):
        """
        Test that WebSocket integration differs between registries.

        EXPECTED: This test should FAIL due to inconsistent WebSocket support
        PURPOSE: Exposes WebSocket integration SSOT violation
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Mock WebSocket manager
            mock_websocket_manager = Mock()
            mock_websocket_manager.create_bridge = Mock(return_value=Mock())

            # Test basic registry WebSocket capabilities
            basic_websocket_methods = [
                method for method in dir(basic_registry)
                if 'websocket' in method.lower()
            ]

            # Test advanced registry WebSocket capabilities
            advanced_websocket_methods = [
                method for method in dir(advanced_registry)
                if 'websocket' in method.lower()
            ]

            print(f"Basic registry WebSocket methods: {basic_websocket_methods}")
            print(f"Advanced registry WebSocket methods: {advanced_websocket_methods}")

            # Advanced should have more WebSocket integration
            self.assertGreater(len(advanced_websocket_methods), len(basic_websocket_methods))

            # Test setting WebSocket manager
            if hasattr(basic_registry, 'set_websocket_manager'):
                basic_registry.set_websocket_manager(mock_websocket_manager)

            if hasattr(advanced_registry, 'set_websocket_manager'):
                advanced_registry.set_websocket_manager(mock_websocket_manager)

            # Advanced should have async WebSocket support
            self.assertTrue(hasattr(advanced_registry, 'set_websocket_manager_async'))
            self.assertFalse(hasattr(basic_registry, 'set_websocket_manager_async'))

            print("🚨 WEBSOCKET SSOT VIOLATION: Inconsistent WebSocket integration between registries")

        except Exception as e:
            self.fail(f"WebSocket integration test failed: {e}")

    async def test_user_isolation_capability_gap(self):
        """
        Test that user isolation is only available in advanced registry.

        EXPECTED: This test should FAIL for basic registry
        PURPOSE: Exposes user isolation SSOT violation critical for Golden Path
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            test_user_id = "test_user_isolation"

            # Test basic registry - should not support user isolation
            with self.assertRaises(AttributeError):
                # This should fail - basic registry has no user isolation
                await basic_registry.get_user_session(test_user_id)

            # Test advanced registry - should support user isolation
            try:
                user_session = await advanced_registry.get_user_session(test_user_id)
                self.assertIsNotNone(user_session)
                self.assertEqual(user_session.user_id, test_user_id)

                # Cleanup
                await advanced_registry.cleanup_user_session(test_user_id)

            except Exception as e:
                self.fail(f"Advanced registry user isolation failed: {e}")

            print("🚨 USER ISOLATION SSOT VIOLATION: Basic registry cannot support multi-user scenarios")
            print("💰 BUSINESS IMPACT: $500K+ ARR at risk due to missing user isolation in basic registry")

        except ImportError as e:
            self.fail(f"Could not test user isolation: {e}")

    def test_factory_pattern_inconsistency(self):
        """
        Test that factory patterns differ between registries.

        EXPECTED: This test should HIGHLIGHT factory pattern differences
        PURPOSE: Shows agent creation SSOT violation
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Check factory-related methods
            basic_factory_methods = [
                method for method in dir(basic_registry)
                if 'factory' in method.lower() or 'create' in method.lower()
            ]

            advanced_factory_methods = [
                method for method in dir(advanced_registry)
                if 'factory' in method.lower() or 'create' in method.lower()
            ]

            print(f"Basic registry factory methods: {basic_factory_methods}")
            print(f"Advanced registry factory methods: {advanced_factory_methods}")

            # Advanced should have more sophisticated factory patterns
            self.assertGreater(len(advanced_factory_methods), len(basic_factory_methods))

            # Advanced should have user-specific agent creation
            self.assertTrue(hasattr(advanced_registry, 'create_agent_for_user'))
            self.assertFalse(hasattr(basic_registry, 'create_agent_for_user'))

            # Advanced should have tool dispatcher factory
            self.assertTrue(hasattr(advanced_registry, 'create_tool_dispatcher_for_user'))
            self.assertFalse(hasattr(basic_registry, 'create_tool_dispatcher_for_user'))

            print("🚨 FACTORY PATTERN SSOT VIOLATION: Inconsistent agent creation patterns")

        except Exception as e:
            self.fail(f"Factory pattern test failed: {e}")

    def test_inheritance_hierarchy_difference(self):
        """
        Test that inheritance hierarchies differ between registries.

        EXPECTED: This test should PASS and show inheritance differences
        PURPOSE: Documents the inheritance SSOT violation
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Get inheritance hierarchies
            basic_mro = type(basic_registry).__mro__
            advanced_mro = type(advanced_registry).__mro__

            basic_hierarchy = [cls.__name__ for cls in basic_mro]
            advanced_hierarchy = [cls.__name__ for cls in advanced_mro]

            print(f"Basic registry MRO: {basic_hierarchy}")
            print(f"Advanced registry MRO: {advanced_hierarchy}")

            # They should have different inheritance chains
            self.assertNotEqual(basic_hierarchy, advanced_hierarchy)

            # Advanced should inherit from BaseAgentRegistry
            advanced_parent_names = [cls.__name__ for cls in advanced_mro[1:]]  # Exclude self
            self.assertIn('BaseAgentRegistry', advanced_parent_names,
                         "Advanced registry should inherit from BaseAgentRegistry")

            # Basic should have simpler inheritance
            basic_parent_names = [cls.__name__ for cls in basic_mro[1:]]  # Exclude self
            self.assertNotIn('BaseAgentRegistry', basic_parent_names,
                           "Basic registry should not inherit from BaseAgentRegistry")

            print("🚨 INHERITANCE SSOT VIOLATION: Different inheritance hierarchies for same-named class")

        except Exception as e:
            self.fail(f"Inheritance hierarchy test failed: {e}")

    def test_line_count_and_complexity_gap(self):
        """
        Test that line counts show significant complexity differences.

        EXPECTED: This test should PASS and show complexity gap
        PURPOSE: Quantifies the SSOT violation magnitude
        """
        import inspect

        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            # Get source lines for comparison
            basic_source = inspect.getsource(BasicRegistry)
            advanced_source = inspect.getsource(AdvancedRegistry)

            basic_lines = len(basic_source.split('\n'))
            advanced_lines = len(advanced_source.split('\n'))

            print(f"Basic registry lines: {basic_lines}")
            print(f"Advanced registry lines: {advanced_lines}")

            # Advanced should be significantly larger
            complexity_ratio = advanced_lines / basic_lines if basic_lines > 0 else float('inf')

            print(f"Complexity ratio (Advanced/Basic): {complexity_ratio:.2f}")

            # Advanced should be at least 3x more complex
            self.assertGreater(complexity_ratio, 3.0,
                             "Advanced registry should be significantly more complex")

            # Get method counts
            basic_methods = len([method for method in dir(BasicRegistry())
                               if not method.startswith('_')])
            advanced_methods = len([method for method in dir(AdvancedRegistry())
                                  if not method.startswith('_')])

            print(f"Basic registry public methods: {basic_methods}")
            print(f"Advanced registry public methods: {advanced_methods}")

            method_ratio = advanced_methods / basic_methods if basic_methods > 0 else float('inf')
            print(f"Method ratio (Advanced/Basic): {method_ratio:.2f}")

            self.assertGreater(method_ratio, 1.5,
                             "Advanced registry should have significantly more methods")

            print("📊 COMPLEXITY SSOT VIOLATION: Same class name with vastly different implementations")
            print(f"💥 IMPACT: Developers cannot predict capabilities from class name alone")

        except Exception as e:
            self.fail(f"Complexity analysis failed: {e}")

    def test_golden_path_compatibility_mismatch(self):
        """
        Test that Golden Path compatibility differs between registries.

        EXPECTED: This test should FAIL for basic registry
        PURPOSE: Exposes Golden Path SSOT violation ($500K+ ARR impact)
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Golden Path requirements checklist
            golden_path_requirements = [
                'set_websocket_manager',      # WebSocket integration
                'create_agent_for_user',      # User-specific agents
                'cleanup_user_session',       # Memory management
                'monitor_all_users',          # System monitoring
                'get_user_session',           # User isolation
                'emergency_cleanup_all'       # System stability
            ]

            basic_coverage = 0
            advanced_coverage = 0
            missing_from_basic = []

            for requirement in golden_path_requirements:
                if hasattr(basic_registry, requirement):
                    basic_coverage += 1
                else:
                    missing_from_basic.append(requirement)

                if hasattr(advanced_registry, requirement):
                    advanced_coverage += 1

            basic_percentage = (basic_coverage / len(golden_path_requirements)) * 100
            advanced_percentage = (advanced_coverage / len(golden_path_requirements)) * 100

            print(f"Basic registry Golden Path coverage: {basic_percentage:.1f}%")
            print(f"Advanced registry Golden Path coverage: {advanced_percentage:.1f}%")
            print(f"Basic registry missing: {missing_from_basic}")

            # This is the CRITICAL SSOT violation
            self.assertLess(basic_percentage, 50.0,
                          "Basic registry inadequate for Golden Path")
            self.assertGreater(advanced_percentage, 80.0,
                             "Advanced registry should support Golden Path")

            print("🚨 CRITICAL: GOLDEN PATH SSOT VIOLATION DETECTED")
            print("💰 BUSINESS IMPACT: Basic registry cannot support $500K+ ARR chat functionality")
            print("🎯 GOLDEN PATH BLOCKED: User login → AI response flow compromised")

        except Exception as e:
            self.fail(f"Golden Path compatibility test failed: {e}")


# Standalone test execution for immediate validation
if __name__ == '__main__':
    import unittest

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentRegistrySSotViolations)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("ISSUE #914 SSOT VIOLATION TEST RESULTS")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFAILURES (Expected - these show SSOT violations):")
        for test, failure in result.failures:
            print(f"- {test}: {failure}")

    if result.errors:
        print("\nERRORS:")
        for test, error in result.errors:
            print(f"- {test}: {error}")

    print("\n🎯 NEXT: Run remaining 6 test files to complete SSOT violation analysis")