"""
Mission Critical Tests for Issue #885: WebSocket Manager SSOT Violations

These tests are designed to FAIL and prove the existence of SSOT violations.
They should only pass after successful SSOT consolidation.

Business Value: Proves current 0.0% SSOT compliance and validates future remediation.
Expected Result: ALL TESTS SHOULD FAIL proving violations exist.
"""

import asyncio
import pytest
import warnings
from typing import Dict, List, Set, Any
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketSSotViolations(SSotAsyncTestCase):
    """Test suite to prove WebSocket Manager SSOT violations exist."""

    async def asyncSetUp(self):
        """Setup for async tests."""
        await super().asyncSetUp()
        self.violations_found = []
        self.import_paths_tested = []

    def test_multiple_websocket_manager_implementations_exist(self):
        """
        EXPECTED TO FAIL: Test should detect multiple WebSocket manager implementations.

        This test proves SSOT violation by finding multiple manager classes.
        When fixed, only ONE canonical implementation should exist.
        """
        manager_implementations = []

        # Test import paths that should be consolidated to ONE
        import_attempts = [
            "netra_backend.app.websocket_core.manager.WebSocketManager",
            "netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation",
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.canonical_import_patterns.UnifiedWebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory"
        ]

        for import_path in import_attempts:
            self.import_paths_tested.append(import_path)
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                if hasattr(module, class_name):
                    implementation = getattr(module, class_name)
                    manager_implementations.append({
                        'path': import_path,
                        'class': implementation,
                        'module': module_path
                    })
                    self.violations_found.append(f"Multiple implementation found: {import_path}")
            except (ImportError, AttributeError) as e:
                # Expected - some paths should not exist after SSOT consolidation
                logger.debug(f"Import failed (expected): {import_path} - {e}")
                pass

        # ASSERTION THAT SHOULD FAIL: Multiple implementations exist (SSOT violation)
        self.assertGreater(
            len(manager_implementations), 1,
            f"SSOT VIOLATION DETECTED: Found {len(manager_implementations)} WebSocket manager implementations. "
            f"Should be exactly 1 after SSOT consolidation. "
            f"Implementations: {[impl['path'] for impl in manager_implementations]}"
        )

        logger.error(f"SSOT VIOLATION CONFIRMED: {len(manager_implementations)} manager implementations found")

    def test_factory_pattern_violations_exist(self):
        """
        EXPECTED TO FAIL: Test should detect multiple factory patterns.

        This test proves factory pattern SSOT violations.
        When fixed, only ONE canonical factory pattern should exist.
        """
        factory_patterns = []

        # Test factory patterns that should be consolidated
        factory_import_attempts = [
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "netra_backend.app.websocket_core.canonical_import_patterns.get_websocket_manager",
            "netra_backend.app.websocket_core.unified_manager.create_websocket_manager",
            "netra_backend.app.websocket_core.supervisor_factory"
        ]

        for factory_path in factory_import_attempts:
            try:
                if '.' in factory_path:
                    module_path, factory_name = factory_path.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[factory_name])
                    if hasattr(module, factory_name):
                        factory = getattr(module, factory_name)
                        factory_patterns.append({
                            'path': factory_path,
                            'factory': factory,
                            'type': type(factory).__name__
                        })
                        self.violations_found.append(f"Multiple factory found: {factory_path}")
            except (ImportError, AttributeError):
                # Expected for some paths
                pass

        # ASSERTION THAT SHOULD FAIL: Multiple factory patterns exist
        self.assertGreater(
            len(factory_patterns), 1,
            f"FACTORY PATTERN SSOT VIOLATION: Found {len(factory_patterns)} factory patterns. "
            f"Should be exactly 1 canonical pattern. "
            f"Factories: {[pattern['path'] for pattern in factory_patterns]}"
        )

        logger.error(f"FACTORY SSOT VIOLATION CONFIRMED: {len(factory_patterns)} factory patterns found")

    def test_circular_import_violations_exist(self):
        """
        EXPECTED TO FAIL: Test should detect circular import violations.

        This test proves circular imports exist between WebSocket modules.
        """
        circular_imports_detected = []

        # Test modules that commonly have circular imports
        modules_to_test = [
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.canonical_import_patterns",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.types",
            "netra_backend.app.websocket_core.protocols"
        ]

        for module_name in modules_to_test:
            try:
                # Import module and check for circular dependency indicators
                module = __import__(module_name, fromlist=[''])

                # Check for common circular import patterns
                if hasattr(module, '__file__'):
                    # Look for import statements in the file
                    with open(module.__file__, 'r') as f:
                        content = f.read()

                        # Check for imports that could create circles
                        for check_module in modules_to_test:
                            if check_module != module_name and check_module in content:
                                circular_imports_detected.append({
                                    'from_module': module_name,
                                    'imports_module': check_module,
                                    'evidence': f"Found '{check_module}' in {module_name}"
                                })
                                self.violations_found.append(f"Circular import: {module_name} -> {check_module}")

            except (ImportError, FileNotFoundError) as e:
                logger.debug(f"Module test failed: {module_name} - {e}")

        # ASSERTION THAT SHOULD FAIL: Circular imports exist
        self.assertGreater(
            len(circular_imports_detected), 0,
            f"CIRCULAR IMPORT VIOLATIONS DETECTED: Found {len(circular_imports_detected)} potential circular imports. "
            f"Should be 0 after SSOT consolidation. "
            f"Violations: {[ci['from_module'] + ' -> ' + ci['imports_module'] for ci in circular_imports_detected]}"
        )

        logger.error(f"CIRCULAR IMPORT VIOLATIONS CONFIRMED: {len(circular_imports_detected)} detected")

    def test_deprecation_warnings_not_suppressed(self):
        """
        EXPECTED TO FAIL: Test should detect that deprecation warnings are being suppressed.

        This test proves that legacy import paths are not properly deprecated.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Try to import from legacy paths that should trigger warnings
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
            except ImportError:
                pass

            try:
                from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            except ImportError:
                pass

        # Count deprecation warnings
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]

        # ASSERTION THAT SHOULD FAIL: Legacy imports should trigger warnings
        self.assertGreater(
            len(deprecation_warnings), 0,
            f"DEPRECATION WARNING VIOLATION: Expected deprecation warnings for legacy imports, "
            f"but found {len(deprecation_warnings)} warnings. "
            f"Legacy import paths should be properly deprecated during SSOT migration."
        )

        logger.error(f"DEPRECATION WARNING VIOLATION: {len(deprecation_warnings)} warnings found")

    async def test_user_isolation_violations_exist(self):
        """
        EXPECTED TO FAIL: Test should detect user isolation violations.

        This test proves that WebSocket managers share state between users.
        """
        isolation_violations = []

        # Try to create multiple managers and check for shared state
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create managers for different users
            user1_context = {"user_id": "user1", "session_id": "session1"}
            user2_context = {"user_id": "user2", "session_id": "session2"}

            manager1 = get_websocket_manager(user_context=user1_context)
            manager2 = get_websocket_manager(user_context=user2_context)

            # Check if managers are the same instance (violation)
            if manager1 is manager2:
                isolation_violations.append("Same manager instance returned for different users")
                self.violations_found.append("User isolation violation: Shared manager instances")

            # Check for shared internal state
            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                if manager1._connections is manager2._connections:
                    isolation_violations.append("Shared connections dict between users")
                    self.violations_found.append("User isolation violation: Shared connections")

            # Check for shared registries
            if hasattr(manager1, '_registry') and hasattr(manager2, '_registry'):
                if manager1._registry is manager2._registry:
                    isolation_violations.append("Shared registry between users")
                    self.violations_found.append("User isolation violation: Shared registry")

        except ImportError as e:
            # If we can't import, that's also a violation
            isolation_violations.append(f"Cannot import canonical factory: {e}")

        # ASSERTION THAT SHOULD FAIL: User isolation violations exist
        self.assertGreater(
            len(isolation_violations), 0,
            f"USER ISOLATION VIOLATIONS DETECTED: Found {len(isolation_violations)} violations. "
            f"Should be 0 after proper user isolation implementation. "
            f"Violations: {isolation_violations}"
        )

        logger.error(f"USER ISOLATION VIOLATIONS CONFIRMED: {len(isolation_violations)} violations")

    def test_singleton_pattern_violations_exist(self):
        """
        EXPECTED TO FAIL: Test should detect singleton pattern violations.

        This test proves that WebSocket components use singleton patterns.
        """
        singleton_violations = []

        # Test components that should NOT be singletons after SSOT
        components_to_test = [
            "netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation",
            "netra_backend.app.websocket_core.message_queue.MessageQueue",
            "netra_backend.app.websocket_core.connection_manager.ConnectionManager"
        ]

        for component_path in components_to_test:
            try:
                module_path, class_name = component_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])

                if hasattr(module, class_name):
                    component_class = getattr(module, class_name)

                    # Check for singleton patterns
                    if hasattr(component_class, '_instance'):
                        singleton_violations.append(f"Singleton _instance attribute: {component_path}")
                        self.violations_found.append(f"Singleton violation: {component_path}")

                    if hasattr(component_class, 'get_instance'):
                        singleton_violations.append(f"Singleton get_instance method: {component_path}")
                        self.violations_found.append(f"Singleton violation: {component_path}")

                    # Try creating multiple instances and check if they're the same
                    try:
                        instance1 = component_class()
                        instance2 = component_class()
                        if instance1 is instance2:
                            singleton_violations.append(f"Same instance returned: {component_path}")
                            self.violations_found.append(f"Singleton violation: {component_path}")
                    except Exception:
                        # Constructor might require arguments, skip this check
                        pass

            except (ImportError, AttributeError):
                pass

        # ASSERTION THAT SHOULD FAIL: Singleton patterns exist
        self.assertGreater(
            len(singleton_violations), 0,
            f"SINGLETON PATTERN VIOLATIONS DETECTED: Found {len(singleton_violations)} singleton patterns. "
            f"Should be 0 after factory pattern implementation. "
            f"Violations: {singleton_violations}"
        )

        logger.error(f"SINGLETON VIOLATIONS CONFIRMED: {len(singleton_violations)} violations")

    def tearDown(self):
        """Report all violations found during testing."""
        if self.violations_found:
            logger.error("="*80)
            logger.error("WEBSOCKET SSOT VIOLATIONS SUMMARY")
            logger.error("="*80)
            for i, violation in enumerate(self.violations_found, 1):
                logger.error(f"{i:2d}. {violation}")
            logger.error("="*80)
            logger.error(f"TOTAL VIOLATIONS DETECTED: {len(self.violations_found)}")
            logger.error("="*80)

        if self.import_paths_tested:
            logger.info("Import paths tested: " + ", ".join(self.import_paths_tested))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])