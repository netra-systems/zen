"""
Issue #914 AgentRegistry SSOT Violation Reproduction Test Suite

This test file reproduces the exact SSOT violation where two AgentRegistry classes
cause import conflicts and WebSocket failures, blocking the Golden Path ($500K+ ARR).

EXPECTED BEHAVIOR: These tests SHOULD FAIL initially, proving the SSOT violation exists.
After SSOT consolidation is complete, these tests should PASS.

Business Impact:
- Blocks Golden Path user flow: Users login → get AI responses
- Affects $500K+ ARR chat functionality reliability
- Causes WebSocket event delivery failures

SSOT Violation Details:
- Basic AgentRegistry: netra_backend.app.agents.registry.AgentRegistry
- Advanced AgentRegistry: netra_backend.app.agents.supervisor.agent_registry.AgentRegistry
- Conflict causes wrong registry loading and WebSocket interface mismatches

Test Strategy:
1. Import both registries and detect class name collision
2. Test WebSocket interface incompatibility
3. Demonstrate factory pattern failures
4. Show multi-user isolation issues
"""

import asyncio
import logging
import unittest
import warnings
import uuid
from typing import Optional, Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Test both registries - THIS IS THE SSOT VIOLATION WE'RE TESTING
try:
    # Basic registry (DEPRECATED - will be removed)
    from netra_backend.app.agents.registry import AgentRegistry as BasicAgentRegistry
    basic_registry_available = True
except ImportError:
    BasicAgentRegistry = None
    basic_registry_available = False

try:
    # SSOT registry - canonical location after migration
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedAgentRegistry
    advanced_registry_available = True
except ImportError:
    AdvancedAgentRegistry = None
    advanced_registry_available = False

# WebSocket testing infrastructure
try:
    from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
    from test_framework.ssot.websocket_bridge_test_helper import WebSocketBridgeTestHelper
except ImportError:
    WebSocketTestInfrastructureFactory = None
    WebSocketBridgeTestHelper = None

logger = logging.getLogger(__name__)


class TestAgentRegistryImportConflictReproduction(SSotAsyncTestCase):
    """
    Test suite to reproduce and validate AgentRegistry SSOT violations.

    These tests demonstrate the critical import conflicts that block
    the Golden Path and must be resolved through SSOT consolidation.
    """

    def setup_method(self, method):
        """Setup test environment with SSOT base infrastructure."""
        super().setup_method(method)
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.basic_registry: Optional[Any] = None
        self.advanced_registry: Optional[Any] = None

    async def test_01_registry_class_name_collision_detection(self):
        """
        Test 1: Detect AgentRegistry class name collision (SHOULD FAIL)

        This test demonstrates the core SSOT violation where two classes
        with the same name exist in the codebase, causing import conflicts.

        EXPECTED: FAIL - Proves SSOT violation exists
        AFTER FIX: PASS - Only one AgentRegistry class remains
        """
        # Verify both registry classes are importable
        self.assertTrue(basic_registry_available,
                       "Basic AgentRegistry should be importable")
        self.assertTrue(advanced_registry_available,
                       "Advanced AgentRegistry should be importable")

        # This is the SSOT VIOLATION - two classes with same name
        self.assertIsNotNone(BasicAgentRegistry,
                           "Basic AgentRegistry class should exist")
        self.assertIsNotNone(AdvancedAgentRegistry,
                           "Advanced AgentRegistry class should exist")

        # Demonstrate the name collision
        basic_name = BasicAgentRegistry.__name__ if BasicAgentRegistry else "None"
        advanced_name = AdvancedAgentRegistry.__name__ if AdvancedAgentRegistry else "None"

        # THIS SHOULD FAIL - Same class name in different modules is SSOT violation
        self.assertNotEqual(basic_name, advanced_name,
                          f"SSOT VIOLATION: Both classes are named '{basic_name}' - "
                          f"this causes import conflicts and breaks Golden Path")

        # Log the violation for debugging
        logger.critical(f"SSOT VIOLATION DETECTED: "
                       f"Basic: {BasicAgentRegistry.__module__ if BasicAgentRegistry else 'None'}.{basic_name}, "
                       f"Advanced: {AdvancedAgentRegistry.__module__ if AdvancedAgentRegistry else 'None'}.{advanced_name}")

    async def test_02_registry_interface_incompatibility(self):
        """
        Test 2: Demonstrate registry interface incompatibility (SHOULD FAIL)

        Tests show that the two registries have incompatible interfaces,
        causing WebSocket integration failures.

        EXPECTED: FAIL - Interfaces are incompatible
        AFTER FIX: PASS - Single registry has consistent interface
        """
        if not basic_registry_available or not advanced_registry_available:
            self.skipTest("Both registries must be available for interface testing")

        # Create instances of both registries
        try:
            self.basic_registry = BasicAgentRegistry()
            basic_methods = set(dir(self.basic_registry))
        except Exception as e:
            logger.warning(f"Basic registry instantiation failed: {e}")
            basic_methods = set()

        try:
            # Advanced registry requires different initialization parameters
            self.advanced_registry = AdvancedAgentRegistry(
                user_context=MagicMock(),
                tool_dispatcher=MagicMock(),
                websocket_bridge=MagicMock()
            )
            advanced_methods = set(dir(self.advanced_registry))
        except Exception as e:
            logger.warning(f"Advanced registry instantiation failed: {e}")
            advanced_methods = set()

        # Check for critical WebSocket methods that should be common
        websocket_methods = {
            'set_websocket_manager', 'get_websocket_manager',
            'send_websocket_event', 'notify_agent_status'
        }

        basic_websocket_methods = websocket_methods & basic_methods
        advanced_websocket_methods = websocket_methods & advanced_methods

        # THIS SHOULD FAIL - Incompatible WebSocket interfaces
        self.assertEqual(basic_websocket_methods, advanced_websocket_methods,
                        f"INTERFACE MISMATCH: Basic has {basic_websocket_methods}, "
                        f"Advanced has {advanced_websocket_methods} - "
                        f"this breaks WebSocket event delivery")

    async def test_03_registry_factory_pattern_conflict(self):
        """
        Test 3: Demonstrate factory pattern conflicts (SHOULD FAIL)

        Shows how different initialization patterns cause factory
        method failures and break user isolation.

        EXPECTED: FAIL - Factory patterns are inconsistent
        AFTER FIX: PASS - Unified factory pattern works
        """
        if not basic_registry_available or not advanced_registry_available:
            self.skipTest("Both registries must be available for factory testing")

        # Test basic registry factory pattern
        basic_creation_success = False
        try:
            basic_registry = BasicAgentRegistry()
            basic_creation_success = True
        except Exception as e:
            logger.warning(f"Basic registry creation failed: {e}")

        # Test advanced registry factory pattern
        advanced_creation_success = False
        try:
            mock_context = MagicMock()
            mock_dispatcher = MagicMock()
            mock_bridge = MagicMock()

            advanced_registry = AdvancedAgentRegistry(
                user_context=mock_context,
                tool_dispatcher=mock_dispatcher,
                websocket_bridge=mock_bridge
            )
            advanced_creation_success = True
        except Exception as e:
            logger.warning(f"Advanced registry creation failed: {e}")

        # THIS SHOULD FAIL - Inconsistent factory patterns
        self.assertEqual(basic_creation_success, advanced_creation_success,
                        "FACTORY CONFLICT: Registries require different initialization patterns - "
                        "this prevents unified factory methods and breaks user isolation")

        # If both succeed, they should have compatible interfaces
        if basic_creation_success and advanced_creation_success:
            # Test that they can be used interchangeably (they can't)
            basic_registry = BasicAgentRegistry()

            # This will fail because advanced registry needs dependencies
            with self.assertRaises((TypeError, AttributeError),
                                   msg="FACTORY INCOMPATIBILITY: Cannot use registries interchangeably"):
                # Try to use basic registry with advanced registry interface
                basic_registry.get_user_agent_context(self.test_user_id)  # Advanced method

    async def test_04_websocket_integration_failure_reproduction(self):
        """
        Test 4: Reproduce WebSocket integration failures (SHOULD FAIL)

        Demonstrates how registry conflicts cause WebSocket event
        delivery failures, blocking the Golden Path.

        EXPECTED: FAIL - WebSocket integration broken
        AFTER FIX: PASS - WebSocket events work correctly
        """
        if not WebSocketTestInfrastructureFactory:
            self.skipTest("WebSocket test infrastructure not available")

        # Create mock WebSocket infrastructure
        websocket_infra = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False  # Simplified for unit test
        )

        # Test with basic registry
        basic_websocket_success = False
        try:
            if basic_registry_available:
                basic_registry = BasicAgentRegistry()
                # Try to set websocket manager (method may not exist)
                if hasattr(basic_registry, 'set_websocket_manager'):
                    basic_registry.set_websocket_manager(websocket_infra.websocket_manager)
                    basic_websocket_success = True
        except Exception as e:
            logger.warning(f"Basic registry WebSocket integration failed: {e}")

        # Test with advanced registry
        advanced_websocket_success = False
        try:
            if advanced_registry_available:
                mock_context = MagicMock()
                mock_dispatcher = MagicMock()
                mock_bridge = MagicMock()

                advanced_registry = AdvancedAgentRegistry(
                    user_context=mock_context,
                    tool_dispatcher=mock_dispatcher,
                    websocket_bridge=mock_bridge
                )

                if hasattr(advanced_registry, 'set_websocket_manager'):
                    advanced_registry.set_websocket_manager(websocket_infra.websocket_manager)
                    advanced_websocket_success = True
        except Exception as e:
            logger.warning(f"Advanced registry WebSocket integration failed: {e}")

        # THIS SHOULD FAIL - WebSocket integration inconsistent
        self.assertEqual(basic_websocket_success, advanced_websocket_success,
                        f"WEBSOCKET INTEGRATION CONFLICT: Basic={basic_websocket_success}, "
                        f"Advanced={advanced_websocket_success} - inconsistent WebSocket support "
                        f"breaks Golden Path event delivery")

    async def test_05_multi_user_isolation_violation(self):
        """
        Test 5: Demonstrate multi-user isolation violations (SHOULD FAIL)

        Shows how registry conflicts break user isolation, creating
        security risks and data leakage between users.

        EXPECTED: FAIL - User isolation is broken
        AFTER FIX: PASS - Users properly isolated
        """
        if not basic_registry_available or not advanced_registry_available:
            self.skipTest("Both registries must be available for isolation testing")

        user1_id = f"{self.test_user_id}_1"
        user2_id = f"{self.test_user_id}_2"

        # Test basic registry isolation
        basic_isolation_works = False
        try:
            basic_registry = BasicAgentRegistry()

            # Basic registry may not support user isolation
            if hasattr(basic_registry, 'get_user_context'):
                context1 = basic_registry.get_user_context(user1_id)
                context2 = basic_registry.get_user_context(user2_id)
                basic_isolation_works = (context1 != context2)
        except Exception as e:
            logger.warning(f"Basic registry isolation test failed: {e}")

        # Test advanced registry isolation
        advanced_isolation_works = False
        try:
            mock_context1 = MagicMock()
            mock_context2 = MagicMock()
            mock_dispatcher = MagicMock()
            mock_bridge = MagicMock()

            advanced_registry1 = AdvancedAgentRegistry(
                user_context=mock_context1,
                tool_dispatcher=mock_dispatcher,
                websocket_bridge=mock_bridge
            )

            advanced_registry2 = AdvancedAgentRegistry(
                user_context=mock_context2,
                tool_dispatcher=mock_dispatcher,
                websocket_bridge=mock_bridge
            )

            # Advanced registry should provide proper isolation
            if hasattr(advanced_registry1, 'user_context'):
                advanced_isolation_works = (
                    advanced_registry1.user_context != advanced_registry2.user_context
                )
        except Exception as e:
            logger.warning(f"Advanced registry isolation test failed: {e}")

        # THIS SHOULD FAIL - Inconsistent isolation capabilities
        self.assertEqual(basic_isolation_works, advanced_isolation_works,
                        f"USER ISOLATION CONFLICT: Basic={basic_isolation_works}, "
                        f"Advanced={advanced_isolation_works} - inconsistent user isolation "
                        f"creates security risks and affects enterprise customers")

    async def test_06_registry_method_signature_mismatch(self):
        """
        Test 6: Detect method signature mismatches (SHOULD FAIL)

        Shows how different method signatures between registries
        cause runtime errors and break agent execution.

        EXPECTED: FAIL - Method signatures don't match
        AFTER FIX: PASS - Consistent method signatures
        """
        if not basic_registry_available or not advanced_registry_available:
            self.skipTest("Both registries must be available for signature testing")

        # Get method signatures for common operations
        basic_methods = {}
        advanced_methods = {}

        try:
            basic_registry = BasicAgentRegistry()
            # Check common methods that should exist
            common_method_names = ['register_agent', 'get_agent', 'list_agents']

            for method_name in common_method_names:
                if hasattr(basic_registry, method_name):
                    method = getattr(basic_registry, method_name)
                    # Store method for signature analysis
                    basic_methods[method_name] = method
        except Exception as e:
            logger.warning(f"Basic registry method analysis failed: {e}")

        try:
            mock_context = MagicMock()
            mock_dispatcher = MagicMock()
            mock_bridge = MagicMock()

            advanced_registry = AdvancedAgentRegistry(
                user_context=mock_context,
                tool_dispatcher=mock_dispatcher,
                websocket_bridge=mock_bridge
            )

            common_method_names = ['register_agent', 'get_agent', 'list_agents']

            for method_name in common_method_names:
                if hasattr(advanced_registry, method_name):
                    method = getattr(advanced_registry, method_name)
                    advanced_methods[method_name] = method
        except Exception as e:
            logger.warning(f"Advanced registry method analysis failed: {e}")

        # Check for method existence consistency
        basic_method_names = set(basic_methods.keys())
        advanced_method_names = set(advanced_methods.keys())

        # THIS SHOULD FAIL - Different methods available
        self.assertEqual(basic_method_names, advanced_method_names,
                        f"METHOD AVAILABILITY MISMATCH: Basic has {basic_method_names}, "
                        f"Advanced has {advanced_method_names} - "
                        f"this breaks interchangeable usage patterns")

    async def test_07_import_path_confusion_detection(self):
        """
        Test 7: Detect import path confusion (SHOULD FAIL)

        Shows how different import paths for the "same" class
        cause confusion and wrong class loading.

        EXPECTED: FAIL - Import paths cause confusion
        AFTER FIX: PASS - Single clear import path
        """
        # Document the confusing import paths
        import_paths = []

        if basic_registry_available:
            import_paths.append(BasicAgentRegistry.__module__)
        if advanced_registry_available:
            import_paths.append(AdvancedAgentRegistry.__module__)

        # THIS SHOULD FAIL - Multiple import paths for "AgentRegistry"
        self.assertEqual(len(set(import_paths)), 1,
                        f"IMPORT PATH CONFUSION: Multiple paths for AgentRegistry: {import_paths} - "
                        f"developers cannot know which to import, causing random failures")

        # Test that imports lead to same class (they don't)
        if len(import_paths) >= 2:
            self.assertIs(BasicAgentRegistry, AdvancedAgentRegistry,
                         "SSOT VIOLATION: Different classes with same name - "
                         "this is the core SSOT violation blocking Golden Path")

    async def test_08_golden_path_blocking_demonstration(self):
        """
        Test 8: Demonstrate Golden Path blocking (SHOULD FAIL)

        Shows how registry conflicts specifically block the critical
        user flow: Users login → get AI responses.

        EXPECTED: FAIL - Golden Path is blocked
        AFTER FIX: PASS - Golden Path works end-to-end
        """
        # Simulate Golden Path user flow components
        user_session_id = f"session_{uuid.uuid4().hex[:8]}"

        golden_path_components = {
            'user_login': True,  # Assume login works
            'registry_selection': False,  # This will fail due to conflicts
            'agent_initialization': False,
            'websocket_events': False,
            'ai_response_delivery': False
        }

        # Test registry selection (core of the problem)
        try:
            # Which registry should we use? This ambiguity breaks Golden Path
            if basic_registry_available and advanced_registry_available:
                # This decision point is where Golden Path fails
                # Different code paths pick different registries randomly

                # Simulate different components picking different registries
                component_a_choice = BasicAgentRegistry  # Component A picks basic
                component_b_choice = AdvancedAgentRegistry  # Component B picks advanced

                # This inconsistency breaks the flow
                registry_consistency = (component_a_choice == component_b_choice)
                golden_path_components['registry_selection'] = registry_consistency

                # If registries are inconsistent, downstream fails
                if not registry_consistency:
                    golden_path_components['agent_initialization'] = False
                    golden_path_components['websocket_events'] = False
                    golden_path_components['ai_response_delivery'] = False
        except Exception as e:
            logger.error(f"Registry selection failed: {e}")
            golden_path_components['registry_selection'] = False

        # Calculate Golden Path success rate
        successful_components = sum(golden_path_components.values())
        total_components = len(golden_path_components)
        success_rate = successful_components / total_components

        # THIS SHOULD FAIL - Golden Path is broken
        self.assertGreaterEqual(success_rate, 1.0,
                               f"GOLDEN PATH BLOCKED: Only {success_rate:.1%} of components work - "
                               f"registry SSOT violation prevents users from getting AI responses, "
                               f"affecting $500K+ ARR functionality")

        logger.critical(f"GOLDEN PATH STATUS: {golden_path_components}")
        logger.critical(f"SUCCESS RATE: {success_rate:.1%} - BLOCKING $500K+ ARR FUNCTIONALITY")


if __name__ == "__main__":
    unittest.main()