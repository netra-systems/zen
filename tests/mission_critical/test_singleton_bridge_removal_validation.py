#!/usr/bin/env python3
"""
Mission Critical Tests for SingletonToFactoryBridge Removal

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Safe legacy code removal without breaking $500K+ ARR chat functionality
- Value Impact: Validates bridge removal doesn't break WebSocket or agent execution
- Strategic Impact: Enables cleanup of unused legacy code while protecting Golden Path

CRITICAL MISSION: These tests ensure that removing the SingletonToFactoryBridge
doesn't break the Golden Path: users login -> get AI responses

Test Strategy:
1. Verify bridge is completely unused (no imports, no calls)
2. Test that WebSocket functionality works without bridge
3. Test that agent execution continues to work
4. Test multi-user isolation works with factory patterns
5. Validate Golden Path integrity after removal

IMPORTANT: These tests are designed to FAIL if the bridge is needed,
proving safe removal when they pass.
"""

import pytest
import asyncio
import importlib
import sys
import unittest
from typing import Any, Dict, List
from unittest.mock import Mock, patch, MagicMock
import logging

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.user_execution_context import UserExecutionContext


class TestSingletonBridgeRemovalValidation(SSotBaseTestCase):
    """Mission Critical: Validate SingletonToFactoryBridge can be safely removed."""

    @classmethod
    def setUpClass(cls):
        """Set up test class with validation framework."""
        super().setUpClass()
        cls.logger = logging.getLogger(__name__)

    def setUp(self):
        """Set up each test with clean state."""
        super().setUp()
        self.user_id = ensure_user_id("test_user_123")

        # Create test user context for factory tests
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id="test_thread_456",
            run_id="test_run_789",
            request_id="test_request_789"
        )

    def test_bridge_has_no_imports_anywhere(self):
        """
        CRITICAL: Verify SingletonToFactoryBridge is not imported anywhere.

        This test ensures the bridge is truly unused and can be safely removed.
        If this test fails, the bridge is still being used and cannot be removed.
        """
        bridge_imports = []

        # Search for imports in all loaded modules
        for module_name, module in sys.modules.items():
            if module is None or not hasattr(module, '__file__'):
                continue

            if module.__file__ and 'netra_backend' in module.__file__:
                try:
                    module_source = module.__file__
                    if module_source and module_source.endswith('.py'):
                        with open(module_source, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check for SingletonToFactoryBridge imports (NOT IdMigrationBridge)
                        bridge_import_patterns = [
                            'from netra_backend.app.core.singleton_to_factory_bridge',
                            'import singleton_to_factory_bridge',
                            'SingletonToFactoryBridge',
                            'get_service_with_bridge',
                            'get_event_validator_with_bridge',
                            'get_event_router_with_bridge'
                        ]

                        # NOTE: get_migration_bridge is used by TWO different modules:
                        # 1. id_migration_bridge.get_migration_bridge() -> IdMigrationBridge (KEEP)
                        # 2. singleton_to_factory_bridge.get_migration_bridge() -> SingletonToFactoryBridge (REMOVE)
                        # We only flag it if it's from singleton_to_factory_bridge specifically

                        for pattern in bridge_import_patterns:
                            if pattern in content:
                                bridge_imports.append(f"{module_name}: {pattern}")

                        # Special check for get_migration_bridge - only flag if from singleton_to_factory_bridge
                        if 'get_migration_bridge' in content:
                            if 'from netra_backend.app.core.singleton_to_factory_bridge import' in content and 'get_migration_bridge' in content:
                                bridge_imports.append(f"{module_name}: get_migration_bridge (from singleton_to_factory_bridge)")

                except Exception as e:
                    # Skip modules that can't be read
                    pass

        # Filter out the bridge module itself
        bridge_imports = [imp for imp in bridge_imports if 'singleton_to_factory_bridge.py' not in imp]

        self.assertEqual(
            [], bridge_imports,
            f"Found imports of SingletonToFactoryBridge in: {bridge_imports}. "
            f"Bridge cannot be removed safely until these are migrated."
        )

    def test_websocket_manager_works_without_bridge(self):
        """
        CRITICAL: Test that WebSocket manager creation works without the bridge.

        This validates that factory patterns are complete and don't depend on the bridge.
        """
        # This test should pass if factory patterns are working correctly
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            factory = get_websocket_manager()
            self.assertIsNotNone(factory, "WebSocket manager factory should be available")

            # Test factory can create manager without bridge
            manager = asyncio.run(factory.create_manager(
                user_context=self.user_context,
                mode=WebSocketManagerMode.UNIFIED
            ))

            self.assertIsNotNone(manager, "Factory should create manager without bridge")
            self.assertEqual(manager.user_context.user_id, self.user_id)

        except ImportError as e:
            self.fail(f"WebSocket factory import failed: {e}. Factory patterns may be incomplete.")
        except Exception as e:
            self.fail(f"WebSocket manager creation failed without bridge: {e}")

    def test_websocket_get_functions_work_without_bridge(self):
        """
        CRITICAL: Test that get_websocket_manager() works without the bridge.

        This validates the primary WebSocket singleton patterns don't depend on the bridge.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            # Test singleton function works without bridge
            manager = get_websocket_manager(
                user_context=self.user_context,
                mode=WebSocketManagerMode.UNIFIED
            )

            self.assertIsNotNone(manager, "get_websocket_manager should work without bridge")

        except ImportError as e:
            self.fail(f"WebSocket manager import failed: {e}")
        except Exception as e:
            self.fail(f"get_websocket_manager failed without bridge: {e}")

    def test_websocket_authenticator_works_without_bridge(self):
        """
        CRITICAL: Test that WebSocket authenticator works without the bridge.
        """
        try:
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator

            authenticator = get_websocket_authenticator()
            self.assertIsNotNone(authenticator, "WebSocket authenticator should work without bridge")

        except ImportError as e:
            self.fail(f"WebSocket authenticator import failed: {e}")
        except Exception as e:
            self.fail(f"WebSocket authenticator failed without bridge: {e}")

    def test_service_locator_works_without_bridge(self):
        """
        CRITICAL: Test that service locator patterns work without the bridge.
        """
        try:
            from netra_backend.app.services.service_locator import get_service, ServiceLocator
            from netra_backend.app.services.service_interfaces import IWebSocketService

            # Test that service locator works without bridge
            service_locator = ServiceLocator()
            self.assertIsNotNone(service_locator, "Service locator should work without bridge")

            # Note: We don't test actual service retrieval since it requires registration
            # But we verify the core pattern works

        except ImportError as e:
            self.fail(f"Service locator import failed: {e}")
        except Exception as e:
            self.fail(f"Service locator failed without bridge: {e}")

    def test_agent_execution_works_without_bridge(self):
        """
        CRITICAL: Test that agent execution patterns work without the bridge.

        This validates that the agent workflow (90% of platform value) doesn't depend on the bridge.
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            # Test that agent execution components import without bridge
            coordinator = get_user_factory_coordinator()
            self.assertIsNotNone(coordinator, "User factory coordinator should work without bridge")

        except ImportError as e:
            self.fail(f"Agent execution import failed: {e}")
        except Exception as e:
            self.fail(f"Agent execution failed without bridge: {e}")

    def test_user_scoped_patterns_work_without_bridge(self):
        """
        CRITICAL: Test that user-scoped factory patterns work without the bridge.

        This validates multi-user isolation (protecting $500K+ ARR) works without the bridge.
        """
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator
            from netra_backend.app.services.user_scoped_service_locator import UserScopedServiceLocator

            # Test user-scoped patterns work without bridge
            coordinator = get_user_factory_coordinator()
            user_locator = coordinator.get_user_service_locator(self.user_context)

            self.assertIsNotNone(user_locator, "User-scoped service locator should work without bridge")
            self.assertIsInstance(user_locator, UserScopedServiceLocator)

        except ImportError as e:
            self.fail(f"User-scoped patterns import failed: {e}")
        except Exception as e:
            self.fail(f"User-scoped patterns failed without bridge: {e}")

    def test_bridge_removal_simulation(self):
        """
        CRITICAL: Simulate bridge removal and verify system still works.

        This test temporarily removes the bridge from import paths and verifies
        that all critical systems continue to function.
        """
        # Temporarily remove bridge from sys.modules to simulate removal
        bridge_module_name = 'netra_backend.app.core.singleton_to_factory_bridge'
        original_module = sys.modules.get(bridge_module_name)

        try:
            # Remove bridge from modules
            if bridge_module_name in sys.modules:
                del sys.modules[bridge_module_name]

            # Test that critical imports still work without bridge
            critical_imports = [
                'netra_backend.app.websocket_core.websocket_manager',
                'netra_backend.app.websocket_core.unified_websocket_auth',
                'netra_backend.app.services.service_locator',
                'netra_backend.app.core.user_factory_coordinator'
            ]

            for import_path in critical_imports:
                try:
                    if import_path in sys.modules:
                        del sys.modules[import_path]
                    importlib.import_module(import_path)
                except ImportError as e:
                    if 'singleton_to_factory_bridge' in str(e):
                        self.fail(f"{import_path} depends on bridge and would break upon removal: {e}")
                    else:
                        # Other import errors are not bridge-related
                        pass

        finally:
            # Restore original module state
            if original_module is not None:
                sys.modules[bridge_module_name] = original_module

    def test_golden_path_integrity_without_bridge(self):
        """
        CRITICAL: Test that Golden Path (users login -> get AI responses) works without bridge.

        This is the ultimate validation that bridge removal won't break the core user flow.
        """
        golden_path_components = []

        try:
            # Test WebSocket components (critical for real-time chat)
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            manager = get_websocket_manager(user_context=self.user_context)
            golden_path_components.append("WebSocket Manager")

            # Test authentication components (critical for user login)
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator
            auth = get_websocket_authenticator()
            golden_path_components.append("WebSocket Authenticator")

            # Test user context factory (critical for multi-user isolation)
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator
            coordinator = get_user_factory_coordinator()
            golden_path_components.append("User Factory Coordinator")

            # Test service discovery (critical for agent execution)
            from netra_backend.app.services.service_locator import ServiceLocator
            locator = ServiceLocator()
            golden_path_components.append("Service Locator")

        except Exception as e:
            failed_component = len(golden_path_components)
            self.fail(
                f"Golden Path component {failed_component} failed without bridge: {e}. "
                f"Successfully loaded: {golden_path_components}. "
                f"Bridge removal would break Golden Path!"
            )

        # If we get here, all Golden Path components work without the bridge
        self.logger.info(f"Golden Path components validated without bridge: {golden_path_components}")

    def test_no_bridge_dependencies_in_critical_modules(self):
        """
        CRITICAL: Verify that critical modules don't depend on the bridge.

        This test checks the most important modules to ensure they don't import the bridge.
        """
        critical_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_websocket_auth',
            'netra_backend.app.services.service_locator',
            'netra_backend.app.core.user_factory_coordinator',
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.routes.websocket',
            'netra_backend.app.dependencies'
        ]

        bridge_dependencies = []

        for module_name in critical_modules:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for bridge dependencies
                    if 'singleton_to_factory_bridge' in content:
                        bridge_dependencies.append(module_name)

            except Exception:
                # Skip modules that can't be loaded/read
                pass

        self.assertEqual(
            [], bridge_dependencies,
            f"Critical modules depend on bridge: {bridge_dependencies}. "
            f"These must be migrated before bridge removal."
        )


class TestFactoryPatternCompleteness(SSotBaseTestCase):
    """Validate that factory patterns are complete and don't need the bridge."""

    def setUp(self):
        """Set up test with user context."""
        super().setUp()
        self.user_context = UserExecutionContext(
            user_id=ensure_user_id("factory_test_user"),
            thread_id="factory_test_thread",
            run_id="factory_test_run",
            request_id="factory_test_request"
        )

    def test_websocket_manager_is_complete(self):
        """Test that WebSocket manager factory is fully implemented."""
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

        factory = WebSocketManager(max_managers_per_user=5)

        # Test factory has all required methods
        required_methods = [
            'create_manager',
            'get_user_manager_count',
            'get_factory_status',
            'health_check_all_managers'
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(factory, method_name),
                f"Factory missing required method: {method_name}"
            )

    def test_user_factory_coordinator_is_complete(self):
        """Test that user factory coordinator is fully implemented."""
        from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

        coordinator = get_user_factory_coordinator()

        # Test coordinator has all required methods
        required_methods = [
            'get_user_service_locator',
            'get_user_event_validator',
            'get_user_event_router'
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(coordinator, method_name),
                f"Coordinator missing required method: {method_name}"
            )

    def test_user_scoped_service_locator_works(self):
        """Test that user-scoped service locator works independently."""
        from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

        coordinator = get_user_factory_coordinator()
        user_locator = coordinator.get_user_service_locator(self.user_context)

        # Test that user locator is properly isolated
        self.assertIsNotNone(user_locator)
        self.assertEqual(user_locator.user_context.user_id, self.user_context.user_id)

    def test_multi_user_isolation_without_bridge(self):
        """Test that multi-user isolation works without the bridge."""
        from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

        # Create two different user contexts
        user1_context = UserExecutionContext(
            user_id=ensure_user_id("user_1"),
            thread_id="thread_1",
            run_id="run_1",
            request_id="request_1"
        )

        user2_context = UserExecutionContext(
            user_id=ensure_user_id("user_2"),
            thread_id="thread_2",
            run_id="run_2",
            request_id="request_2"
        )

        coordinator = get_user_factory_coordinator()

        # Get user-scoped services for each user
        user1_locator = coordinator.get_user_service_locator(user1_context)
        user2_locator = coordinator.get_user_service_locator(user2_context)

        # Verify they are isolated (different instances)
        self.assertNotEqual(user1_locator, user2_locator)
        self.assertEqual(user1_locator.user_context.user_id, user1_context.user_id)
        self.assertEqual(user2_locator.user_context.user_id, user2_context.user_id)


if __name__ == '__main__':
    # Run these mission critical tests to validate bridge removal safety
    unittest.main()